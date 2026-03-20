from __future__ import annotations
import argparse
import csv
import os
import sys
from pathlib import Path
import psycopg2
from psycopg2.extras import execute_values

# ─────────────────────────────────────────────────────────────────────────────
#  Config
# ─────────────────────────────────────────────────────────────────────────────

_HERE = Path(__file__).parent
DATA_ROOT = _HERE if (_HERE / "data").exists() else _HERE.parent

CSV_PATH = DATA_ROOT / "data" / "processed" / "interactions_ansm.csv"

SOURCE = "ANSM_2023"

SEVERITY_RANK = {"MAJOR": 3, "MODERATE": 2, "MINOR": 1}

# ── Corrections manuelles de fragments de parsing ──────────────────────────
DCI_B_FIXES: dict[str, str] = {
    "OR": "SEL(S) D'OR",
}


# ─────────────────────────────────────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _db_conn():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "db"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        dbname=os.getenv("POSTGRES_DB", "saferx"),
        user=os.getenv("POSTGRES_USER", "saferx"),
        password=os.getenv("POSTGRES_PASSWORD", ""),
    )


def _ensure_table(cur) -> None:
    """Crée la table si elle n'existe pas encore."""
    cur.execute("""
        CREATE TABLE IF NOT EXISTS drug_interactions (
            id             SERIAL PRIMARY KEY,
            dci_a          VARCHAR(255) NOT NULL,
            dci_b          VARCHAR(255) NOT NULL,
            level_fr       VARCHAR(50)  NOT NULL,
            severity       VARCHAR(20)  NOT NULL,
            mechanism      TEXT,
            recommendation TEXT,
            source         VARCHAR(50)  NOT NULL DEFAULT 'ANSM_2023',
            created_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            UNIQUE (dci_a, dci_b)
        );
        CREATE INDEX IF NOT EXISTS idx_di_dci_a ON drug_interactions (dci_a);
        CREATE INDEX IF NOT EXISTS idx_di_dci_b ON drug_interactions (dci_b);
        CREATE INDEX IF NOT EXISTS idx_di_severity ON drug_interactions (severity);
    """)


# ─────────────────────────────────────────────────────────────────────────────
#  Étape 1 — Lecture + corrections
# ─────────────────────────────────────────────────────────────────────────────


def load_csv(path: Path) -> list[dict]:
    rows = []
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            # Correction fragments
            row["dci_b"] = DCI_B_FIXES.get(row["dci_b"], row["dci_b"])
            rows.append(row)
    print(f"  CSV lu          : {len(rows):,} lignes  ({path.name})")
    return rows


# ─────────────────────────────────────────────────────────────────────────────
#  Étape 2 — Déduplication
# ─────────────────────────────────────────────────────────────────────────────


def deduplicate(rows: list[dict]) -> list[dict]:
    """
    Pour une même paire (dci_a, dci_b), on garde l'entrée au niveau
    le plus sévère. En cas d'égalité de sévérité, on prend la première
    (mécanisme le plus long comme critère secondaire).
    """
    best: dict[tuple, dict] = {}
    for row in rows:
        key = (row["dci_a"], row["dci_b"])
        existing = best.get(key)
        if existing is None:
            best[key] = row
        else:
            r_rank = SEVERITY_RANK.get(row["severity"], 0)
            e_rank = SEVERITY_RANK.get(existing["severity"], 0)
            if r_rank > e_rank:
                best[key] = row
            elif r_rank == e_rank:
                # Garder le mécanisme le plus complet
                if len(row["mechanism"]) > len(existing["mechanism"]):
                    best[key] = row

    deduped = list(best.values())
    removed = len(rows) - len(deduped)
    print(
        f"  Après dédup     : {len(deduped):,} lignes  ({removed} doublons supprimés)"
    )
    return deduped


# ─────────────────────────────────────────────────────────────────────────────
#  Étape 3 — Symétrie
# ─────────────────────────────────────────────────────────────────────────────


def add_symmetric(rows: list[dict]) -> list[dict]:
    """
    Insère B+A pour chaque paire A+B absente.
    On réutilise le même mécanisme et la même conduite.
    """
    existing_pairs = {(r["dci_a"], r["dci_b"]) for r in rows}
    symmetric_rows = []

    for row in rows:
        inv_key = (row["dci_b"], row["dci_a"])
        if inv_key not in existing_pairs:
            symmetric_rows.append(
                {
                    "dci_a": row["dci_b"],
                    "dci_b": row["dci_a"],
                    "level_fr": row["level_fr"],
                    "severity": row["severity"],
                    "mechanism": row["mechanism"],
                    "recommendation": row["recommendation"],
                }
            )
            existing_pairs.add(inv_key)

    total = rows + symmetric_rows
    print(
        f"  Après symétrie  : {len(total):,} lignes  (+{len(symmetric_rows)} paires inversées)"
    )
    return total


