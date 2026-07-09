# Build the "Grounding Paradox" manuscript.
#   make            -> grounding_paradox.pdf (pdflatex + bibtex + 2 passes)
#   make clean      -> remove LaTeX aux files
#   make distclean  -> also remove the PDF
#
# The figures (figs/*.pdf) and the numbers in the tables are produced by the
# analysis scripts named in the Data-and-code-availability section:
#   - Fig. paradox / chemistry map : scripts/analysis/run_e5_comparison.py over
#     results/e5_sigma_grounding/seed_{42,43,44}/  (see ../results/e5_sigma_grounding/THREE_SEED_SUMMARY.md)
#   - Table 2 (closure/insufficiency): scripts/analysis/run_b_insuff_decomposition.py
#     -> results/b_insuff/decomposition.json
# Regenerate those artifacts first, then `make` to rebuild the PDF.

MAIN = grounding_paradox
LATEX = pdflatex -interaction=nonstopmode -halt-on-error
BIBTEX = bibtex

.PHONY: all clean distclean
all: $(MAIN).pdf

$(MAIN).pdf: $(MAIN).tex references_verified.bib sections/*.tex figs/*.pdf
	$(LATEX) $(MAIN).tex
	-$(BIBTEX) $(MAIN)
	$(LATEX) $(MAIN).tex
	$(LATEX) $(MAIN).tex

clean:
	rm -f $(MAIN).aux $(MAIN).bbl $(MAIN).blg $(MAIN).log $(MAIN).out $(MAIN).toc

distclean: clean
	rm -f $(MAIN).pdf
