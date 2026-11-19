# Enveda CASMI 2026 — staged solution development

See [`docs/stage1_problem_and_research.md`](docs/stage1_problem_and_research.md) for competition requirements and research notes.

## Data audit

```bash
python -m pip install -r requirements.txt
python src/data_audit.py --test /path/to/test.parquet --out artifacts/stage2_eda
```

Optional `--train /path/to/train.parquet` inspects both files. This is useful for schema/EDA without training.

## PyTorch baseline pipeline (requires train labels and test spectra)

`src/solution.py` is a reproducible, offline starting point. It bins each MS/MS spectrum, trains a compact PyTorch convolutional model to predict Morgan fingerprints from labeled spectra, splits validation by molecule ID, aggregates replicate test spectra, and ranks training-set structures using predicted fingerprint similarity with precursor-mass evidence as a weak guardrail. It writes `submission.csv`, metrics JSON, model weights, and a composite diagnostic plot.

```bash
python -m pip install -r requirements.txt
python src/solution.py --train /path/to/train.parquet --test /path/to/test.parquet --out artifacts/run
```

Options include `--smiles-column`, `--epochs`, `--batch-size`, `--validation-fraction`, `--seed`, and `--cpu`. Runtime and memory should be benchmarked on the target machine; defaults are a research baseline, not competition-validated settings.

**Scientific limitation:** test.parquet alone cannot supervise the fingerprint predictor, and it contains no structures for candidates. It can support test-set EDA and preprocessing checks only. The ranking candidates here are limited to training SMILES; candidates outside that set cannot be recovered. The reported validation loss/bit-F1 are model diagnostics, not MRR@25. Before trusting a submission, add grouped-identity retrieval metrics (Recall@K/MRR@25 after official canonicalization), verify adduct conventions and schema against the actual parquet, compare against spectral-library retrieval, and run the official metric locally. No performance gain is claimed until those experiments are run.
