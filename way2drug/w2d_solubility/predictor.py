"""Предсказание растворимости для веб-сервиса: SMILES вещества -> панель растворителей.

ЧТО ЭТО ЗА МОДЕЛЬ. Ансамбль из трёх обученных DirectGNN (сиды 42/43/44), измеренных на
одном и том же расщеплении по остовам: n=5608 размеченных тестовых строк, MAE 1.70 +- 0.03
в единицах ln x2. Это самая точная из моделей проекта; физическая модель со слоем COSMO-SAC
на том же расщеплении идёт позади (1.795 +- 0.071) и вдобавок несёт итеративный поиск
неподвижной точки, у которого число итераций при обучении и при выводе -- разные числа,
и рассогласование сдвигает MAE на величину, большую любого сравнения, ради которого модель
существует. Для публичного сервиса это лишний способ ошибиться молча.

ТРИ ПРИНЦИПА, НА КОТОРЫХ ЭТОТ ФАЙЛ НАПИСАН.

1. Признаки строит тот же самый класс датасета, что и при обучении. Ни одна строчка
   featurisation здесь не повторена: конфиг достаётся из чекпойнта, флаги признаков
   переносятся в загрузчик ПЕРЕСЕЧЕНИЕМ СИГНАТУР. Руками их не перечислить -- их 22, и
   среди них, например, use_pseudo_hansen=True, который по названию модели не угадывается.
2. Порядок строк на выходе обязан совпадать с порядком на входе. Датасет молча выбрасывает
   строки, чьи SMILES не разобрались, поэтому SMILES проверяются ДО сборки таблицы, а
   совпадение длин проверяется утверждением после.
3. Число без границ применимости и без интервала на публичном сервисе вреднее, чем
   отсутствие числа. Ответ всегда несёт и то, и другое.
"""
from __future__ import annotations

import dataclasses
import inspect
import json
import math
import os
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from rdkit import Chem, RDLogger
from rdkit.Chem import Descriptors, rdFingerprintGenerator

from tgnn_solv.baselines.direct_gnn import DirectGNN
from tgnn_solv.config import TGNNSolvConfig
from tgnn_solv.data.dataset import make_loader

RDLogger.DisableLog("rdApp.*")

HERE = Path(__file__).resolve().parent
PKG = HERE.parent
ROOT = PKG.parent

#: Где искать веса. В репозитории они лежат в checkpoints/e5_current_split; в архиве
#: передачи такой структуры нет, поэтому каталог переопределяется переменной окружения --
#: это дешевле, чем править код на принимающей стороне.
_CKPT_DIR = Path(os.environ.get("W2D_CHECKPOINT_DIR")
                 or ROOT / "checkpoints/e5_current_split")
DEFAULT_CHECKPOINTS = sorted(_CKPT_DIR.glob("directgnn_seed*.pt"))
PANEL_PATH = PKG / "solvent_panel.json"
DOMAIN_PATH = PKG / "train_domain.npz"
TEMPLATE_PATH = PKG / "template_row.csv"

#: Служебные аргументы make_loader: их задаёт сервис, а не конфиг обучения.
#:
#: source_uncertainty_csv здесь НЕ случайно. В конфиге обучения он заполнен, и датасет
#: пытается приклеить к каждой строке дисперсию источника, падая на строках, которых в
#: таблице источников нет -- то есть на всех пользовательских. На предсказание он влиять
#: не может: колонка source_sigma_ln_x2 не читается ни одной моделью проекта, только
#: датасетом и функцией потерь. Проверено grep'ом по src/tgnn_solv, а не предположено.
RESERVED_LOADER_ARGS = {
    "batch_size", "shuffle", "num_workers", "seed", "drop_last", "cache",
    "use_pair_temperature_batching", "source_uncertainty_csv",
}
#: Позиционные аргументы forward: их передаём явно, из targets их брать нельзя.
POSITIONAL_FORWARD_ARGS = {"solute_data", "solvent_data", "T"}

#: Порог сходства Танимото к ближайшему обучающему веществу.
#:
#: 0.4 -- обычная граница «похожести» для Morgan/ECFP4 в хемоинформатике, и она здесь не
#: калибрована под точность: это грубый фильтр «модель такого не видела», а не измеренная
#: граница ошибки. Названо порогом предупреждения именно поэтому.
SIMILARITY_WARN = 0.40

#: Разброс между лабораториями для одного и того же измерения, в единицах ln x2.
#: Ниже этого никакая модель не опустится, и интервал сервиса не имеет права быть уже.
ALEATORIC_FLOOR_LN = 0.7

