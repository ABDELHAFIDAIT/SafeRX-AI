import re
import sys
import unicodedata
from pathlib import Path

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F
from pyspark.sql.types import (
    StringType,
    FloatType,
    BooleanType,
)

# ── Chemins ──────────────────────────────────────────────────────────────────
# En Docker : script dans /app/ → parent = /app  (data/ est présent ici)
# En local  : script dans etl/  → parent = etl/, on remonte d'un cran
_HERE = Path(__file__).resolve().parent
ROOT = _HERE if (_HERE / "data").exists() else _HERE.parent
INPUT_CSV = ROOT / "data" / "raw" / "all_drugs_med_ma.csv"
OUTPUT_DIR = ROOT / "data" / "processed"

OUTPUT_DRUGS = str(OUTPUT_DIR / "drugs_ma.parquet")
OUTPUT_DCI = str(OUTPUT_DIR / "dci_components.parquet")


# ════════════════════════════════════════════════════════════════════════════
# 1. Session Spark
# ════════════════════════════════════════════════════════════════════════════


def get_spark() -> SparkSession:
    return (
        SparkSession.builder.appName("SafeRx-ETL-Transform-MedMa")
        .config("spark.sql.shuffle.partitions", "4")  # petit dataset
        .config("spark.driver.memory", "2g")
        .getOrCreate()
    )


# ════════════════════════════════════════════════════════════════════════════
# 2. Extraction du prix  (UDF)
#    "372.00 dhs" → 372.0      None si non parseable
# ════════════════════════════════════════════════════════════════════════════


@F.udf(FloatType())
def parse_price(raw):
    if not raw:
        return None
    m = re.search(r"([\d]+(?:[.,]\d+)?)", raw.replace("\xa0", ""))
    if m:
        return float(m.group(1).replace(",", "."))
    return None


# ════════════════════════════════════════════════════════════════════════════
# 3. Normalisation de la classe toxicité
#    "Aucun" → None  |  "A"/"B"/"C" → conservé
# ════════════════════════════════════════════════════════════════════════════


@F.udf(StringType())
def clean_toxicity(val):
    if not val:
        return None
    v = val.strip().upper()
    return None if v in ("AUCUN", "AUCUNE", "") else v


# ════════════════════════════════════════════════════════════════════════════
# 4. Normalisation de l'âge minimal
#    "15 ans" → 15  |  "30 mois" → None (stocké en months_min à part)
#    "Six ans." → 6  via mapping verbal
# ════════════════════════════════════════════════════════════════════════════

_WORD_TO_NUM = {
    "un": 1,
    "une": 1,
    "deux": 2,
    "trois": 3,
    "quatre": 4,
    "cinq": 5,
    "six": 6,
    "sept": 7,
    "huit": 8,
    "neuf": 9,
    "dix": 10,
    "onze": 11,
    "douze": 12,
}


@F.udf(StringType())
def normalize_min_age(val):
    """Retourne une chaîne normalisée ex: '15 ans' | '30 mois' | None."""
    if not val:
        return None
    v = val.strip().rstrip(".")
    v_low = v.lower()

    # Remplace les mots-nombres
    for word, num in _WORD_TO_NUM.items():
        v_low = re.sub(rf"\b{word}\b", str(num), v_low)

    m = re.search(r"(\d+)\s*(ans?|mois)", v_low)
    if m:
        qty = int(m.group(1))
        unit = "ans" if m.group(2).startswith("an") else "mois"
        return f"{qty} {unit}"
    return v.strip() or None


# ════════════════════════════════════════════════════════════════════════════
# 5. Nettoyage générique d'une chaîne de texte
#    - retire \xa0, espaces multiples, caractères de contrôle
#    - strip
# ════════════════════════════════════════════════════════════════════════════


@F.udf(StringType())
def clean_str(val):
    if not val:
        return None
    # Remplace \xa0 et autres espaces insécables par espace ordinaire
    s = val.replace("\xa0", " ").replace("\u200b", "")
    # Normalise unicode (NFD → NFC)
    s = unicodedata.normalize("NFC", s)
    # Supprime caractères de contrôle sauf \n
    s = re.sub(r"[\r\t\x00-\x08\x0b\x0c\x0e-\x1f]", " ", s)
    # Collapse espaces multiples sur une même ligne
    s = re.sub(r" {2,}", " ", s)
    return s.strip() or None


