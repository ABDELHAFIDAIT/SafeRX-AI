from __future__ import annotations
import argparse
import csv
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
import pdfplumber

# ─────────────────────────────────────────────────────────────────────────────
#  Constantes
# ─────────────────────────────────────────────────────────────────────────────

COLUMN_SPLIT = 310

FONT_DCI_A = "CIDFont+F1"
FONT_DCI_B = "CIDFont+F3"
FONT_LEVEL = "CIDFont+F1"
FONT_BODY = "CIDFont+F2"

SIZE_DCI_A = 9.0

LEVEL_PATTERNS = {
    r"(?i)association\s+d[eé]conseil+[eé]+": ("Association déconseillée", "MAJOR"),
    r"(?i)contre[- ]?indication": ("Contre-indication", "MAJOR"),
    r"(?i)pr[eé]caution\s+d['']emploi": ("Précaution d'emploi", "MODERATE"),
    r"(?i)[aà]\s+prendre\s+en\s+compte": ("À prendre en compte", "MINOR"),
    r"(?i)\basdec\b": ("Association déconseillée", "MAJOR"),
    r"(?i)\bapec\b": ("À prendre en compte", "MINOR"),
    r"(?i)\bpe\b": ("Précaution d'emploi", "MODERATE"),
    r"(?i)\bci\b": ("Contre-indication", "MAJOR"),
}


def _match_level(text: str) -> tuple[str, str] | None:
    t = text.strip()
    for pattern, result in LEVEL_PATTERNS.items():
        if re.search(pattern, t):
            return result
    return None


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


# ─────────────────────────────────────────────────────────────────────────────
#  Data model
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class Interaction:
    dci_a: str
    dci_b: str
    level_fr: str
    severity: str
    mechanism: str = ""
    recommendation: str = ""


# ─────────────────────────────────────────────────────────────────────────────
#  Parser principal — bi-colonne par coordonnées
# ─────────────────────────────────────────────────────────────────────────────


def parse_thesaurus(pdf_path: str | Path, verbose: bool = False) -> list[Interaction]:
    interactions: list[Interaction] = []

    current_dci_a = ""
    current_dci_b = ""
    current_level = ""
    current_sev = ""
    mech_lines: list[str] = []
    cond_lines: list[str] = []

    def _flush():
        nonlocal current_level, current_sev, mech_lines, cond_lines
        if current_dci_a and current_dci_b and current_level:
            interactions.append(
                Interaction(
                    dci_a=_clean(current_dci_a),
                    dci_b=_clean(current_dci_b),
                    level_fr=current_level,
                    severity=current_sev,
                    mechanism=_clean(" ".join(mech_lines)),
                    recommendation=_clean(" ".join(cond_lines)),
                )
            )
        current_level = ""
        current_sev = ""
        mech_lines = []
        cond_lines = []

    with pdfplumber.open(pdf_path) as pdf:
        total = len(pdf.pages)
        if verbose:
            print(f"PDF ouvert — {total} pages", file=sys.stderr)

        for page_num, page in enumerate(pdf.pages, start=1):
            if verbose and page_num % 30 == 0:
                print(
                    f"  Page {page_num}/{total} — {len(interactions)} interactions",
                    file=sys.stderr,
                )

            words = page.extract_words(
                extra_attrs=["fontname", "size"],
                x_tolerance=3,
                y_tolerance=3,
                keep_blank_chars=False,
            )
            if not words:
                continue

            # Grouper par ligne
            lines: dict[int, list[dict]] = defaultdict(list)
            for w in words:
                lines[round(w["top"])].append(w)

            for top_key in sorted(lines.keys()):
                row = sorted(lines[top_key], key=lambda w: w["x0"])

                left = [w for w in row if w["x0"] < COLUMN_SPLIT]
                right = [w for w in row if w["x0"] >= COLUMN_SPLIT]

                left_text = _clean(" ".join(w["text"] for w in left))
                right_text = _clean(" ".join(w["text"] for w in right))

                left_font = left[0].get("fontname", "") if left else ""
                left_size = left[0].get("size", 0.0) or 0 if left else 0.0
                right_font = right[0].get("fontname", "") if right else ""

                # ── 1. DCI_A ─────────────────────────────────────────────
                if (
                    left
                    and left_font == FONT_DCI_A
                    and left_size >= SIZE_DCI_A
                    and not left_text.startswith("+")
                ):
                    _flush()
                    current_dci_a = left_text
                    current_dci_b = ""
                    continue

                # ── 2. DCI_B (ligne commençant par "+") ───────────────────
                if left and left[0]["text"] == "+":
                    _flush()
                    dci_b_parts = [w["text"] for w in left if w["text"] != "+"]
                    current_dci_b = _clean(" ".join(dci_b_parts))
                    continue

                # ── 3. Niveau (colonne droite, font F1) ───────────────────
                if right and right_font == FONT_LEVEL:
                    level_match = _match_level(right_text)
                    if level_match:
                        if current_level:
                            _flush()
                        current_level, current_sev = level_match
                        if left_text:
                            mech_lines.append(left_text)
                        continue

                # ── 4. Mécanisme (gauche, font F2) ────────────────────────
                if left and left_font == FONT_BODY and left_text and current_dci_b:
                    mech_lines.append(left_text)

                # ── 5. Conduite (droite, font F2) ─────────────────────────
                if right and right_font == FONT_BODY and right_text and current_level:
                    cond_lines.append(right_text)

        _flush()

    if verbose:
        print(f"\nTotal : {len(interactions)} interactions extraites", file=sys.stderr)

    return interactions


