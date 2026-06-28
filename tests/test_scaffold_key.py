from tgnn_solv.data.utils import scaffold_key


def test_ring_molecule_returns_scaffold():
    key = scaffold_key("c1ccccc1CCO")  # 2-phenylethanol
    assert key and "c1ccccc1" in key.replace("C", "")  # benzene ring retained


def test_acyclic_falls_back_to_canonical_smiles():
    # hexane is acyclic -> Murcko scaffold is empty; key must be non-empty so the
    # guard can dedup it against held-out acyclic molecules.
    key = scaffold_key("CCCCCC")
    assert key  # non-empty
    # two spellings of hexane map to the same key
    assert scaffold_key("CCCCCC") == scaffold_key("C(CC)CCC")


def test_invalid_smiles_returns_none():
    assert scaffold_key("not_a_smiles") is None
