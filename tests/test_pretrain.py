import random
import sys

import numpy as np
import pytest
import torch
from torch_geometric.data import Data

sys.path.insert(0, "src")

import tgnn_solv.pretrain as pretrain


def test_pretrain_mask_alignment(monkeypatch: pytest.MonkeyPatch) -> None:
    x = torch.arange(12, dtype=torch.float).view(4, 3)
    edge_index = torch.zeros((2, 1), dtype=torch.long)
    edge_attr = torch.zeros((1, 1), dtype=torch.float)
    base_graph = Data(x=x.clone(), edge_index=edge_index, edge_attr=edge_attr)

    def fake_smiles_to_graph(_smi: str) -> Data:
        return base_graph.clone()

    def fake_compute_properties(_smi: str) -> np.ndarray:
        return np.zeros(pretrain.N_PROPERTIES, dtype=np.float32)

    monkeypatch.setattr(pretrain, "smiles_to_graph", fake_smiles_to_graph)
    monkeypatch.setattr(pretrain, "compute_properties", fake_compute_properties)

    ds = pretrain.PretrainDataset(["C"], mask_ratio=0.5, cache=False)

    random.seed(123)
    candidates = list(range(4))
    random.shuffle(candidates)
    expected_idx = torch.tensor(candidates[:2], dtype=torch.long)
    expected_mask = torch.zeros(4, dtype=torch.bool)
    expected_mask[expected_idx] = True

    random.seed(123)
    torch.manual_seed(123)
    graph, mask, atom_targets, _, _, _, _, _ = ds[0]

    assert torch.equal(mask, expected_mask)
    assert torch.allclose(atom_targets, x[expected_mask])
    assert torch.all(graph.x[mask] == 0.0)
