# latex_tools
a set of python helpers to work with latex created with copilot

# scanarconyms.py
used to scan acronyms in your latex document when using the glossaries package. Acronym frequency, acronym replacement, for less used acronyms. Recreation of acronym definitions based on usage.

usage:
```
python scanacronyms.py /home/documents/manuscript.tex --min-count 4
```

# filterbib.py
filter a *bib file based on particular regular expressions and usage in your document to obtain a slim version of your document that can be shared w/ others, e.g. conferences etc.
