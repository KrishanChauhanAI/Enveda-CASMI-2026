"""Stage 2 utilities: load, validate, and characterize CASMI parquet files.

Development version: 0.1.0 | 2026-11-19 00:00 UTC (stage implementation date)
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

REQUIRED_TEST_COLUMNS = {"molecule_id", "precursor_mz", "ms2_mzs", "ms2_normalized_intensities"}


# Load a parquet file with a useful error message if the optional parquet engine is absent.
def load_parquet(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Could not find {path}. Place test.parquet there or pass --test.")
    try:
        return pd.read_parquet(path)
    except ImportError as exc:
        raise RuntimeError("Reading parquet requires pyarrow or fastparquet; install requirements.txt.") from exc


# Check schema, identifiers, precursor values, and paired spectral-array integrity.
def validate_frame(frame: pd.DataFrame, label: str, is_test: bool) -> dict[str, Any]:
    errors: list[str] = []
    required = REQUIRED_TEST_COLUMNS | ({"normalized_smiles"} if not is_test else set())
    missing = sorted(required - set(frame.columns))
    if missing:
        errors.append(f"missing required columns: {missing}")
    if "molecule_id" in frame:
        if frame["molecule_id"].isna().any():
            errors.append("molecule_id contains nulls")
        # Repeated IDs may be legitimate replicate spectra; report their count instead of rejecting them.
    # Row-level scans are robust to parquet list columns being represented as Python lists or arrays.
    bad_pairs = 0
    bad_precursor = 0
    if {"ms2_mzs", "ms2_normalized_intensities"}.issubset(frame.columns):
        for mzs, intensities in zip(frame["ms2_mzs"], frame["ms2_normalized_intensities"]):
            try:
                a, b = np.asarray(mzs, dtype=float), np.asarray(intensities, dtype=float)
                if a.ndim != 1 or b.ndim != 1 or len(a) != len(b) or not np.isfinite(a).all() or not np.isfinite(b).all() or (a < 0).any() or (b < 0).any():
                    bad_pairs += 1
            except (TypeError, ValueError):
                bad_pairs += 1
        if bad_pairs:
            errors.append(f"{bad_pairs} rows have malformed/nonfinite/negative or unpaired peak arrays")
    if "precursor_mz" in frame:
        p = pd.to_numeric(frame["precursor_mz"], errors="coerce")
        bad_precursor = int((~np.isfinite(p) | (p <= 0)).sum())
        if bad_precursor:
            errors.append(f"{bad_precursor} rows have invalid precursor_mz")
    report = {
        "label": label,
        "rows": int(len(frame)),
        "columns": {str(c): str(t) for c, t in frame.dtypes.items()},
        "missing_by_column": {str(k): int(v) for k, v in frame.isna().sum().items()},
        "unique_molecules": int(frame["molecule_id"].nunique()) if "molecule_id" in frame else None,
        "duplicate_molecule_rows": int(frame["molecule_id"].duplicated().sum()) if "molecule_id" in frame else None,
        "median_peaks": float(np.median([len(x) if isinstance(x, (list, tuple, np.ndarray)) else 0 for x in frame["ms2_mzs"]])) if "ms2_mzs" in frame and len(frame) else None,
        "errors": errors,
    }
    return report


# Summarize relevant fields and create compact composite EDA plots without modifying the source data.
def make_eda(frame: pd.DataFrame, output_dir: Path, label: str) -> dict[str, Any]:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import seaborn as sns

    output_dir.mkdir(parents=True, exist_ok=True)
    report = validate_frame(frame, label, is_test=("normalized_smiles" not in frame.columns))
    if "precursor_mz" in frame:
        precursor = pd.to_numeric(frame["precursor_mz"], errors="coerce").dropna()
        peak_counts = frame["ms2_mzs"].map(lambda x: len(x) if isinstance(x, (list, tuple, np.ndarray)) else 0) if "ms2_mzs" in frame else pd.Series(dtype=int)
        fig, ax = plt.subplots(1, 2, figsize=(12, 4.4))
        if len(precursor):
            sns.histplot(precursor, bins=50, ax=ax[0], color="#187c78")
            ax[0].set(title="Precursor m/z distribution", xlabel="precursor m/z", ylabel="spectra")
        if len(peak_counts):
            sns.histplot(peak_counts, bins=40, ax=ax[1], color="#da7b35")
            ax[1].set(title="Peaks per spectrum", xlabel="number of peaks", ylabel="spectra")
        fig.suptitle(f"{label}: data coverage and spectrum size")
        fig.tight_layout()
        fig.savefig(output_dir / f"{label.lower()}_overview.png", dpi=150)
        plt.close(fig)
    if "adduct" in frame:
        report["adduct_counts"] = frame["adduct"].value_counts(dropna=False).head(30).to_dict()
    if "collision_energy" in frame:
        report["collision_energy_summary"] = pd.to_numeric(frame["collision_energy"], errors="coerce").describe().to_dict()
    return report


# Run an auditable test-only or train-and-test data audit from the command line.
def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--test", type=Path, default=Path("data/test.parquet"))
    parser.add_argument("--train", type=Path, default=None, help="Optional; full train file is not required for test EDA")
    parser.add_argument("--out", type=Path, default=Path("artifacts/stage2_eda"))
    args = parser.parse_args()
    paths = [("test", args.test, True)]
    if args.train:
        paths.insert(0, ("train", args.train, False))
    all_reports = []
    for label, path, is_test in paths:
        frame = load_parquet(path)
        report = make_eda(frame, args.out, label)
        report["errors"].extend(validate_frame(frame, label, is_test)["errors"])
        all_reports.append(report)
        print(json.dumps(report, indent=2, default=str))
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "audit.json").write_text(json.dumps(all_reports, indent=2, default=str))
    if any(report["errors"] for report in all_reports):
        raise SystemExit("Audit found schema/data errors; see printed report and audit.json")


if __name__ == "__main__":
    main()
