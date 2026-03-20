"""
SafeRx AI — DAG 1 : scraping_etl_pipeline
==========================================
Automatise chaque dimanche à 02h00 la chaîne complète :

  1. scrape_medicaments    → scraper_med_ma.py
                             Scrape medicament.ma → data/raw/all_drugs_med_ma.csv

  2. transform_data        → transform_med_ma.py
                             Nettoie et normalise → data/processed/drugs_ma_clean.csv
                                                  → data/processed/dci_components.csv

  3. load_drugs            → load_med_ma.py
                             Insère / met à jour les tables drugs_ma et dci_components

  4. load_interactions     → load_interactions.py
                             Charge drug_interactions depuis interactions_ansm.csv

Les scripts ETL sont montés depuis ./etl et ./scraping dans /app/etl et /app/scraping.
Les données sont partagées via le volume ./data monté dans /app/data.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
#  Chemins dans le container Airflow
#  (correspondant aux volumes montés dans docker-compose)
# ─────────────────────────────────────────────────────────────────────────────

SCRAPING_DIR = "/app/scraping"
ETL_DIR      = "/app/etl"
DATA_RAW     = "/app/data/raw"
DATA_PROC    = "/app/data/processed"

# ─────────────────────────────────────────────────────────────────────────────
#  Paramètres par défaut — s'appliquent à toutes les tâches du DAG
# ─────────────────────────────────────────────────────────────────────────────

default_args = {
    "owner":            "saferx",
    "depends_on_past":  False,
    "retries":          2,                      # 2 tentatives en cas d'échec
    "retry_delay":      timedelta(minutes=10),  # attente entre chaque tentative
    "email_on_failure": False,
    "email_on_retry":   False,
}

# ─────────────────────────────────────────────────────────────────────────────
#  Vérification de pré-condition : compter les nouvelles lignes scrappées
# ─────────────────────────────────────────────────────────────────────────────

def verifier_fichier_scrape(**context) -> None:
    """
    Vérifie que le fichier CSV brut existe et contient des données.
    Lève une exception si le fichier est vide → arrête le DAG proprement
    sans marquer une erreur sur le scraper.
    """
    import os
    import csv

    csv_path = f"{DATA_RAW}/all_drugs_med_ma.csv"

    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Fichier scraping introuvable : {csv_path}")

    with open(csv_path, encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = sum(1 for _ in reader)

    if rows < 2:  # header + au moins 1 ligne de données
        raise ValueError(f"Fichier scraping vide ou header seul ({rows} lignes) : {csv_path}")

    logger.info(f"[DAG] Fichier scraping OK : {rows - 1} médicaments trouvés")
    context["ti"].xcom_push(key="nb_medicaments_scrapes", value=rows - 1)


# ─────────────────────────────────────────────────────────────────────────────
#  Définition du DAG
# ─────────────────────────────────────────────────────────────────────────────

with DAG(
    dag_id      = "scraping_etl_pipeline",
    description = "Scraping medicament.ma + ETL ANSM — hebdomadaire (dimanche 02h00)",
    default_args= default_args,
    schedule    = "0 2 * * 0",           # cron : dimanche à 02h00 UTC
    start_date  = datetime(2025, 1, 1),
    catchup     = False,                 # ne pas exécuter les runs passés au démarrage
    max_active_runs = 1,                 # empêche deux runs simultanés
    tags        = ["saferx", "etl", "scraping"],
) as dag:

    dag.doc_md = """
    ## scraping_etl_pipeline

    Pipeline hebdomadaire de mise à jour des données médicamenteuses.

    **Planification** : Chaque dimanche à 02h00 UTC

    **Étapes** :
    1. `scrape_medicaments` → Scrape medicament.ma
    2. `verifier_scrape` → Valide que le CSV est non vide
    3. `transform_data` → Nettoyage + normalisation
    4. `load_drugs` → Chargement drugs_ma + dci_components
    5. `load_interactions` → Chargement drug_interactions (ANSM)
    """

    # ── Tâche 1 : Scraping medicament.ma ─────────────────────────────────────
    scrape = BashOperator(
        task_id      = "scrape_medicaments",
        bash_command = (
            f"cd {SCRAPING_DIR} && "
            f"python scraper_med_ma.py --output {DATA_RAW}/all_drugs_med_ma.csv"
        ),
        doc_md = "Scrape medicament.ma et sauvegarde le CSV brut dans data/raw/.",
    )

    # ── Tâche 2 : Vérification du fichier scrappé ────────────────────────────
    verifier = PythonOperator(
        task_id         = "verifier_scrape",
        python_callable = verifier_fichier_scrape,
        doc_md          = "Vérifie que le CSV contient des données avant de continuer.",
    )

    # ── Tâche 3 : Transformation ──────────────────────────────────────────────
    transform = BashOperator(
        task_id      = "transform_data",
        bash_command = f"cd {ETL_DIR} && python transform_med_ma.py",
        doc_md       = (
            "Nettoie all_drugs_med_ma.csv → drugs_ma_clean.csv + dci_components.csv "
            "dans data/processed/."
        ),
    )

    # ── Tâche 4 : Chargement médicaments en base ──────────────────────────────
    load_drugs = BashOperator(
        task_id      = "load_drugs",
        bash_command = f"cd {ETL_DIR} && python load_med_ma.py",
        doc_md       = "Insère ou met à jour les tables drugs_ma et dci_components.",
    )

    # ── Tâche 5 : Chargement interactions ANSM ───────────────────────────────
    load_interactions = BashOperator(
        task_id      = "load_interactions",
        bash_command = f"cd {ETL_DIR} && python load_interactions.py",
        doc_md       = (
            "Charge drug_interactions depuis data/processed/interactions_ansm.csv. "
            "Ce fichier ne change pas — seuls les nouveaux médicaments peuvent créer "
            "de nouvelles interactions."
        ),
    )

    # ── Ordre d'exécution ─────────────────────────────────────────────────────
    # scrape → verifier → transform → load_drugs → load_interactions
    scrape >> verifier >> transform >> load_drugs >> load_interactions