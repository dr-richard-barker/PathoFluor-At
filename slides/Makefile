# Build the slide deck: make  ->  PathoFluor-At_slides.pdf
.PHONY: all clean
all: PathoFluor-At_slides.pdf
PathoFluor-At_slides.pdf: slides.tex ../manuscript/numbers.tex $(wildcard ../figures/*.pdf)
	latexmk -pdf -interaction=nonstopmode -halt-on-error slides.tex
	cp slides.pdf PathoFluor-At_slides.pdf
clean:
	latexmk -C slides.tex 2>/dev/null || true
