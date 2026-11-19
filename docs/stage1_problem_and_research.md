# Stage 1 — Problem understanding and research

**Prepared:** 2026-11-19 (UTC) · **Version:** 1.0 · **Status:** research baseline; no modeling/data claims made yet

## Competition contract (official Kaggle page, checked 2026-11-19)

- **Task:** Given LC–MS/MS data for an unknown small molecule from complex biological extracts, return up to 25 ranked 2D structures as SMILES. Molecules may be known or novel.
- **Unit of prediction:** one row per `molecule_id`; up to 25 guesses in one `smiles` field separated by semicolons, best first.
- **Metric:** MRR@25 over molecules. Only the first correct candidate matters; reciprocal rank is `1/r` for the first correct candidate at rank `r`, otherwise zero.
- **Identity criterion:** RDKit tautomer canonicalization (competition page pins version 2026.03.3), then first 14 characters / connectivity block of InChIKey. Stereochemistry and tautomer differences do not hurt; connectivity errors do.
- **Submission validity:** exactly the required `molecule_id,smiles` columns; every test ID once, no null/empty fields, no duplicate IDs, and no more than 25 semicolon-delimited guesses. Fewer than 25 are allowed.
- **Execution:** Kaggle notebook submission only; internet disabled at inference; CPU and GPU notebook limits are each 9 hours; freely/publicly available external data and pretrained models are allowed; output must be `submission.csv`.
- **Timeline:** starts 2026-09-14; entry/team merge deadline 2026-12-07; final submission 2026-12-14 (11:59 PM UTC). The 2026-11-19 check showed 25 days to close. Prize pool $50,000.
- **Input science:** ionization/adduct and precursor m/z constrain the neutral molecule/formula; collision-energy-dependent fragmentation produces peaks (m/z, abundance). Positive/negative modes and adduct types must not be conflated. A molecule can have multiple spectra.

