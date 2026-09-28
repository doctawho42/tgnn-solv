#!/usr/bin/env python
"""Где именно выученный sigma-профиль расходится с депонированным, бин за бином.

ЗАЧЕМ ЭТО ИЗМЕРЕНИЕ. Обе половины статьи живут в пространстве ОШИБКИ: граница говорит,
что доминирует misspecification замыкания, локализация -- на какой химии. Здесь измеряется
сам ВХОД: разность между профилем, который выдаёт энкодер, и тем, который подставляется
при замене. Раз это один и тот же массив на одной сетке (проверено 2026-09-28), вычитание
корректно поточечно.

ЧТО ПРОВЕРЯЕТСЯ. Предсказание из границы: остаток должен скапливаться в ДОНОРНОЙ области.
В статье это уже показано на четырёх молекулах отозванного прогона -- 44.0, 32.4, 24.5 и
50.7 A^2 донорной площади у выученного профиля против ровно 0.000 в эталоне. Здесь то же
самое измеряется помолекулярно, на плечах записи (grounded_a, сиды 42-46), и с числом,
которое ложится на шкалу Salih et al., Digital Discovery 2025, 4, 2711 (10.1039/d5dd00087d).

ПОЧЕМУ ОБЛАСТИ БЕРУТСЯ ПО ЯДРУ 2002, А НЕ ПО ТИПИЗАЦИИ 2010. Заголовочное плечо работает
на ядре 2002 с ОДНИМ нетипизированным профилем в 51 бин -- оракул грузит n_bins=51.
Разбиение NHB/OH/OT живёт в ядре 2010 на сетке 153 и к этим профилям неприменимо: у них
нет типа. Зато у ядра 2002 есть собственный порог: водородная связь включается за
|sigma| > sigma_hb, и он же задаёт три области. Это разбиение из самого ядра, а не
изобретённое здесь.

ПРОФИЛЬ СНИМАЕТСЯ ХУКОМ, А НЕ ПЕРЕСЧИТЫВАЕТСЯ. head_sigma читает ПРЕДвзаимодействующий
эмбеддинг молекулы, поэтому профиль зависит только от молекулы; forward прогоняется на
self-парах, а значения берутся ровно те, что модель подала в замыкание.

    python scripts/analysis/run_sigma_profile_residual.py
    python scripts/analysis/run_sigma_profile_residual.py --limit 40   # быстрый прогон
"""
from __future__ import annotations

import argparse
import dataclasses
import inspect
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from tgnn_solv.config import TGNNSolvConfig            # noqa: E402
from tgnn_solv.data.dataset import make_loader         # noqa: E402
from tgnn_solv.model import TGNNSolv                   # noqa: E402
from tgnn_solv.sigma_oracle import load_sigma_profiles  # noqa: E402

CKPT_DIR = ROOT / "checkpoints/e5_leakfree"
PROFILES = ROOT / "results/sigma_profile_artifact/sigma_profiles.csv"
TEST = ROOT / "notebooks/data/processed/test.csv"
OUT_DIR = ROOT / "results/sigma_profile_residual"

#: Служебные аргументы make_loader; см. way2drug/w2d_solubility/predictor.py, там же
#: объяснено, почему source_uncertainty_csv отключается (на предсказание не влияет).
RESERVED = {"batch_size", "shuffle", "num_workers", "seed", "drop_last", "cache",
            "use_pair_temperature_batching", "source_uncertainty_csv"}


def hellinger(p: np.ndarray, q: np.ndarray) -> float:
    """H(p,q) = sqrt(1/2 * sum (sqrt(p)-sqrt(q))^2), формула (9) Salih et al.

    Профили НЕнормированы (площадь в A^2), как и у них, поэтому H тоже в sqrt(A^2).
    """
    return float(np.sqrt(0.5 * np.sum((np.sqrt(np.clip(p, 0, None))
                                       - np.sqrt(np.clip(q, 0, None))) ** 2)))


def hellinger_to_delta(p: np.ndarray, grid: np.ndarray) -> float:
    """H до дельта-функции той же площади -- метрика «сколько информации в профиле».

    Дельта ставится в бин, ближайший к средневзвешенному заряду профиля: это и есть
    «нулевая информация», когда от профиля остаётся только суммарный заряд и площадь.
    """
    area = float(p.sum())
    if area <= 0:
        return float("nan")
    centre = int(np.argmin(np.abs(grid - float((p * grid).sum() / area))))
    delta = np.zeros_like(p)
    delta[centre] = area
    return hellinger(p, delta)


