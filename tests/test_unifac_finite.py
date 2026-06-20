import math
import sys

import pytest

sys.path.insert(0, "src")

pytest.importorskip("thermo.unifac")

from tgnn_solv.unifac import modified_unifac_lngamma_binary


def test_modified_unifac_lngamma_binary_returns_finite_value() -> None:
    value = modified_unifac_lngamma_binary("CCO", "O", 298.15, 0.10)

    assert value is not None
    assert math.isfinite(value)


def test_modified_unifac_lngamma_binary_varies_with_composition() -> None:
    low = modified_unifac_lngamma_binary("CCO", "O", 298.15, 0.05)
    high = modified_unifac_lngamma_binary("CCO", "O", 298.15, 0.20)

    assert low is not None
    assert high is not None
    assert not math.isclose(low, high, rel_tol=0.0, abs_tol=1.0e-8)


def test_modified_unifac_lngamma_binary_rejects_invalid_composition() -> None:
    assert modified_unifac_lngamma_binary("CCO", "O", 298.15, 0.0) is None
    assert modified_unifac_lngamma_binary("CCO", "O", 298.15, 1.0) is None
    assert modified_unifac_lngamma_binary("CCO", "O", 298.15, -0.1) is None
