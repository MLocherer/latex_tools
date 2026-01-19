#!/usr/bin/env python3
import argparse
import os
import re
from pathlib import Path

# -----------------------------
# Regex patterns
# -----------------------------

ACRONYM_USAGE_RE = re.compile(
    r"\\(?:gls|glspl|Gls|Glspl|"
    r"acrshort|acrshortpl|Acrshort|Acrshortpl|"
    r"acrlong|acrlongpl|Acrlong|Acrlongpl|"
    r"acrfull|acrfullpl|Acrfull|Acrfullpl)"
    r"\{([^\}]+)\}"
)

ACRONYM_DEF_RE = re.compile(
    r"(\\newacronym"
    r"\{(?P<id>[^\}]+)\}"
    r"\{(?P<short>(?:[^{}]|\{[^{}]*\})*)\}"
    r"\{(?P<long>(?:[^{}]|\{[^{}]*\})*)\})"
)

ACRONYM_DEF_LINE_RE = re.compile(
    r"^[ \t]*\\newacronym"
    r"\{(?P<id>[^\}]+)\}"
    r"\{(?P<short>(?:[^{}]|\{[^{}]*\})*)\}"
    r"\{(?P<long>(?:[^{}]|\{[^{}]*\})*)\}"
    r"[ \t]*$",
    re.MULTILINE
)

# We search for the \makeglossaries command:
MAKEGLOSSARIES_RE = re.compile(
    r"\\makeglossaries"
)

INPUT_RE = re.compile(r"\\(?:input|include)\{(?P<file>[^\}]+)\}")

DOCUMENT_START_RE = re.compile(r"\\begin\{document\}")
DOCUMENT_END_RE = re.compile(r"\\end\{document\}")


# -----------------------------
# File loading helpers
# -----------------------------

def load_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def resolve_tex_path(base: Path, include_path: str) -> Path:
    p = Path(include_path)
    if not p.suffix:
        p = p.with_suffix(".tex")
    if not p.is_absolute():
        p = base.parent / p
    return p


def split_document(content: str):
    start = DOCUMENT_START_RE.search(content)
    end = DOCUMENT_END_RE.search(content)
    if not start or not end:
        return content, "", ""
    preamble = content[: start.end()]
    body = content[start.end() : end.start()]
    ending = content[end.start() :]
    return preamble, body, ending


# -----------------------------
# Recursive document body scanner
# -----------------------------

def extract_document_body(content: str) -> str:
    start = DOCUMENT_START_RE.search(content)
    end = DOCUMENT_END_RE.search(content)
    if not start or not end:
        return ""
    return content[start.end(): end.start()]


def scan_body_recursive(content: str, base_path: Path, visited=None) -> str:
    if visited is None:
        visited = set()

    body = extract_document_body(content)
    combined = body

    for match in INPUT_RE.finditer(body):
        inc_file = resolve_tex_path(base_path, match.group("file"))
        if inc_file.exists() and inc_file not in visited:
            visited.add(inc_file)
            sub_content = load_file(inc_file)
            combined += scan_body_recursive(sub_content, inc_file, visited)

    return combined


# -----------------------------
# Main analysis functions
# -----------------------------

def find_acronym_usages(text: str):
    counts = {}
    for match in ACRONYM_USAGE_RE.finditer(text):
        acronym = match.group(1)  # first capture group
        counts[acronym] = counts.get(acronym, 0) + 1
    return counts


def find_acronym_definitions(content: str):
    return [
        {
            "id": m.group("id"),
            "short": m.group("short"),
            "long": m.group("long"),
            "full": m.group(1),   # <-- exact LaTeX definition
        }
        for m in ACRONYM_DEF_RE.finditer(content)
    ]

    
    
def filter_relevant_definitions(definitions, usage_counts):
    used_ids = set(usage_counts.keys())
    return [d for d in definitions if d["id"] in used_ids]

# Insert the new acronym block after the glossaries package line
def insert_after_glossaries(preamble: str, acronym_block: str) -> str:
    match = MAKEGLOSSARIES_RE.search(preamble)
    if not match:
        # fallback: append at end of preamble
        return preamble + "\n" + acronym_block

    insert_pos = match.end()
    return preamble[:insert_pos] + "\n\n" + acronym_block + "\n" + preamble[insert_pos:]

