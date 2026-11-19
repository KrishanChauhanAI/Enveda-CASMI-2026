"""Offline CASMI starter: spectrum-to-fingerprint PyTorch model and candidate ranking.

Version 0.2.0 | 2026-11-19 UTC. Intended to run locally with train.parquet + test.parquet.
Test-only data can be audited, but cannot supervise or validate molecular predictions.
"""
from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

BIN_WIDTH = 0.5
MAX_MZ = 2048.0
N_BINS = int(MAX_MZ / BIN_WIDTH)
FP_BITS = 2048


# Convert a SMILES string to the fixed-size Morgan fingerprint used as the learning target.
def smiles_to_fp(smiles: str) -> np.ndarray:
    from rdkit import Chem, DataStructs
    from rdkit.Chem import AllChem
    mol = Chem.MolFromSmiles(str(smiles))
    if mol is None:
        return np.zeros(FP_BITS, dtype=np.float32)
    fp = AllChem.GetMorganFingerprintAsBitVect(mol, radius=2, nBits=FP_BITS)
    result = np.zeros((FP_BITS,), dtype=np.int8)
    DataStructs.ConvertToNumpyArray(fp, result)
    return result.astype(np.float32)


# Convert adducted precursor m/z to an approximate neutral mass for conservative candidate filtering.
def neutral_mass(mz: float, adduct: Any) -> float:
    text = str(adduct).replace(" ", "").lower()
    shifts = {
        "[m+h]+": 1.007276, "[m+h]+1": 1.007276, "[m+na]+": 22.989218,
        "[m+nh4]+": 18.033823, "[m-h]-": -1.007276, "[m+cl]-": 34.969402,
        "[m+hcoo]-": 44.998201, "[m+formate]-": 44.998201,
    }
    shift = next((v for k, v in shifts.items() if k in text), None)
    if shift is None or not np.isfinite(mz):
        return float(mz)
    return float(mz) - shift


# Encode one spectrum as sparse-intensity binned channels, preserving both raw and square-root abundance.
def encode_spectrum(mzs: Any, intensities: Any) -> np.ndarray:
    features = np.zeros((2, N_BINS), dtype=np.float32)
    try:
        mzs = np.asarray(mzs, dtype=np.float64)
        intensities = np.asarray(intensities, dtype=np.float64)
    except (TypeError, ValueError):
        return features.reshape(-1)
    valid = np.isfinite(mzs) & np.isfinite(intensities) & (mzs >= 0) & (mzs < MAX_MZ) & (intensities > 0)
    if valid.any():
        bins = np.floor(mzs[valid] / BIN_WIDTH).astype(np.int64)
        weights = intensities[valid]
        if weights.max() > 1.0:
            weights = weights / weights.max()
        np.maximum.at(features[0], bins, weights)
        np.maximum.at(features[1], bins, np.sqrt(weights))
    return features.reshape(-1)


# Build one training example per spectrum while preserving labels and molecule groups for leakage-safe splitting.
def build_training(frame: pd.DataFrame, smiles_col: str) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[str]]:
    required = {"ms2_mzs", "ms2_normalized_intensities", smiles_col}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Training parquet lacks required fields: {sorted(missing)}")
    x, y, groups, smiles_list = [], [], [], []
    for row in frame.itertuples(index=False):
        row_data = row._asdict()
        smi = str(row_data.get(smiles_col, ""))
        if not smi or smi.lower() == "nan":
            continue
        fp = smiles_to_fp(smi)
        if not fp.any():
            continue
        x.append(encode_spectrum(row_data["ms2_mzs"], row_data["ms2_normalized_intensities"]))
        y.append(fp)
        groups.append(str(row_data.get("molecule_id", smi)))
        smiles_list.append(smi)
    if not x:
        raise ValueError("No usable labeled spectra. Check SMILES column name and data contents.")
    return np.stack(x), np.stack(y), np.asarray(groups), smiles_list


