-- ==========================================
-- SCRIPT D'INITIALISATION DE LA BDD SAFERX
-- Exécuté au premier lancement du conteneur
-- ==========================================

-- 1. Activation des extensions nécessaires
-- Permet de générer des UUIDs (ex: uuid_generate_v4()) pour les logs
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 2. Création du Schéma "KNOWLEDGE_BASE"
-- Ce schéma contiendra toutes les données froides importées par l'ETL (RxNorm, Interactions, etc.)
CREATE SCHEMA IF NOT EXISTS knowledge_base;

-- 3. Création du Schéma "OPERATIONAL"
-- Ce schéma contiendra les données chaudes générées par l'API (Logs, Audits, Feedbacks)
CREATE SCHEMA IF NOT EXISTS operational;

-- 4. Configuration de la Timezone
-- Force le stockage des dates en UTC pour éviter les décalages horaires
ALTER DATABASE saferx_db SET timezone TO 'UTC';