# SafeRx-AI
SafeRx-AI est un système d’aide à la décision clinique (CDSS) qui analyse les prescriptions médicales en temps réel pour détecter surdosages, interactions et contre-indications. Il combine règles médicales, IA et RAG pour générer des alertes pertinentes, réduire l’alert-fatigue et améliorer la sécurité des prescriptions.


# Cahier de Charge
 
## SafeRX AI - SYSTEME D'AIDE A LA DÉCISION CLINIQUE (CDSS)

```
Réalisé Par :
Abdelhafid AIT EL MOKHTAR
Encadré Par :
M. Hamid OUFAKIR
2025-
```

## TABLE DES MATIÈRES


- I. Contexte et Problématique :
   - 1. La Problématique de l'Erreur de Prescription :
   - 2. Le Défi de l'Interopérabilité (Standards FHIR & CDS Hooks) :
   - 3. L'Enjeu de l'Alert-Fatigue (Fatigue des Alarmes) :
- II. Objectifs du Projet :
- III. Source des Données :
   - 1. Dataset Référentiel Clinique (Vidal.fr) :
   - 2. Dataset Référentiel Économique et Local (Medicament.ma) :
   - 3. Dataset Patients & Clinique (Simulation) :
   - 4. Dataset Logs d'Audit & Historique (Apprentissage IA) :
- IV. Exigences Fonctionnelles :
   - 1. Module Data Engineering & ETL (Back-Office) :
      - 1.1. Ingestion par Scraping Automatisé (Extract) :
      - 1.2. Nettoyage et Normalisation Massive (Transform) :
      - 1.3. Chargement de la Base de Connaissances (Load) :
   - 2. Module Moteur de Règles CDSS (Backend API - FastAPI) :
      - 2.1. Interopérabilité et Réception FHIR :
      - 2.2. Analyse Déterministe des Risques :
   - 3. Module Intelligence Artificielle & NLP (AI Engine) :
      - 3.1. Filtre IA "Anti-Fatigue" :
      - 3.2. Justification Contextuelle par RAG :
      - 3.3. Validation Sémantique des Overrides :
   - 4. Module Interface Utilisateur (Frontend - React) :
      - 4.1. Simulateur de Prescription (EHR) :
      - 4.2. Système d'Alerte "Smart Card" :
      - 4.3. Dashboard de Monitoring :
   - 5. Module Transverse - Sécurité & Audit :
      - 5.1. Journalisation Immuable (Audit Trail) :
      - 5.2. Gestion des Accès (RBAC) :
- V. Exigences Non Fonctionnelles :
   - 1. Performance et Scalabilité :
   - 2. Disponibilité :
   - 3. Sécurité :
   - 4. Confidentialité et Conformité :
   - 5. Confidentialité et Conformité :
   - 6. Localisation et Langue :
   - 7. Extensibilité et Testabilité :
- VI. Architecture technique :
   - 1. Schéma Logique Global :
   - 2. Couche Client (Frontend) :
   - 3. Couche Application (Backend API) :
   - 4. Couche Intelligence Artificielle & NLP :
   - 5. Pipeline de Données (Data Engineering) :
   - 6. Couche de Stockage (Persistence) :
   - 7. Infrastructure et Déploiement :


**Introduction :**
L'informatisation des systèmes de santé a transformé la gestion des dossiers patients,
mais la sécurité des prescriptions reste un défi majeur. L'erreur médicamenteuse, ou
iatrogénie, constitue l'une des principales causes d'incidents évitables à l'hôpital.
Ce projet porte sur la conception et le développement d'un Système d'Aide à la Décision
Clinique **(CDSS - Clinical Decision Support System)**. Il s'agit d'une solution logicielle
intelligente conçue pour agir comme un copilote de sécurité pour les médecins.
L'objectif principal est de s'interfacer en temps réel avec le Dossier Patient Électronique
**(EHR)** pour analyser chaque prescription au moment de la saisie. En croisant les
données pharmacologiques avec le profil clinique du patient, le système détecte les
anomalies critiques (surdosages, interactions, contre-indications) et propose des
corrections actionnables.
Au-delà d'un simple moteur de règles, ce projet intègre des dimensions avancées de
Data Engineering pour la gestion des connaissances médicales, et d'Intelligence
Artificielle pour lutter contre la fatigue des alertes et analyser les justifications médicales.
**I. Contexte et Problématique :**
Le projet s'inscrit dans un contexte médical où la complexité des traitements et la
charge de travail des soignants augmentent le risque d'erreur humaine.

### 1. La Problématique de l'Erreur de Prescription :

