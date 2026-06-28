from tgnn_solv.trainer import _sigma_step_due


def _fire_indices(n_batches: int, steps_target: int) -> list[int]:
    done = 0
    fired = []
    for i in range(n_batches):
        if _sigma_step_due(i, n_batches, done, steps_target):
            fired.append(i)
            done += 1
    return fired


def test_disabled_when_target_zero():
    assert _fire_indices(100, 0) == []


def test_fires_exactly_target_times():
    assert len(_fire_indices(100, 10)) == 10


def test_interleaved_not_frontloaded():
    fired = _fire_indices(100, 10)
    # front-loading would give [0..9]; interleaving spreads them out.
    assert fired != list(range(10))
    assert max(fired) >= 80  # last step lands near the end of the epoch


def test_more_target_than_batches_fires_every_batch():
    assert _fire_indices(5, 20) == [0, 1, 2, 3, 4]