**Source:** [Official Kaggle competition page](https://www.kaggle.com/competitions/enveda-CASMI26-molecule-id-mass-spectra). The official page's overview was accessible; its data tab/schema and complete rules still need inspection against downloaded competition files and rules page before modeling. No competition data are present in this checkout.

## Scientific framing and risks

This is a *retrieval plus ranking* problem, not simply unconstrained SMILES generation. Candidate recall is a hard ceiling on MRR; rank-1 ordering has disproportionate value (1.0 versus 0.04 at rank 25). A robust solution should separately report candidate Recall@K, MRR@25, top-1/5/25 accuracy, and identity/coverage by chemical novelty and spectral availability.

Key risks/hypotheses to test, not assume:

1. **Leakage / split realism:** random spectrum splits can place spectra of the same structure on both sides. Use molecule/identity-grouped validation, plus scaffold and source/instrument stress tests where data support them.
2. **Candidate coverage:** training structures and public spectral/chemical libraries can help known compounds, but novel chemistry needs formula-aware or learned retrieval. Measure recall before spending effort tuning rerankers.
3. **Mass and adduct correctness:** exact neutral-mass conversion, charge, isotope/charge state, adduct annotation, ppm tolerance and collision metadata need validation. Infer consensus across repeated spectra rather than treating them as independent molecules.
4. **Spectral ambiguity:** isomers can share precursor/formula and similar fragments. Use fragment and neutral-loss evidence, collision-energy profiles, library matches, and multiple spectra; explicitly quantify irreducible ambiguity.
5. **Metric-specific structure identity:** deduplicate and evaluate by the official tautomer-canonical InChIKey14, not raw SMILES, while retaining a valid representative SMILES.
6. **Offline/runtime constraint:** package all required indexes, model weights, and dependencies in the notebook environment; benchmark under the 9-hour limit with internet disabled.
7. **External resource governance:** record provenance, license, availability, and size for every database/model. Public does not automatically mean redistribution is permitted.

## Public-solution reconnaissance (initial shortlist, not a verified leaderboard)

Search was conducted 2026-11-19. Kaggle notebook pages/rankings are not consistently indexed, so this is a technically oriented shortlist of publicly discoverable solution repositories, **not a claim that these are the ten highest-ranked Kaggle notebooks**. Scores and rank claims below come from repository descriptions, are self-reported, and are not independently verified. We should obtain the actual Kaggle Code leaderboard and inspect source notebooks before treating any as authoritative.

| Priority for follow-up | Public solution / evidence visible in search | Method / reported finding | Follow-up caveat |
|---|---|---|---|
| 1 | [OmerFarukMerey team solutions](https://github.com/OmerFarukMerey/Enveda-CASMI-2026-Molecule-ID-From-Mass-Spectra-Competition-Solutions) | Detailed experiment lineage reports later public-score progression and interventions: library evidence, candidate promotion, fragment reranking, rank fusion. | Self-reported; inspect exact notebook versions, validation, and score regime. |
| 2 | [SSanjay0614](https://github.com/SSanjay0614/Enveda-CASMI-Kaggle) | Reports a public pipeline with library/model ensembles and extensive version history; its description cites a best confirmed score around 0.465. | Self-reported; score/date and code-to-score provenance need confirmation. |
| 3 | [xiaoyuzhoux120 / V44 baseline (referenced by another repo)](https://github.com/leesirleesirlee-star/Enveda_CASMI-2026_Molecule-ID-From-Mass-Spectra) | Reported strong baseline: mass-window candidate pool and LightGBM LambdaRank; another repo describes a 0.417 reproduction. | Original notebook/source, split methodology, and current metric regime need verification. |
| 4 | [tanish-ml](https://github.com/tanish-ml/enveda-casmi-2026) | Describes precursor filtering, peak cleaning, modified cosine + entropy, multi-spectrum reciprocal-rank fusion, mass-nearest fallback. | Search result presents a pipeline; no verified score. |
| 5 | [ibnmarzuk](https://github.com/ibnmarzuk/casmi26-molecule-id) | Library-search baseline plus candidate generation, spectral/chemical features, LightGBM/XGBoost rankers, multi-spectrum aggregation. | Broad project outline; determine which components were implemented and evaluated. |
| 6 | [shiferaxa](https://github.com/shiferaxa/casmi26) | Describes identity-disjoint folds and a candidate-ranking architecture combining library, analog, fragmentation and spectrum-to-fingerprint evidence. | Results and availability of artifacts/data need direct audit. |
| 7 | [leesirleesirlee-star public-frontier analysis](https://github.com/leesirleesirlee-star/Enveda_CASMI-2026_Molecule-ID-From-Mass-Spectra) | Reports scan of 250 public notebooks, a 0.417 baseline and a candidate-recall ceiling concern. | These are author-reported results; inspect notebook inventory and reproducibility. |
| 8 | [Satsuki-Tam](https://github.com/Satsuki-Tam/CASMI2026) | Research index references forward models (ICEBERG/GLACIER), fingerprint models and unseen-molecule experiments. | Need per-experiment results and leakage-safe evaluation. |
| 9 | [OctaLuna](https://github.com/OctaLuna/enveda-casmi-2026) | Proposes retrieval (DreaMS/FAISS), fingerprints, de novo routes (DiffMS/CFM-ID), and learned reranking. | Architecture proposal alone is not evidence of competitive performance; verify weights/runtime/licensing. |
| 10 | [gnshx](https://github.com/gnshx/Enveda-CASMI-2026---Molecule-ID-From-Mass-Spectra) | Describes a candidate pipeline using train structures and public databases, then ranking. | Search excerpt appears partly templated; audit source before assigning credibility. |

**Prioritization basis:** first inspect solutions with experimentally documented iteration and scores, then reproducible baseline/ranking methods, then promising architecture ideas. Popularity, Kaggle votes, notebook leaderboard rank, and notebook code were not reliably exposed by search and are therefore not ranked or inferred here. These repository leads are independent public references, not copied implementation material.

## Initial strategic assessment

The most defensible starting point is a **modular candidate-generation + ranking ensemble**:

- Candidate channels: exact-mass/formula constrained train-set structures; public spectral-library retrieval; and, subject to licensing/runtime, public natural-product/chemical databases.
- Evidence: calibrated precursor/adduct mass error, library spectral similarity, peak/neutral-loss agreement, collision-energy behavior, cross-spectrum consistency, and structure-derived fragmentation or learned spectrum-to-fingerprint scores.
- Ranking: leakage-safe learned ranker if sufficient grouped training examples; otherwise calibrated evidence fusion. Preserve a strong direct library hit instead of allowing broad priors to displace it without validation.
- Backoff: novelty-aware formula/mass candidate pool; avoid pretending a mass-nearest structure is meaningful when formula or connectivity evidence is absent.
- Validation: grouped identity split as the principal estimate, with an instrument/source holdout where feasible. Tune candidate recall and top-rank quality separately.

This is a plan, not a selected final architecture. Model choices await inspection of the actual data, allowed runtime, available hardware, and validation behavior.

## Stage-1 completion checklist and next stage

- [x] Record official task, metric, identity rule, submission schema, runtime and deadline.
- [x] Frame scientific and evaluation risks.
- [x] Identify ten public solution leads and clearly label evidence limitations.
- [ ] Inspect official data-tab files/schema/sample submission and competition rules using the actual competition download.
- [ ] Obtain/inspect the source notebooks and verify public scores/rankings; create a provenance and methods matrix before borrowing ideas.
- [ ] Stage 2: data loading and validation, once competition data are available in the workspace.

**No code or models were run in this stage:** the repository contains only a README and license, and no competition data. This avoids fabricating EDA or claiming experimental gains. Next, provide/mount the competition data (or confirm Kaggle CLI access in the notebook); then we can validate schema and begin stage 2 incrementally.