# ════════════════════════════════════════════════════════════════════════════
# 6. Détection is_psychoactive
#    Le CSV a une colonne "Substance (s) psychoactive (s)" = "Oui" ou vide
# ════════════════════════════════════════════════════════════════════════════


@F.udf(BooleanType())
def parse_psychoactive(val):
    if not val:
        return False
    return val.strip().lower() in ("oui", "yes", "true", "1")


# ════════════════════════════════════════════════════════════════════════════
# 7. Normalisation du statut
# ════════════════════════════════════════════════════════════════════════════


@F.udf(StringType())
def clean_status(val):
    if not val:
        return "Commercialisé"  # valeur par défaut du schéma
    return val.strip()


# ════════════════════════════════════════════════════════════════════════════
# 8. Transformation principale  →  DataFrame drugs_ma
# ════════════════════════════════════════════════════════════════════════════


def transform_drugs_ma(spark: SparkSession) -> DataFrame:
    """
    Lit le CSV brut et retourne un DataFrame propre,
    aligné sur la table drugs_ma du schéma SafeRx.
    """
    print(f"[T] Lecture de {INPUT_CSV}")
    raw = (
        spark.read.option("header", "true")
        .option("encoding", "UTF-8")
        .option("multiLine", "true")  # les textes longs contiennent des \n
        .option("quote", '"')
        .option("escape", '"')
        .csv(str(INPUT_CSV))
    )

    print(f"[T] Lignes brutes : {raw.count()}")

    # Renommage des colonnes brutes → noms intermédiaires lisibles
    df = (
        raw.withColumnRenamed("drug_name", "_brand_name_raw")
        .withColumnRenamed("Présentation", "_presentation_raw")
        .withColumnRenamed("Dosage", "_dosage_raw")
        .withColumnRenamed("Distributeur ou fabriquant", "_labo_raw")
        .withColumnRenamed("Composition", "_composition_raw")
        .withColumnRenamed("Classe thérapeutique", "_class_raw")
        .withColumnRenamed("Statut", "_statut_raw")
        .withColumnRenamed("Code ATC", "_atc_raw")
        .withColumnRenamed("PPV", "_ppv_raw")
        .withColumnRenamed("Prix hospitalier", "_ph_raw")
        .withColumnRenamed("Tableau", "_tableau_raw")
        .withColumnRenamed("Nature du Produit", "_nature_raw")
        .withColumnRenamed("Indication(s)", "_indic_raw")
        .withColumnRenamed("Substance (s) psychoactive (s)", "_psycho_raw")
        .withColumnRenamed("Contres-indication(s)", "_ci_raw")
        .withColumnRenamed("Age minimal d'utilisation", "_age_raw")
        .withColumnRenamed("Lien du Produit", "_lien_raw")
    )

    # ── Transformations colonne par colonne ──────────────────────────────────
    df = (
        df
        # brand_name : strip + nettoyage
        .withColumn("brand_name", clean_str(F.col("_brand_name_raw")))
        # presentation
        .withColumn("presentation", clean_str(F.col("_presentation_raw")))
        # dosage_raw : conservé tel quel (nettoyé) — sera parsé dans dosage_rules (Vidal)
        .withColumn("dosage_raw", clean_str(F.col("_dosage_raw")))
        # dci : nettoyage + suppression des | multiples uniformes
        # On garde la chaîne complète ici ; la table dci_components fera le split
        .withColumn("dci", clean_str(F.col("_composition_raw")))
        # labo_name
        .withColumn("labo_name", clean_str(F.col("_labo_raw")))
        # therapeutic_class
        .withColumn("therapeutic_class", clean_str(F.col("_class_raw")))
        # status (default 'Commercialisé')
        .withColumn("status", clean_status(F.col("_statut_raw")))
        # atc_code : uppercase + strip
        .withColumn(
            "atc_code",
            F.when(
                F.col("_atc_raw").isNotNull(), F.upper(F.trim(F.col("_atc_raw")))
            ).otherwise(F.lit(None).cast(StringType())),
        )
        # price_ppv : "19.10 dhs" → 19.10
        .withColumn("price_ppv", parse_price(F.col("_ppv_raw")))
        # price_hospital
        .withColumn("price_hospital", parse_price(F.col("_ph_raw")))
        # toxicity_class : "Aucun" → NULL, A/B/C conservé
        .withColumn("toxicity_class", clean_toxicity(F.col("_tableau_raw")))
        # product_type
        .withColumn("product_type", clean_str(F.col("_nature_raw")))
        # indications
        .withColumn("indications", clean_str(F.col("_indic_raw")))
        # is_psychoactive
        .withColumn("is_psychoactive", parse_psychoactive(F.col("_psycho_raw")))
        # contraindications
        .withColumn("contraindications", clean_str(F.col("_ci_raw")))
        # min_age normalisé ("15 ans", "30 mois", None)
        .withColumn("min_age", normalize_min_age(F.col("_age_raw")))
        # source_url : "Cliquez ici" est inutilisable → NULL
        .withColumn(
            "source_url",
            F.when(
                F.lower(F.trim(F.col("_lien_raw"))).isin(
                    "cliquez ici", "click here", ""
                ),
                F.lit(None).cast(StringType()),
            ).otherwise(clean_str(F.col("_lien_raw"))),
        )
    )

    # ── Suppression lignes sans brand_name (données corrompues) ──────────────
    df = df.filter(F.col("brand_name").isNotNull())

    # ── Ajout d'un ID déterministe (row_number) ──────────────────────────────
    # Important : stable si le CSV ne change pas d'ordre
    from pyspark.sql.window import Window

    window = Window.orderBy(F.col("brand_name"), F.col("atc_code"), F.col("dosage_raw"))
    df = df.withColumn("id", F.row_number().over(window))

    # ── Sélection finale : uniquement les colonnes du schéma drugs_ma ────────
    final = df.select(
        "id",
        "brand_name",
        "presentation",
        "dosage_raw",
        "dci",
        "labo_name",
        "therapeutic_class",
        "status",
        "atc_code",
        "price_ppv",
        "price_hospital",
        "toxicity_class",
        "product_type",
        "indications",
        "is_psychoactive",
        "contraindications",
        "min_age",
        "source_url",
    )

    print(f"[T] Lignes après nettoyage drugs_ma : {final.count()}")
    return final, df  # df conservé avec l'id pour la table DCI


