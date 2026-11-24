# CASMI 2026 — scientific problem analysis and execution plan

**Project plan version:** 1.1.0 · **Project version:** 0.5.0 · **Reviewed:** 2026-11-19 UTC

This document supersedes scattered planning notes as the working scientific plan. It does not claim a trained model, an official score, or completion of blocked work packages. Every iteration follows **identify → hypothesize → plan → implement → test → evaluate → verify against the competition objective → version/log**.

## 1. What is actually being predicted?

The competition gives multiple tandem-MS spectra for each unknown molecule and expects **one ranked list per molecule**: at most 25 semicolon-delimited SMILES in the `smiles` column. The primary objective is mean reciprocal rank at 25, using RDKit tautomer canonicalization and first InChIKey block matching. Thus this is not merely formula prediction or SMILES generation. It is a staged **candidate retrieval and evidence ranking** problem under chemical ambiguity.

MRR makes candidate ordering important: the first correct candidate at rank `r` contributes `1/r`; a molecule without a correct candidate in its top 25 contributes zero. Candidate recall is the ceiling for any ranker. We will therefore report both (i) candidate Recall@K and (ii) ranking MRR@25/top-k, and will not spend time polishing a ranker whose candidate pool misses the truth.

## 2. Data facts from the official Kaggle Data tab

