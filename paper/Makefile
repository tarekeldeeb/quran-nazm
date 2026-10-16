# Build the Quran-Nazm paper (ACM acmart, sigconf). Requires pdfLaTeX, BibTeX and the
# libertine, newtx and inconsolata packages (all in a full TeX Live).
main.pdf: main.tex refs.bib acmart.cls ACM-Reference-Format.bst $(wildcard figures/*)
	pdflatex -interaction=nonstopmode main.tex
	bibtex main
	pdflatex -interaction=nonstopmode main.tex
	pdflatex -interaction=nonstopmode main.tex

figures:
	python3 make_figures.py

clean:
	rm -f *.aux *.bbl *.blg *.log *.out build.log

.PHONY: figures clean
