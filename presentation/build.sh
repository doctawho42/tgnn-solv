#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
python generate_molecule_assets.py
python ../scripts/analysis/generate_presentation_figures.py
latexmk -xelatex -interaction=nonstopmode seminar_talk.tex
