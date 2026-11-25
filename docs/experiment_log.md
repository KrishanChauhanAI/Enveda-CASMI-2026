# CASMI 2026 experiment log

This log records hypotheses, configuration, evidence and decisions. A successful code run is not a performance claim. The visible test preview is training-derived and is not independent validation.

## EXP-001 — v1.1.0 repository/scientific audit and full-row plot summaries

- **Date:** 2026-11-19 UTC
- **Problem:** Previous v1.0.0 validation split held out complete identities while creating candidates only from training structures. Held-out answer identities were therefore absent from the candidate universe; resulting retrieval MRR/recall would be meaningless.
- **Hypothesis:** Separate known-structure held-out-spectrum evaluation from unseen-identity evaluation, and make all-row aggregate distributions available without retaining/rendering millions of nested spectra.
- **Plan:** Add track-specific deterministic split helpers; disable invalid evaluator; precompute exact molecular masses and use binary-search ppm windows; compute fixed-bin full-file histograms while retaining only a bounded point-level view; update source and notebook together.
- **Changes:** `src/validation.py`, `src/candidate_index.py`, updates to `src/solution.py` and `src/task1_eda.py`; `notebooks/Enveda_CASMI_2026_Pipeline_v1.1.0.ipynb`; `docs/model_library_responsibilities.md` and `docs/experiment_checklist.md`.
- **Configuration/data:** RDKit 2026.03.3; available `data/test.parquet` only (1,213 rows); no `train.parquet`; no PyTorch. Notebook code cells executed with plot figures redirected to `/tmp/casmi_pipeline_v1.1.0` for the check.
- **Evaluation:** 17 tests and 10 subtests passed; Python compilation and `git diff --check` passed; all 44 notebook code cells executed. Exact histograms covered all 1,213 rows for precursor mass, peak count and base-peak intensity, and 1,809 collision-energy values. Synthetic candidate-index and submission dedup checks passed.
- **Result:** The scanner and notebook changes are functionally checked on the available preview; candidate index, validation tracks and interface helpers have synthetic test coverage.
- **Limitations:** No real train scan, full-size timing/RAM benchmark, independent validation MRR/Recall@K, external catalog coverage/license audit, PyTorch training, Auto3D experiment, hidden-ID submission or offline <=9h rerun.
- **Decision:** Keep the validation protocol correction and exact aggregate histogram approach. Treat all predictive pipeline stages as prototypes until unchecked criteria in `docs/experiment_checklist.md` are completed.
- **Next experiment:** Run the actual train file through the full scanner; build Track A reference holdout and report known-reference coverage, Recall@K and MRR@25 separately from Track B candidate coverage on an independently permitted catalog.
