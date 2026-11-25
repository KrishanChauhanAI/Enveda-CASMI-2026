# CASMI 2026 research and release checklist

**Project v1.1.0 · State as of 2026-11-19 UTC.** Checkboxes indicate actual evidence, not code presence. Do not mark a gate complete without recording the artifact, data fingerprint, command, configuration and result in `docs/experiment_log.md`.

## A. Repository and scientific audit

- [x] Preserve tested RDKit identity/MRR functions rather than rewriting without cause (`src/identity.py`, `tests/test_identity.py`).
- [x] Identify and disable the invalid identity-disjoint/train-only-candidate-pool retrieval metric in pipeline v1.0; it excluded the validation truth.
- [x] Separate validation claims into Track A (held-out spectrum IDs for known structures), Track B (unseen identity plus independent candidate source), and Track C (known structure without a reference spectrum).
- [x] Document model/library roles, dependency/license/offline questions, Auto3D limitations and go/no-go experiment (`docs/model_library_responsibilities.md`).
- [x] Replace per-query RDKit mass reconstruction with a precomputed exact-mass index and binary-search window (`src/candidate_index.py`).
- [x] Update baseline training groups and candidate deduplication to use official InChIKey14; reject misaligned peak arrays (`src/solution.py`).
- [x] Add exact all-row histogram summaries and bounded-memory plotted population distributions (`src/task1_eda.py`, pipeline v1.1.0).
- [ ] Confirm actual train file hash, row count, schema and full-scan integrity in the target local/Colab environment.
- [ ] Audit dependency licenses, model weights/licenses, source provenance and offline package availability for every chosen external tool.

## B. Task 1 — full data audit (P0)

- [x] Stream all columns and rows in bounded Arrow batches; export exact endpoint rows, exact categories/null/QC, spectra-per-molecule and full-data fixed-bin histograms.
- [x] Keep point-level interactive views separate and labelled; do not claim they represent every row.
- [ ] Run on the actual 2.5M-row `train.parquet` and hidden-equivalent test file; verify Parquet metadata row counts and histogram in-range + under/overflow accounting.
- [ ] Save and review `full_data_audit.json`, schema report, endpoint exports, all-row PNG/HTML histogram charts and domain-shift summary.
- [ ] Add formula-vs-SMILES consistency, precursor/adduct ppm error distribution, duplicate-spectrum and library-overlap audit on full train.

## C. Task 2 — identity and official MRR@25 (P0)

- [x] Pin the competition RDKit version and remove stereochemistry before tautomer canonicalization; compare InChIKey14.
- [x] Test tautomer/stereo, invalid SMILES, connectivity, duplicate candidate removal, rank 1/2/25 and no-hit reciprocal-rank examples.
- [ ] Run local scorer against the official metric notebook in the matching RDKit version on a fixture covering malformed inputs, all ranks 1–25, duplicate identities and exact ID coverage.
- [ ] Make one authoritative source implementation shared or parity-tested between `src/identity.py` and notebook-inline implementation.

## D. Task 3 — preprocessing and adduct chemistry (P1)

- [x] Reject non-1D/misaligned arrays; deterministic peak filtering/binning and normalization smoke tests.
- [x] Explicitly handle known singly charged test adduct shifts, polarity consistency and eV metadata validity in pipeline notebook.
- [ ] Reconcile notebook adduct constants against `src/chemistry.py` for every official test adduct; test exact masses and edge cases.
- [ ] Compare untouched, relative intensity floor, square-root/log, top-N and windowed top-N preprocessing on Track A and B validation.
- [ ] Select thresholds only when held-out MRR/Recall improves with stable confidence intervals; otherwise retain no filter.
- [ ] Keep collision-energy units/source provenance; never treat NCE, V and eV as interchangeable without an explicitly validated conversion.

## E. Task 4 — spectral retrieval (P0)