#: Выше этой мольной доли разбавленное приближение для пересчёта в г/л неприменимо.
DILUTE_LIMIT_X2 = 0.1

_FP_GEN = rdFingerprintGenerator.GetMorganGenerator(radius=2, fpSize=2048)


@dataclass
class Prediction:
    """Предсказание для одной пары вещество/растворитель."""
    solvent_smiles: str
    solvent_name: str
    ln_x2: float
    ln_x2_sd_ensemble: float
    ln_x2_interval: tuple[float, float]
    mole_fraction: float
    concentration_g_per_l: float | None
    concentration_note: str

    def as_dict(self) -> dict:
        return {
            "solvent_smiles": self.solvent_smiles,
            "solvent_name": self.solvent_name,
            "ln_x2": round(self.ln_x2, 3),
            "ln_x2_sd_ensemble": round(self.ln_x2_sd_ensemble, 3),
            "ln_x2_interval": [round(self.ln_x2_interval[0], 3),
                               round(self.ln_x2_interval[1], 3)],
            "mole_fraction": float(f"{self.mole_fraction:.4g}"),
            "concentration_g_per_l": (None if self.concentration_g_per_l is None
                                      else float(f"{self.concentration_g_per_l:.4g}")),
            "concentration_note": self.concentration_note,
        }


def canonical_smiles(smiles: str) -> str | None:
    """Канонический SMILES, или None если RDKit структуру не принял."""
    mol = Chem.MolFromSmiles(smiles)
    return None if mol is None else Chem.MolToSmiles(mol)


def _fingerprint(smiles: str) -> np.ndarray | None:
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    arr = np.zeros(2048, dtype=np.uint8)
    for b in _FP_GEN.GetFingerprint(mol).GetOnBits():
        arr[b] = 1
    return arr