# ─────────────────────────────────────────────────────────────────────────────
#  Étape 4 — Insertion PostgreSQL
# ─────────────────────────────────────────────────────────────────────────────


def insert(rows: list[dict], dry_run: bool = False) -> int:
    tuples = [
        (
            r["dci_a"],
            r["dci_b"],
            r["level_fr"],
            r["severity"],
            r["mechanism"] or None,
            r["recommendation"] or None,
            SOURCE,
        )
        for r in rows
    ]

    if dry_run:
        print(
            f"\n  [DRY-RUN] {len(tuples):,} lignes prêtes à insérer — aucune connexion DB."
        )
        print("  Exemples :")
        for t in tuples[:3]:
            print(f"    [{t[3]}] {t[0]}  +  {t[1]}")
        return 0

    conn = _db_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                _ensure_table(cur)

                execute_values(
                    cur,
                    """
                    INSERT INTO drug_interactions
                        (dci_a, dci_b, level_fr, severity, mechanism, recommendation, source)
                    VALUES %s
                    ON CONFLICT (dci_a, dci_b) DO UPDATE SET
                        level_fr       = EXCLUDED.level_fr,
                        severity       = EXCLUDED.severity,
                        mechanism      = EXCLUDED.mechanism,
                        recommendation = EXCLUDED.recommendation,
                        source         = EXCLUDED.source
                    """,
                    tuples,
                    page_size=500,
                )
                # Récupérer le compte réel inséré / mis à jour
                cur.execute(
                    "SELECT COUNT(*) FROM drug_interactions WHERE source = %s",
                    (SOURCE,),
                )
                count = cur.fetchone()[0]

        print(f"  Insertions OK   : {count:,} lignes dans drug_interactions")
        return count

    finally:
        conn.close()


# ─────────────────────────────────────────────────────────────────────────────
#  Stats post-insertion
# ─────────────────────────────────────────────────────────────────────────────


def print_db_stats() -> None:
    conn = _db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT severity, COUNT(*)
                FROM drug_interactions
                GROUP BY severity
                ORDER BY COUNT(*) DESC
            """)
            rows = cur.fetchall()
            print("\n  Distribution en DB :")
            for sev, n in rows:
                print(f"    {sev:<10} : {n:,}")

            cur.execute("""
                SELECT dci_a, COUNT(*) as nb
                FROM drug_interactions
                GROUP BY dci_a
                ORDER BY nb DESC
                LIMIT 5
            """)
            top = cur.fetchall()
            print("\n  Top 5 DCI_A les plus impliquées :")
            for dci, n in top:
                print(f"    {dci:<40} : {n:,} interactions")
    finally:
        conn.close()


# ─────────────────────────────────────────────────────────────────────────────
#  Main
# ─────────────────────────────────────────────────────────────────────────────


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Load interactions ANSM → drug_interactions"
    )
    ap.add_argument(
        "--csv", default=str(CSV_PATH), help=f"Chemin du CSV (défaut: {CSV_PATH})"
    )
    ap.add_argument(
        "--dry-run", action="store_true", help="Simuler sans écrire en base"
    )
    ap.add_argument(
        "--no-symmetric",
        action="store_true",
        help="Ne pas ajouter les paires inversées",
    )
    args = ap.parse_args()

    csv_path = Path(args.csv)
    if not csv_path.exists():
        print(f"Fichier introuvable : {csv_path}", file=sys.stderr)
        sys.exit(1)

    print("═══════════════════════════════════════════════════")
    print("  SafeRx — Load interactions ANSM → PostgreSQL")
    print("═══════════════════════════════════════════════════")

    rows = load_csv(csv_path)
    rows = deduplicate(rows)

    if not args.no_symmetric:
        rows = add_symmetric(rows)

    print()
    count = insert(rows, dry_run=args.dry_run)

    if count and not args.dry_run:
        print()
        print_db_stats()

    print("\n==== Terminé ====")


if __name__ == "__main__":
    main()
