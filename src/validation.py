"""Leakage-aware CASMI validation protocols.

Version 0.1.0 | 2026-11-19 UTC.
Track A holds out spectra while preserving known structures in a catalog;
Track B holds out complete identities and requires an independent candidate catalog.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

try:
    from .identity import canonicalize_smiles_to_ik14
except ImportError:
    from identity import canonicalize_smiles_to_ik14


@dataclass(frozen=True)
class SpectrumHoldout:
    """Track A: query spectra and reference spectra are disjoint by spectrum ID."""
    reference: pd.DataFrame
    query: pd.DataFrame
    catalog: pd.DataFrame
    identities_with_reference: frozenset[str]
    identities_without_reference: frozenset[str]


def identity_keys(frame: pd.DataFrame, smiles_col: str = "normalized_smiles") -> pd.Series:
    if smiles_col not in frame:
        raise ValueError(f"Missing identity column {smiles_col!r}")
    return frame[smiles_col].map(canonicalize_smiles_to_ik14)


def split_known_structure_spectra(
    frame: pd.DataFrame,
    query_fraction: float = 0.2,
    seed: int = 42,
    id_col: str = "spectrum_id",
    smiles_col: str = "normalized_smiles",
) -> SpectrumHoldout:
    """Deterministically hold out spectra per identity without removing its catalog entry.

    Only identities with at least two usable, unique spectrum IDs can contribute a
    query/reference pair. Singleton spectra are kept in reference. The returned
    catalog contains one SMILES per identity but no spectrum arrays.
    """
    if not 0 < query_fraction < 1:
        raise ValueError("query_fraction must be between 0 and 1")
    if id_col not in frame or smiles_col not in frame:
        raise ValueError(f"Required columns: {id_col!r}, {smiles_col!r}")
    data = frame.copy()
    data["_identity14"] = identity_keys(data, smiles_col)
    data = data[data["_identity14"].notna() & data[id_col].notna()].copy()
    if data[id_col].duplicated().any():
        raise ValueError("spectrum IDs must be unique before Track A splitting")
    rng = np.random.default_rng(seed)
    query_ids: set[Any] = set()
    for identity, group in data.groupby("_identity14", sort=True):
        ids = group[id_col].to_numpy()
        if len(ids) < 2:
            continue
        shuffled = ids.copy()
        rng.shuffle(shuffled)
        n_query = min(len(ids) - 1, max(1, int(round(len(ids) * query_fraction))))
        query_ids.update(shuffled[:n_query].tolist())
    query_mask = data[id_col].isin(query_ids)
    query = data.loc[query_mask].copy()
    reference = data.loc[~query_mask].copy()
    ref_ids = set(reference[id_col])
    if ref_ids & set(query[id_col]):
        raise AssertionError("Track A spectrum leakage detected")
    catalog = (data[["_identity14", smiles_col]].drop_duplicates("_identity14")
               .rename(columns={"_identity14": "inchikey14", smiles_col: "smiles"}).reset_index(drop=True))
    query_identities = set(query["_identity14"])
    identities_with_reference = frozenset(query_identities & set(reference["_identity14"]))
    identities_without_reference = frozenset(query_identities - set(reference["_identity14"]))
    return SpectrumHoldout(reference, query, catalog, identities_with_reference, identities_without_reference)


def split_unseen_identities(
    frame: pd.DataFrame,
    validation_fraction: float = 0.2,
    seed: int = 42,
    smiles_col: str = "normalized_smiles",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Track B: split complete identities; the returned frames have no shared InChIKey14."""
    if not 0 < validation_fraction < 1:
        raise ValueError("validation_fraction must be between 0 and 1")
    data = frame.copy()
    data["_identity14"] = identity_keys(data, smiles_col)
    data = data[data["_identity14"].notna()].copy()
    identities = np.array(sorted(data["_identity14"].unique()), dtype=object)
    if len(identities) < 2:
        raise ValueError("At least two valid molecular identities are required")
    rng = np.random.default_rng(seed)
    rng.shuffle(identities)
    n_valid = min(len(identities) - 1, max(1, int(round(len(identities) * validation_fraction))))
    valid_ids = set(identities[:n_valid])
    valid_mask = data["_identity14"].isin(valid_ids)
    train, valid = data.loc[~valid_mask].copy(), data.loc[valid_mask].copy()
    if set(train["_identity14"]) & set(valid["_identity14"]):
        raise AssertionError("Track B identity leakage detected")
    return train.drop(columns="_identity14"), valid.drop(columns="_identity14")


def validate_track_b_catalog(
    train: pd.DataFrame,
    valid: pd.DataFrame,
    candidate_catalog: pd.DataFrame,
    smiles_col: str = "normalized_smiles",
    catalog_smiles_col: str = "smiles",
) -> dict[str, int]:
    """Audit that candidate catalog is explicit and measure truth coverage, not silently seed it."""
    if catalog_smiles_col not in candidate_catalog:
        raise ValueError(f"Candidate catalog needs {catalog_smiles_col!r}")
    train_ids = set(identity_keys(train, smiles_col).dropna())
    valid_ids = set(identity_keys(valid, smiles_col).dropna())
    overlap = train_ids & valid_ids
    if overlap:
        raise ValueError(f"Train/validation identity overlap: {len(overlap)}")
    catalog_ids = set(candidate_catalog[catalog_smiles_col].map(canonicalize_smiles_to_ik14).dropna())
    covered = valid_ids & catalog_ids
    return {"train_identities": len(train_ids), "valid_identities": len(valid_ids),
            "identity_overlap": 0, "catalog_identities": len(catalog_ids),
            "candidate_covered_truths": len(covered),
            "candidate_truth_coverage": len(covered) / max(len(valid_ids), 1)}
