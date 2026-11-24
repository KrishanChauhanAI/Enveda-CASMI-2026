"""Streaming Task 1 EDA for Enveda CASMI parquet files.

Version 1.0.0 | 2026-11-19 UTC. Works in Colab/local Python; scans large train parquet in batches.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
import pyarrow.parquet as pq


# Scan a parquet file in bounded-memory batches and calculate schema, null, group, category and peak summaries.
def scan_parquet(path: Path, sample_rows: int = 100_000, batch_size: int = 25_000, seed: int = 42) -> tuple[dict[str, Any], Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Parquet file not found: {path}")
    parquet = pq.ParquetFile(path)
    schema = parquet.schema_arrow
    nulls = Counter()
    categories: dict[str, Counter] = {name: Counter() for name in ("ingest_lib", "adduct", "ionization_mode", "instrument_type", "collision_energy_orig_units")}
    molecule_ids: set[str] = set()
    n_rows = 0
    seen_rows = 0
    peak_counts: list[int] = []
    precursor_values: list[float] = []
    sample_batches = []
    rng = np.random.default_rng(seed)
    selected = [n for n in schema.names if n in {"molecule_id", "spectrum_id", "ms2_mzs", "ms2_normalized_intensities", "precursor_mz", "base_peak_intensity", "collision_energy_ev", "collision_energy_orig", "collision_energy_orig_units", "adduct", "ionization_mode", "instrument_type", "ingest_lib", "normalized_smiles", "inchikey14", "molecular_formula", "precursor_error_ppm", "num_peaks"}]
    for batch in parquet.iter_batches(batch_size=batch_size, columns=selected, use_threads=True):
        frame = batch.to_pandas()
        n_rows += len(frame)
        for name in frame.columns:
            nulls[name] += int(frame[name].isna().sum())
        if "molecule_id" in frame:
            molecule_ids.update(frame["molecule_id"].dropna().astype(str).unique())
        for col, counts in categories.items():
            if col in frame:
                counts.update(frame[col].fillna("<NULL>").astype(str).value_counts().to_dict())
        mz_col = "ms2_mzs" if "ms2_mzs" in frame else None
        if mz_col:
            vals = frame[mz_col].map(lambda x: len(x) if isinstance(x, (list, tuple, np.ndarray)) else 0).to_numpy(dtype=np.int32)
            peak_counts.extend(vals.tolist())
            if len(peak_counts) > sample_rows:
                peak_counts[:] = np.asarray(peak_counts)[rng.choice(len(peak_counts), sample_rows, replace=False)].tolist()
        if "precursor_mz" in frame:
            p = frame["precursor_mz"].to_numpy(dtype=float, na_value=np.nan)
            precursor_values.extend(p[np.isfinite(p)].tolist())
            if len(precursor_values) > sample_rows:
                precursor_values[:] = np.asarray(precursor_values)[rng.choice(len(precursor_values), sample_rows, replace=False)].tolist()
        if sample_rows > 0:
            # Reservoir sampling gives each scanned spectrum equal probability while bounding sample memory.
            for record in frame.to_dict("records"):
                seen_rows += 1
                if len(sample_batches) < sample_rows:
                    sample_batches.append(record)
                else:
                    j = int(rng.integers(0, seen_rows))
                    if j < sample_rows:
                        sample_batches[j] = record
    report = {
        "file": str(path), "rows": n_rows, "unique_molecules": len(molecule_ids),
        "columns": [{"name": field.name, "type": str(field.type), "nullable": field.nullable} for field in schema],
        "null_count": dict(nulls),
        "category_counts": {col: counts.most_common(40) for col, counts in categories.items() if counts},
        "precursor_mz_quantiles": np.quantile(precursor_values, [0, .01, .25, .5, .75, .99, 1]).tolist() if precursor_values else [],
        "peaks_per_spectrum_quantiles": np.quantile(peak_counts, [0, .25, .5, .75, .95, .99, 1]).tolist() if peak_counts else [],
        "sample_rows": len(sample_batches),
    }
    import pandas as pd
    return report, pd.DataFrame.from_records(sample_batches)


# Create composite overview plots that answer concrete questions about coverage and train-test domain shift.
def plot_eda(train_sample: Any | None, test_sample: Any | None, output: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import pandas as pd
    import seaborn as sns

    output.parent.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(2, 3, figsize=(16, 9))
    pairs = [("train", train_sample), ("test", test_sample)]
    for name, frame in pairs:
        if frame is None:
            continue
        if "precursor_mz" in frame:
            sns.histplot(pd.to_numeric(frame.precursor_mz, errors="coerce"), bins=50, stat="density", element="step", fill=False, ax=axes[0, 0], label=name)
        if "ms2_mzs" in frame:
            peak_n = frame.ms2_mzs.map(lambda x: len(x) if isinstance(x, (list, tuple, np.ndarray)) else 0)
            sns.histplot(peak_n, bins=40, element="step", fill=False, ax=axes[0, 1], label=name)
        if "collision_energy_ev" in frame:
            energy = frame.collision_energy_ev.map(lambda x: x if isinstance(x, (list, tuple, np.ndarray)) else [x] if pd.notna(x) else [])
            flat = [float(v) for row in energy for v in row if pd.notna(v)]
            if flat:
                sns.histplot(flat, bins=30, element="step", fill=False, ax=axes[0, 2], label=name)
    axes[0, 0].set(title="Precursor m/z (domain shift)", xlabel="m/z")
    axes[0, 1].set(title="Peaks per spectrum", xlabel="peak count")
    axes[0, 2].set(title="Collision energy (eV)", xlabel="eV")
    for ax in axes[0]:
        if ax.get_legend_handles_labels()[0]: ax.legend()
    if train_sample is not None and "ingest_lib" in train_sample:
        train_sample.ingest_lib.fillna("<NULL>").value_counts().head(12).sort_values().plot.barh(ax=axes[1, 0], color="#237c78")
        axes[1, 0].set(title="Training sources (sample)", xlabel="rows")
    else:
        axes[1, 0].axis("off")
    if train_sample is not None and "adduct" in train_sample:
        train_sample.adduct.fillna("<NULL>").value_counts().head(12).plot.bar(ax=axes[1, 1], color="#dd8c36")
        axes[1, 1].tick_params(axis="x", rotation=65)
        axes[1, 1].set(title="Training adducts (sample)", ylabel="rows")
    else:
        axes[1, 1].axis("off")
    if train_sample is not None and "instrument_type" in train_sample:
        train_sample.instrument_type.fillna("<NULL>").value_counts().head(12).sort_values().plot.barh(ax=axes[1, 2], color="#7859a6")
        axes[1, 2].set(title="Training instruments (sample)", xlabel="rows")
    else:
        axes[1, 2].axis("off")
    fig.suptitle("CASMI Task 1 — dataset coverage and acquisition heterogeneity")
    fig.tight_layout()
    fig.savefig(output, dpi=160)
    plt.close(fig)


# Run streaming EDA for a test file and optionally the large training file, then save reusable reports and figures.
def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--test", type=Path, required=True)
    parser.add_argument("--train", type=Path)
    parser.add_argument("--out", type=Path, default=Path("artifacts/task1"))
    parser.add_argument("--sample-rows", type=int, default=100_000)
    parser.add_argument("--batch-size", type=int, default=25_000)
    args = parser.parse_args()
    reports = {}
    samples = {}
    for name, path in (("train", args.train), ("test", args.test)):
        if path is not None:
            reports[name], samples[name] = scan_parquet(path, args.sample_rows, args.batch_size)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "data_dictionary_and_quality.json").write_text(json.dumps(reports, indent=2, default=str))
    plot_eda(samples.get("train"), samples.get("test"), args.out / "composite_eda.png")
    print(json.dumps({k: {"rows": v["rows"], "unique_molecules": v["unique_molecules"], "columns": [x["name"] for x in v["columns"]]} for k, v in reports.items()}, indent=2))


if __name__ == "__main__":
    main()
