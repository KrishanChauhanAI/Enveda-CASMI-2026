"""Competition-compatible molecular identity and MRR@25 utilities.

Version 1.0.0 | 2026-11-19 UTC. Canonicalization matches Kaggle's public metric notebook.
"""
from __future__ import annotations

from collections.abc import Iterable
from functools import lru_cache
from typing import Any

import pandas as pd

EXPECTED_RDKIT_VERSION = "2026.03.3"
ACCEPTED_RDKIT_VERSIONS = {"2026.03.3", "2026.3.3"}


# Lazily load and cache RDKit plus the competition tautomer canonicalizer, rejecting version drift by default.
@lru_cache(maxsize=2)
def _rdkit_tools(require_competition_version: bool = True) -> tuple[Any, Any]:
    try:
        import rdkit
        from rdkit import Chem, RDLogger
        from rdkit.Chem.MolStandardize import rdMolStandardize
    except ImportError as exc:
        raise RuntimeError("RDKit is required; install the competition wheel or requirements.txt.") from exc
    RDLogger.DisableLog("rdApp.*")
    if require_competition_version and rdkit.__version__ not in ACCEPTED_RDKIT_VERSIONS:
        raise RuntimeError(
            f"Official identity requires RDKit {EXPECTED_RDKIT_VERSION}; found {rdkit.__version__}. "
            "Use the pinned competition wheel to avoid canonicalization drift."
        )
    return Chem, rdMolStandardize.TautomerEnumerator()


# Return the competition's first InChIKey block after removing stereochemistry then canonicalizing tautomer.
def canonicalize_smiles_to_ik14(smiles: Any, require_competition_version: bool = True) -> str | None:
    if not isinstance(smiles, str) or not smiles.strip():
        return None
    Chem, enumerator = _rdkit_tools(require_competition_version)
    try:
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return None
        # This order is essential: stereochemistry can otherwise constrain tautomer canonicalization.
        Chem.RemoveStereochemistry(mol)
        canonical_mol = enumerator.Canonicalize(mol)
        key = Chem.MolToInchiKey(canonical_mol)
        return key[:14] if key and len(key) >= 14 else None
    except (ValueError, RuntimeError, TypeError):
        return None


# Create a fast heavy-atom-composition gate that cannot exclude a valid InChIKey14 match.
def heavy_atom_composition(smiles: Any, require_competition_version: bool = True) -> tuple[tuple[str, int], ...] | None:
    if not isinstance(smiles, str):
        return None
    Chem, _ = _rdkit_tools(require_competition_version)
    try:
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return None
        counts: dict[str, int] = {}
        for atom in mol.GetAtoms():
            symbol = atom.GetSymbol()
            if symbol != "H":
                counts[symbol] = counts.get(symbol, 0) + 1
        return tuple(sorted(counts.items()))
    except (ValueError, RuntimeError, TypeError):
        return None


# Remove invalid or identity-duplicate candidates while preserving first-seen rank order.
def deduplicate_candidates(candidates: Iterable[Any], max_rank: int = 25, require_competition_version: bool = True) -> list[str]:
    if not isinstance(max_rank, int) or max_rank < 1:
        raise ValueError("max_rank must be a positive integer")
    if isinstance(candidates, str):
        candidates = candidates.split(";")
    unique: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        if not isinstance(candidate, str) or not candidate.strip():
            continue
        smiles = candidate.strip()
        identity = canonicalize_smiles_to_ik14(smiles, require_competition_version)
        if identity is None or identity in seen:
            continue
        seen.add(identity)
        unique.append(smiles)
        if len(unique) >= max_rank:
            break
    return unique


# Validate the official one-row-per-molecule submission format and all semicolon-separated candidates.
def validate_submission(submission: pd.DataFrame, max_rank: int = 25, require_competition_version: bool = True) -> None:
    if max_rank < 1:
        raise ValueError("max_rank must be positive")
    required = {"molecule_id", "smiles"}
    if not required.issubset(submission.columns):
        raise ValueError(f"Submission missing columns: {sorted(required - set(submission.columns))}")
    if submission.empty:
        raise ValueError("Submission is empty")
    if submission[list(required)].isna().any().any():
        raise ValueError("Submission has null molecule_id or smiles")
    if submission["molecule_id"].duplicated().any():
        raise ValueError("Each molecule_id must appear exactly once")
    for molecule_id, raw in zip(submission["molecule_id"], submission["smiles"]):
        guesses = [part.strip() for part in str(raw).split(";") if part.strip()]
        if not guesses:
            raise ValueError(f"No candidate SMILES for molecule_id {molecule_id}")
        if len(guesses) > max_rank:
            raise ValueError(f"More than {max_rank} guesses for molecule_id {molecule_id}")
        for guess in guesses:
            if canonicalize_smiles_to_ik14(guess, require_competition_version) is None:
                raise ValueError(f"Invalid SMILES for molecule_id {molecule_id}: {guess!r}")


# Compute official reciprocal rank per molecule and mean score from one answer SMILES per molecule.
def mrr_at_k(solution: pd.DataFrame, submission: pd.DataFrame, k: int = 25, require_competition_version: bool = True) -> float:
    if k < 1:
        raise ValueError("k must be a positive integer")
    if not {"molecule_id", "smiles"}.issubset(solution.columns):
        raise ValueError("Solution must contain molecule_id and smiles columns")
    validate_submission(submission, max_rank=k, require_competition_version=require_competition_version)
    if solution["molecule_id"].isna().any() or solution["molecule_id"].duplicated().any():
        raise ValueError("Solution molecule_id values must be non-null and unique")
    guesses_by_id = dict(zip(submission["molecule_id"], submission["smiles"].astype(str)))
    target_ids = set(solution["molecule_id"])
    if set(guesses_by_id) != target_ids:
        missing = target_ids - set(guesses_by_id)
        extra = set(guesses_by_id) - target_ids
        raise ValueError(f"Submission ID coverage mismatch: missing={len(missing)}, extra={len(extra)}")
    scores = []
    identity_cache: dict[str, str | None] = {}
    for row in solution.itertuples(index=False):
        row_data = row._asdict()
        molecule_id = row_data["molecule_id"]
        answer = row_data["smiles"]
        if not isinstance(answer, str) or not answer.strip():
            raise ValueError(f"Missing answer SMILES for {molecule_id}")
        target = canonicalize_smiles_to_ik14(answer, require_competition_version)
        if target is None:
            raise ValueError(f"Invalid solution SMILES for {molecule_id}: {answer!r}")
        reciprocal_rank = 0.0
        guesses = [part.strip() for part in guesses_by_id[molecule_id].split(";") if part.strip()]
        for rank, candidate in enumerate(guesses[:k], start=1):
            if candidate not in identity_cache:
                identity_cache[candidate] = canonicalize_smiles_to_ik14(candidate, require_competition_version)
            if identity_cache[candidate] == target:
                reciprocal_rank = 1.0 / rank
                break
        scores.append(reciprocal_rank)
    return float(sum(scores) / len(scores)) if scores else 0.0