L'écriture d'ordonnances ou de protocoles hospitaliers est un flux rapide où des erreurs
de saisie ou d'inattention peuvent avoir des conséquences fatales. Les erreurs les plus
fréquentes que ce système vise à éradiquer incluent :
● **Les erreurs d'ordre de grandeur :** La confusion classique entre milligrammes
(mg) et grammes (g), pouvant entraîner des surdosages de 1000%.


```
● L'inadéquation au patient : La prescription de doses standards à des patients
vulnérables, comme ceux souffrant d'insuffisance rénale ou les enfants
nécessitant un dosage au poids (mg/kg).
● Les interactions dangereuses : L'association de molécules incompatibles par
manque de vérification immédiate dans la littérature.
```
### 2. Le Défi de l'Interopérabilité (Standards FHIR & CDS Hooks) :

Le contexte technique actuel exige que les solutions ne soient pas isolées. Les hôpitaux
modernes utilisent des standards d'interopérabilité. Ce projet s'appuie sur la norme HL
FHIR pour structurer les données de santé et sur le standard CDS Hooks pour
déclencher l'analyse à des moments précis du workflow (ex : **order-sign** au moment de
la signature). L'enjeu est de fournir une réponse en moins de **300 ms** pour ne pas
ralentir le médecin.

### 3. L'Enjeu de l'Alert-Fatigue (Fatigue des Alarmes) :

Les systèmes existants échouent souvent car ils bombardent les médecins d'alertes
mineures, ce qui conduit les praticiens à les ignorer systématiquement. Ce projet place
l'expérience utilisateur au centre en minimisant les faux positifs et l'alerte-fatigue. Il
implémente les **5 rights du CDS (bonne info, bonne personne, bon format, bon canal,
bon moment** ) pour garantir que seules les alertes pertinentes et critiques interrompent
le médecin.
**II. Objectifs du Projet :**
Pour répondre à cette problématique, le système développé vise à atteindre les objectifs
suivants :
● **Détection et Interception :** Identifier automatiquement les incohérences
manifestes (ex : **dose > 100x la normale** ) et les contre-indications basées sur les
données physiologiques du patient ( **âge, poids, créatinine** ).


● **Pédagogie et Actionnabilité :** Fournir au prescripteur non seulement une alerte,
mais un message pédagogique justifié par des sources bibliographiques, avec des
options immédiates pour corriger ou justifier l'exception ( **Override** ).
● **Traçabilité et Audit :** Enregistrer de manière immuable toutes les interactions, les
alertes levées et les justifications fournies par les médecins pour permettre un
audit clinique et une amélioration continue de la qualité des soins.
Ce projet ne se limite pas à l'application de règles statiques ; il ambitionne de créer un
écosystème intelligent capable d'apprendre et d'évoluer grâce à l'analyse de données et
l'intelligence artificielle.
**III. Source des Données :**
Pour réaliser ce Système d'Aide à la Décision Clinique (CDSS) robuste et performant,
l'architecture de données repose sur une approche **ETL (Extract, Transform, Load)**
alimentée par des scripts de **Web Scraping** massifs. Cette stratégie remplace l'utilisation
d'APIs tierces par une base de connaissances locale, garantissant la maîtrise totale du
référentiel, la rapidité de traitement via **PySpark** , et une adaptation parfaite au contexte
médical franco-marocain.

### 1. Dataset Référentiel Clinique (Vidal.fr) :

Ce dataset constitue le cœur scientifique du système. Il est extrait par scraping
dynamique pour structurer les règles de sécurité médicale.
● **Source :** Vidal.fr (Base de données pharmaceutiques de référence).
● **Méthode d'Extraction :** Scraping asynchrone via Playwright. Navigation dans les
monographies pour extraire les données cliniques non disponibles en Open Data.
**● Features (Colonnes) cibles :**
○ **_dci :_** Dénomination Commune Internationale (Clé pivot centrale).
○ **_interaction_level :_** Sévérité de l'interaction (Contre-indication, Association
déconseillée, Précaution d'emploi, À prendre en compte).
○ **_mechanism :_** Explication physiologique de l'interaction (utilisée pour le
module RAG).


```
○ contraindications_cim10 : Liste des pathologies incompatibles (codées en
CIM-10).
○ max_daily_dose : Dose maximale de sécurité par 24h.
```
### 2. Dataset Référentiel Économique et Local (Medicament.ma) :