# ─────────────────────────────────────────────────────────────────────────────
#  Export CSV
# ─────────────────────────────────────────────────────────────────────────────

FIELDNAMES = ["dci_a", "dci_b", "level_fr", "severity", "mechanism", "recommendation"]


def export_csv(interactions: list[Interaction], out_path: str | Path) -> None:
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        for i in interactions:
            writer.writerow(
                {
                    "dci_a": i.dci_a,
                    "dci_b": i.dci_b,
                    "level_fr": i.level_fr,
                    "severity": i.severity,
                    "mechanism": i.mechanism,
                    "recommendation": i.recommendation,
                }
            )
    print(f"- CSV exporté : {out}  ({len(interactions):,} lignes)")


# ─────────────────────────────────────────────────────────────────────────────
#  Statistiques
# ─────────────────────────────────────────────────────────────────────────────


def print_stats(interactions: list[Interaction]) -> None:
    from collections import Counter

    sev = Counter(i.severity for i in interactions)
    lvl = Counter(i.level_fr for i in interactions)

    print("\n══════════════════════════════════════════════════")
    print("  STATISTIQUES DU THÉSAURUS PARSÉ")
    print("══════════════════════════════════════════════════")
    print(f"  Total interactions          : {len(interactions):,}")
    print(f"  DCI_A uniques               : {len({i.dci_a for i in interactions}):,}")
    print(f"  DCI_B uniques               : {len({i.dci_b for i in interactions}):,}")
    print("\n  Par sévérité :")
    for s in ["MAJOR", "MODERATE", "MINOR"]:
        print(f"    {s:<12} : {sev.get(s, 0):,}")
    print("\n  Par niveau ANSM :")
    for lv, n in lvl.most_common():
        print(f"    {lv:<38} : {n:,}")
    print(
        f"\n  Avec mécanisme renseigné    : {sum(1 for i in interactions if i.mechanism):,}"
    )
    print(
        f"  Avec conduite renseignée    : {sum(1 for i in interactions if i.recommendation):,}"
    )
    print("\n  ── 5 exemples ──────────────────────────────────")
    for inter in interactions[:5]:
        print(f"\n  [{inter.severity}] {inter.dci_a}  +  {inter.dci_b}")
        print(f"  Niveau    : {inter.level_fr}")
        if inter.mechanism:
            print(f"  Mécanisme : {inter.mechanism[:100]}")
        if inter.recommendation:
            print(f"  Conduite  : {inter.recommendation[:100]}")


# ─────────────────────────────────────────────────────────────────────────────
#  CLI
# ─────────────────────────────────────────────────────────────────────────────


def main() -> None:
    ap = argparse.ArgumentParser(description="Parse le Thésaurus ANSM → CSV")
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--out", default="data/processed/interactions_ansm.csv")
    ap.add_argument("--verbose", "-v", action="store_true")
    ap.add_argument("--stats", "-s", action="store_true")
    args = ap.parse_args()

    pdf = Path(args.pdf)
    if not pdf.exists():
        print(f"- Fichier introuvable : {pdf}", file=sys.stderr)
        sys.exit(1)

    print(f"- Parsing : {pdf.name} …")
    items = parse_thesaurus(pdf, verbose=args.verbose)
    export_csv(items, args.out)
    if args.stats:
        print_stats(items)


if __name__ == "__main__":
    main()
