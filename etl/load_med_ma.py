import os
import math
import logging
from pathlib import Path
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


# ── Chemins ──────────────────────────────────────────────────────────────────
_HERE = Path(__file__).resolve().parent
ROOT = _HERE if (_HERE / "data").exists() else _HERE.parent

DRUGS_CSV = ROOT / "data" / "processed" / "drugs_ma_clean" / "drugs_ma_clean.csv"
DCI_CSV = ROOT / "data" / "processed" / "dci_components" / "dci_components.csv"


# ── Connexion PostgreSQL ──────────────────────────────────────────────────────
def get_connection():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "db"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        dbname=os.getenv("POSTGRES_DB", "saferx"),
        user=os.getenv("POSTGRES_USER", "saferx"),
        password=os.getenv("POSTGRES_PASSWORD", "saferx"),
    )


# ── Helpers ───────────────────────────────────────────────────────────────────
def nan_to_none(val):
    if val is None:
        return None
    if isinstance(val, float) and math.isnan(val):
        return None
    return val


def to_bool(val):
    if val is None:
        return False
    if isinstance(val, bool):
        return val
    if isinstance(val, float) and math.isnan(val):
        return False
    return str(val).strip().lower() in ("true", "1", "yes", "oui")


def is_valid_id(val):
    """Filtre les lignes parasites (pied de page 'Source : ...')."""
    try:
        int(val)
        return True
    except (ValueError, TypeError):
        return False


# ── Load drugs_ma ─────────────────────────────────────────────────────────────
def load_drugs(conn, csv_path: Path) -> set:
    log.info(f"Lecture de {csv_path}")
    df = pd.read_csv(csv_path, engine="python", on_bad_lines="skip")
    log.info(f"  -> {len(df)} lignes chargees")

    # FIX 1 : ignorer les lignes dont l'id n'est pas un entier (pied de page)
    df = df[df["id"].apply(is_valid_id)].copy()
    log.info(f"  -> {len(df)} lignes valides apres filtrage")

    rows = [
        (
            int(r["id"]),
            nan_to_none(r.get("brand_name")),
            nan_to_none(r.get("presentation")),
            nan_to_none(r.get("dosage_raw")),
            nan_to_none(r.get("dci")),
            nan_to_none(r.get("labo_name")),
            nan_to_none(r.get("therapeutic_class")),
            nan_to_none(r.get("status")),
            nan_to_none(r.get("atc_code")),
            nan_to_none(r.get("price_ppv")),
            nan_to_none(r.get("price_hospital")),
            nan_to_none(r.get("toxicity_class")),
            nan_to_none(r.get("product_type")),
            nan_to_none(r.get("indications")),
            to_bool(r.get("is_psychoactive")),
            nan_to_none(r.get("contraindications")),
            nan_to_none(r.get("min_age")),
            nan_to_none(r.get("source_url")),
        )
        for _, r in df.iterrows()
    ]

    sql = """
        INSERT INTO drugs_ma (
            id, brand_name, presentation, dosage_raw, dci,
            labo_name, therapeutic_class, status, atc_code,
            price_ppv, price_hospital, toxicity_class, product_type,
            indications, is_psychoactive, contraindications, min_age, source_url
        ) VALUES %s
        ON CONFLICT (id) DO NOTHING
    """

    with conn.cursor() as cur:
        execute_values(cur, sql, rows, page_size=500)
    conn.commit()

    inserted_ids = {r[0] for r in rows}
    log.info(f"  ✓ {len(rows)} lignes inserees dans drugs_ma")
    # FIX 2 : retourne les ids inseres pour filtrer dci_components
    return inserted_ids


# ── Load dci_components ───────────────────────────────────────────────────────
def load_dci(conn, csv_path: Path, valid_drug_ids: set):
    log.info(f"Lecture de {csv_path}")
    df = pd.read_csv(csv_path)
    log.info(f"  -> {len(df)} lignes chargees")

    # FIX 3 : ignorer les drug_id absents de drugs_ma (contrainte FK)
    rows = [
        (int(r["drug_id"]), str(r["dci"]).strip(), int(r["position"]))
        for _, r in df.iterrows()
        if pd.notna(r["drug_id"])
        and pd.notna(r["dci"])
        and int(r["drug_id"]) in valid_drug_ids
    ]

    skipped = len(df) - len(rows)
    if skipped:
        log.warning(f"  ⚠ {skipped} lignes ignorees (drug_id absent de drugs_ma)")

    sql = """
        INSERT INTO dci_components (drug_id, dci, position)
        VALUES %s
        ON CONFLICT DO NOTHING
    """

    with conn.cursor() as cur:
        execute_values(cur, sql, rows, page_size=500)
    conn.commit()
    log.info(f"  ✓ {len(rows)} lignes inserees dans dci_components")


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    log.info("══════════════════════════════════════════")
    log.info("  SafeRx ETL - Load step")
    log.info("══════════════════════════════════════════")

    for path in (DRUGS_CSV, DCI_CSV):
        if not path.exists():
            log.error(f"Fichier introuvable : {path}")
            raise FileNotFoundError(path)

    log.info("Connexion a PostgreSQL...")
    conn = get_connection()
    log.info("  ✓ Connecte")

    try:
        inserted_ids = load_drugs(conn, DRUGS_CSV)
        load_dci(conn, DCI_CSV, inserted_ids)
        log.info("══ Load termine avec succes ══")
    except Exception as e:
        conn.rollback()
        log.error(f"Erreur - rollback effectue : {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
