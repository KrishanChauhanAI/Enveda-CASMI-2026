# CASMI 2026 scientific architecture and library responsibilities

**Status:** research plan, not evidence that any component improves MRR@25. Review date: 2026-11-19 UTC.

## Decision framing

Do not rewrite the repository wholesale. Preserve the data-audit, RDKit identity/MRR and adduct primitives that have tests; refactor the spectrum-to-fingerprint prototype and retrieval code only after measuring them against leakage-safe baselines. The repository currently has a useful audit and prototype, but no reproduced real-train scan, valid independent MRR, measured candidate recall, or proven competitive model. This is an evidence-based audit, not an endorsement of the current predictor.

The target is ranked 2D connectivity, not 3D pose prediction. For each `molecule_id`, aggregate all spectra and return at most 25 valid, identity-distinct SMILES. Evaluate with RDKit 2026.03.3 tautomer canonicalization and InChIKey14, exactly matching the public competition scorer.

## Validation tracks (must not be conflated)

1. **Known-structure / held-out-spectrum retrieval:** for a molecule with multiple independently acquired spectra, hold out query spectrum IDs while allowing the identity to exist in the candidate catalog. No held-out spectrum or exact duplicate may enter the reference index. Report which molecules have at least one reference spectrum and separately evaluate molecules without one. This tests whether a reference library identifies known structures; it does not test unseen-structure generalization.
2. **Unseen-identity generalization:** split by InChIKey14 so no identity-level spectra or labels cross the supervised train/validation boundary. Use a separate, rule-compliant candidate catalog (e.g. independently sourced structures) or a declared formula-constrained candidate generator. Report candidate coverage/Recall@K first; ranking MRR is meaningful only where the truth is in the candidate universe. Never use held-out labels to seed the candidate generator in a claimed blind evaluation.
3. **Known structure without reference spectrum:** retain the correct structure only in an independently constructed structure catalog, hide all its spectra from retrieval, and measure mass/formula/learned candidate recall and ranking separately.

The v1.0.0 `evaluate_retrieval` implementation checked identity-disjoint training and validation and then built candidates solely from training SMILES. That protocol necessarily excludes the held-out truth, so its MRR/recall is not a valid retrieval-quality estimate. Replace it with the separated tracks above; do not report its scores as model performance.

## Responsibilities and proposed tools

| Layer / tool | Responsible for | Appropriate CASMI use | Gate / caveat |
|---|---|---|---|
| PyArrow / pandas / NumPy | Parquet schema, bounded batch scans, QC and numeric summaries | Scan every row/column; stream aggregates | Do not expand millions of nested peak arrays into one frame |
| RDKit | Parse/standardize molecules, exact mass/formula, fingerprints, InChIKey14 | Identity contract, formula/mass, candidate validation | Pin competition version; preserve source SMILES and never let a model silently change identity |
| matchms | Spectrum cleaning and established cosine / modified cosine / entropy similarities | Conventional spectral library baseline | Verify score behavior, tolerance, precursor handling, duplicate policy and scaling on small fixtures before full index |
| GNPS / MassBank / MoNA / MassIVE / COCONUT | External spectra or structures, depending on resource | Optional library/candidate expansion | Each resource needs rule eligibility, license/provenance, offline packaging and leakage audit |
| SIRIUS | Precursor/fragment formula hypotheses, fragmentation trees, candidate scoring | Formula constraints and interpretable evidence | External executable/model/runtime and licensing must be checked; predictions are evidence, not labels |
| CSI:FingerID | Structure fingerprints from spectra / database candidate ranking (SIRIUS ecosystem) | Candidate-conditioned structure ranking | Availability, license and compatible offline runtime must be verified |
| MIST-CF | Learned formula prediction / formula-level evidence | Independent formula hypothesis channel | Treat as optional; benchmark formula recall and domain compatibility |
| DreaMS | Learned MS/MS embeddings, self-supervised representation | Retrieval/embedding baseline or pretraining | Check model/data license, inference dependencies, timsTOF/natural-product transfer and runtime |
| ICEBERG, CFM-ID, GLACIER | Forward fragmentation / predicted spectra for a candidate | Candidate verification and reranking | Run only after candidate pruning; compare to measured spectra; simulator agreement is not proof of correctness |
| Auto3D | Generate/optimize 3D conformers from an input SMILES | Optional geometry feature for a supplied candidate | It does **not** infer SMILES from MS/MS or create chemically distinct candidate identities. A request for 25 conformers is a geometry-generation setting, not 25 structure predictions. Benchmark conformer success, energy/geometry reproducibility, GPU/CPU cost, license and whether 3D improves held-out MRR before inclusion. MS/MS connectivity evidence is primarily 2D/fragmentation; 3D evidence is a hypothesis, not a default channel. |
| PyTorch | Train spectrum embeddings, fingerprint predictors or candidate-conditioned rankers | P2 after retrieval/candidate baseline | Grouped validation, seed control, early stopping, memory/runtime measurement; bit loss is not MRR |
| Custom ranking engine | Fuse calibrated channels by molecule across spectra | Produce top-25 candidates | Tune weights only on appropriate validation; report ablations and bootstrap uncertainty |

