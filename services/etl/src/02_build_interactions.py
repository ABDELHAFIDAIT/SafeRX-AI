import sys
import os
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, upper, trim, lit
from pyspark.sql.types import StructType, StructField, StringType

# ================================================================
#   Le but est de convertir un fichier CSV où les médicaments 
#   sont écrits en toutes lettres (ex: "Aspirin") en une table
#   SQL propre où ils sont remplacés par des codes uniques
#                       officiels (RXCUI).
# ================================================================


# Préparer, Configurer et Sécuriser les variables
APP_NAME = "SafeRX_02_Interactions"
INTERACTIONS_PATH = "/data/raw/interactions/drug_interactions.csv"
DB_URL = os.getenv("DB_URL")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")


def main() :
    # Création et initialisation de la Session Spark
    spark = SparkSession.builder.appName(APP_NAME).getOrCreate()
    print(f"--- Démarrage de l'ETL : {APP_NAME} ---")

    print(f"Lecture du fichier interactions : {INTERACTIONS_PATH}")
    
    # On force un schéma strict de 3 colonnes
    csv_schema = StructType([
        StructField("drug_1_name", StringType(), True),
        StructField("drug_2_name", StringType(), True),
        StructField("description", StringType(), True)
    ])
    
    try :
        # Lecture du ficher drug_interactions.csv 
        raw_inter_df = spark.read.csv(INTERACTIONS_PATH, schema=csv_schema, header=True)
    except Exception as e :
        print(f"ERREUR : Impossible de lire le fichier {INTERACTIONS_PATH}")
        sys.exit(1)
    
    
    print("Chargement du référentiel KB_DRUGS depuis la BDD ...")
    
    jdbc_properties = {
        "user" : DB_USER,
        "password": DB_PASSWORD,
        "driver": "org.postgresql.Driver"   
    }
    
    # Chercher et lire la table kb_drugs déjà créé
    drugs_ref_df = spark.read.jdbc(
        url=DB_URL,
        table="knowledge_base.kb_drugs",
        properties=jdbc_properties
    ).select(
        col('rxcui'),
        upper(trim(col("name"))).alias("ref_name_upper")
    )
    
    print("Mapping des interactions (Recherche des IDs correspondants) ...")
    
    # Étape A : On prépare le CSV (Mise en majuscule)
    input_df = raw_inter_df.select(
        upper(trim(col("drug_1_name"))).alias("d1_input"),
        upper(trim(col("drug_2_name"))).alias("d2_input"),
        col("description"),
        col("drug_1_name").alias("original_name_1"),
        col("drug_2_name").alias("original_name_2")
    )
    
    # Étape B : Jointure Médicament 1
    df_step1 = input_df.join(
        drugs_ref_df,
        input_df.d1_input == drugs_ref_df.ref_name_upper,
        "inner"
    ).withColumnRenamed("rxcui", "rxcui_1").drop("ref_name_upper")
    
    # Étape C : Jointure Médicament 2
    df_final = df_step1.join(
        drugs_ref_df,
        df_step1.d2_input == drugs_ref_df.ref_name_upper,
        "inner"
    ).withColumnRenamed("rxcui", "rxcui_2").drop("ref_name_upper")
    
    kb_interactions_df = df_final.select(
        col("rxcui_1"),
        col("original_name_1").alias("drug_1_name"),
        col("rxcui_2"),
        col("original_name_2").alias("drug_2_name"),
        col("description").alias("severity_description"),
        col("description").alias("interaction_text")
    )
    
    count_raw = raw_inter_df.count()
    count_mapped = kb_interactions_df.count()
    
    print(f"- Résultat du Mapping :")
    print(f"* Lignes lues dans le CSV : {count_raw}")
    print(f"* Interactions validées (IDs trouvés) : {count_mapped}")
    
    if count_mapped == 0:
        print("ATTENTION : Aucune interaction mappée !")
    
    
    print("Écriture dans PostgreSQL (Table: knowledge_base.kb_interactions)...")
    
    try :
        # Sauvegarder le résultat final (ID_1, ID_2, Description) dans PostgreSQL.
        kb_interactions_df.write.jdbc(
            url=DB_URL,
            table="knowledge_base.kb_interactions",
            mode="overwrite",
            properties=jdbc_properties
        )
        
        print("SUCCESS : Interactions chargées avec succès !")
    
    except Exception as e :
        print(f"ERREUR SQL : {e}")
        sys.exit(1)
        
    
    spark.stop()



if __name__ == "__main__":
    main()
