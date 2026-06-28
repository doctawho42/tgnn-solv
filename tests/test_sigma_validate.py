from sigma_fixtures import make_tiny_cosmo_trainer_and_loader


def test_validate_sigma_no_grad_metrics():
    trainer, loader = make_tiny_cosmo_trainer_and_loader()
    metrics = trainer.validate_sigma(loader)
    assert {"sigma_profile", "sigma_shape", "sigma_area", "sigma_area_mae"} <= set(metrics)
    assert all(isinstance(v, float) for v in metrics.values())
    assert metrics["sigma_area_mae"] >= 0.0
    # validate must not leave grad on parameters
    assert all(p.grad is None for p in trainer.model.head_sigma.parameters())