# ════════════════════════════════════════════════════════════════════════════
# 9. Table dci_components  (normalization multi-DCI)
#    "Acide acétylsalicylique | Vitamine C | Vitamine B1"
#    → 3 lignes : (drug_id=X, dci="Acide acétylsalicylique", position=1)
#                 (drug_id=X, dci="Vitamine C",               position=2)
#                 (drug_id=X, dci="Vitamine B1",              position=3)
# ════════════════════════════════════════════════════════════════════════════


def build_dci_components(df_with_id: DataFrame) -> DataFrame:
    """
    Éclate la colonne dci (composition) en une table de jointure
    drug_id ↔ DCI individuelle.
    Cette table est la clé pivot pour rejoindre Vidal (interactions, posologies).
    """
    # Split sur le séparateur '|' (avec espaces variables et \xa0 déjà nettoyé)
    dci_exploded = (
        df_with_id.select("id", "dci")
        .filter(F.col("dci").isNotNull())
        .withColumn(
            "dci_array",
            F.split(F.regexp_replace(F.col("dci"), r"\s*\|\s*", "|"), r"\|"),
        )
        .withColumn("dci_raw", F.explode("dci_array"))
        .withColumn(
            "dci_clean",
            # Nettoyage de chaque DCI individuelle
            F.trim(F.regexp_replace(F.col("dci_raw"), r"\s+", " ")),
        )
        .filter(F.col("dci_clean") != "")
        .filter(F.length(F.col("dci_clean")) > 1)
    )

    # Ajout de la position (1=première DCI = molécule principale)
    from pyspark.sql.window import Window

    w = Window.partitionBy("id").orderBy(F.monotonically_increasing_id())
    dci_final = dci_exploded.withColumn("position", F.row_number().over(w)).select(
        F.col("id").alias("drug_id"),
        F.col("dci_clean").alias("dci"),
        F.col("position"),
    )

    print(f"[T] Lignes dci_components : {dci_final.count()}")
    return dci_final


