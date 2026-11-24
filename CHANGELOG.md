# Changelog

All project changes use semantic versions. Any source, test, notebook, or workflow change must update `VERSION`, add a changelog entry, and update the affected module/notebook version header in the same change. Each entry records scope, evidence, and unresolved acceptance gates; version bumps do not imply an accuracy improvement.

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
