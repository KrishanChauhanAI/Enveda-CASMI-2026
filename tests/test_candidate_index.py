import pandas as pd

from src.candidate_index import MassCandidateIndex
from src.chemistry import neutral_mass
from rdkit import Chem
from rdkit.Chem import rdMolDescriptors


def test_index_precomputes_and_queries_mass_with_identity_deduplication():
    frame = pd.DataFrame({
        "normalized_smiles": ["CCO", "OCC", "CCN", "CCC"],
        "molecular_formula": ["C2H6O", "C2H6O", "C2H7N", "C3H8"],
        "ingest_lib": ["a", "b", "a", "b"],
    })
    index = MassCandidateIndex.from_frame(frame)
    assert len(index.table) == 3  # CCO/OCC share official connectivity identity
    ethanol = rdMolDescriptors.CalcExactMolWt(Chem.MolFromSmiles("CCO"))
    result = index.query_neutral_mass(ethanol, ppm=1.0)
    assert result.iloc[0].smiles in {"CCO", "OCC"}
    precursor = ethanol + 1.007276
    by_adduct = index.query_precursor(precursor, "[M+H]+", ppm=2.0)
    assert "CCO" in by_adduct.smiles.tolist()


def test_index_rejects_empty_catalog_and_unknown_adduct_is_empty():
    import pytest
    with pytest.raises(ValueError, match="No valid"):
        MassCandidateIndex.from_frame(pd.DataFrame({"normalized_smiles": ["invalid"]}))
    frame = pd.DataFrame({"normalized_smiles": ["CCO"]})
    index = MassCandidateIndex.from_frame(frame)
    assert index.query_precursor(100.0, "[M+UNKNOWN]+", ppm=10).empty
