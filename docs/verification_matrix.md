# Iterative verification matrix

**Project version 0.5.0 | Review date 2026-11-19 UTC**

This matrix treats each acceptance criterion as an evidence claim. `PASS` means the test/data evidence named below exists; `PARTIAL` means code exists but an acceptance condition remains; `BLOCKED` means required inputs or implementation are absent. The visible test parquet is training-derived and is not valid independent validation.

| Work package | Acceptance check | Status | Evidence / blocker | Next verification action |
|---|---|---|---|---|
| 1. Data understanding / EDA | Document fields and types, data quality, spectra-to-molecule relation, relevant distributions; generate real-file report/plots. | **PARTIAL** | `docs/data_dictionary.md`, streaming `src/task1_eda.py`, Colab notebook, synthetic integration test. Test proves rows/molecule count on tiny parquet only; no actual competition parquet is mounted, so real-data acceptance is not established. | Run notebook on the actual train/test files; inspect schema, nulls, duplicate spectrum IDs, array lengths, adduct/source/instrument distribution, spectra-per-molecule, and plots. |
| 2. Identity / official MRR@25 | Canonicalize by RDKit competition version; tests of stereo/tautomer/connectivity, submission constraints, reciprocal rank. | **PASS for tested contract; parity still to confirm** | `src/identity.py`; pinned RDKit 2026.3.3; 8 identity unit tests including Kaggle's documented stereo/tautomer regression and 0.75 example, keto/enol, MRR ranks, malformed submission and dedup. | On Kaggle's metric notebook environment, compare several local scores and edge cases against the official scorer; keep exact metric as source of truth. |
| 3. Spectrum preprocessing | Deterministic input sanitation, filtering/normalization, adduct/mode/energy handling, edge-case tests. | **PARTIAL** | Fixed m/z binning and intensity transforms exist in `src/solution.py`, and all ten documented test adduct mass shifts are implemented/tested in `src/chemistry.py`; this is not a complete peak-cleaning or collision-energy pipeline. | Add tests for malformed/mismatched peak arrays, duplicate peaks, thresholds and energy-list inputs; compare preprocessing alternatives in leakage-safe validation. |
| 4. Spectral library retrieval | Search matching spectra with mass-aware cosine/entropy and multi-spectrum fusion; establish validation MRR. | **BLOCKED** | No cosine/entropy reference search or leakage-safe retrieval validation is implemented. | Build a train molecule-held-out spectral index; benchmark exact and modified cosine/entropy, then report candidate Recall@K and MRR@25. |
| 5. Candidate generation | Formula/neutral-mass-constrained pool and identity dedup including eligible public structures; measure recall. | **PARTIAL** | `src/chemistry.py` maps all ten official test adducts to neutral mass and unit tests those shifts. Current candidates remain training-set SMILES only; no formula/database index or measured candidate Recall@K. | Build a formula/mass candidate index, deduplicate by official InChIKey14, and measure held-out candidate recall. |
| 6. Deep learning | Demonstrate improvement on molecule-disjoint validation, at feasible memory/runtime. | **NOT ACCEPTED** | PyTorch fingerprint architecture is prototype-only. `build_training` materializes all binned spectra in dense arrays and will not fit typical Colab RAM for ~2.5M rows; no actual training or valid molecule-disjoint MRR result exists. | Replace with streaming/chunked data or an explicitly bounded reproducible sample first; benchmark memory/time; evaluate fingerprint retrieval on molecule-disjoint split and compare to baselines. |
| 7. Ranking / ensemble | Ablation shows ensemble improves over strongest component on valid held-out molecules. | **BLOCKED** | Existing fingerprint/mass rank heuristic is not calibrated; no library evidence ensemble, ablation, uncertainty or MRR improvement is measured. | Add ranking features only after retrieval, then compare single-channel and ensemble MRR with grouped/bootstrap evaluation. |
| 8. Submission / offline deployment | Exact test ID coverage, valid unique SMILES, <=25 candidates, official scorer, offline <=9h notebook rerun. | **PARTIAL** | Baseline writes a CSV and Task 2 validator checks schema/SMILES/IDs given a solution frame. No real submission, hidden rerun, runtime benchmark, or offline notebook audit exists. | Validate template and exact hidden IDs at inference, run official metric on legal validation, test offline notebook with bundled weights/index under time/memory cap. |

## Recent rerun (project 0.5.0)

Command: `PYTHONPATH=. .venv/bin/python -m unittest discover -s tests -v`. Result: **11 tests passed** (8 identity + 2 adduct-mass + 1 synthetic parquet EDA). `py_compile src/*.py`, unified notebook JSON/code-cell parsing/version match, and `git diff --check` also passed. These checks do not prove real-data readiness, MRR parity across every edge case, model training performance, or leaderboard score.

## Versioning and change gate

For every code, test, notebook, or workflow change:

1. Increment root `VERSION` (patch for correction, minor for backward-compatible capability, major for behavior/schema break).
2. Add an entry to `CHANGELOG.md` with date, scope, evidence and remaining gaps.
3. Update the affected module's top version/date header and test/notebook version when touched.
4. Run the narrow tests, then the complete available suite; re-run compile/format checks.
5. Update this matrix, changing status only when the actual acceptance evidence exists. Never convert a blocked/partial task to pass based on code presence alone.
