# Build the manuscript PDF.
#
#   make          manuscript.pdf (latexmk)
#   make numbers  regenerate numbers.tex from ../tables (run after the analysis scripts)
#   make draft    also copies it to PathoFluor-At_draft.pdf
#   make check    every \cite resolves and nothing in references.bib is uncited
#   make clean    remove build artefacts

.PHONY: all numbers draft check clean

all: supplementary.pdf manuscript.pdf

numbers:
	cd .. && .venv/bin/python scripts/07_numbers.py > /dev/null

manuscript.pdf: manuscript.tex sections/methods.tex numbers.tex references.bib $(wildcard ../figures/*.pdf)
	latexmk -pdf -interaction=nonstopmode -halt-on-error manuscript.tex

supplementary.pdf: supplementary.tex numbers.tex $(wildcard generated/*.tex) $(wildcard ../figures/*.pdf)
	latexmk -pdf -interaction=nonstopmode -halt-on-error supplementary.tex

draft: all
	cp manuscript.pdf PathoFluor-At_draft.pdf
	cp supplementary.pdf PathoFluor-At_supplement_draft.pdf

check:
	@python3 -c "import re;s=open('manuscript.tex').read()+open('sections/methods.tex').read();c={k.strip() for g in re.findall(r'\\\\cite[pt]?\{([^}]*)\}',s) for k in g.split(',')};b=set(re.findall(r'^@\w+\{([^,]+),',open('references.bib').read(),re.M));print('undefined:',sorted(c-b) or 'none');print('uncited:',sorted(b-c) or 'none');exit(bool(c-b or b-c))"

clean:
	latexmk -C manuscript.tex supplementary.tex 2>/dev/null || true
