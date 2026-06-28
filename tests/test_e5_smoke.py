import subprocess


def test_run_e5_script_parses():
    # bash -n: syntax check without executing (no GPU/training needed)
    r = subprocess.run(["bash", "-n", "scripts/experiments/run_e5_sigma_grounding.sh"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
