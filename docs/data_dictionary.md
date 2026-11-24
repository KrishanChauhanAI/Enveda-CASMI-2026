# Competition data dictionary

**Version 1.1.0 | 2026-11-19 UTC**

This is a guide transcribed from the official Kaggle Data tab, not a substitute for checking the actual parquet. `src/task1_eda.py` reports actual Arrow types, null counts, value counts, and row/molecule cardinalities on the files you run it against. There is one row per spectrum; repeated `molecule_id` values are expected and must be grouped for prediction.

## Shared spectrum columns

| Column | Meaning / notes |
|---|---|
| `molecule_id` | Anonymous compound identifier; the unit of prediction and output. Several spectra may map to one ID. |
| `spectrum_id` | Unique identifier for a measured/aggregated spectrum. Verify uniqueness in actual data. |
| `ms2_mzs` | Array of fragment-ion m/z values. |
| `ms2_normalized_intensities` | Aligned abundance array; competition docs say each spectrum's maximum is 1.0. Peak index `i` in both arrays is one pair. |
| `base_peak_intensity` | Raw intensity of the strongest peak before normalization; may be null in training sources that supplied pre-normalized intensities. |
| `adduct` | Standardized precursor-ion annotation. Test lists ten forms: `[M+H]+`, `[M+NH4]+`, `[M-H2O+H]+`, `[M-2H2O+H]+`, `[M+Na]+`, `[M+K]+`, `[M-H]-`, `[M-H2O-H]-`, `[M+CH2O2-H]-`, `[M+Cl]-`. |
| `ionization_mode` | Positive or negative ionization. Do not mix modes/adducts without a charge-aware transformation. |
| `instrument_type` | Test: `timsTOF`; train: source-provided free text, often null. |
| `precursor_mz` | Measured precursor m/z. Convert to neutral mass only with a correctly parsed adduct and charge. |
| `collision_energy_ev` | Best-effort collision-energy values in eV, represented as a list; can be null for unresolved training metadata and can represent merged acquisitions. |
| `collision_energy_orig` | Lossless source-recorded collision-energy string; may contain several values. |
| `collision_energy_orig_units` | Source/original energy units (eV, NCE, V, unknown); NCE-to-eV is approximate. |

## Training-only columns

| Column | Meaning / notes |
|---|---|
| `normalized_smiles` | Standardized molecular structure label. |
| `inchikey` | Full structure key; use official RDKit normalization for evaluation, not string equality. |
| `inchikey14` | First InChIKey block as supplied by the dataset; validate against the competition canonicalizer before using as a label identity. |
| `molecular_formula` | Neutral molecular formula. |
| `ingest_lib` | Source library. Training spectra have heterogeneous sources, instrument protocols, collision-energy formats, and chemistry distributions. |
| `adduct_orig` | Original source adduct string before standardization. |
| `precursor_error_ppm` | Source precursor error against the labeled structure/adduct; useful for quality analysis, not a test feature. |
| `num_peaks` | Supplied number of peaks; compare against parsed array lengths. |

## Official documented scale / interpretation

Kaggle reports approximately 2.5 million training spectra and 275k unique structures; visible test preview has approximately 1.5k spectra for 400 molecules, typically 1–16 spectra per molecule. The preview is training-derived and replaced with hidden test data on rerun, so it is not independent validation. Training library sizes overlap at the compound level; counts by source do not sum to unique structures. The test preview is all `timsTOF`; `enveda-180` and `enveda-np-examples` are the training sources documented as uniformly matching that instrument. The actual downloaded file and run-time mount must be audited before relying on approximate counts or schema. The page itself has two documentation inconsistencies: it enumerates ten test adducts but elsewhere says “one of the seven above,” and labels train as 18 columns despite listing 12 test columns plus the training-only fields (20 if `inchikey` and `inchikey14` are distinct). Arrow schema is the authority.
