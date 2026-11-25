# Changelog

All project changes use semantic versions. Any source, test, notebook, or workflow change must update `VERSION`, add a changelog entry, and update the affected module/notebook version header in the same change. Each entry records scope, evidence, and unresolved acceptance gates; version bumps do not imply an accuracy improvement.

## 1.0.0 — 2026-11-19

- Rename and extend the self-contained notebook as `Enveda_CASMI_2026_Pipeline_v1.0.0.ipynb`, retaining EDA and adding inline Tasks 2–8 utilities: pinned identity/MRR tests, deterministic preprocessing, cosine/modified-cosine/entropy similarity, molecule-level spectrum fusion, mass-based candidate pool, grouped evaluation helper, optional fingerprint MLP with early stopping, rank fusion, and strict submission assembly.
- Clearly gate measured retrieval/recall/MRR, candidate coverage/licensing, learned-model improvements, and offline submission: no local `train.parquet` is mounted and the visible test preview is not independent validation.
- **Verification:** notebook JSON and all code-cell syntax parsed. Pipeline code cells executed with RDKit 2026.03.3: Task 2 identity/MRR and Task 3 preprocessing/adduct assertions passed; Task 4 similarity and Task 7 fusion smoke checks passed; synthetic mass-candidate retrieval passed. No train parquet was present, PyTorch was unavailable, and no Task 4–8 performance acceptance is claimed.

## 0.9.0 — 2026-11-19

- Add evidence-based interpretation of supplied train/test sample correlations, sample quantiles, and molecular-label statistics. Explicitly distinguish spectra-level versus molecule-aggregated effects, sample coverage and domain shift; avoid performance claims.
- Carry forward inline display of the static 600-DPI and interactive plots while saving both artifacts.
- **Verification:** notebook JSON and executable-cell syntax validation pending for this revision; supplied summaries are user-provided outputs, not independently reproduced in this workspace.

## 0.8.0 — 2026-11-19

- Make every EDA visualization appear inline in the running notebook cell as both the saved 600-DPI PNG and interactive Plotly figure, while writing PNG and HTML artifacts to `casmi_eda_v0.8.0/`.
- **Verification:** notebook format/source updated; rerun against the available Parquet files is pending.

## 0.7.0 — 2026-11-19

- Add a fully inline notebook revision with exact raw first/last-five endpoint exports, complete batch scanning, 600-DPI per-chart PNGs and hoverable HTML plots.
- Add raw preview, sample/full-count correlation diagnostics, Task 2 identity/MRR tests, and Task 3 preprocessing/adduct smoke tests.
- **Verification:** executed all notebook code cells against the available test preview: 1,213 rows / 400 molecules scanned; identity/preprocessing assertions and chart generation passed. `train.parquet` is unavailable, so full train scan and train/test comparisons remain pending.

## 0.6.0 — 2026-11-19

- Add a self-contained Task 1 notebook that imports no project `src/` files and processes every train/test Parquet row and column in bounded Arrow batches.
- Add exact ID/category/null/peak-array audit counts, disk-backed spectrum-ID duplicate check, bounded plotting sample, synthetic scanner test, and 3x3 diagnostic visualizations.
- **Verification:** notebook code cells parse; synthetic full-scan and chart smoke tests pass. Actual Kaggle Parquet scans remain pending because files are not mounted.

## 0.5.0 — 2026-11-19

- Add a unified Colab/local Jupyter workbench for data audit, unit tests, preprocessing checks and opt-in bounded PyTorch smoke run.
- Add reproducible setup/path instructions and explicit warnings distinguishing integration smoke outputs from a competition submission.
- Prepare a portable project ZIP excluding Git history, datasets, private credentials and third-party development clones.
- **Verification:** notebook JSON and code cells parse; project tests/compile/static checks rerun. The actual parquet and optional model cell remain unexecuted in this workspace.

## 0.4.0 — 2026-11-19

- Add consolidated scientific problem analysis and eight-phase plan with explicit acceptance gates and novelty/domain-shift risks.
- Record official Kaggle Data-tab contradictions (10 vs 7 adduct wording; stated column-count mismatch) and defer to actual Arrow schema.
- Review and shallow-clone all five requested development/learning repositories into ignored `.external/`; install only Fractals Node deps with scripts disabled, do not launch its privileged agent executor. Add compatibility/license/safety notes.
- Add a critical data-page analysis, including documented schema/adduct inconsistencies, and a gated eight-phase scientific action plan.
- Remove unused dense-pipeline bookkeeping in `src/solution.py`; version the affected module.
- **Verification:** 11 synthetic/unit tests, compile and notebook-format checks pass; no real-data or model experiment was run. Current limitations are recorded in the verification matrix.

## 0.3.0 — 2026-11-19

- Add iterative verification matrix for all eight competition work packages and root semantic-version/change-log policy.
- Extend Task 1 audit to report spectra-per-molecule distribution; add competition data dictionary.
- Add `src/chemistry.py` with tested neutral-mass conversion for every documented test adduct; update PyTorch baseline adduct handling.
- **Verification:** 10 automated tests pass (identity, official adduct mass shifts, synthetic parquet EDA); Python compilation and `git diff --check` pass. Real parquet execution, full Kaggle metric parity, and model training/performance remain pending.

## 0.2.0 — 2026-11-19

- Add exact RDKit 2026.3.3 identity and local MRR@25 utilities, tests, and third-party tooling review.
- **Verification:** six Task 2 tests passed at this point; see the newer matrix for current suite run.

## 0.1.0 — 2026-11-19

- Initial staged competition analysis, data audit, Task 1 EDA, and PyTorch fingerprint baseline.
- No real-data model training or score was claimed.