# ════════════════════════════════════════════════════════════════════════════
# 10. Rapport de qualité des données
# ════════════════════════════════════════════════════════════════════════════


def print_quality_report(df: DataFrame):
    total = df.count()
    print("\n" + "═" * 55)
    print("  RAPPORT QUALITÉ — drugs_ma")
    print("═" * 55)
    cols_to_check = [
        "brand_name",
        "dci",
        "labo_name",
        "atc_code",
        "price_ppv",
        "price_hospital",
        "toxicity_class",
        "product_type",
        "therapeutic_class",
    ]
    for col in cols_to_check:
        null_count = df.filter(F.col(col).isNull()).count()
        fill_pct = round((total - null_count) / total * 100, 1)
        print(f"  {col:<22}  {fill_pct:5.1f}%  ({total - null_count}/{total})")

    print("═" * 55)

    # Distribution toxicity_class
    print("\n  toxicity_class distribution :")
    df.groupBy("toxicity_class").count().orderBy("toxicity_class").show(truncate=False)

    # Distribution product_type
    print("  product_type distribution :")
    df.groupBy("product_type").count().orderBy(F.col("count").desc()).show(
        truncate=False
    )

    # Produits multi-DCI
    multi = df.filter(F.col("dci").contains("|")).count()
    print(f"  Produits multi-DCI : {multi}/{total} ({round(multi / total * 100, 1)}%)")
    print()


# ════════════════════════════════════════════════════════════════════════════
# 11. Écriture des outputs
# ════════════════════════════════════════════════════════════════════════════


def write_outputs(drugs_df: DataFrame, dci_df: DataFrame):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"[T] Écriture → {OUTPUT_DRUGS}")
    (
        drugs_df.coalesce(1)
        .write.mode("overwrite")
        .option("compression", "snappy")
        .parquet(OUTPUT_DRUGS)
    )

    print(f"[T] Écriture → {OUTPUT_DCI}")
    (
        dci_df.coalesce(1)
        .write.mode("overwrite")
        .option("compression", "snappy")
        .parquet(OUTPUT_DCI)
    )

    # Aussi en CSV pour inspection rapide / chargement direct en BDD
    drugs_csv = str(OUTPUT_DIR / "drugs_ma_clean.csv")
    dci_csv = str(OUTPUT_DIR / "dci_components.csv")

    print(f"[T] Écriture CSV → {drugs_csv}")
    drugs_df.coalesce(1).write.mode("overwrite").option("header", "true").csv(drugs_csv)

    print(f"[T] Écriture CSV → {dci_csv}")
    dci_df.coalesce(1).write.mode("overwrite").option("header", "true").csv(dci_csv)

    print("[T] ✓ Tous les fichiers écrits.")


# ════════════════════════════════════════════════════════════════════════════
# 12. Point d'entrée
# ════════════════════════════════════════════════════════════════════════════


def main():
    if not INPUT_CSV.exists():
        print(f"[ERREUR] CSV introuvable : {INPUT_CSV}", file=sys.stderr)
        sys.exit(1)

    spark = get_spark()
    spark.sparkContext.setLogLevel("WARN")

    try:
        # Transform
        drugs_df, df_with_id = transform_drugs_ma(spark)

        # Table DCI pivot
        dci_df = build_dci_components(df_with_id)

        # Rapport qualité
        print_quality_report(drugs_df)

        # Écriture
        write_outputs(drugs_df, dci_df)

    finally:
        spark.stop()

    print("[T] ✓ Transform terminé avec succès.")


if __name__ == "__main__":
    main()
