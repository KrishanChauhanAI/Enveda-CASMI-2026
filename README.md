# Enveda CASMI 2026 — staged solution development

**Project version:** see [`VERSION`](VERSION); the current scientific plan is [`docs/analysis_and_action_plan.md`](docs/analysis_and_action_plan.md), and changes/evidence are tracked in [`CHANGELOG.md`](CHANGELOG.md) and [`docs/verification_matrix.md`](docs/verification_matrix.md).

See [`docs/stage1_problem_and_research.md`](docs/stage1_problem_and_research.md) for initial research; [`docs/analysis_and_action_plan.md`](docs/analysis_and_action_plan.md) is the current scientific plan; [`docs/task_plan.md`](docs/task_plan.md) records work packages. Third-party repository review and safety notes are in [`docs/third_party_tooling.md`](docs/third_party_tooling.md).

## Colab / Jupyter workbench

For the latest self-contained workbench (all code inline, no `src/` imports), open [`notebooks/CASMI_2026_local_eda_v0.9.0.ipynb`](notebooks/CASMI_2026_local_eda_v0.9.0.ipynb). It scans every available Parquet row in batches, exports raw first/last-five records, displays each static 600-DPI PNG and interactive hoverable Plotly figure inline while saving both PNG and HTML files to `casmi_eda_v0.9.0/`, and includes Task 2 identity/MRR and Task 3 preprocessing smoke tests. Set `DATA_DIR` to the local/Drive folder containing Parquet files; the complete train scan runs when `train.parquet` is present.

The earlier [`CASMI_2026_local_workbench.ipynb`](notebooks/CASMI_2026_local_workbench.ipynb) covers audit, unit tests, preprocessing and optional model smoke checks, but imports project modules; its bounded PyTorch run is **not a competition-ready predictor**.

## Task 1: data understanding and EDA

The runnable Colab notebook is [`notebooks/01_task1_data_understanding.ipynb`](notebooks/01_task1_data_understanding.ipynb). For local/Colab terminal execution, install dependencies and use the streaming scanner (safe for the ~3 GB training parquet):

```bash
python -m pip install -r requirements.txt
python src/task1_eda.py --test /path/to/test.parquet --train /path/to/train.parquet --out artifacts/task1
```

Omit `--train` for test-only EDA. Deliverables: `data_dictionary_and_quality.json` and `composite_eda.png`. The scanner uses Arrow batches and a bounded reservoir sample rather than loading the full training table into pandas. A simpler single-file audit is also available in `src/data_audit.py`.

## Task 2: molecular identity and evaluation

`src/identity.py` implements Kaggle's public canonicalization behavior (stereo removed before tautomer canonicalization; pinned `rdkit==2026.3.3`), first-block InChIKey identity, identity deduplication, submission validation, and local MRR@K. It expects one ground-truth SMILES per solution molecule and the competition's semicolon-joined predictions.

```bash
python -m pip install -r requirements.txt
PYTHONPATH=. python -m unittest tests.test_identity -v
```

The tests cover the official stereo/tautomer regression, keto/enol equivalence, different connectivity, reciprocal rank, duplicate candidate identity, and invalid submission rows. The complete metric notebook remains the source of truth; compare Kaggle's provided metric implementation before using this evaluator as a final scorer.

## PyTorch baseline pipeline (requires train labels and test spectra)

`src/solution.py` is a reproducible, offline starting point. It bins each MS/MS spectrum, trains a compact PyTorch convolutional model to predict Morgan fingerprints from labeled spectra, splits validation by molecule ID, aggregates replicate test spectra, and ranks training-set structures using predicted fingerprint similarity with precursor-mass evidence as a weak guardrail. It writes `submission.csv`, metrics JSON, model weights, and a composite diagnostic plot.

```bash
python -m pip install -r requirements.txt
python src/solution.py --train /path/to/train.parquet --test /path/to/test.parquet --out artifacts/run
```

Options include `--smiles-column`, `--epochs`, `--batch-size`, `--validation-fraction`, `--seed`, and `--cpu`. Runtime and memory should be benchmarked on the target machine; defaults are a research baseline, not competition-validated settings.

**Scientific limitation:** test.parquet alone cannot supervise the fingerprint predictor, and it contains no structures for candidates. It can support test-set EDA and preprocessing checks only. The ranking candidates here are limited to training SMILES; candidates outside that set cannot be recovered. The reported validation loss/bit-F1 are model diagnostics, not MRR@25. Before trusting a submission, add grouped-identity retrieval metrics (Recall@K/MRR@25 after official canonicalization), verify adduct conventions and schema against the actual parquet, compare against spectral-library retrieval, and run the official metric locally. No performance gain is claimed until those experiments are run.
