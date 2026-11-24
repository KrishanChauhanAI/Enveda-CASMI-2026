# Changelog

All project changes use semantic versions. Any source, test, notebook, or workflow change must update `VERSION`, add a changelog entry, and update the affected module/notebook version header in the same change. Each entry records scope, evidence, and unresolved acceptance gates; version bumps do not imply an accuracy improvement.

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