# Define a compact convolutional encoder and multi-label Morgan fingerprint prediction head.
class SpectrumFingerprintNet(nn.Module):
    def __init__(self, bits: int = FP_BITS) -> None:
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv1d(2, 32, kernel_size=9, stride=2, padding=4), nn.BatchNorm1d(32), nn.GELU(),
            nn.Conv1d(32, 64, kernel_size=7, stride=2, padding=3), nn.BatchNorm1d(64), nn.GELU(),
            nn.Conv1d(64, 96, kernel_size=5, stride=2, padding=2), nn.BatchNorm1d(96), nn.GELU(),
            nn.AdaptiveMaxPool1d(64),
        )
        self.head = nn.Sequential(nn.Flatten(), nn.Linear(96 * 64, 512), nn.GELU(), nn.Dropout(0.2), nn.Linear(512, bits))

    # Run spectral bins through the encoder and return fingerprint logits.
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.head(self.conv(x))


# Split spectra by molecule identity so replicate spectra of one molecule cannot leak across folds.
def grouped_split(groups: np.ndarray, validation_fraction: float, seed: int) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    unique = np.unique(groups)
    rng.shuffle(unique)
    n_val = max(1, int(round(len(unique) * validation_fraction))) if len(unique) > 1 else 0
    val_groups = set(unique[:n_val])
    val = np.asarray([g in val_groups for g in groups])
    return np.flatnonzero(~val), np.flatnonzero(val)


# Train the fingerprint model with grouped validation and report validation bit metrics.
def train_model(x: np.ndarray, y: np.ndarray, groups: np.ndarray, args: argparse.Namespace, out: Path) -> tuple[SpectrumFingerprintNet, dict[str, Any]]:
    torch.manual_seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() and not args.cpu else "cpu")
    model = SpectrumFingerprintNet().to(device)
    train_idx, val_idx = grouped_split(groups, args.validation_fraction, args.seed)
    tx = torch.from_numpy(x.reshape(-1, 2, N_BINS))
    ty = torch.from_numpy(y)
    loader = DataLoader(TensorDataset(tx[train_idx], ty[train_idx]), batch_size=args.batch_size, shuffle=True)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate, weight_decay=1e-4)
    loss_fn = nn.BCEWithLogitsLoss()
    best_loss = float("inf")
    best_state = None
    patience = 3
    stale = 0
    history = []
    for epoch in range(args.epochs):
        model.train()
        losses = []
        for xb, yb in loader:
            xb, yb = xb.to(device), yb.to(device)
            optimizer.zero_grad(set_to_none=True)
            loss = loss_fn(model(xb), yb)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 2.0)
            optimizer.step()
            losses.append(float(loss.detach().cpu()))
        model.eval()
        with torch.no_grad():
            if len(val_idx):
                logits = model(tx[val_idx].to(device)).cpu()
                val_loss = float(loss_fn(logits, ty[val_idx]).item())
                probabilities = torch.sigmoid(logits).numpy()
                truth = y[val_idx]
                pred = probabilities >= 0.5
                f1 = float((2 * (pred & (truth > 0)).sum()) / max(1, pred.sum() + (truth > 0).sum()))
            else:
                val_loss, f1 = float("nan"), float("nan")
        history.append({"epoch": epoch + 1, "train_bce": float(np.mean(losses)), "validation_bce": val_loss, "validation_bit_f1": f1})
        score = val_loss if np.isfinite(val_loss) else float(np.mean(losses))
        if score < best_loss:
            best_loss, best_state, stale = score, {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}, 0
        else:
            stale += 1
            if stale >= patience:
                break
    if best_state is not None:
        model.load_state_dict(best_state)
    model.to(device).eval()
    out.mkdir(parents=True, exist_ok=True)
    torch.save({"state_dict": model.cpu().state_dict(), "fingerprint_bits": FP_BITS, "bin_width": BIN_WIDTH, "max_mz": MAX_MZ}, out / "spectrum_fp_model.pt")
    return model, {"device": str(device), "train_spectra": int(len(train_idx)), "validation_spectra": int(len(val_idx)), "history": history}


