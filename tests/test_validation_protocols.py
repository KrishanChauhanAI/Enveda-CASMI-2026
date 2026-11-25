import pandas as pd
import pytest

from src.validation import split_known_structure_spectra, split_unseen_identities, validate_track_b_catalog
from src.identity import canonicalize_smiles_to_ik14


def _spectra_frame():
    return pd.DataFrame({
        "spectrum_id": [f"s{i}" for i in range(8)],
        "normalized_smiles": ["CCO", "OCC", "CCO", "CCN", "CCN", "CCC", "CCC", "CCO"],
        "ms2_mzs": [[30.0]] * 8,
        "ms2_normalized_intensities": [[1.0]] * 8,
    })


def test_track_a_holds_out_spectrum_ids_and_retains_catalog_identities():
    frame = _spectra_frame()
    result = split_known_structure_spectra(frame, query_fraction=0.34, seed=7)
    assert not (set(result.reference.spectrum_id) & set(result.query.spectrum_id))
    query_ids = set(result.query["_identity14"])
    catalog_ids = set(result.catalog.inchikey14)
    assert query_ids <= catalog_ids
    assert result.identities_with_reference
    assert set(result.query.spectrum_id) | set(result.reference.spectrum_id) == set(frame.spectrum_id)


def test_track_a_rejects_duplicate_spectrum_ids():
    frame = _spectra_frame()
    frame.loc[1, "spectrum_id"] = frame.loc[0, "spectrum_id"]
    with pytest.raises(ValueError, match="unique"):
        split_known_structure_spectra(frame)


def test_track_b_splits_complete_identities_and_catalog_reports_coverage():
    frame = _spectra_frame()
    train, valid = split_unseen_identities(frame, validation_fraction=0.5, seed=12)
    train_ids = set(train.normalized_smiles.map(canonicalize_smiles_to_ik14))
    valid_ids = set(valid.normalized_smiles.map(canonicalize_smiles_to_ik14))
    assert not (train_ids & valid_ids)
    full_catalog = pd.DataFrame({"smiles": frame.normalized_smiles.unique()})
    report = validate_track_b_catalog(train, valid, full_catalog)
    assert report["identity_overlap"] == 0
    assert report["candidate_truth_coverage"] == 1.0


def test_track_b_requires_multiple_identities():
    frame = pd.DataFrame({"normalized_smiles": ["CCO", "OCC"]})
    with pytest.raises(ValueError, match="two"):
        split_unseen_identities(frame)
