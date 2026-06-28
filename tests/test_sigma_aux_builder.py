import importlib

from tgnn_solv.config import TGNNSolvConfig


def test_builder_default_n_bins_matches_config():
    mod = importlib.import_module("scripts.data.build_sigma_profile_aux_stream")
    # parse with no CLI args -> defaults
    import sys
    argv = sys.argv
    try:
        sys.argv = ["build_sigma_profile_aux_stream.py"]
        ns = mod.parse_args()
    finally:
        sys.argv = argv
    assert ns.n_bins == TGNNSolvConfig().cosmo_sac_n_bins


def test_grid_metadata_helper():
    mod = importlib.import_module("scripts.data.build_sigma_profile_aux_stream")
    cfg = TGNNSolvConfig()
    grid = mod.grid_metadata(51)
    assert grid["n_bins"] == 51
    assert grid["sigma_min"] == cfg.cosmo_sac_sigma_min
    assert grid["sigma_max"] == cfg.cosmo_sac_sigma_max
