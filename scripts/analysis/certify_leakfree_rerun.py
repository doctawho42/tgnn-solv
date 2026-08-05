#!/usr/bin/env python3
r"""Certify the leak-free sigma-grounding re-run, arm by arm and seed by seed.

WHAT THIS IS FOR
----------------
Two referees asked for the same thing in different words. Referee 1: both arms at
five seeds "on a stream whose build hash is recorded beside the split hash in each
run's manifest". Referee 2: ">=5 seeds, ungrounded vs grounded, on the identical
5608-row lock", with "certification at the point of use, not of the builder", and
"the stream file's SHA-256 in each run manifest beside the pinned split hash, so
the artifact certifies which build fed which arm".

This script is the check that those things are true of the runs that landed. It
reads only deposited artifacts -- per-run manifests, per-row prediction files, the
per-seed comparison.json -- trains nothing, loads no model, needs no GPU, and exits
non-zero if any of the following fails:

  1. every requested (seed, arm) has a run manifest;
  2. every manifest pins the SAME train/val/test SHA-256 -- one split, not several;
  3. the grounded arm's manifest carries a sigma stream with its SHA-256 and row
     count, and the ungrounded arm's manifest records that it carried NO stream
     (absence asserted, not merely absent);
  4. the stream file every grounded run consumed is ONE file (one SHA-256 across
     seeds), and -- recomputed here from the deposited stream, not trusted from the
     manifest -- shares no canonical SMILES and no Bemis-Murcko scaffold with
     val union test;
  5. the per-seed row lock is the expected labelled set (5608 by default) and is
     the same key set in every arm and seed;
  6. per-seed MAE is present for both arms, so the contrast can be printed per
     seed rather than only as mean +/- sd.

It prints the per-seed table the article has to report. It does NOT decide whether
the supervision gain survives -- that is a number, and the decision rule attached
to it is pre-committed in the article's disclosure paragraph.

USAGE
-----
    KMP_DUPLICATE_LIB_OK=TRUE PYTHONPATH=src python \
        scripts/analysis/certify_leakfree_rerun.py \
        --results-root results/e5_sigma_grounding_leakfree \
        --manifest-root checkpoints/e5_leakfree \
        --seeds 42 43 44 45 46 \
        --report results/e5_sigma_grounding_leakfree/provenance_certificate.json

``--manifest-root`` is where scripts/train.py writes ``<arm>_seed<N>.manifest.json``
(next to the checkpoint, i.e. CKPT_DIR -- NOT the results directory). If the GPU
host is torn down without copying that directory back, criteria 1-4 cannot be
checked at all; fetch it with the results.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
if str(REPO / "src") not in sys.path:
    sys.path.insert(0, str(REPO / "src"))

from tgnn_solv.stream_provenance import certify_stream_disjoint, sha256_of  # noqa: E402

# The article's numbers, hard-coded on purpose: a check that reads its expectations
# out of the files it is checking checks nothing.
N_LABELLED_DEFAULT = 5608
KEY = ["solute_smiles", "solvent_smiles", "T"]


def _fail(problems: list[str], message: str) -> None:
    problems.append(message)


def _load_manifest(root: Path, arm: str, seed: int) -> dict[str, Any] | None:
    path = root / f"{arm}_seed{seed}.manifest.json"
    if not path.exists():
        return None
    return json.loads(path.read_text())


def _input_hash(manifest: dict[str, Any], role: str) -> str | None:
    for record in manifest.get("inputs", []) or []:
        if record.get("role") == role:
            return record.get("sha256")
    return None


def _stream_records(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    meta = manifest.get("metadata", {}) or {}
    records = meta.get("grounding_streams")
    if isinstance(records, list):
        return records
    # Manifests written before the provenance block existed: fall back to the
    # sigma_train_data input record, which at least carries the file's SHA-256.
    sha = _input_hash(manifest, "sigma_train_data")
    if sha is None:
        return []
    return [{"role": "sigma_train", "present": True, "sha256": sha,
             "n_rows": None, "certified_no_leak": None, "legacy_record": True}]


def _row_key_set(path: Path) -> tuple[set[tuple], int]:
    frame = pd.read_csv(path, low_memory=False)
    frame = frame.drop_duplicates(KEY, keep="first").copy()
    frame["T"] = frame["T"].round(6)
    if frame["has_solubility"].dtype == object:
        sup = frame["has_solubility"].map(lambda v: str(v).strip().lower() in ("true", "1"))
    else:
        sup = frame["has_solubility"].fillna(False).astype(bool)
    labelled = frame[sup]
    keys = set(map(tuple, labelled[KEY].itertuples(index=False, name=None)))
    n_nonfinite = int((~np.isfinite(frame["ln_x2_pred"].to_numpy(float))).sum())
    return keys, n_nonfinite


def _mae_on(path: Path, keys: set[tuple]) -> float:
    frame = pd.read_csv(path, low_memory=False)
    frame = frame.drop_duplicates(KEY, keep="first").copy()
    frame["T"] = frame["T"].round(6)
    frame = frame.set_index(KEY)
    sub = frame.loc[[k for k in sorted(keys) if k in frame.index]]
    err = sub["ln_x2_true"].to_numpy(float) - sub["ln_x2_pred"].to_numpy(float)
    return float(np.mean(np.abs(err)))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--results-root", default="results/e5_sigma_grounding_leakfree")
    ap.add_argument("--manifest-root", default="checkpoints/e5_leakfree")
    ap.add_argument("--seeds", nargs="+", type=int, default=[42, 43, 44, 45, 46])
    ap.add_argument("--arms", nargs="+", default=["ungrounded", "grounded_a"])
    ap.add_argument("--grounded-arm", default="grounded_a")
    ap.add_argument("--ungrounded-arm", default="ungrounded")
    ap.add_argument("--held-out", nargs="+",
                    default=["notebooks/data/processed/val.csv",
                             "notebooks/data/processed/test.csv"])
    ap.add_argument("--stream-csv", default=None,
                    help="Local copy of the stream the runs consumed. The manifests record "
                         "the compute host's absolute path, which does not exist here, so "
                         "point this at the deposited file; its SHA-256 is checked against "
                         "the manifests before it is re-certified.")
    ap.add_argument("--expect-n-locked", type=int, default=N_LABELLED_DEFAULT)
    ap.add_argument("--report", default=None, help="write the full certificate here")
    args = ap.parse_args()

    results_root = Path(args.results_root)
    manifest_root = Path(args.manifest_root)
    problems: list[str] = []
    report: dict[str, Any] = {"results_root": str(results_root),
                              "manifest_root": str(manifest_root),
                              "seeds": args.seeds, "arms": args.arms,
                              "per_run": {}, "per_seed": {}}

    # --- 1-3. manifests, split pinning, stream provenance -----------------
    split_hashes: dict[str, set[str]] = {"train_data": set(), "val_data": set(),
                                         "test_data": set()}
    stream_hashes: set[str] = set()
    stream_paths: set[str] = set()

    for seed in args.seeds:
        for arm in args.arms:
            tag = f"{arm}_seed{seed}"
            manifest = _load_manifest(manifest_root, arm, seed)
            if manifest is None:
                _fail(problems, f"{tag}: no run manifest at "
                                f"{manifest_root / (tag + '.manifest.json')}")
                continue
            entry: dict[str, Any] = {"manifest": str(manifest_root / (tag + ".manifest.json"))}
            for role in split_hashes:
                sha = _input_hash(manifest, role)
                entry[role] = sha
                if sha is None:
                    _fail(problems, f"{tag}: manifest does not pin a {role} hash")
                else:
                    split_hashes[role].add(sha)

            records = _stream_records(manifest)
            entry["grounding_streams"] = records
            sigma = next((r for r in records if r.get("role") == "sigma_train"), None)
            present = bool(sigma and sigma.get("present", True))
            if arm == args.grounded_arm:
                if not present:
                    _fail(problems, f"{tag}: grounded arm has no sigma_train stream "
                                    "recorded in its manifest")
                else:
                    stream_hashes.add(str(sigma.get("sha256")))
                    if sigma.get("path"):
                        stream_paths.add(str(sigma["path"]))
                    if sigma.get("legacy_record"):
                        _fail(problems, f"{tag}: manifest predates the point-of-use "
                                        "certification block; it carries the stream hash "
                                        "but not the in-run leak check")
                    elif sigma.get("certified_no_leak") is not True:
                        _fail(problems, f"{tag}: the run's own stream certification did "
                                        "not pass (certified_no_leak="
                                        f"{sigma.get('certified_no_leak')})")
            elif arm == args.ungrounded_arm:
                if present:
                    _fail(problems, f"{tag}: the ungrounded arm carries a sigma stream "
                                    "(sha256="
                                    f"{str(sigma.get('sha256'))[:16]}) -- the contrast is "
                                    "not ungrounded-vs-grounded")
                elif sigma is None:
                    _fail(problems, f"{tag}: manifest does not record the ABSENCE of a "
                                    "sigma stream; absence must be asserted, not inferred")
            report["per_run"][tag] = entry

    for role, hashes in split_hashes.items():
        if len(hashes) > 1:
            _fail(problems, f"runs do not share one {role}: {len(hashes)} distinct hashes "
                            f"{sorted(h[:16] for h in hashes)}")
    if len(stream_hashes) > 1:
        _fail(problems, f"grounded runs consumed {len(stream_hashes)} distinct stream "
                        f"builds: {sorted(h[:16] for h in stream_hashes)}")
    report["split_hashes"] = {k: sorted(v) for k, v in split_hashes.items()}
    report["stream_hashes"] = sorted(stream_hashes)
    report["stream_paths"] = sorted(stream_paths)

    # --- 3b. the local splits must BE the pinned splits ---------------------
    # Re-certifying the stream against a different copy of val/test certifies nothing,
    # so the local files are checked against the hashes the runs pinned first.
    local_split_roles = {"val_data": None, "test_data": None}
    for path in args.held_out:
        local = Path(path)
        if not local.exists():
            _fail(problems, f"held-out file for re-certification is missing: {local}")
            continue
        sha = sha256_of(local)
        role = "val_data" if local.name.startswith("val") else "test_data"
        local_split_roles[role] = sha
        pinned = split_hashes.get(role, set())
        if pinned and sha not in pinned:
            _fail(problems, f"{local} is not the {role} the runs pinned "
                            f"(local {sha[:16]}, manifests {sorted(h[:16] for h in pinned)})")
    report["local_held_out_hashes"] = local_split_roles

    # --- 4. recompute the leak check on the deposited stream ---------------
    if args.stream_csv:
        stream_paths = {str(Path(args.stream_csv).resolve())}
    if len(stream_paths) == 1:
        stream_path = Path(next(iter(stream_paths)))
        if stream_path.exists():
            recomputed = certify_stream_disjoint(stream_path, args.held_out)
            report["stream_recertified"] = recomputed
            if not recomputed["certified_no_leak"]:
                _fail(problems, "the deposited stream does NOT re-certify leak-free: "
                                f"{recomputed['leak_by_canonical_smiles']} by canonical "
                                f"SMILES, {recomputed['leak_by_murcko_scaffold']} by "
                                "Murcko scaffold")
            if stream_hashes and recomputed["sha256"] not in stream_hashes:
                _fail(problems, "the stream on disk is not the build the runs consumed "
                                f"(disk {recomputed['sha256'][:16]}, manifests "
                                f"{sorted(h[:16] for h in stream_hashes)}) -- re-certifying "
                                "a different file certifies nothing")
        else:
            _fail(problems, f"the stream the manifests name is not deposited: {stream_path}")
    elif not stream_paths:
        _fail(problems, "no grounded run recorded a stream path; cannot re-certify")

    # --- 5-6. the row lock and the per-seed contrast ------------------------
    lock_reference: set[tuple] | None = None
    per_seed_rows: list[dict[str, Any]] = []
    for seed in args.seeds:
        sdir = results_root / f"seed_{seed}"
        seed_entry: dict[str, Any] = {}
        keysets: dict[str, set[tuple]] = {}
        for arm in args.arms:
            pred = sdir / f"{arm}_predictions.csv"
            if not pred.exists():
                _fail(problems, f"seed {seed}: missing {pred}")
                continue
            keys, n_nonfinite = _row_key_set(pred)
            keysets[arm] = keys
            seed_entry[f"{arm}_n_labelled"] = len(keys)
            seed_entry[f"{arm}_n_nonfinite_pred"] = n_nonfinite
            if n_nonfinite:
                _fail(problems, f"seed {seed} arm {arm}: {n_nonfinite} non-finite "
                                "ln_x2_pred -- the lock stops being arm-independent")
            if len(keys) != args.expect_n_locked:
                _fail(problems, f"seed {seed} arm {arm}: {len(keys)} labelled rows, "
                                f"expected {args.expect_n_locked}")
        if len(keysets) == len(args.arms):
            common = set.intersection(*keysets.values())
            seed_entry["n_locked"] = len(common)
            if lock_reference is None:
                lock_reference = common
            elif common != lock_reference:
                _fail(problems, f"seed {seed}: the locked row set differs from the first "
                                "seed's -- the arms are not on one lock")
            for arm in args.arms:
                seed_entry[f"{arm}_mae"] = _mae_on(sdir / f"{arm}_predictions.csv", common)
            if args.ungrounded_arm in keysets and args.grounded_arm in keysets:
                seed_entry["supervision_gain"] = (
                    seed_entry[f"{args.ungrounded_arm}_mae"]
                    - seed_entry[f"{args.grounded_arm}_mae"]
                )
        comparison = sdir / "comparison.json"
        if comparison.exists():
            payload = json.loads(comparison.read_text())
            seed_entry["comparison_n_locked"] = payload.get("n_locked")
            if payload.get("n_locked") != seed_entry.get("n_locked"):
                _fail(problems, f"seed {seed}: comparison.json n_locked="
                                f"{payload.get('n_locked')} disagrees with the recomputed "
                                f"{seed_entry.get('n_locked')}")
        else:
            _fail(problems, f"seed {seed}: missing {comparison}")
        seed_entry["seed"] = seed
        report["per_seed"][str(seed)] = seed_entry
        per_seed_rows.append(seed_entry)

    gains = [r["supervision_gain"] for r in per_seed_rows if "supervision_gain" in r]
    if gains:
        report["supervision_gain_per_seed"] = gains
        report["supervision_gain_mean"] = float(np.mean(gains))
        report["supervision_gain_sd"] = float(np.std(gains, ddof=1)) if len(gains) > 1 else None
        report["supervision_gain_sign_unanimous"] = bool(
            all(g > 0 for g in gains) or all(g < 0 for g in gains)
        )

    # --- print ------------------------------------------------------------
    print(f"seeds={args.seeds}  arms={args.arms}")
    print("split hashes: " + ", ".join(
        f"{role}={sorted(h)[0][:12] if h else 'MISSING'}" for role, h in split_hashes.items()))
    print("stream build: " + (sorted(stream_hashes)[0][:16] if stream_hashes else "NONE RECORDED"))
    if per_seed_rows:
        header = f"{'seed':>6} {'ungrounded':>12} {'grounded':>12} {'gain':>10} {'n_locked':>9}"
        print(header)
        print("-" * len(header))
        for row in per_seed_rows:
            print(f"{row.get('seed'):>6} "
                  f"{row.get(args.ungrounded_arm + '_mae', float('nan')):>12.4f} "
                  f"{row.get(args.grounded_arm + '_mae', float('nan')):>12.4f} "
                  f"{row.get('supervision_gain', float('nan')):>10.4f} "
                  f"{str(row.get('n_locked', '-')):>9}")
    if gains:
        sd = report["supervision_gain_sd"]
        print(f"gain: mean {report['supervision_gain_mean']:+.4f}"
              + (f" sd {sd:.4f}" if sd is not None else "")
              + f" over {len(gains)} seeds; sign unanimous: "
              + ("yes" if report["supervision_gain_sign_unanimous"] else "NO"))

    report["problems"] = problems
    report["certified"] = not problems
    if args.report:
        Path(args.report).parent.mkdir(parents=True, exist_ok=True)
        Path(args.report).write_text(json.dumps(report, indent=2))
        print(f"certificate written to {args.report}")

    if problems:
        print(f"\nFAILED {len(problems)} check(s):")
        for problem in problems:
            print(f"  - {problem}")
        return 1
    print("\nCERTIFIED: one split, one stream build, one lock, both arms, all seeds.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
