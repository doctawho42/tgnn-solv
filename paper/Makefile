# Build the "Grounding Paradox" submission, which is TWO documents:
#   grounding_paradox.tex     the article
#   grounding_paradox_si.tex  the Supporting Information (ACS deposits it separately)
#
#   make            -> both PDFs
#   make article    -> the article only        (SI cross-references may be stale)
#   make si         -> the Supporting Information only  (ditto, the other way)
#   make clean      -> remove LaTeX aux files of both
#   make distclean  -> also remove both PDFs
#
# XELATEX, NOT PDFLATEX. The manuscript is set in STIX Two Text through fontspec;
# this Makefile used to say pdflatex, which is not what the documented build uses.
#
# WHY `all' RUNS THE TWO INTERLEAVED. The documents cross-reference each other through
# xr-hyper (see preamble.tex), and xr-hyper reads the OTHER document's .aux at the top
# of a run. So each document needs a pass after the other one has written its .aux, and
# the section/table/figure numbers only settle after both have been rebuilt on settled
# input. From clean that is: both, bibtex both, both, both. Running `make article'
# alone from clean leaves this document's references into the SI printing as `??' --
# LaTeX calls that a warning, not an error, so it will NOT stop the build. `make check'
# is the guard: it greps both logs for undefined references and fails if there are any.
#
# The figures (figs/*.pdf) and the numbers in the tables are produced by the
# analysis scripts named in the Data-and-code-availability section:
#   - Fig. paradox / chemistry map : scripts/analysis/run_e5_comparison.py over
#     results/e5_sigma_grounding/seed_{42,43,44}/  (see ../results/e5_sigma_grounding/THREE_SEED_SUMMARY.md)
#   - Table 2 (closure/insufficiency): scripts/analysis/run_b_insuff_decomposition.py
#     -> results/b_insuff/decomposition.json
# Regenerate those artifacts first, then `make' to rebuild the PDFs.

MAIN  = grounding_paradox
SI    = grounding_paradox_si
LATEX = xelatex -interaction=nonstopmode
BIBTEX = bibtex

SRC = preamble.tex references_verified.bib sections/*.tex si_tables/*.tex figs/*.pdf

.PHONY: all both article si check clean distclean
all: both

both: $(MAIN).tex $(SI).tex $(SRC)
	$(LATEX) $(MAIN).tex
	$(LATEX) $(SI).tex
	-$(BIBTEX) $(MAIN)
	-$(BIBTEX) $(SI)
	$(LATEX) $(MAIN).tex
	$(LATEX) $(SI).tex
	$(LATEX) $(MAIN).tex
	$(LATEX) $(SI).tex

article: $(MAIN).tex $(SRC)
	$(LATEX) $(MAIN).tex
	-$(BIBTEX) $(MAIN)
	$(LATEX) $(MAIN).tex
	$(LATEX) $(MAIN).tex

si: $(SI).tex $(SRC)
	$(LATEX) $(SI).tex
	-$(BIBTEX) $(SI)
	$(LATEX) $(SI).tex
	$(LATEX) $(SI).tex

# Undefined references are warnings in LaTeX, and a split submission is exactly where
# they appear silently. This is the gate.
check:
	@python3 ../scripts/analysis/check_split_refs.py

clean:
	rm -f $(MAIN).aux $(MAIN).bbl $(MAIN).blg $(MAIN).log $(MAIN).out $(MAIN).toc $(MAIN).xdv
	rm -f $(SI).aux $(SI).bbl $(SI).blg $(SI).log $(SI).out $(SI).toc $(SI).xdv

distclean: clean
	rm -f $(MAIN).pdf $(SI).pdf
