#!/bin/bash
# Usage: figtest.sh figures/xxx.tex  -> compiles standalone preview to /tmp/figtest/xxx.png
set -e
cd /home/claude/ProvGuard
f=$1; b=$(basename $f .tex)
mkdir -p /tmp/figtest
cat > /tmp/figtest/$b.tex <<TEX
\documentclass[12pt]{article}
\usepackage[margin=2.5cm,a4paper]{geometry}
\usepackage{amsmath,amssymb,xcolor,tikz,pgfplots}
\usetikzlibrary{arrows.meta,positioning,calc,fit,backgrounds,shapes.geometric,shapes.symbols,shapes.misc,decorations.pathreplacing,patterns,matrix,shadows.blur}
\pgfplotsset{compat=1.18}\usepgfplotslibrary{groupplots,fillbetween}
\input{figures/tikz_styles}
\input{sections/macros}
\pagestyle{empty}
\begin{document}
\noindent\fbox{\parbox{\textwidth}{\centering\input{$f}}}
\end{document}
TEX
TEXINPUTS=.:/home/claude/ProvGuard//: pdflatex -interaction=nonstopmode -output-directory=/tmp/figtest /tmp/figtest/$b.tex > /tmp/figtest/$b.out 2>&1 || { grep -A5 "^!" /tmp/figtest/$b.log | head -30; exit 1; }
grep -E "Overfull|Warning" /tmp/figtest/$b.log | grep -v "Font shape" | head -5
pdftoppm -r 110 -png -singlefile /tmp/figtest/$b.pdf /tmp/figtest/$b
echo OK /tmp/figtest/$b.png
