"""Streaming Task 1 EDA for Enveda CASMI parquet files.

Version 1.2.0 | 2026-11-19 UTC. Adds exact all-row histogram aggregates; point samples remain display-only views.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
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
    spectra_per_molecule: Counter = Counter()
    n_rows = 0
    seen_rows = 0
    peak_counts: list[int] = []
    precursor_values: list[float] = []
    sample_batches = []
    # Full-file histogram accumulators; these are exact over all rows and avoid retaining nested peaks.
    histogram_edges = {
        "precursor_mz": np.linspace(0, 2000, 101),
        "peak_count": np.linspace(0, 40000, 101),
        "log10_base_peak_intensity": np.linspace(0, 10, 101),
        "collision_energy_ev": np.linspace(-100, 500, 121),
    }
    histogram_counts = {key: np.zeros(len(edges) - 1, dtype=np.int64) for key, edges in histogram_edges.items()}
    histogram_underflow = Counter()
    histogram_overflow = Counter()
    rng = np.random.default_rng(seed)
    selected = [n for n in schema.names if n in {"molecule_id", "spectrum_id", "ms2_mzs", "ms2_normalized_intensities", "precursor_mz", "base_peak_intensity", "collision_energy_ev", "collision_energy_orig", "collision_energy_orig_units", "adduct", "ionization_mode", "instrument_type", "ingest_lib", "normalized_smiles", "inchikey14", "molecular_formula", "precursor_error_ppm", "num_peaks"}]
    for batch in parquet.iter_batches(batch_size=batch_size, columns=selected, use_threads=True):
        frame = batch.to_pandas()
        n_rows += len(frame)
        for name in frame.columns:
            nulls[name] += int(frame[name].isna().sum())
        if "precursor_mz" in frame:
            values = pd.to_numeric(frame["precursor_mz"], errors="coerce").to_numpy(dtype=float)
            values = values[np.isfinite(values)]
            histogram_counts["precursor_mz"] += np.histogram(values, bins=histogram_edges["precursor_mz"])[0]
            histogram_underflow["precursor_mz"] += int((values < histogram_edges["precursor_mz"][0]).sum())
            histogram_overflow["precursor_mz"] += int((values > histogram_edges["precursor_mz"][-1]).sum())
        if "molecule_id" in frame:
            molecule_counts = frame["molecule_id"].dropna().astype(str).value_counts()
            molecule_ids.update(molecule_counts.index.tolist())
            spectra_per_molecule.update(molecule_counts.to_dict())
        for col, counts in categories.items():
            if col in frame:
                counts.update(frame[col].fillna("<NULL>").astype(str).value_counts().to_dict())
        mz_col = "ms2_mzs" if "ms2_mzs" in frame else None
        if mz_col:
            vals = frame[mz_col].map(lambda x: len(x) if isinstance(x, (list, tuple, np.ndarray)) else 0).to_numpy(dtype=np.int32)
            histogram_counts["peak_count"] += np.histogram(vals, bins=histogram_edges["peak_count"])[0]
            histogram_underflow["peak_count"] += int((vals < histogram_edges["peak_count"][0]).sum())
            histogram_overflow["peak_count"] += int((vals > histogram_edges["peak_count"][-1]).sum())
            peak_counts.extend(vals.tolist())
            if len(peak_counts) > sample_rows:
                peak_counts[:] = np.asarray(peak_counts)[rng.choice(len(peak_counts), sample_rows, replace=False)].tolist()
        if "base_peak_intensity" in frame:
            bp = pd.to_numeric(frame["base_peak_intensity"], errors="coerce").to_numpy(dtype=float)
            bp = bp[np.isfinite(bp) & (bp > 0)]
            logbp = np.log10(np.maximum(bp, 1.0))
            histogram_counts["log10_base_peak_intensity"] += np.histogram(logbp, bins=histogram_edges["log10_base_peak_intensity"])[0]
            histogram_underflow["log10_base_peak_intensity"] += int((logbp < histogram_edges["log10_base_peak_intensity"][0]).sum())
            histogram_overflow["log10_base_peak_intensity"] += int((logbp > histogram_edges["log10_base_peak_intensity"][-1]).sum())
        if "collision_energy_ev" in frame:
            energies = [value for entry in frame["collision_energy_ev"] for value in (entry if isinstance(entry, (list, tuple, np.ndarray)) else [entry])]
            energies = np.asarray(pd.to_numeric(pd.Series(energies), errors="coerce"), dtype=float)
            energies = energies[np.isfinite(energies)]
            histogram_counts["collision_energy_ev"] += np.histogram(energies, bins=histogram_edges["collision_energy_ev"])[0]
            histogram_underflow["collision_energy_ev"] += int((energies < histogram_edges["collision_energy_ev"][0]).sum())
            histogram_overflow["collision_energy_ev"] += int((energies > histogram_edges["collision_energy_ev"][-1]).sum())
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
        "spectra_per_molecule_quantiles": np.quantile(list(spectra_per_molecule.values()), [0, .25, .5, .75, .95, .99, 1]).tolist() if spectra_per_molecule else [],
        "spectra_per_molecule_distribution": dict(Counter(spectra_per_molecule.values()).most_common()),
        "columns": [{"name": field.name, "type": str(field.type), "nullable": field.nullable} for field in schema],
        "null_count": dict(nulls),
        "category_counts": {col: counts.most_common(40) for col, counts in categories.items() if counts},
        "precursor_mz_quantiles": np.quantile(precursor_values, [0, .01, .25, .5, .75, .99, 1]).tolist() if precursor_values else [],
        "peaks_per_spectrum_quantiles": np.quantile(peak_counts, [0, .25, .5, .75, .95, .99, 1]).tolist() if peak_counts else [],
        "sample_rows": len(sample_batches),
        "sample_rows_note": "Reservoir sample is for point-level detail views only; exact histogram/category/QC counts below use all scanned rows.",
        "full_data_histograms": {key: {"edges": histogram_edges[key].tolist(), "counts": histogram_counts[key].tolist(),
                                      "underflow": int(histogram_underflow[key]), "overflow": int(histogram_overflow[key])}
                                 for key in histogram_edges},
    }
    return report, pd.DataFrame.from_records(sample_batches)


# Create composite overview plots that answer concrete questions about coverage and train-test domain shift.
def plot_eda(train_sample: Any | None, test_sample: Any | None, output: Path, reports: dict[str, Any] | None = None) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import pandas as pd
    import seaborn as sns

    output.parent.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(2, 3, figsize=(16, 9))
    pairs = [("train", train_sample), ("test", test_sample)]
    for name, frame in pairs:
        full_report = (reports or {}).get(name)
        if full_report and full_report.get("full_data_histograms"):
            hist = full_report["full_data_histograms"]
            for key, axis in (("precursor_mz", axes[0, 0]), ("peak_count", axes[0, 1]), ("collision_energy_ev", axes[0, 2])):
                item = hist[key]; edges = np.asarray(item["edges"]); counts = np.asarray(item["counts"])
                axis.stairs(counts, edges, label=f"{name} (all {full_report['rows']:,} rows)")
            continue
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
    if reports and "train" in reports and "ingest_lib" in reports["train"].get("category_counts", {}):
        counts = dict(reports["train"]["category_counts"]["ingest_lib"])
        pd.Series(counts).sort_values().tail(12).plot.barh(ax=axes[1, 0], color="#237c78")
        axes[1, 0].set(title="Training sources (exact full-data counts)", xlabel="rows")
    elif train_sample is not None and "ingest_lib" in train_sample:
        train_sample.ingest_lib.fillna("<NULL>").value_counts().head(12).sort_values().plot.barh(ax=axes[1, 0], color="#237c78")
        axes[1, 0].set(title="Training sources (sample)", xlabel="rows")
    else:
        axes[1, 0].axis("off")
    if reports and "train" in reports and "adduct" in reports["train"].get("category_counts", {}):
        counts = dict(reports["train"]["category_counts"]["adduct"])
        pd.Series(counts).sort_values(ascending=False).head(12).plot.bar(ax=axes[1, 1], color="#dd8c36")
        axes[1, 1].tick_params(axis="x", rotation=65)
        axes[1, 1].set(title="Training adducts (exact full-data counts)", ylabel="rows")
    elif train_sample is not None and "adduct" in train_sample:
        train_sample.adduct.fillna("<NULL>").value_counts().head(12).plot.bar(ax=axes[1, 1], color="#dd8c36")
        axes[1, 1].tick_params(axis="x", rotation=65)
        axes[1, 1].set(title="Training adducts (sample)", ylabel="rows")
    else:
        axes[1, 1].axis("off")
    if reports and "train" in reports and "instrument_type" in reports["train"].get("category_counts", {}):
        counts = dict(reports["train"]["category_counts"]["instrument_type"])
        pd.Series(counts).sort_values().tail(12).plot.barh(ax=axes[1, 2], color="#7859a6")
        axes[1, 2].set(title="Training instruments (exact full-data counts)", xlabel="rows")
    elif train_sample is not None and "instrument_type" in train_sample:
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
    plot_eda(samples.get("train"), samples.get("test"), args.out / "composite_eda.png", reports=reports)
    print(json.dumps({k: {"rows": v["rows"], "unique_molecules": v["unique_molecules"], "columns": [x["name"] for x in v["columns"]]} for k, v in reports.items()}, indent=2))


if __name__ == "__main__":
    main()
