"""Resolve residual English tree strings against the existing TSV id table.

Strategy: canonicalize each residual (lowercase, drop parens/brackets), squash
all spaces, then look the squashed form up in the id section of
OfficialDependencyNames.tsv.  Emits resolved.tsv / unresolved.txt for the
supplement pipeline.
"""
import re
import sys

TSV = r"e:\Code\sc2\Work\sc2ed_dpifix\l10n\OfficialDependencyNames.tsv"
RESIDUAL = r"e:\Code\sc2\Work\sc2ed_dpifix\tools\residual_en.txt"
OUT_RESOLVED = r"e:\Code\sc2\Work\sc2ed_dpifix\tools\resolved.tsv"
OUT_UNRESOLVED = r"e:\Code\sc2\Work\sc2ed_dpifix\tools\unresolved.txt"


def canonical(text):
    text = text.lower()
    text = re.sub(r"[()\[\]{}]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def squash(text):
    return canonical(text).replace(" ", "")


def main():
    ids = {}
    with open(TSV, encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("#") or "\t" not in line:
                continue
            key, _, value = line.rstrip("\n").partition("\t")
            if key.startswith("@display:"):
                continue
            ids[key.strip().lower()] = value

    with open(RESIDUAL, encoding="utf-8") as fh:
        residuals = [line.rstrip("\n") for line in fh if line.strip()]

    resolved, unresolved = [], []
    for text in residuals:
        hit = ids.get(squash(text))
        if hit:
            resolved.append((text, hit))
        else:
            unresolved.append(text)

    with open(OUT_RESOLVED, "w", encoding="utf-8") as fh:
        for text, translation in resolved:
            fh.write(f"{text}\t{translation}\n")
    with open(OUT_UNRESOLVED, "w", encoding="utf-8") as fh:
        fh.write("\n".join(unresolved) + "\n")

    ascii_in_translation = sum(
        1 for _, t in resolved if re.search(r"[A-Za-z]{3,}", t))
    print(f"residuals={len(residuals)} resolved={len(resolved)} "
          f"unresolved={len(unresolved)}")
    print(f"resolved-with-english-leftovers={ascii_in_translation} "
          f"(machine-munged translations)")


if __name__ == "__main__":
    sys.exit(main())
