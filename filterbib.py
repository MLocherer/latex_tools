import re
import os
import argparse
from collections import Counter

# -----------------------------
# Regex patterns
# -----------------------------

CITE_PATTERN = re.compile(
    r'\\(?:cite|parencite|textcite|autocite|footcite|citep|citet)'
    r'(?:\[[^\]]*\])*'     # zero or more optional arguments
    r'\{([^}]*)\}'         # required argument with citation keys
)

INPUT_PATTERN = re.compile(r'\\(?:input|include)\{([^}]*)\}')
BIBRESOURCE_PATTERN = re.compile(r'\\addbibresource\{([^}]*)\}')
BIBLIOGRAPHY_PATTERN = re.compile(r'\\bibliography\{([^}]*)\}')
ENTRY_START = re.compile(r'@\w+\{([^,]+),')

# fields in the bibtex entries
ALLOWED_FIELDS = [
    "author", "title", "publisher", "address",
    "year", "journal", "booktitle", "note", "volume", 
    "pages", "number", "doi"
]

ALLOWED_SET = set(ALLOWED_FIELDS)


# -----------------------------
# 1. Parse LaTeX project
# -----------------------------

def read_tex_recursive(path, visited=None):
    """Reads a .tex file and all recursively included files."""
    if visited is None:
        visited = set()

    if path in visited:
        return ""

    visited.add(path)

    if not os.path.exists(path):
        return ""

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # Find included files
    for inc in INPUT_PATTERN.findall(content):
        inc_path = inc if inc.endswith(".tex") else inc + ".tex"
        if os.path.exists(inc_path):
            content += "\n" + read_tex_recursive(inc_path, visited)
            
    return content


def extract_citations(tex_content):
    """Extract citation keys and count occurrences."""
    citations = Counter()

    matches = CITE_PATTERN.findall(tex_content)
    
    for match in matches:
        for key in match.split(","):
            key = key.strip()
            if key:
                citations[key] += 1

    return citations


def extract_bib_files(tex_content):
    """Detect bibliography files from \\addbibresource and \\bibliography commands."""
    bibs = []

    # BibLaTeX: \addbibresource{file.bib}
    for bib in BIBRESOURCE_PATTERN.findall(tex_content):
        if bib.endswith(".bib"):
            bibs.append(bib)

    # Classic LaTeX: \bibliography{file1,file2}
    for group in BIBLIOGRAPHY_PATTERN.findall(tex_content):
        for bib in group.split(","):
            bib = bib.strip()
            if not bib:
                continue

            # Add .bib extension if missing
            if not bib.endswith(".bib"):
                bib = bib + ".bib"

            bibs.append(bib)

    return bibs



# -----------------------------
# 2. Extract relevant BibTeX entries
# -----------------------------
def filter_bib_fields(entry_text):
    """Keep only allowed fields, normalize formatting, and pretty-print."""
    lines = entry_text.splitlines()
    header = lines[0]  # e.g. @article{key,
    fields = {}
    current_field = None
    buffer = []

    # Parse fields
    for line in lines[1:]:
        stripped = line.strip()

        # End of entry
        if stripped == "}":
            break

        # Field start?
        if "=" in stripped:
            # Save previous field
            if current_field and current_field in ALLOWED_SET:
                fields[current_field] = " ".join(buffer).strip()

            # Start new field
            name, value = stripped.split("=", 1)
            current_field = name.strip().lower()
            buffer = [value.strip().rstrip(",")]
        else:
            # Continuation line
            if current_field:
                buffer.append(stripped)

    # Save last field
    if current_field and current_field in ALLOWED_SET:
        fields[current_field] = " ".join(buffer).strip()

    # Pretty-print output
    out = [header]
    for field in ALLOWED_FIELDS:
        if field in fields:
            out.append(f"  {field} = {fields[field]},")
    out.append("}")

    return "\n".join(out)


def extract_relevant_bib_entries(bib_path, citation_keys):
    relevant = {}
    current_key = None
    current_entry = []

    with open(bib_path, "r", encoding="utf-8") as f:
        for line in f:
            start = ENTRY_START.match(line)
            if start:
                # Save previous entry
                if current_key in citation_keys:
                    entry_text = "".join(current_entry)
                    entry_text = filter_bib_fields(entry_text)
                    relevant[current_key] = entry_text

                # Start new entry
                current_key = start.group(1).strip()
                current_entry = [line]
            else:
                if current_entry is not None:
                    current_entry.append(line)

        # Save last entry
        if current_key in citation_keys:
            entry_text = "".join(current_entry)
            entry_text = filter_bib_fields(entry_text)
            relevant[current_key] = entry_text

    return relevant


def resolve_bib_paths(bib_files, tex_dir):
    """Convert detected .bib filenames into absolute paths relative to the main .tex file."""
    resolved = []
    for bib in bib_files:
        # If already absolute, keep it
        if os.path.isabs(bib):
            resolved.append(bib)
        else:
            resolved.append(os.path.join(tex_dir, bib))
    return resolved


# -----------------------------
# 3. Write output
# -----------------------------

def write_bib_file(path, entries):
    with open(path, "w", encoding="utf-8") as f:
        for entry in entries.values():
            f.write(entry + "\n")


# -----------------------------
# 4. Command-line interface
# -----------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Extract only the cited BibTeX entries from a LaTeX project."
    )

    parser.add_argument("texfile", help="Main LaTeX .tex file")
    parser.add_argument(
        "bibfile",
        nargs="?",
        help="BibTeX .bib file (optional if \\addbibresource is used)"
    )
    parser.add_argument(
        "-o", "--output",
        default="filtered.bib",
        help="Output .bib file (default: filtered.bib)"
    )

    args = parser.parse_args()

    # Determine directory of the main .tex file
    tex_dir = os.path.dirname(os.path.abspath(args.texfile))

    print("Reading LaTeX project...")
    tex_content = read_tex_recursive(args.texfile)

    print("Extracting citations...")
    citations = extract_citations(tex_content)
    print(f"Found {len(citations)} unique citation keys.\n")

    # Determine bibliography files
    if args.bibfile:
        bib_files = [args.bibfile]
    else:
        print("\nDetecting bibliography files from \\addbibresource and \\bibliography...")
        bib_files = extract_bib_files(tex_content)

    # Resolve bib paths relative to tex file
    bib_files = resolve_bib_paths(bib_files, tex_dir)

    print("\nUsing bibliography files:")
    for b in bib_files:
        print("  ", b)

    # Extract entries
    all_entries = {}
    for bib in bib_files:
        print(f"Processing {bib}...")
        entries = extract_relevant_bib_entries(bib, citations.keys())
        all_entries.update(entries)

    print(f"\nTotal relevant BibTeX entries: {len(all_entries)}")

    # Output path in tex folder
    output_path = os.path.join(tex_dir, args.output)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    print(f"Writing output to {output_path}...")
    write_bib_file(output_path, all_entries)

    print("Done.")


if __name__ == "__main__":
    # usage 
    # python filterbib.py main.tex references.bib -o filtered.bib
    # or# 
    # python filterbib.py main.tex
    main()
    