def build_model(ckpt: Path) -> tuple[TGNNSolv, dict, TGNNSolvConfig]:
    ck = torch.load(ckpt, map_location="cpu", weights_only=False)
    fields = {f.name for f in dataclasses.fields(TGNNSolvConfig)}
    cfg = TGNNSolvConfig(**{k: v for k, v in ck["config"].items() if k in fields})
    model = TGNNSolv(node_feat_dim=ck["node_feat_dim"],
                     edge_feat_dim=ck["edge_feat_dim"], cfg=cfg)
    state = ck.get("model_state") or ck["model_state_dict"]
    missing, unexpected = model.load_state_dict(state, strict=False)
    if missing:
        raise SystemExit(f"{ckpt.name}: не загрузились веса {missing[:5]} "
                         f"(всего {len(missing)}) -- профиль был бы от неинициализированной головы")
    model.eval()
    return model, ck, cfg


def learned_profiles(model: TGNNSolv, cfg: TGNNSolvConfig,
                     smiles: list[str], template: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Профили в РОЛИ растворяемого и в РОЛИ растворителя, (n_mol, n_bins) каждый.

    РОЛЬ ИМЕЕТ ЗНАЧЕНИЕ, И ЭТО ИЗМЕРЕНО, А НЕ ПРЕДПОЛОЖЕНО. Энкодер собран с
    encoder_role_mode="shared_residual" и двумя role-specific слоями, поэтому одна и та же
    молекула получает РАЗНЫЙ профиль в зависимости от того, какую сторону пары она занимает:
    этанол выходит с площадью 88.3 A^2 как растворяемое и 108.0 A^2 как растворитель.
    Эталонный профиль при этом один на молекулу. ПОПРАВЛЕНО 2026-09-28: раньше здесь стояло
    «и оракул подставляет его в ОБА слота» -- это неверно. По размеченным строкам теста 7704
    подставляются только в слоте растворителя, 354 в обеих ролях, 8 только в слоте растворяемого.
    Механизм -- «безролевой массив попадает не в своё распределение в том слоте, который
    вытесняет, почти всегда в слот растворителя», а не «один массив в оба слота».

    От партнёра профиль при этом НЕ зависит: этанол-как-растворяемое даёт 88.281 A^2 с водой,
    бензолом и ацетонитрилом с точностью 3e-06. Первая функция здесь -- это проверить, а вторая
    -- не смешать одно с другим.
    """
    captured: list[torch.Tensor] = []
    handle = model.head_sigma.register_forward_hook(
        lambda _m, _i, out: captured.append(out["p_sigma"].detach().cpu()))
    try:
        rows = []
        for smi in smiles:
            r = template.iloc[0].copy()
            r["solute_smiles"] = r["solvent_smiles"] = smi     # self-пара: обе роли за прогон
            r["temperature"], r["ln_x2"] = 298.15, 0.0
            rows.append(r)
        df = pd.DataFrame(rows).reset_index(drop=True)

        sig = set(inspect.signature(make_loader).parameters)
        fields = {f.name for f in dataclasses.fields(TGNNSolvConfig)}
        kwargs = {k: getattr(cfg, k) for k in (sig & fields) - RESERVED}
        loader = make_loader(df, batch_size=64, shuffle=False, num_workers=0, cache=True,
                             use_pair_temperature_batching=False, **kwargs)
        if len(loader.dataset) != len(df):
            raise RuntimeError(f"датасет оставил {len(loader.dataset)} из {len(df)} строк")

        with torch.no_grad():
            for sol, slv, tgt in loader:
                fwd = set(inspect.signature(model.forward).parameters)
                extra = {k: v for k, v in tgt.items()
                         if k in fwd - {"solute_data", "solvent_data", "T"}}
                model(sol, slv, tgt["T"], **extra)
    finally:
        handle.remove()

    # head_sigma зовётся ДВАЖДЫ НА БАТЧ (сначала solute, потом solvent), а не дважды на строку.
    if len(captured) % 2:
        raise RuntimeError(f"нечётное число вызовов хука ({len(captured)}): разбор по ролям неверен")
    as_solute = np.vstack([c.numpy() for c in captured[0::2]])
    as_solvent = np.vstack([c.numpy() for c in captured[1::2]])
    if as_solute.shape != as_solvent.shape or len(as_solute) != len(smiles):
        raise RuntimeError(f"формы не сошлись: {as_solute.shape} / {as_solvent.shape} "
                           f"на {len(smiles)} молекул")
    return as_solute, as_solvent


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="взять только N молекул")
    ap.add_argument("--seeds", type=int, nargs="*", default=None)
    args = ap.parse_args()

    cks = sorted(CKPT_DIR.glob("grounded_a_seed*.pt"))
    if args.seeds:
        cks = [p for p in cks if any(f"seed{s}" in p.name for s in args.seeds)]
    if not cks:
        print(f"нет чекпойнтов в {CKPT_DIR}")
        return 1

    _, _, cfg0 = build_model(cks[0])
    n_bins = int(cfg0.cosmo_sac_n_bins)
    grid = np.linspace(cfg0.cosmo_sac_sigma_min, cfg0.cosmo_sac_sigma_max, n_bins)
    s_hb = float(cfg0.cosmo_sac_sigma_hb)
    donor = grid <= -s_hb          # ядро 2002 включает HB за |sigma| > sigma_hb
    acceptor = grid >= s_hb
    nonpolar = ~(donor | acceptor)
    print(f"сетка: {n_bins} бинов, sigma в [{grid[0]:.3f}, {grid[-1]:.3f}], "
          f"порог ядра {s_hb}; донор {donor.sum()} бинов, неполярная {nonpolar.sum()}, "
          f"акцептор {acceptor.sum()}")

    table = load_sigma_profiles(str(PROFILES), n_bins=n_bins)
    test = pd.read_csv(TEST, low_memory=False)
    scored = test[test["ln_x2"].notna()]
    seen = set(scored["solute_smiles"].astype(str)) | set(scored["solvent_smiles"].astype(str))

    from tgnn_solv.data.utils import canonicalize
    mols = sorted({s for s in seen if (c := canonicalize(str(s))) is not None and c in table})
    if args.limit:
        mols = mols[:args.limit]
    print(f"молекул со сверяемым профилем, встречающихся в размеченном тесте: {len(mols)}")
    if not mols:
        print("пересечение пусто -- сверять нечего")
        return 1

    template = pd.read_csv(TEST, nrows=1, low_memory=False)
    ref = np.vstack([table[canonicalize(str(m))][0] for m in mols])

    per_seed, records = {}, []
    for ck in cks:
        model, ckd, cfg = build_model(ck)
        seed = int(ckd.get("seed", -1))
        print(f"  сид {seed}: прогоняю {len(mols)} молекул ...", flush=True)
        sol_p, slv_p = learned_profiles(model, cfg, mols, template)
        per_seed[seed] = (sol_p, slv_p)
        for i, smi in enumerate(mols):
            rp = ref[i]
            rec = {"seed": seed, "smiles": smi,
                   "area_reference": float(rp.sum()),
                   "donor_area_reference": float(rp[donor].sum()),
                   "hellinger_reference_to_delta": hellinger_to_delta(rp, grid),
                   # расхождение РОЛЕЙ: у эталона его нет по построению, у выученного есть
                   "hellinger_solute_vs_solvent": hellinger(sol_p[i], slv_p[i])}
            # БАЗОВАЯ ЛИНИЯ -- ДОЛЯ ПЛОЩАДИ, А НЕ ДОЛЯ БИНОВ. Первая версия сравнивала
            # долю остатка с долей бинов сетки (1/3 на окно) и объявляла остаток
            # «сконцентрированным в центре». Это неверная база: sigma-профиль органической
            # молекулы резко пикован около нуля, у половины этих растворителей донорная
            # площадь эталона ровно 0.00, то есть площадь и так почти вся в центре.
            # Правильный вопрос -- обогащение: доля остатка, делённая на долю ПЛОЩАДИ в том
            # же окне. Обогащение около 1 означает, что остаток пропорционален площади,
            # то есть НЕ структурирован; это слабее и честнее, чем «сконцентрирован».
            for reg, msk in (("donor", donor), ("nonpolar", nonpolar), ("acceptor", acceptor)):
                rec[f"area_frac_reference_{reg}"] = float(rp[msk].sum() / (rp.sum() or np.nan))
            for role, lp in (("solute", sol_p[i]), ("solvent", slv_p[i])):
                resid = lp - rp
                tot = float(np.abs(resid).sum()) or float("nan")
                rec.update({
                    f"hellinger_{role}_vs_reference": hellinger(lp, rp),
                    f"hellinger_{role}_to_delta": hellinger_to_delta(lp, grid),
                    f"area_{role}": float(lp.sum()),
                })
                for reg, msk in (("donor", donor), ("nonpolar", nonpolar),
                                 ("acceptor", acceptor)):
                    rf = float(np.abs(resid[msk]).sum() / tot)
                    # база: средняя доля площади двух профилей, которые и вычитаются
                    af = 0.5 * (float(lp[msk].sum() / (lp.sum() or np.nan))
                                + float(rp[msk].sum() / (rp.sum() or np.nan)))
                    rec[f"area_{reg}_{role}"] = float(lp[msk].sum())
                    rec[f"area_frac_{reg}_{role}"] = af
                    rec[f"resid_frac_{reg}_{role}"] = rf
                    rec[f"enrichment_{reg}_{role}"] = float(rf / af) if af else float("nan")
            records.append(rec)

    df = pd.DataFrame(records)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_DIR / "per_molecule.csv", index=False)

    # Доля бинов в каждой области -- база сравнения. Без неё «40% остатка в доноре»
    # ничего не значит: если донор и есть 40% сетки, это ровно ожидание.
    base = {"donor": float(donor.mean()), "nonpolar": float(nonpolar.mean()),
            "acceptor": float(acceptor.mean())}
    donor_free = df["donor_area_reference"] <= 1e-9
    summary = {
        "n_molecules": len(mols), "seeds": sorted(per_seed),
        "sigma_hb": s_hb, "bin_fraction_by_region": base,
        "median_hellinger_to_reference": {
            r: float(df[f"hellinger_{r}_vs_reference"].median()) for r in ("solute", "solvent")},
        "median_hellinger_role_gap": float(df["hellinger_solute_vs_solvent"].median()),
        "median_hellinger_to_delta": {
            "solute": float(df["hellinger_solute_to_delta"].median()),
            "solvent": float(df["hellinger_solvent_to_delta"].median()),
            "reference": float(df["hellinger_reference_to_delta"].median())},
        "median_resid_frac": {
            r: {reg: float(df[f"resid_frac_{reg}_{r}"].median())
                for reg in ("donor", "nonpolar", "acceptor")} for r in ("solute", "solvent")},
        "median_area_frac": {
            r: {reg: float(df[f"area_frac_{reg}_{r}"].median())
                for reg in ("donor", "nonpolar", "acceptor")} for r in ("solute", "solvent")},
        "median_enrichment": {
            r: {reg: float(df[f"enrichment_{reg}_{r}"].median())
                for reg in ("donor", "nonpolar", "acceptor")} for r in ("solute", "solvent")},
        "donor_free_reference_molecules": int(df.loc[donor_free, "smiles"].nunique()),
        "median_donor_area_where_reference_is_zero": {
            r: float(df.loc[donor_free, f"area_donor_{r}"].median()) for r in ("solute", "solvent")},
    }
    (OUT_DIR / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf8")

    print(f"\n{'':30s}{'донор':>10}{'неполярн':>11}{'акцептор':>11}")
    print(f"  {'доля бинов сетки':28s}{base['donor']:>10.3f}{base['nonpolar']:>11.3f}"
          f"{base['acceptor']:>11.3f}")
    for r in ("solute", "solvent"):
        a = summary["median_area_frac"][r]
        m = summary["median_resid_frac"][r]
        e = summary["median_enrichment"][r]
        print(f"  {'доля ПЛОЩАДИ, ' + r:28s}{a['donor']:>10.3f}{a['nonpolar']:>11.3f}"
              f"{a['acceptor']:>11.3f}")
        print(f"  {'доля |остатка|, ' + r:28s}{m['donor']:>10.3f}{m['nonpolar']:>11.3f}"
              f"{m['acceptor']:>11.3f}")
        print(f"  {'ОБОГАЩЕНИЕ, ' + r:28s}{e['donor']:>10.2f}{e['nonpolar']:>11.2f}"
              f"{e['acceptor']:>11.2f}")
    print(f"\n  H(выученный, эталон): растворяемое "
          f"{summary['median_hellinger_to_reference']['solute']:.3f}, растворитель "
          f"{summary['median_hellinger_to_reference']['solvent']:.3f}")
    print(f"  H между РОЛЯМИ одной молекулы:     "
          f"{summary['median_hellinger_role_gap']:.3f}   (у эталона роли нет вовсе)")
    d = summary["median_hellinger_to_delta"]
    print(f"  H до delta (шкала Salih): выученный {d['solute']:.3f}/{d['solvent']:.3f}, "
          f"эталон {d['reference']:.3f}")
    print(f"\n  молекул с НУЛЕВОЙ донорной площадью в эталоне: "
          f"{summary['donor_free_reference_molecules']}")
    z = summary["median_donor_area_where_reference_is_zero"]
    print("  у них медианная донорная площадь выученного: "
          f"{z['solute']:.2f} / {z['solvent']:.2f} A^2 (растворяемое / растворитель)")
    print(f"\nзаписано: {OUT_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
