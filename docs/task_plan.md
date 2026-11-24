# CASMI 2026 work breakdown and ownership

**Date:** 2026-11-19 UTC · **Version:** 1.0

## Competition-grounded facts

The current official Kaggle Data page describes one row per spectrum; predictions aggregate by `molecule_id`. It reports approximately 2.5 million training spectra / 275k unique structures, and about 1,500 test spectra / 400 molecules (1–16 spectra per molecule, median 3). The test examples visible through the page are a training-derived preview and are replaced with the hidden test on notebook rerun. **Do not use this visible test preview as an independent validation set**: its origins overlap training by design. Test columns include molecule/spectrum IDs, peak arrays, precursor/adduct/mode, instrument, collision-energy and base-peak metadata. Train adds standardized SMILES, InChIKeys, formula, source library, original adduct and precursor error. Always audit actual parquet schema before relying on a stated column. Source: [Kaggle Data tab](https://www.kaggle.com/competitions/enveda-CASMI26-molecule-id-mass-spectra/data?select=train.parquet).

## Eight work packages and acceptance gates

1. **Data understanding / EDA (P0, current):** bounded-memory parquet scan, schema and null report, spectra-per-molecule, mass/peak/energy distributions, source/instrument/adduct coverage and useful train/test visuals. Gate: report generated from real files; claims cite observed outputs, not approximations.
2. **Molecular identity and metric (P0, next):** pinned RDKit tautomer canonicalization and InChIKey14 identity, robust invalid-SMILES handling, candidate identity deduplication, unit tests against known pairs, MRR@25. Gate: tests cover tautomer/stereo equivalence, connectivity distinction, rank positions, empty/no-hit cases; compare semantics with official metric notebook.
3. **Spectrum preprocessing (P1):** validate aligned arrays, deterministic normalization/filtering, adduct/mode and collision-energy handling; preserve raw features alongside transforms. Gate: deterministic output and explicit malformed-row handling.
4. **Spectral retrieval baseline (P0):** precursor-aware library search using cosine/modified cosine/entropy and multi-spectrum fusion. Gate: leakage-safe molecule-disjoint Recall@K and MRR@25 plus valid submission.
5. **Candidate generation (P1):** train library and permitted structure collections, exact mass/formula filtering, dedup by official identity. Gate: report candidate recall by held-out molecule and novelty/source group.
6. **Learned spectrum-to-structure evidence (P2):** fingerprint multi-label model / spectrum embeddings or contrastive model, only after retrieval baseline and splits are stable. Gate: improvement on molecule-disjoint validation, not just training fit.
7. **Ranking and ensemble (P2):** fuse independent calibrated evidence; assess rank-specific gains and ablations. Gate: reproducible MRR lift over strongest component, with uncertainty and groups reported.
8. **Offline deployment/submission (P0):** notebook environment, bundled resources, 9-hour execution, format and identity validation. Gate: offline rerun creates exactly one row per test molecule with <=25 unique candidates and valid SMILES.

## Repository leads (existence and high-level contents checked 2026-11-19)

- **[OfficialBhattacharya/kaggle_CASMI_2026](https://github.com/OfficialBhattacharya/kaggle_CASMI_2026):** appears well organized for onboarding: `notebooks/`, `src/`, `scripts/`, `tests/`, `experiments/`, `docs/`. Good structural reference for the Task 1 → tests → experiments workflow. Repository tree existence was verified, not the scientific correctness or leaderboard performance of every component.
- **[shiferaxa/casmi26](https://github.com/shiferaxa/casmi26):** public-pipeline harness with `src/`, `scripts/`, `tests/`, `docs/`, Kaggle assets; useful for studying identity-safe validation and fingerprint/pipeline integration. Do not transplant code without licensing and validation review.
- **[Mathys-Gouverneur/Enveda-CASMI-2026](https://github.com/Mathys-Gouverneur/Enveda-CASMI-2026):** organized `src/`, `scripts/`, `tests/`, `notebooks/`, `kaggle/`, `docs/`; useful as another research/workflow reference.

No external repository is installed into this project. Repository existence/organization is not proof of accuracy, winning rank, reproducibility, or license compatibility. Treat them as references and independently reproduce results. The competition data page states CC BY-NC 4.0; inspect every additional resource's terms separately.

## Current implementation status (2026-11-19)

- **Task 1:** scanner, Colab notebook, synthetic test and acceptance guidance exist. Synthetic testing passed; real competition files are not mounted here, so real-data EDA acceptance remains pending.
- **Task 2:** `src/identity.py` and unit tests implement the official RDKit canonicalization sequence and MRR checks. Six tests passed against RDKit 2026.3.3 in this environment. Final parity against Kaggle's full scorer should still be confirmed in the competition notebook.
- **Tasks 3–8:** planned only; not yet claimed complete. No full-data training, cross-validation, model selection or leaderboard score has been produced.

## Ownership / learning workflow

For each task, the code and its tests are the implementation owner; the task report records evidence and outstanding assumptions. Run small tests first, then the real dataset; never represent a planned metric as a measured score. Current artifact: `notebooks/01_task1_data_understanding.ipynb` calling `src/task1_eda.py`. Next increment is Task 2, implemented only after reviewing actual Task 1 schema/results.
