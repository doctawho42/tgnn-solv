import torch

from tgnn_solv.loss import sigma_profile_emd_loss


def test_emd_is_sum_over_bins_and_returns_components():
    # pred mass entirely in bin 0, target mass entirely in bin 2 (3-bin toy grid).
    pred_shape = torch.tensor([[1.0, 0.0, 0.0]])
    target_shape = torch.tensor([[0.0, 0.0, 1.0]])
    pred_area = torch.tensor([100.0])
    target_area = torch.tensor([100.0])
    mask = torch.tensor([True])

    total, comps = sigma_profile_emd_loss(
        pred_shape, target_shape, pred_area, target_area, mask,
        mode="emd", area_scale=75.0, shape_weight=1.0, return_components=True,
    )
    # cumsum(pred)=[1,1,1], cumsum(target)=[0,0,1]; |diff|=[1,1,0]; SUM=2.0
    # (mean-over-bins would give 0.667 — this asserts the SUM behaviour).
    assert abs(comps["sigma_shape"] - 2.0) < 1e-6
    assert abs(comps["sigma_area"] - 0.0) < 1e-6
    assert abs(float(total) - 2.0) < 1e-6


def test_area_term_uses_scale_and_shape_weight_applies():
    pred_shape = torch.tensor([[0.5, 0.5]])
    target_shape = torch.tensor([[0.5, 0.5]])  # zero shape loss
    pred_area = torch.tensor([150.0])
    target_area = torch.tensor([75.0])  # diff 75, scale 75 -> (1.0)^2 = 1.0
    mask = torch.tensor([True])

    total, comps = sigma_profile_emd_loss(
        pred_shape, target_shape, pred_area, target_area, mask,
        mode="emd", area_scale=75.0, shape_weight=3.0, return_components=True,
    )
    assert abs(comps["sigma_shape"] - 0.0) < 1e-6
    assert abs(comps["sigma_area"] - 1.0) < 1e-6
    assert abs(float(total) - 1.0) < 1e-6  # shape_weight*0 + 1.0


def test_empty_mask_returns_zero_with_components():
    z = torch.zeros(1, 3, requires_grad=True)
    total, comps = sigma_profile_emd_loss(
        z, z.detach(), torch.zeros(1), torch.zeros(1), torch.tensor([False]),
        return_components=True,
    )
    assert float(total) == 0.0
    assert comps == {"sigma_shape": 0.0, "sigma_area": 0.0}