No external tool should modify molecular identity implicitly. Each interface should carry original SMILES, canonical InChIKey14, canonicalized representation, tool/version, score provenance and transformation logs.

## Recommended sequence and acceptance evidence

1. Correct the validation protocol and audit the current implementation. Record assumptions, dependency inventory and reproducibility.
2. Establish full-file Parquet/QC reports through bounded batch scans. Exact row/category/null/integrity summaries cover all records; exact endpoint records are exported. For visualization, use full-data aggregated histograms/density or category counts. Plotting millions of raw interactive marks is neither memory-safe nor informative; any bounded point-level display must be clearly labelled as a view, not full-data evidence.
3. Validate RDKit identity/MRR against public metric examples and edge cases; keep code and tests in `src/` synchronized with notebook behavior.
4. Benchmark preprocessing ablations (no filtering, justified intensity floors, top-N/windowed peaks, sqrt/log transforms, mass tolerance) on Track A and Track B as appropriate. No filtering threshold is accepted without measured metric impact.
5. Build and benchmark a compact library baseline (matchms or an independently verified implementation). Precompute/cache identities and exact neutral masses; use sorted mass indexes and bounded candidates. Measure Recall@1/5/25/100, MRR@25, coverage and runtime.
6. Add formula/structure catalogs only with recorded licenses and offline artifacts. Measure candidate recall before ranking.
7. Add learned channels only if they improve molecule-disjoint validation over the best simpler baseline; compare fingerprint prediction to candidate-conditioned ranking.
8. Test ensemble gains by ablation, bootstrap, exact official MRR and instrument/source/scaffold slices.
9. Perform a clean offline Kaggle rerun under nine hours and validate exact hidden IDs and output schema.

## Current repository audit summary

- **Sound foundation:** bounded Arrow scan, documented scope gates, RDKit identity helper, adduct shifts, and no claim that a smoke test equals competition performance.
- **Needs correction:** v1.0.0 retrieval evaluator's identity-disjoint split excludes the validation truth from the training-only candidate pool; this cannot measure correct candidate recovery. It should be replaced by Track A/B/C protocols above.
- **Scaling risk:** current candidate retrieval loops through structures and repeatedly constructs RDKit molecules; current pairwise spectral comparisons are nested loops. Correctness fixtures first, then precompute/catalog indexes and benchmark.
- **Unverified assumptions:** binned spectra/fingerprint prediction, fixed mass penalties, default preprocessing, and multi-channel scores have not demonstrated predictive value on real group validation.
- **Dependency discipline:** avoid adding Auto3D, matchms, SIRIUS/MIST-CF or pretrained models until role, license, offline packaging and incremental validation benefit are established. EDA-only cells need plotting/Parquet dependencies; final inference environment should be a separately pinned minimal set.
- **Plot completeness:** full dataset rows/columns must be scanned. Full-data figures should aggregate all observations; interactive per-spectrum plots can be bounded views because browsers cannot sensibly render millions of points.

## Auto3D go/no-go experiment

Before using Auto3D to generate conformers for up to 25 candidates per query, sample a molecule-identity-held-out set and compare candidate rankings with and without a conformer-derived feature. Record: valid conformer yield, conformers per molecule, optimization failures, deterministic seed behavior, wall time, peak memory/GPU, package/model license, and MRR@25 delta with confidence intervals. Until this experiment exists, Auto3D is **not part of the core pipeline**. Its role is optional candidate geometry generation, not structure generation from spectrum.
