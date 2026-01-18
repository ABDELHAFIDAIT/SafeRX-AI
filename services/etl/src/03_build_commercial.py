import sys
import os
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, upper, trim, split
from pyspark.sql.types import StructType, StructField, StringType, IntegerType

# --- CONFIGURATION ---
APP_NAME = "SafeRX_03_Commercial"
IMAGE_DATA_PATH = "/data/raw/commercial/drugs_images.csv"

# Infos DB
DB_URL = os.getenv("DB_URL", "jdbc:postgresql://db:5432/saferx_db")
DB_USER = os.getenv("DB_USER", "admin")
DB_PASSWORD = os.getenv("DB_PASSWORD", "saferx_password")

def main():
    spark = SparkSession.builder.appName(APP_NAME).getOrCreate()
    print(f"--- Démarrage de l'ETL : {APP_NAME} ---")

    # 1. Lecture du CSV Images
    print(f"Lecture du fichier : {IMAGE_DATA_PATH}")
    
    schema = StructType([
        StructField("medicine_name", StringType(), True),
        StructField("composition", StringType(), True),
        StructField("uses", StringType(), True),
        StructField("side_effects", StringType(), True),
        StructField("image_url", StringType(), True),
        StructField("manufacturer", StringType(), True),
        StructField("excellent_review", IntegerType(), True),
        StructField("average_review", IntegerType(), True),
        StructField("poor_review", IntegerType(), True)
    ])

    try:
        # escape="\"" est important car certaines descriptions contiennent des guillemets
        raw_df = spark.read.csv(IMAGE_DATA_PATH, schema=schema, header=True, escape="\"")
    except Exception as e:
        print(f"ERREUR : Impossible de lire le fichier.\n{e}")
        sys.exit(1)

    # 2. Nettoyage de la colonne 'Composition'
    print("Nettoyage des compositions pour le mapping...")
    
    # On prend le premier mot avant la parenthèse "("
    clean_df = raw_df.withColumn(
        "ingredient_key",
        upper(trim(split(col("composition"), "\\(").getItem(0))) 
    )

    # 3. Chargement de KB_DRUGS (Sans filtre sur tty cette fois !)
    print("Chargement du référentiel...")
    jdbc_properties = {"user": DB_USER, "password": DB_PASSWORD, "driver": "org.postgresql.Driver"}

    # CORRECTION ICI : On ne filtre plus sur 'tty' car la colonne n'existe pas en base.
    drugs_df = spark.read.jdbc(url=DB_URL, table="knowledge_base.kb_drugs", properties=jdbc_properties) \
        .select(col("rxcui"), upper(trim(col("name"))).alias("ref_name"))

    # 4. Jointure (Mapping)
    print("Croisement des données (Images <-> RxNorm)...")
    
    final_df = clean_df.join(
        drugs_df,
        clean_df.ingredient_key == drugs_df.ref_name,
        "inner"
    ).select(
        col("rxcui"), # Clé étrangère vers KB_DRUGS
        col("medicine_name").alias("brand_name"),
        col("manufacturer"),
        col("image_url"),
        col("uses").alias("medical_uses"),
        col("side_effects")
    ).dropDuplicates(["brand_name"])

    count = final_df.count()
    print(f"--> Produits commerciaux mappés et valides : {count}")

    if count == 0:
        print("ATTENTION : Aucun produit n'a pu être lié. Vérifiez la logique de nettoyage.")

    # 5. Écriture
    print("Sauvegarde dans PostgreSQL (kb_commercial_products)...")
    
    try:
        final_df.write.jdbc(
            url=DB_URL,
            table="knowledge_base.kb_commercial_products",
            mode="overwrite",
            properties=jdbc_properties
        )
        print("--- SUCCESS : Produits commerciaux chargés ---")
    except Exception as e:
        print(f"ERREUR SQL : {e}")
        sys.exit(1)

    spark.stop()

if __name__ == "__main__":
    main()
    

# docker exec saferx-etl spark-submit --packages org.postgresql:postgresql:42.6.0 /app/src/03_build_commercial.py