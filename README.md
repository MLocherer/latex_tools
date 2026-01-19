# latex_tools
a set of python helpers to work with latex created with copilot

## scanarconyms.py
used to scan acronyms in your latex document when using the glossaries package. Acronym frequency, acronym replacement, for less used acronyms. Recreation of acronym definitions based on usage.

usage:
```
$ python scanacronyms.py -h
usage: scanacronyms.py [-h] [--update] [--min-count MIN_COUNT] mainfile

Scan LaTeX project for glossary acronym usage and definitions.

positional arguments:
  mainfile              Main LaTeX file (e.g., main.tex)

options:
  -h, --help            show this help message and exit
  --update              Enable interactive replacement of low‑usage acronyms.
  --min-count MIN_COUNT
                        Minimum number of acronym uses required before replacement is suggested.
```

## filterbib.py
filter a *bib file based on particular regular expressions and usage in your document to obtain a slim version of your document that can be shared w/ others, e.g. conferences etc.

```
$ python filterbib.py -h
usage: filterbib.py [-h] [-o OUTPUT] texfile [bibfile]

Extract only the cited BibTeX entries from a LaTeX project.

positional arguments:
  texfile               Main LaTeX .tex file
  bibfile               BibTeX .bib file (optional if \addbibresource is used)

options:
  -h, --help            show this help message and exit
  -o OUTPUT, --output OUTPUT
                        Output .bib file (default: filtered.bib)
```