# Aggregate multiple spectra of a molecule into a single mean binned representation.
def aggregate_test(frame: pd.DataFrame) -> tuple[list[str], np.ndarray, pd.DataFrame]:
    required = {"molecule_id", "ms2_mzs", "ms2_normalized_intensities"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Test parquet lacks required fields: {sorted(missing)}")
    rows: dict[str, list[np.ndarray]] = defaultdict(list)
    for row in frame.itertuples(index=False):
        data = row._asdict()
        rows[str(data["molecule_id"])].append(encode_spectrum(data["ms2_mzs"], data["ms2_normalized_intensities"]))
    ids = list(rows)
    spectra = np.stack([np.mean(rows[k], axis=0) for k in ids])
    return ids, spectra, frame


# Rank available training structures by predicted fingerprint agreement and precursor mass consistency.
def rank_candidates(model: SpectrumFingerprintNet, ids: list[str], encoded: np.ndarray, train_frame: pd.DataFrame, test_frame: pd.DataFrame, smiles_col: str, device: torch.device, top_k: int = 25) -> list[str]:
    smiles = train_frame[smiles_col].dropna().astype(str).drop_duplicates().tolist()
    valid_smiles, fps, masses = [], [], []
    mass_by_smiles = {}
    if "precursor_mz" in train_frame.columns:
        for _, row in train_frame[[smiles_col, "precursor_mz"] + (["adduct"] if "adduct" in train_frame else [])].dropna(subset=[smiles_col, "precursor_mz"]).iterrows():
            mass_by_smiles.setdefault(str(row[smiles_col]), neutral_mass(float(row["precursor_mz"]), row.get("adduct", "")))
    for smi in smiles:
        fp = smiles_to_fp(smi)
        if fp.any():
            valid_smiles.append(smi)
            fps.append(fp)
            masses.append(mass_by_smiles.get(smi, np.nan))
    if not valid_smiles:
        raise ValueError("No valid candidate structures found in training SMILES.")
    cand_fp = torch.from_numpy(np.stack(fps)).to(device)
    model.to(device).eval()
    predictions = []
    with torch.no_grad():
        batch = torch.from_numpy(encoded.reshape(-1, 2, N_BINS)).to(device)
        for chunk in batch.split(128):
            predictions.append(torch.sigmoid(model(chunk)).cpu())
    pred = torch.cat(predictions).numpy()
    cand = cand_fp.cpu().numpy()
    # Cosine similarity is used as a stable differentiable-fingerprint proxy; mass is a weak tie-breaker.
    cand_norm = np.maximum(np.linalg.norm(cand, axis=1), 1e-6)
    score = (pred @ cand.T) / np.maximum(np.linalg.norm(pred, axis=1, keepdims=True) * cand_norm[None, :], 1e-6)
    train_mass = np.asarray(masses, dtype=np.float64)
    test_mass_by_id: dict[str, float] = {}
    if "precursor_mz" in test_frame.columns:
        for molecule_id, group in test_frame.groupby("molecule_id", sort=False):
            values = [neutral_mass(float(row.precursor_mz), getattr(row, "adduct", "")) for row in group.itertuples() if pd.notna(row.precursor_mz)]
            if values:
                test_mass_by_id[str(molecule_id)] = float(np.median(values))
    rankings = []
    for i, molecule_id in enumerate(ids):
        local = score[i].copy()
        target_mass = test_mass_by_id.get(molecule_id, float("nan"))
        known = np.isfinite(train_mass)
        if np.isfinite(target_mass) and known.any():
            ppm = np.abs(train_mass - target_mass) / max(abs(target_mass), 1.0) * 1e6
            # Exact mass is a guardrail, not a hard gate: uncalibrated/adduct-unrecognized rows remain eligible.
            local[known] -= np.minimum(ppm[known], 100.0) * 0.0005
            in_window = known & (ppm <= 30.0)
            if in_window.any():
                local[~in_window] -= 0.10
        rankings.append(";".join(np.asarray(valid_smiles, dtype=object)[np.argsort(-local)[:top_k]].tolist()))
    return rankings


# Generate the diagnostic plots and training-history figure used to inspect the run.
def plot_diagnostics(train: pd.DataFrame, test: pd.DataFrame, history: list[dict[str, Any]], out: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import seaborn as sns
    out.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    if "precursor_mz" in train:
        sns.histplot(pd.to_numeric(train["precursor_mz"], errors="coerce"), bins=50, ax=axes[0, 0], color="#187c78", label="train")
    if "precursor_mz" in test:
        sns.histplot(pd.to_numeric(test["precursor_mz"], errors="coerce"), bins=50, ax=axes[0, 0], color="#da7b35", alpha=.55, label="test")
    axes[0, 0].set(title="Precursor m/z: train vs test", xlabel="m/z")
    if axes[0, 0].get_legend_handles_labels()[0]: axes[0, 0].legend()
    if "ms2_mzs" in train:
        train_n = train["ms2_mzs"].map(lambda v: len(v) if isinstance(v, (list, tuple, np.ndarray)) else 0)
        sns.histplot(train_n, bins=40, ax=axes[0, 1], color="#187c78", label="train")
    if "ms2_mzs" in test:
        test_n = test["ms2_mzs"].map(lambda v: len(v) if isinstance(v, (list, tuple, np.ndarray)) else 0)
        sns.histplot(test_n, bins=40, ax=axes[0, 1], color="#da7b35", alpha=.55, label="test")
    axes[0, 1].set(title="Peaks per spectrum", xlabel="peak count")
    axes[0, 1].legend()
    if history:
        hist = pd.DataFrame(history)
        axes[1, 0].plot(hist.epoch, hist.train_bce, label="train BCE")
        axes[1, 0].plot(hist.epoch, hist.validation_bce, label="grouped validation BCE")
        axes[1, 0].set(title="Learning curves", xlabel="epoch", ylabel="BCE")
        axes[1, 0].legend()
    if "adduct" in train:
        train["adduct"].fillna("missing").value_counts().head(12).plot.bar(ax=axes[1, 1], color="#7353a6")
        axes[1, 1].set(title="Most common training adducts", xlabel="adduct", ylabel="spectra")
    else:
        axes[1, 1].axis("off")
    fig.suptitle("CASMI data and model diagnostics")
    fig.tight_layout()
    fig.savefig(out / "pipeline_diagnostics.png", dpi=160)
    plt.close(fig)


# Load data, train the PyTorch fingerprint model, generate candidate lists, and write auditable artifacts.
def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train", type=Path, default=Path("data/train.parquet"))
    parser.add_argument("--test", type=Path, default=Path("data/test.parquet"))
    parser.add_argument("--smiles-column", default="normalized_smiles")
    parser.add_argument("--out", type=Path, default=Path("artifacts/run"))
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--learning-rate", type=float, default=1e-3)
    parser.add_argument("--validation-fraction", type=float, default=0.15)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--cpu", action="store_true")
    args = parser.parse_args()
    if not args.train.exists() or not args.test.exists():
        raise FileNotFoundError(f"Need both labeled training and test parquet files; train={args.train.exists()}, test={args.test.exists()}")
    train, test = pd.read_parquet(args.train), pd.read_parquet(args.test)
    x, y, groups, _ = build_training(train, args.smiles_column)
    model, metrics = train_model(x, y, groups, args, args.out)
    ids, test_x, _ = aggregate_test(test)
    device = torch.device("cuda" if torch.cuda.is_available() and not args.cpu else "cpu")
    # Candidate fallback is available training structures only; no arbitrary external chemistry is invented.
    predictions = rank_candidates(model, ids, test_x, train, test, args.smiles_column, device)
    submission = pd.DataFrame({"molecule_id": ids, "smiles": predictions})
    if submission.isna().any().any() or submission.molecule_id.duplicated().any() or (submission.smiles.str.count(";") >= 25).any():
        raise ValueError("Generated submission failed basic Kaggle format checks.")
    args.out.mkdir(parents=True, exist_ok=True)
    submission.to_csv(args.out / "submission.csv", index=False)
    (args.out / "metrics.json").write_text(json.dumps(metrics, indent=2))
    plot_diagnostics(train, test, metrics["history"], args.out)
    print(json.dumps({"submission_rows": len(submission), "metrics": metrics, "artifacts": str(args.out)}, indent=2))


if __name__ == "__main__":
    main()