# -----------------------------
# CLI
# -----------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Scan LaTeX project for glossary acronym usage and definitions."
    )
    parser.add_argument("mainfile", type=str, help="Main LaTeX file (e.g., main.tex)")
    parser.add_argument("--update", action="store_true", help="Enable interactive replacement of low‑usage acronyms.")
    parser.add_argument( "--min-count", type=int, default=2, help="Minimum number of acronym uses required before replacement is suggested.")
    
    args = parser.parse_args()
    

    main_path = Path(args.mainfile)
    if not main_path.exists():
        print(f"Error: File not found: {main_path}")
        return

    main_content = load_file(main_path)
    preamble, body_text, ending = split_document(main_content)
    preamble_clean = ACRONYM_DEF_LINE_RE.sub("", preamble)
    preamble_clean = re.sub(r"\n\s*\n+", "\n\n", preamble_clean)


    # Extract definitions from preamble
    preamble = main_content.split("\\begin{document}")[0]
    definitions = find_acronym_definitions(preamble)

    # Extract and scan document body recursively
    body_text = scan_body_recursive(main_content, main_path)
    usage_counts = find_acronym_usages(body_text)
    
    print(usage_counts)
    
    # -----------------------------
    # Output
    # -----------------------------
    print("\n=== Acronym Definitions (from preamble) ===")
    for d in definitions:
        print(f"{d['id']:20}  {d['short']:10}  {d['long']}")

    print(f"\n=== Acronym Usage Counts (in document body) (N={len(usage_counts)}) ===")
    for acro, count in sorted(usage_counts.items(), key=lambda x: x[0].lower()):
        print(f"{acro:20}  {count}")

    # Filter relevant definitions
    relevant_defs = filter_relevant_definitions(definitions, usage_counts)

    # Sort alphabetically
    relevant_defs = sorted(relevant_defs, key=lambda d: d["id"].lower())
    
    # Now build a clean acronym block:
    acronym_block = "\n".join(d["full"] for d in relevant_defs) + "\n"

    print("\n=== Relevant Acronym Definitions (exact LaTeX, sorted) ===")
    for d in relevant_defs:
        print(d["full"])

    # NEW: Acronyms used fewer than 3 times
    low_usage = {a: c for a, c in usage_counts.items() if c < args.min_count}
    low_usage = dict(sorted(low_usage.items(), key=lambda x: x[0].lower()))

    print(f"\n=== Acronyms Used Fewer Than {args.min_count} Times ===")
    for acro, count in low_usage.items():
        print(f"{acro:20}  {count}")

    # Interactive replacement for low‑usage acronyms
    replacements = {}

    if args.update:
        print("\n=== Update mode enabled: interactive acronym replacement ===")

        for acro, count in low_usage.items():
            print(f"\nAcronym '{acro}' is used only {count} times.")
            answer = input(
                f"Do you want to replace all occurrences of '{acro}' with its full definition? [y/N]: "
            ).strip().lower()

            if answer == "y":
                definition = next((d for d in definitions if d["id"] == acro), None)
                if definition:
                    long_form = definition["long"]
                    replacements[acro] = long_form
                    print(f"→ Will replace '{acro}' with '{long_form}'")

                    # Remove from relevant definitions
                    relevant_defs = [d for d in relevant_defs if d["id"] != acro]
                else:
                    print(f"Warning: No definition found for '{acro}'. Skipping.")
            else:
                print(f"→ Keeping acronym '{acro}' unchanged.")
        
        print(f"\n=== Updated Relevant Acronym Definitions (after replacements) (N = {len(relevant_defs)}) ===")
        for d in relevant_defs:
            print(d["full"])


        # Apply replacements to the document body
        for acro, long_form in replacements.items():
            # Build a safe replacement string for re.sub
            replacement = "{\\color{red} " + long_form + "}"
            replacement = replacement.replace("\\", "\\\\")  # escape for regex replacement

            body_text = re.sub(
                rf"\\(?:gls|glspl|Gls|Glspl|"
                rf"acrshort|acrshortpl|Acrshort|Acrshortpl|"
                rf"acrlong|acrlongpl|Acrlong|Acrlongpl|"
                rf"acrfull|acrfullpl|Acrfull|Acrfullpl)"
                rf"\{{{acro}\}}",
                replacement,
                body_text,
            )
        
        new_preamble = insert_after_glossaries(preamble_clean, acronym_block)

        new_content = new_preamble + body_text + ending

        output_path = main_path.with_name(main_path.stem + "_expanded.tex")
        output_path.write_text(new_content, encoding="utf-8")
        print(f"\nUpdated document written to: {output_path}")
        
    else:
        print("\nUpdate flag not set — skipping acronym replacement.")

    print("Done.")

if __name__ == "__main__":
    main()