Ce dataset permet de localiser le système pour le marché marocain en liant les
molécules aux produits commercialisés localement.
● **Source :** Medicament.ma (Index des médicaments au Maroc).
● **Méthode d'Extraction :** Scraping via Playwright pour extraire l'intégralité du
catalogue pharmaceutique incluant les données économiques.
**● Features (Colonnes) cibles :**
○ **_code_ppm :_** Identifiant unique du produit au Maroc (Code PPM).
○ **_brand_name :_** Nom commercial du produit (ex: ABIP 15 MG).
○ **_price_ppv :_** Prix Public de Vente au Maroc en DH (ex: 372.00 dhs).
○ **_atc_code :_** Classification Anatomique Thérapeutique et Chimique (ex:
N05AX12).
○ **_labo_name :_** Laboratoire distributeur ou fabricant (ex: SOTHEMA,
LAPROPHAN).
○ **_tableau :_** Classification de toxicité (Tableau A, B ou Aucun).

### 3. Dataset Patients & Clinique (Simulation) :

Ce dataset simule les données provenant d'un Dossier Patient Électronique (EHR) pour
tester la réaction du CDSS.
● **Source :** Synthea (Générateur de patients fictifs réalistes au standard FHIR).
**● Features (Colonnes) cibles :**
○ **birthdate et gender :** Pour les calculs d'âge et de posologie spécifiques.
○ **_weight_kg :_** Poids actuel, crucial pour les dosages pédiatriques.
○ **_creatinine_clearance :_** Fonction rénale pour les alertes sur les molécules
néphrotoxiques.
○ **_known_allergies :_** Liste des molécules allergènes pour le patient.


### 4. Dataset Logs d'Audit & Historique (Apprentissage IA) :

Ce dataset est généré par le système pour alimenter le modèle de réduction de la
fatigue des alertes.
● **Source :** Génération continue via la table immuable audit_cds_hooks.
**● Features (Colonnes) cibles :**
○ **_doctor_specialty_** et **_time_of_day :_** Variables contextuelles pour prédire la
pertinence de l'alerte.
○ **_action_taken :_** Réponse du médecin (Acceptée ou ignorée/Overridden).
○ **_override_reason :_** Justification textuelle pour l'analyse sémantique par
LLM.
**IV. Exigences Fonctionnelles :**
Ce chapitre détaille les capacités opérationnelles du système **SafeRx-AI** , organisées en
modules interconnectés visant à transformer des données brutes issues du web en une
aide à la décision clinique en temps réel.

### 1. Module Data Engineering & ETL (Back-Office) :

Ce module constitue le socle du système en alimentant la base de connaissances
médicale et économique.

#### 1.1. Ingestion par Scraping Automatisé (Extract) :

```
● Développement de scripts de collecte via Playwright pour extraire les
monographies cliniques de Vidal.fr (molécules, interactions, contre-indications).
● Collecte exhaustive du catalogue national sur Medicament.ma incluant le nom de
marque, le code PPM , le prix PPV et le Tableau de toxicité.
● Gestion de l'orchestration des flux de collecte hebdomadaires via Apache Airflow.
```

#### 1.2. Nettoyage et Normalisation Massive (Transform) :

```
● Utilisation de PySpark pour traiter les volumes de fichiers JSON et nettoyer les
données textuelles brutes.
● Normalisation des unités hétérogènes (g, mg, μg) vers une unité pivot (mg) via
des expressions régulières pour permettre les calculs de sécurité.
● Fusion des référentiels ( Vidal et Medicament.ma ) en utilisant la DCI
(Dénomination Commune Internationale) comme clé de jointure centrale.
```
#### 1.3. Chargement de la Base de Connaissances (Load) :

```
● Insertion des données structurées dans PostgreSQL au sein d'un schéma
versionné (knowledge_base).
```
### 2. Module Moteur de Règles CDSS (Backend API - FastAPI) :

Ce module assure l'analyse en temps réel des prescriptions avec un objectif de réponse
inférieur à **300 ms**.

#### 2.1. Interopérabilité et Réception FHIR :

```
● Exposition de points de terminaison compatibles avec le standard CDS Hooks
(notamment le hook order-sign).
● Validation des ressources HL7 FHIR entrantes via des modèles Pydantic.
```
#### 2.2. Analyse Déterministe des Risques :

```
● Détection d'interactions : Identification des conflits entre molécules selon les
niveaux de gravité (Majeur, Modéré, Mineur).
● Contrôle Posologique : Vérification automatique des doses prescrites par rapport
à la max_daily_dose et aux caractéristiques du patient (âge, poids mg/kg).
● Sécurité Clinique : Alerte en cas de contre-indications liées au profil du patient
(ex: insuffisance rénale ou allergies connues).
```

### 3. Module Intelligence Artificielle & NLP (AI Engine) :

Ce module apporte une analyse prédictive et sémantique pour améliorer l'acceptabilité
des alertes.

