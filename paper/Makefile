# Build the Quran-Nazm paper. Requires XeLaTeX, BibTeX and the TeX Gyre fonts.
main.pdf: main.tex refs.bib IEEEtran.cls IEEEtran.bst $(wildcard figures/*)
	xelatex -interaction=nonstopmode main.tex
	bibtex main
	xelatex -interaction=nonstopmode main.tex
	xelatex -interaction=nonstopmode main.tex

figures:
	python3 make_figures.py

clean:
	rm -f *.aux *.bbl *.blg *.log *.out build.log

.PHONY: figures clean