- [x] Include transparent exact cosine, modified cosine and entropy-style similarity primitives with synthetic unit checks.
- [x] State that the v1.0 train-only candidate evaluator was invalid and disable its score path.
- [ ] Build Track A: hold out spectrum IDs, retain structure catalog, exclude query and exact duplicate spectra from index; report known-reference coverage and no-reference cases separately.
- [ ] Benchmark matchms or another verified implementation against local primitives on a fixed toy fixture and representative real spectra.
- [ ] Measure Recall@1/5/25/100, MRR@25, top-candidate calibration, per-molecule fusion, source/instrument/adduct/energy slices, runtime and RAM.
- [ ] Validate Track B separately with an independently permitted candidate catalog; report candidate coverage before conditional ranking metrics.
- [ ] Profile full-size indexing only after small-fixture correctness; use cached spectra, sparse/disk-backed index and bounded candidates where needed.

## F. Task 5 — candidate generation (P1)

- [x] Create identity-deduplicated structure index with precomputed RDKit neutral exact masses and binary-search ppm query.
- [ ] Verify all adduct neutral-mass equations and candidate precursor windows against known structure/adduct fixtures.
- [ ] Add formula constraints only after formula integrity has been checked against canonical SMILES.
- [ ] For each external database (e.g. COCONUT, PubChem, GNPS), record allowed-use rules, license, source release/hash, structure count, dedup method, offline footprint and availability before integration.
- [ ] Measure candidate coverage/Recall@K and candidate-pool size by novelty/chemical class; do not infer value from database size alone.

## G. Task 6 — deep-learning research (P2, conditional)

- [x] Retain compact fingerprint and spectrum-embedding options as prototypes, not accepted predictors.
- [ ] Establish a retrieval baseline first.
- [ ] Compare fingerprint prediction with candidate-conditioned pairwise/listwise ranking on identity-disjoint folds.
- [ ] Split using official InChIKey14; never split spectrum rows or raw SMILES strings when equivalent tautomers/stereoisomers map to the same scored identity.
- [ ] Tune only on validation MRR@25/candidate recall, report BCE/embedding loss as diagnostics, and use early stopping.
- [ ] Benchmark memory/time and full-data streaming; reject architectures that cannot meet available hardware/runtime.
- [ ] Keep a model only if it adds reproducible held-out improvement over the strongest simpler channel.

## H. Task 7 — fusion and calibration (P2, conditional)

- [x] Include deterministic reciprocal-rank fusion smoke utility.
- [ ] Calibrate spectral, mass, formula, learned and fragmentation scores using held-out data only.
- [ ] Compare each channel and the ensemble with molecule-level grouped/bootstrap uncertainty; test multiple-spectrum fusion policies.
- [ ] Keep only channels with reproducible MRR@25 or candidate-recall benefit; record negative ablations too.

## I. Auto3D conformers (optional experiment; not a core task)

- [x] Document that Auto3D takes SMILES and generates/optimizes 3D conformers; it does not infer a structure from MS/MS or make 25 distinct structural predictions.
- [ ] Select a small identity-held-out candidate set; record conformer yield/failures, seed reproducibility, geometry/energy validity, CPU/GPU time, memory, licensing and deployment dependencies.
- [ ] Compare ranking **with vs. without** conformer-derived evidence at fixed candidate pool and evaluation split; use confidence intervals.
- [ ] Do not run Auto3D for every top-25 candidate unless the measured benefit justifies the 25x geometry cost and offline budget.

## J. Task 8 — submission and offline release (P0)

- [x] Add helper that requires exact molecule IDs, valid unique SMILES and at most 25 candidates; it fails closed rather than fabricating guesses.
- [ ] Generate one row per actual hidden `molecule_id`; verify template set equality and no nulls/duplicates.
- [ ] Run official scorer on legally held-out labels; validate output and candidate identity exactly.
- [ ] Create a clean Kaggle notebook with internet disabled, pinned/local dependencies and all artifacts available offline.
- [ ] Record full CPU/GPU runtime, peak RAM, artifacts/checksums, reproducibility seed and confirm <=9 hours.

## Release stop conditions

Do not claim a final solution or competitive performance until: (1) the actual train scan passes; (2) scorer parity passes; (3) retrieval and candidate coverage are measured on the appropriate validation tracks; (4) all model/fusion choices beat a documented baseline; (5) final hidden-ID output validates; and (6) the offline runtime gate passes. Current workspace does not include `train.parquet` or PyTorch, so the unchecked gates remain open.