#### 3.1. Filtre IA "Anti-Fatigue" :

```
● Modèle de classification ( Random Forest ) entraîné sur l'historique des logs pour
prédire la probabilité d'ignorance d'une alerte par le médecin.
● Priorisation intelligente des alertes critiques pour réduire “la fatigue des alarmes”.
```
#### 3.2. Justification Contextuelle par RAG :

```
● Enrichissement des alertes par un résumé généré via LLM et LangChain ,
expliquant le mécanisme de l'interaction à partir des sources médicales ingérées.
```
#### 3.3. Validation Sémantique des Overrides :

```
● Analyse du texte saisi par le médecin lors du forçage d'une alerte pour déterminer
si la justification médicale est valide ou s'il s'agit d'un bruit.
```
### 4. Module Interface Utilisateur (Frontend - React) :

L'interface simule un dossier patient moderne et interactif.

#### 4.1. Simulateur de Prescription (EHR) :

```
● Formulaire dynamique permettant de sélectionner des produits marocains (issus
de Medicament.ma) et de configurer le profil physiologique du patient.
```
#### 4.2. Système d'Alerte "Smart Card" :

```
● Affichage de cartes d'alerte nonbloquantes (ou modales critiques) présentant le
risque, la source bibliographique et les options d'action (Corriger ou Justifier).
```
#### 4.3. Dashboard de Monitoring :

```
● Visualisation des statistiques de sécurité, du taux de conformité et des erreurs les
plus fréquentes (Top 10).
```

### 5. Module Transverse - Sécurité & Audit :

Garantit la conformité légale et la traçabilité des décisions médicales.

#### 5.1. Journalisation Immuable (Audit Trail) :

```
● Enregistrement systématique de chaque transaction (Prescription + Alerte +
Action du médecin) dans une table SQL en mode "Insert-only".
```
#### 5.2. Gestion des Accès (RBAC) :

● Contrôle d'accès basé sur les rôles pour distinguer les capacités des médecins,
pharmaciens et administrateurs.
**V. Exigences Non Fonctionnelles :**
Ces exigences définissent les contraintes de qualité et les standards techniques
auxquels le système SafeRx-AI doit répondre pour garantir une exploitation en milieu
hospitalier critique.

### 1. Performance et Scalabilité :

Le système doit être extrêmement réactif pour s'intégrer de manière fluide dans le flux
de travail des médecins sans provoquer de ralentissement.
● **Temps de réponse :** L'objectif est une réponse globale (inférieure à **300 ms** ) pour
chaque appel de hook en temps réel. L'utilisation de **FastAPI** avec ses capacités
asynchrones natives est privilégiée pour atteindre ce seuil de performance.
● **Scalabilité :** L'architecture microservices doit supporter une charge d'environ
**1000 requêtes par minute** par établissement de santé.
● **Traitement de données :** Le pipeline ETL (PySpark) doit être capable de traiter
l'intégralité des données scrapées (Vidal et Medicament.ma) en moins de 2
heures lors des mises à jour hebdomadaires.


### 2. Disponibilité :

Compte tenu de l'enjeu vital du CDSS, la disponibilité du service est critique.
● **Haute Disponibilité :** L'architecture doit prévoir une redondance multi-zone et
une haute disponibilité pour les services de base de données et les APIs.
● **SLA :** Le niveau de service (Service Level Agreement) visé est de **99,9 %** de
disponibilité pendant les heures de soins intensifs.

### 3. Sécurité :

La sécurité est primordiale pour protéger l'intégrité du système et les données sensibles.
● **Transport :** Utilisation obligatoire de **TLS 1.2+** (HTTPS) pour toutes les
communications entre le frontend React et le backend FastAPI.
● **Authentification :** Utilisation de **JWT** (JSON Web Tokens) et OAuth2 pour
sécuriser les points de terminaison de l'API.
● **Chiffrement :** Les données au repos dans PostgreSQL doivent être chiffrées en
**AES-**.
● **Contrôle d'accès :** Mise en place d'une gestion des accès basée sur les rôles
( **RBAC** ) pour distinguer les droits des médecins, des pharmaciens et des
administrateurs.

### 4. Confidentialité et Conformité :

```
● Réglementation : Conformité avec les lois locales (ex : législation marocaine
sur la santé/IT) et internationales si applicable (GDPR, HIPAA).
```

### 5. Confidentialité et Conformité :

```
● Réglementation : Conformité stricte avec la législation marocaine sur la
protection des données de santé et les normes internationales telles que le RGPD
ou HIPAA.
● Anonymisation : Les données des patients issues de Synthea utilisées pour les
tests doivent rester strictement fictives et isolées des données réelles.
```
### 6. Localisation et Langue :

