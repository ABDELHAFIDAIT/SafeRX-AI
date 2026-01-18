import sys
import os
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, split, trim
from pyspark.sql.types import StructType, StructField, StringType


# ================================================================
#   Transformer le fichier brut très complexe RxNorm/RXNCONSO 
#       en une table propre et utilisable dans la BDD
# ================================================================




# Préparer, Configurer et Sécuriser les variables
APP_NAME = "SafeRX_01_MasterData"
RXNORM_PATH = "/data/raw/rxnorm/RXNCONSO.RRF"
DB_URL = os.getenv("DB_URL")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")


def main():
    # Création et initialisation de la Session Spark
    spark = SparkSession.builder.appName(APP_NAME).getOrCreate()
    print(f"Démarrage de l'ETL : {APP_NAME} ...")

    print(f"Lecture du fichier brut : {RXNORM_PATH} ...")
    
    try:
        # Lecture du ficher RXNCONSO sous forme text tel que chaque ligne est comme un seul string
        raw_text_df = spark.read.text(RXNORM_PATH)
    except Exception as e:
        print(f"ERREUR : lors de la lecture du fichier : {e}")
        sys.exit(1)

    
    print("Découpage et structuration des données...")
    
    # Prendre chaque ligne et on la coupe à chaque fois on voit un symbole "|"
    split_col = split(col("value"), "\\|")
    
    # On ne garde que les colonnes utiles (ID, Langue, Source, Type, Nom) et on jette le reste 
    # il y a 19 colonnes dans le fichier d'origine, on en garde 6
    df_parsed = raw_text_df.select(
        trim(split_col.getItem(0)).alias("rxcui"),
        trim(split_col.getItem(1)).alias("lat"),
        trim(split_col.getItem(11)).alias("sab"),
        trim(split_col.getItem(12)).alias("tty"),
        trim(split_col.getItem(13)).alias("code"),
        trim(split_col.getItem(14)).alias("name")
    )

    target_tty = ['IN', 'SCD', 'SBD', 'MIN', 'PIN']
    
    print("Application des filtres (ENG + RXNORM)...")
    clean_df = df_parsed.filter(
        (col("lat") == "ENG") &         # Règle 1 : Uniquement l'anglais
        (col("sab") == "RXNORM") &      # Règle 2 : Uniquement la source officielle
        (col("tty").isin(target_tty))   # Règle 3 : Uniquement les vrais médicaments (pas les équipements)
    ).drop("lat", "sab", "tty", "code").dropDuplicates(["rxcui"])


    count = clean_df.count()
    print(f"--> Nombre de médicaments valides trouvés : {count}")
    
    if count == 0:
        print("ERREUR : Aucun médicament trouvé après filtrage. Vérifiez le contenu du fichier RRF.")
        sys.exit(1)


    print("Écriture dans PostgreSQL (Table: knowledge_base.kb_drugs)...")
    
    jdbc_properties = {
        "user": DB_USER,
        "password": DB_PASSWORD,
        "driver": "org.postgresql.Driver"
    }

    try:
        # Il ouvre une connexion vers PostgreSQL
        # Si la table existe déjà, il l'efface et la recrée
        # Si la table n'existe pas, Spark va créer la commande CREATE TABLE automatiquement en regardant les colonnes de clean_df
        clean_df.write.jdbc(
            url=DB_URL,
            table="knowledge_base.kb_drugs",
            mode="overwrite",
            properties=jdbc_properties
        )
        print("SUCCESS : ETL Terminé avec succès ...")
    except Exception as e:
        print(f"ERREUR SQL : Impossible d'écrire dans la base.\n{e}")
        sys.exit(1)

    spark.stop()



if __name__ == "__main__" :
    main()