class SolubilityPredictor:
    """Ансамбль DirectGNN плюс панель растворителей и область применимости."""

    def __init__(self, checkpoints: list[Path] | None = None, device: str = "cpu") -> None:
        paths = list(checkpoints or DEFAULT_CHECKPOINTS)
        if not paths:
            raise SystemExit(
                f"Не найдено ни одного чекпойнта в {_CKPT_DIR}.\n"                f"  Каталог задаётся переменной W2D_CHECKPOINT_DIR.\n"
                f"  Сервису нужны файлы directgnn_seed*.pt из этой директории.")
        self.device = torch.device(device)
        self.models: list[DirectGNN] = []
        self.loader_kwargs: dict = {}
        self.seeds: list[int] = []
        self.reported_metrics: list[dict] = []

        cfg_fields = {f.name for f in dataclasses.fields(TGNNSolvConfig)}
        loader_sig = set(inspect.signature(make_loader).parameters)

        for path in paths:
            ck = torch.load(path, map_location="cpu", weights_only=False)
            if ck.get("model_class") != "DirectGNN":
                raise SystemExit(f"{path.name}: ожидался DirectGNN, а в чекпойнте "
                                 f"{ck.get('model_class')!r}")
            cfg = TGNNSolvConfig(**{k: v for k, v in ck["config"].items() if k in cfg_fields})
            model = DirectGNN(node_feat_dim=ck["node_feat_dim"],
                              edge_feat_dim=ck["edge_feat_dim"], cfg=cfg)
            model.load_state_dict(ck["model_state"], strict=True)
            model.eval().to(self.device)
            self.models.append(model)
            self.seeds.append(int(ck.get("seed", -1)))
            self.reported_metrics.append(ck.get("test_metrics") or {})

            kwargs = {k: getattr(cfg, k) for k in (loader_sig & cfg_fields) - RESERVED_LOADER_ARGS}
            if self.loader_kwargs and kwargs != self.loader_kwargs:
                # Ансамбль имеет смысл только если все его члены строят признаки одинаково.
                differing = {k for k in kwargs if self.loader_kwargs.get(k) != kwargs[k]}
                raise SystemExit(f"{path.name}: флаги признаков расходятся с остальным "
                                 f"ансамблем по {sorted(differing)}. Усреднять такие модели "
                                 f"нельзя -- они видят разный вход.")
            self.loader_kwargs = kwargs

        self._template = pd.read_csv(TEMPLATE_PATH, low_memory=False)
        self.panel = json.loads(PANEL_PATH.read_text(encoding="utf8"))
        dom = np.load(DOMAIN_PATH)
        self._domain = np.unpackbits(dom["fingerprints"], axis=1).astype(np.uint8)
        self._domain_popcount = self._domain.sum(axis=1)
        env = dom["envelope"]
        self.mw_range = (float(env[0]), float(env[1]))
        self.heavy_range = (float(env[2]), float(env[3]))

    # ------------------------------------------------------------------ область применимости
    def nearest_training_similarity(self, smiles: str) -> float:
        """Максимальный Танимото к обучающим веществам. 1.0 = вещество было в обучении."""
        fp = _fingerprint(smiles)
        if fp is None:
            return float("nan")
        inter = self._domain @ fp
        union = self._domain_popcount + fp.sum() - inter
        with np.errstate(divide="ignore", invalid="ignore"):
            tan = np.where(union > 0, inter / union, 0.0)
        return float(tan.max())

    # ------------------------------------------------------------------ предсказание
    def _predict_pairs(self, pairs: list[tuple[str, str, float]]) -> np.ndarray:
        """ln x2 для каждой пары каждой моделью. Форма (n_models, n_pairs)."""
        rows = []
        for solute, solvent, temperature in pairs:
            r = self._template.iloc[0].copy()
            r["solute_smiles"], r["solvent_smiles"] = solute, solvent
            r["temperature"], r["ln_x2"] = float(temperature), 0.0
            rows.append(r)
        df = pd.DataFrame(rows).reset_index(drop=True)

        loader = make_loader(df, batch_size=64, shuffle=False, num_workers=0, cache=True,
                             use_pair_temperature_batching=False, **self.loader_kwargs)
        # ПОРЯДОК И ПОЛНОТА. Датасет выбрасывает строки с неразобранными SMILES, а сервис
        # обязан вернуть ответ для каждой пары и в том же порядке. Всё, что сюда попало,
        # уже проверено RDKit выше по стеку, поэтому расхождение длины -- это ошибка кода,
        # а не пользовательского ввода, и она должна упасть, а не сдвинуть колонку.
        if len(loader.dataset) != len(df):
            raise RuntimeError(f"датасет оставил {len(loader.dataset)} из {len(df)} строк; "
                               f"выравнивание ответа нарушено")

        out = np.zeros((len(self.models), len(df)), dtype=np.float64)
        for mi, model in enumerate(self.models):
            at = 0
            with torch.no_grad():
                for sol, slv, tgt in loader:
                    fwd = set(inspect.signature(model.forward).parameters)
                    extra = {k: v for k, v in tgt.items()
                             if k in fwd - POSITIONAL_FORWARD_ARGS}
                    pred = model(sol, slv, tgt["T"], **extra)["ln_x2"].squeeze(-1)
                    n = pred.shape[0]
                    out[mi, at:at + n] = pred.cpu().numpy()
                    at += n
            assert at == len(df), f"модель {mi} вернула {at} строк вместо {len(df)}"
        return out

    def predict_panel(self, solute_smiles: str, temperature: float | None = None) -> dict:
        """Полный ответ сервиса для одного вещества по всей панели растворителей."""
        canonical = canonical_smiles(solute_smiles)
        if canonical is None:
            return {"input": solute_smiles, "error": "RDKit не смог разобрать структуру"}

        T = float(temperature if temperature is not None
                  else self.panel["reference_temperature_K"])
        solvents = self.panel["solvents"]
        pairs = [(canonical, s["smiles"], T) for s in solvents]
        raw = self._predict_pairs(pairs)

        similarity = self.nearest_training_similarity(canonical)
        mol = Chem.MolFromSmiles(canonical)
        molar_mass = float(Descriptors.MolWt(mol))

        results = []
        for i, s in enumerate(solvents):
            mean = float(raw[:, i].mean())
            sd = float(raw[:, i].std(ddof=1)) if len(self.models) > 1 else float("nan")
            half = self._interval_half_width(sd)
            x2 = math.exp(mean)
            conc, note = self._to_g_per_l(x2, molar_mass, s)
            results.append(Prediction(
                solvent_smiles=s["smiles"], solvent_name=s["name"],
                ln_x2=mean, ln_x2_sd_ensemble=sd,
                ln_x2_interval=(mean - half, mean + half),
                mole_fraction=x2, concentration_g_per_l=conc, concentration_note=note))

        results.sort(key=lambda p: p.ln_x2, reverse=True)
        return {
            "input": solute_smiles,
            "canonical_smiles": canonical,
            "molar_mass_g_per_mol": round(molar_mass, 3),
            "temperature_K": T,
            "applicability": self._applicability(similarity, T, mol),
            "predictions": [p.as_dict() for p in results],
            "model": self.describe(),
        }

    # ------------------------------------------------------------------ вспомогательное
    @staticmethod
    def _interval_half_width(sd_ensemble: float) -> float:
        """Полуширина интервала: разброс ансамбля, но не уже шума самих измерений.

        Разброс трёх сидов -- это неопределённость обучения, а не полная ошибка: он
        систематически меньше настоящей, потому что все три модели учились на одних данных
        и делят с ними одни и те же смещения. Складывать его с межлабораторным полом
        квадратично -- грубо, но честнее, чем отдавать пользователю голое стандартное
        отклонение ансамбля, которое на порядок оптимистичнее реальности.
        """
        s = 0.0 if (sd_ensemble is None or math.isnan(sd_ensemble)) else float(sd_ensemble)
        return 1.96 * math.sqrt(s * s + ALEATORIC_FLOOR_LN ** 2)

    @staticmethod
    def _to_g_per_l(x2: float, molar_mass: float, solvent: dict) -> tuple[float | None, str]:
        rho = solvent.get("density_g_per_cm3_298K")
        if rho is None:
            return None, (f"нет плотности {solvent['name']} при 298 K в депонированной "
                          f"таблице; мольная доля предсказана как обычно")
        if x2 > DILUTE_LIMIT_X2:
            return None, (f"мольная доля {x2:.3g} выше {DILUTE_LIMIT_X2}: разбавленное "
                          f"приближение неприменимо, пересчёт не даётся")
        # c [моль/л] = x2 * (rho / M_растворителя) * 1000 см3/л, разбавленный предел
        m_solvent = solvent["molar_mass_g_per_mol"]
        c_mol_per_l = x2 * (rho / m_solvent) * 1000.0
        return c_mol_per_l * molar_mass, "разбавленное приближение при 298 K"

    def _applicability(self, similarity: float, T: float, mol) -> dict:
        """Три независимых сторожа: похожесть, размер, температура.

        РАЗМЕР ПРОВЕРЯЕТСЯ ОТДЕЛЬНО ОТ ПОХОЖЕСТИ, потому что двоичный Morgan-фингерпринт
        её не видит: у полимера и его олигомера включены одни и те же биты. На этих
        ассетах макроцикл C21 даёт Танимото 1.000 к циклопропану, а декапептид глицина --
        0.900 к дипептиду. Без второго сторожа сервис объявил бы полимер «внутри области».

        Что НЕ ловится и здесь: молекула обычного размера с необычной топологией -- тот же
        макроцикл C21 лежит внутри конверта по массе и числу атомов. Сходство для него
        завышено, конверт молчит, и предсказание выйдет без предупреждения. Это известное
        ограничение метрики, а не недосмотр; см. MODEL_CARD.md.
        """
        notes = []
        mw = float(Descriptors.MolWt(mol))
        heavy = int(mol.GetNumHeavyAtoms())
        similar_enough = similarity >= SIMILARITY_WARN
        size_ok = (self.mw_range[0] <= mw <= self.mw_range[1]
                   and self.heavy_range[0] <= heavy <= self.heavy_range[1])

        if not similar_enough:
            notes.append(f"ближайшее обучающее вещество похоже лишь на {similarity:.2f} "
                         f"по Танимото (порог {SIMILARITY_WARN}); модель такой химии "
                         f"почти не видела, предсказание ненадёжно")
        if not size_ok:
            notes.append(f"размер вне обучающего диапазона: M={mw:.0f} г/моль "
                         f"({self.mw_range[0]:.0f}-{self.mw_range[1]:.0f}), "
                         f"тяжёлых атомов {heavy} "
                         f"({self.heavy_range[0]:.0f}-{self.heavy_range[1]:.0f}); "
                         f"для полимеров и пептидов предсказание не имеет смысла")
        if similarity >= 0.999:
            notes.append("вещество присутствует в обучающей выборке: это НЕ независимая "
                         "оценка точности")
        if not (273.0 <= T <= 373.0):
            notes.append(f"температура {T:.2f} K вне диапазона, на котором модель обучалась")
        return {
            "nearest_training_similarity": round(similarity, 3),
            "molecular_weight": round(mw, 2),
            "heavy_atoms": heavy,
            "in_domain": bool(similar_enough and size_ok),
            "notes": notes,
        }

    def describe(self) -> dict:
        maes = [float(m["mae"]) for m in self.reported_metrics if m.get("mae") is not None]
        return {
            "name": "TGNN-Solv / DirectGNN ensemble",
            "n_members": len(self.models),
            "seeds": self.seeds,
            "reported_test_mae_ln_x2": [round(m, 4) for m in maes],
            "test_set": "solute-scaffold split, n=5608 labelled rows",
            "aleatoric_floor_ln_x2": ALEATORIC_FLOOR_LN,
        }