Source: [competition data page](https://www.kaggle.com/competitions/enveda-CASMI26-molecule-id-mass-spectra/data?select=train.parquet), read 2026-11-19.

- Train is documented as about 2.5 million spectra over about 275k structures, one row per spectrum. Test preview is about 1,500 spectra over about 400 molecules, usually 1–16 spectra per molecule (median about 3); test predictions are per molecule, not per spectrum.
- The preview `test.parquet` is drawn from training examples and is replaced by hidden test data during a competition notebook rerun. It is useful for plumbing/format checks, **not a valid independent validation set**.
- Test data are all Bruker timsTOF and the closest documented reference channel is `enveda-np-examples` (250 common natural products from matching instruments/processing). The much larger `enveda-180` source is also timsTOF but is drug-like screening chemistry, so instrument match does not mean chemical-domain match.
- Training source libraries differ in instruments, energy conventions, precision, filtering, and chemical composition. Compounds recur across libraries even though duplicate spectra were removed.
- Spectra contain aligned `ms2_mzs` and `ms2_normalized_intensities`, with a stated per-spectrum base intensity of 1.0. Precursor m/z, adduct, ionization mode, collision energy, source and instrument metadata matter.
- Official page prose enumerates **ten** test adducts. Another column description says the adduct is “one of the seven above,” while the enumerated list contains ten. The page labels test as 12 columns and train as 18 columns, but the listed shared fields plus training-only fields appear to total 20 columns if `inchikey` and `inchikey14` are separate. Treat those as documentation inconsistencies; use the actual Arrow schema and sample submission as truth.
- Kaggle says test spectra are minimally curated (weak base-peak spectra dropped, peaks above precursor +2 Da removed) and that `collision_energy_ev` is a best-effort conversion for heterogeneous training metadata. Retain and audit rather than assuming every train/test source was prepared identically.
- External sources/models must be checked individually for licenses, permitted use, size and offline availability. Kaggle's competition data license is CC BY-NC 4.0; do not assume this license grants other resources' rights.

## 3. Why the problem is hard, and what the solution should do

1. **Many-to-one / ambiguous fragmentation:** isomers can share precursor formula and fragments. Solution: retrieve/rank evidence; do not claim that one spectrum deterministically encodes a unique structure.
2. **Heterogeneous acquisition and multi-spectrum evidence:** a molecule can have several adducts and energies, while training libraries differ. Solution: preserve per-spectrum/adduct/source evidence, then aggregate per molecule using calibrated rank/score fusion. Do not average spectra blindly before testing information loss.
3. **Novelty mix is hidden:** exact library hits, known structures with no spectrum, and unseen structures require different candidate paths. Solution: staged candidate channels with measurable coverage: spectral library → mass/formula chemical pool → learned structure/fingerprint evidence. De novo generative chemistry is a late-stage option, not a baseline.
4. **Domain shift:** a large instrument-matched synthetic library is not a natural-product distribution. Solution: evaluate by source, instrument, scaffold and chemical family; calibrate priors and avoid raw popularity dominating direct spectral evidence.
5. **Label leakage:** spectrum-random splits leak replicate spectra and repeated structures. Solution: primary molecule/identity-grouped split, followed by harder source/instrument/scaffold/novelty split. Every scaler, frequency prior, training target and feature must be fold-safe.
6. **Adduct/neutral-mass errors:** an incorrect neutral mass creates false candidates and wrong formula filters. Solution: versioned, unit-tested adduct table, mode/charge awareness, report unknown adduct rather than treating precursor m/z as neutral mass.
7. **Scale/runtime:** train parquet is ~3 GB compressed and expands substantially into Python lists/dense features; test run is offline and time-limited. Solution: streaming Arrow/Parquet readers, compact sparse/binned representations, bounded memory, cached molecular identities, measured inference time. No full dense materialization of millions of spectra.
8. **Metric identity:** raw SMILES or plain InChIKey comparison is not the metric. Solution: the pinned canonicalizer is the identity oracle; deduplicate top candidates by the same identity while retaining valid representative SMILES.

## 4. Ordered work plan, questions, artifacts and gates

### Phase A — Contract/data audit (Task 1; current, not data-verified)

**Question:** What is actually in our local files, and what is one row?

**Do:** stream actual train/test Arrow schema; nulls; ID uniqueness/coverage; spectra per molecule; peak-array alignment/finite values/intensity normalization; peak count and precursor distributions; adduct/mode/energy/source/instrument distributions; compare source/test domains; document differences and conflicts.

**Deliver:** `docs/data_dictionary.md`, `src/task1_eda.py`, Colab notebook, audit JSON, composite plot, recorded row/unique counts and data-quality exceptions.

**Gate:** only pass after your real files are scanned. Synthetic tests prove implementation mechanics, not dataset facts.

### Phase B — Identity and evaluation (Task 2; code implemented, tests run)

**Question:** Does our local score exactly encode the official matching contract?

**Do:** pin RDKit 2026.3.3; remove stereochemistry before tautomer enumeration; compare first InChIKey block; test official examples, invalid structures, tautomer/stereo equivalence, connectivity differences, no-hit, rank positions, row coverage and <=25 guesses. Differential-test against Kaggle's scorer.

**Deliver:** reusable metric and identity/dedup module.

**Gate:** exact results agree with official metric on all public edge cases and randomized valid toy samples.

### Phase C — Scientific preprocessing (Task 3)

**Question:** Which cleaning steps remove noise without discarding diagnostic low-intensity evidence?

**Do:** preserve raw arrays; validate paired lengths; quantify invalids; compare no-clean, relative floor (e.g. 0.1/1/2%), precursor bounds, top-N global vs per-mass-window, deisotoping, sqrt/log transforms; retain adduct/mode/energy. Use one transform only when grouped validation improves Recall@K/MRR, not because it is conventional.

**Gate:** deterministic transformer, explicit malformed-data behavior and ablations.

### Phase D — Leak-safe splits and baseline (Task 4; build immediately after actual data access)

**Question:** Can known molecules be found by their reference spectra, and how often?

**Do:** build fold-safe reference spectra indexed by InChIKey14; exclude all spectra and duplicate structures of held-out molecules; search precursor-compatible spectra with exact cosine, modified cosine (fragment/neutral-loss shifts), and spectral entropy. Aggregate 1–16 query spectra by reciprocal-rank fusion or calibrated score fusion. Start with simpler cosine to get a reliable floor, then compare variants.

**Report:** candidate Recall@1/5/25/100; MRR@25, top-1/5/25; results by source/instrument, molecule spectra count, adduct/mode, scaffold. Include random row split only as a labeled leakage demonstration, never as headline validation.

**Gate:** reproducible, fold-safe baseline and ablation table.

### Phase E — Candidate pool expansion (Task 5)

**Question:** How much of the held-out truth lies outside the spectral library?

**Do:** rank candidates from (1) exact spectral library; (2) training structures with exact mass/formula; (3) permitted natural-product/chemical DBs; then optionally formula inference. Compute formula/neutral mass consistently, exact ppm errors, charge/adduct compatibility. Deduplicate by official InChIKey14. For each channel record Recall@K and resource license/storage/runtime.

**Gate:** measured candidate coverage per novelty proxy and by held-out structure/source. No ranker is accepted without its candidate recall.

### Phase F — Learned generalization (Task 6)

**Question:** Does a model add information on unseen molecules beyond retrieval and mass/formula?

**Plan:** establish retrieval baseline first. Benchmark (a) multi-label Morgan fingerprint prediction from binned spectrum, (b) spectrum embeddings/contrastive candidate scoring, and where feasible (c) pretrained DreaMS/other approved weights. Train on identity-grouped folds, keep source metadata leakage-safe, and test scaffold/source holdouts. Begin with bounded-size sample/streaming training and resource estimate; compute candidate-level predictions only after pool generation.

**Gate:** materially improves grouped-validation Recall@25 or MRR over strongest non-neural baseline and is reproducible offline within memory/time. If not, do not include it in final stack.

### Phase G — Calibrated ranking/ensemble (Task 7)

**Question:** Which evidence helps choose the right top ranks, and when?

**Do:** candidate-level features from spectral scores, mass/formula error, peak/neutral-loss compatibility, source reliability, multiple spectra consistency, fingerprint/model similarity. Train pairwise/listwise ranker only on fold-safe candidates; use stratified/grouped validation and ablations. Add confidence gates so weak priors cannot displace strong library matches.

**Gate:** same fold + candidates; improvement over strongest component, confidence intervals/seed stability, no hidden leakage, and no pathological novelty subgroup regressions.

### Phase H — Offline deployment (Task 8)

**Question:** Can the exact pipeline create valid output on Kaggle's hidden rerun?

**Do:** package all model weights/indexes inside allowed inputs; no runtime network; test fresh process; use exact sample submission ID coverage; validate every SMILES and identity dedup; at most 25; no nulls/duplicates; profile peak RAM and wall time on full data and under 9-hour notebook maximum.

**Gate:** committed offline notebook produces one row per hidden `molecule_id`, passes Kaggle scorer/local format validation, completes within resource limits. Only then call it submission-ready.

## 5. Iteration contract / versioned recursive loop

For each small increment, write a short experiment record with:

- **Problem:** observed failure/uncertainty and why it affects MRR/coverage or validity.
- **Hypothesis:** one falsifiable scientific reason for the change.
- **Plan:** minimal code/experiment, split, metric, resource budget and acceptance threshold.
- **Execution:** commit-level version, config/seed, dependencies, command and artifact paths.
- **Evaluation:** measured metrics and subgroup results; compare to prior version, include negative findings.
- **Verification:** tests, static checks, objective connection and unresolved limitations.
- **Version:** bump root `VERSION`; append `CHANGELOG.md`; update touched module/test/notebook headers; update `docs/verification_matrix.md`.

Do not parallelize dependent scientific tasks until data schema and metric are sound. Fractals can visualize a dependency tree, but its agent executor is not part of the model pipeline. Agent Skills/Understand Anything/DeepTutor/Learn Anything are optional development/learning aids only, not competition dependencies. See `docs/third_party_tooling.md` for compatibility and safety decisions.

## 6. Present status (truthful, not aspirational)

See `docs/verification_matrix.md`. Current verified work is synthetic EDA mechanics, local identity/adduct unit tests and static compilation. Actual parquet analysis, independent validation, retrieval, candidate recall, trained model score, ensemble gain, and full offline hidden-set execution remain unverified or blocked. The next actionable step is for you to run the Task 1 notebook on local Parquet files and share `data_dictionary_and_quality.json` (or summarize it); then we lock the actual schema and move to Task 3/4 with evidence.