```
● Interface Utilisateur : L'interface React doit être multilingue (Français,
Arabe/Darija, et Anglais).
● Contenu Médical : Les sources bibliographiques et les explications du RAG
doivent être présentées en français et en anglais selon la préférence du praticien.
```
### 7. Extensibilité et Testabilité :

```
● Évolutivité : Le système doit permettre l'ajout facile de nouveaux scrapers pour
d'autres bases de données nationales sans modifier le cœur du moteur de règles.
● Tests automatisés :
○ Backend (FastAPI) : Utilisation de Pytest pour les tests unitaires et
d'intégration.
○ Frontend (React) : Utilisation de Vitest pour les composants et Playwright
pour les tests de bout en bout (E2E).
● Environnement de test : Mise en place d'une "sandbox" incluant des simulateurs
d'EHR pour tester les réactions du CDSS face à des scénarios cliniques complexes.
```

**VI. Architecture technique :**
L’architecture de SafeRx-AI repose sur une approche modulaire et conteneurisée,
privilégiant la performance asynchrone pour le temps réel et la puissance du calcul
distribué pour le traitement des données médicales massives.

### 1. Schéma Logique Global :

L'architecture est découpée en quatre couches distinctes :
● **Couche d'Acquisition (Scraping)** : Extraction des données depuis Vidal et
Medicament.ma.
● **Couche de Traitement (ETL)** : Nettoyage et normalisation via Spark.
● **Couche de Service (API)** : Moteur de règles et IA sous FastAPI.
● **Couche Présentation (Client)** : Interface réactive sous React.

### 2. Couche Client (Frontend) :

L'interface utilisateur est conçue comme une Single Page Application (SPA) moderne.
● **Framework : React** (avec Vite pour un build ultra-rapide).
● **Gestion d'État :** Context API ou Redux Toolkit pour le suivi du panier de
prescription et des alertes.
● **Stylisation : Tailwind CSS** & **ShadCN UI** pour une interface clinique épurée et
responsive.
● **Communication :** Axios pour les appels asynchrones vers l'API FastAPI.

### 3. Couche Application (Backend API) :

Le cœur du système est désormais unifié en Python pour une intégration native avec les
outils de Data Science.


```
● Framework : FastAPI.
○ Justification : Gestion native de l'asynchronisme (async/await), validation
automatique via Pydantic et génération automatique de la documentation
Swagger.
● Standard Interopérabilité : Implémentation des spécifications HL7 FHIR et des
protocoles CDS Hooks.
● Moteur de Règles : Logique métier développée en Python pour croiser les
ressources FHIR avec la base de connaissances SQL.
```
### 4. Couche Intelligence Artificielle & NLP :

Le module IA est directement intégré au backend pour minimiser la latence.
● **Modèle Prédictif : Scikit** - **learn** (Random Forest) pour le filtrage de la fatigue des
alertes.
● **Pipeline RAG : LangChain** couplé à un modèle de langage (LLM) pour
transformer les monographies scrapées en explications textuelles intelligibles.
● **Traitement de Texte :** Regex avancées et bibliothèques NLP pour le parsing des
posologies complexes.

### 5. Pipeline de Données (Data Engineering) :

Le flux de données est automatisé pour garantir la fraîcheur du référentiel.
● **Scraping** : **Playwright** (Python). Utilisation de navigateurs "headless" pour simuler
des interactions humaines et contourner les protections anti-bot de manière
éthique.
● **Moteur ETL** : **Apache Spark (PySpark)**. Traitement distribué pour la normalisation
des unités (ex: conversion de toutes les formes de fer en fer élémentaire mg).
● **Orchestration** : **Apache Airflow**. Gestion des DAGs (Directed Acyclic Graphs) pour
planifier les tâches de scraping, de nettoyage et d'insertion en base.


### 6. Couche de Stockage (Persistence) :

● **Base de Données Principale** : **PostgreSQL 15**.
○ _Schéma Knowledge Base_ : Tables relationnelles pour les interactions et les
produits marocains.
○ _Schéma Audit_ : Table immuable pour la traçabilité légale.
● **Stockage de Fichiers** : Volumes Docker pour les fichiers JSON bruts (Landing
Zone).

### 7. Infrastructure et Déploiement :

● **Conteneurisation** : **Docker & Docker Compose**. Chaque module (Web, API, DB,
Scraper, Spark) possède son propre conteneur pour une isolation totale.
● **Environnement** : Configuration centralisée via fichiers .env.
● **Monitoring** : **pgAdmin** pour la supervision des données et logs Docker pour le
suivi des services.


