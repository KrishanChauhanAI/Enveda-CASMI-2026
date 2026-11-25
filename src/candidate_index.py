"""Cached exact-mass candidate catalog with indexed ppm-window queries.

Version 0.1.0 | 2026-11-19 UTC. Candidate generation only; it does not claim
that a generated pool has adequate recall. Check external structure licenses separately.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

try:
    from .chemistry import neutral_mass
    from .identity import canonicalize_smiles_to_ik14
except ImportError:
    from chemistry import neutral_mass
    from identity import canonicalize_smiles_to_ik14


@dataclass
class MassCandidateIndex:
    """Sorted, precomputed molecule catalog; each query uses binary search."""
    table: pd.DataFrame
    masses: np.ndarray

    @classmethod
    def from_frame(
        cls,
        frame: pd.DataFrame,
        smiles_col: str = "normalized_smiles",
        formula_col: str = "molecular_formula",
        source_col: str | None = "ingest_lib",
    ) -> "MassCandidateIndex":
        if smiles_col not in frame:
            raise ValueError(f"Missing SMILES column {smiles_col!r}")
        from rdkit import Chem
        from rdkit.Chem import rdMolDescriptors

        rows: dict[str, dict[str, Any]] = {}
        for row in frame.itertuples(index=False):
            d = row._asdict()
            smiles = d.get(smiles_col)
            identity = canonicalize_smiles_to_ik14(smiles)
            if identity is None or identity in rows:
                continue
            mol = Chem.MolFromSmiles(smiles)
            if mol is None:
                continue
            formula = d.get(formula_col)
            if not isinstance(formula, str) or not formula:
                formula = rdMolDescriptors.CalcMolFormula(mol)
            rows[identity] = {
                "inchikey14": identity,
                "smiles": smiles,
                "formula": formula,
                "neutral_exact_mass": float(rdMolDescriptors.CalcExactMolWt(mol)),
                "source": d.get(source_col) if source_col and source_col in d else None,
            }
        table = pd.DataFrame(rows.values())
        if table.empty:
            raise ValueError("No valid, identity-distinct candidate structures")
        table = table.sort_values(["neutral_exact_mass", "inchikey14"], kind="stable").reset_index(drop=True)
        return cls(table=table, masses=table["neutral_exact_mass"].to_numpy(dtype=np.float64))

    def query_neutral_mass(self, mass: float, ppm: float = 10.0) -> pd.DataFrame:
        if not np.isfinite(mass) or mass <= 0 or not np.isfinite(ppm) or ppm <= 0:
            return self.table.iloc[0:0].copy()
        tol = float(mass) * float(ppm) * 1e-6
        left = int(np.searchsorted(self.masses, mass - tol, side="left"))
        right = int(np.searchsorted(self.masses, mass + tol, side="right"))
        out = self.table.iloc[left:right].copy()
        out["mass_error_ppm"] = (out["neutral_exact_mass"] - mass).abs() / mass * 1e6
        return out.sort_values(["mass_error_ppm", "inchikey14"], kind="stable").reset_index(drop=True)

    def query_precursor(self, precursor_mz: float, adduct: str, ppm: float = 10.0) -> pd.DataFrame:
        mass = neutral_mass(precursor_mz, adduct)
        return self.query_neutral_mass(mass, ppm)

    def save(self, path: str | Path) -> None:
        self.table.to_parquet(path, index=False)

    @classmethod
    def load(cls, path: str | Path) -> "MassCandidateIndex":
        table = pd.read_parquet(path).sort_values(["neutral_exact_mass", "inchikey14"], kind="stable").reset_index(drop=True)
        return cls(table=table, masses=table["neutral_exact_mass"].to_numpy(dtype=np.float64))
