# Seminar Presentation

Этот каталог содержит отдельную LaTeX Beamer-презентацию для лабораторного семинара.

Важно:

- это отдельная поверхность от `tools/docs_presentation/`, которая остаётся React/MkDocs-презентацией для документации;
- seminar deck собран как автономный `XeLaTeX`-файл, чтобы его можно было быстро править под выступление и PDF-раздачу.

## Файлы

- `seminar_talk.tex` — основной Beamer deck на русском языке
- `talk_text.md` — опорный сценарий выступления по слайдам
- `talk_text_verbatim.md` — разговорная дословная версия для репетиции
- `build.sh` — локальная сборка через генерацию ассетов и `latexmk + xelatex`
- `generate_molecule_assets.py` — генерация RDKit/Pillow molecule assets
- `figures/molecules/` — PNG-рендеры молекул, molecular graph views и TIMP channel highlight
- `../scripts/analysis/generate_presentation_figures.py` — генерация data-backed PDF/PNG графиков
- `figures/generated/` — корпусные гистограммы, NRTL/SLE curves, sensitivity и diagnostic plots

Актуальные KNN/modelability assets для ответа на критику:

- `figures/generated/knn_summary_table.{pdf,png,csv}`
- `figures/generated/knn_vs_adaptive_benchmarks.{pdf,png}`
- `figures/generated/knn_controlled_subset_comparison.{pdf,png}`
- `figures/generated/knn_modelability_diagnostics.{pdf,png}`

## Сборка

```bash
cd presentation
bash build.sh
```

Ожидаемые зависимости:

- `latexmk`
- `xelatex`
- пакеты `beamer`, `fontspec`, `polyglossia`, `tikz`, `pgfplots`
- шрифты `PT Serif`, `PT Sans`, `PT Mono`

Molecule assets уже сгенерированы и лежат в `figures/molecules/`. Если нужно
пересоздать их после изменения SMILES или стиля:

```bash
cd presentation
python generate_molecule_assets.py
python ../scripts/analysis/generate_presentation_figures.py
bash build.sh
```

`build.sh` уже запускает оба генератора перед `latexmk`.
Для molecule assets нужны `rdkit` и `Pillow`. Для графиков нужны
`matplotlib`, `numpy`, опционально `pandas` и `rdkit`; если processed CSV или
RDKit недоступны, генератор использует synthetic/fallback данные, чтобы Beamer
сборка не ломалась.

## Тема

Файл использует:

- `Madrid` как стабильную Beamer-тему;
- отключённые navigation symbols и headline;
- собственный компактный footline с номером кадра;
- rounded blocks без теней, чтобы избежать PGF/nullfont warnings в TeX Live 2022.
- визуальный язык, близкий к React-презентации в `tools/docs_presentation/`:
  светлая поверхность, синяя пастельная верхняя плашка, flat bullets, rounded
  cards без объёмных 2007-style эффектов, синий/оранжевый как устойчивые цвета
  TGNN/TIMP каналов.

## Speaker Notes

Во всех кадрах добавлены `\note{...}` для спикера.

По умолчанию в PDF они скрыты:

```tex
\setbeameroption{hide notes}
```

Если нужен handout с notes-pages, это можно переключить вручную в преамбуле.

В текущей версии deck содержит `112` логических Beamer-кадров для расширенного
семинарского рассказа. Основной доклад перестроен под последовательность:
обозначения → данные → цель и задачи → физика → архитектура → обучение →
диагностика → обновления модели → приложения. Планы и абляции вынесены в раздел
`Дополнение`, чтобы не перегружать основной нарратив. На выводных
физико-математических слайдах включены `\pause`, поэтому обычный PDF содержит
больше страниц, чем кадров: один шаг пошагового появления разворачивается
в отдельную PDF-страницу. Текущая сборка даёт `154` PDF-страниц при `112`
логических кадрах.

## Структура

- постановка задачи, ранние обозначения, BigSolDB, IDAC, вода в размеченном подмножестве и протокол разбиений;
- цель и задачи проекта;
- базовое введение в параметры Хансена, молекулярные графы, GNN, Set2Set и дескрипторы;
- физический фундамент SLE/NRTL, числовые примеры и дифференцируемый решатель;
- архитектура TGNN-Solv: GC-приоры, перекрёстное внимание, MoE по типам растворителей, температурное кодирование и ограниченная коррекция;
- предобучение этапа 0, curriculum, 12 компонент функции потерь и регуляризаторы;
- диагностика, TIMP с визуальными слайдами на уровне связи, SASA-взвешенным выходным блоком, физическими признаками рёбер, зарядами Gasteiger и супервизией каналов;
- результаты, неопределённость/OOD, приложения, Experiment Lab, резюме;
- дополнение: Wilson/UNIQUAC, запланированные эксперименты, абляции и дорожная карта.

Если нужна handout-версия строго по одной странице на кадр, можно временно
добавить опцию `handout` в `\documentclass[...]` в `seminar_talk.tex`.

## Источники содержания

Основные формулы, числа и narrative deck синхронизированы с:

- `main.tex`
- актуальным состоянием `configs/`, `src/tgnn_solv/`
- canonical processed corpus в `notebooks/data/processed/`

На слайдах с TIMP часть утверждений помечена как гипотеза/ожидание, если это ещё не зафиксированный экспериментальный результат.
