# SafeRX-AI
Clinical Decision Support System


```bash
SafeRX_Project/
├── docker-compose.yml           # Le fichier maître qui lance tous les services
├── .env                         # Variables d'environnement (Mots de passe DB, Clés API)
├── README.md                    # Documentation du projet
│
├── data/                        # LE DATA LAKE (Volume partagé)
│   ├── raw/                     # Données brutes (RxNorm, OpenFDA, Twosides)
│   │   ├── rxnorm/              # Fichiers .RRF
│   │   ├── openfda/             # Fichiers .json
│   │   └── twosides/            # Fichiers .csv
│   ├── processed/               # Données nettoyées (Parquet/CSV propres)
│   └── postgres_data/           # Persistance de la Base de Données (Ne pas toucher)
│
├── services/                    # LES MICRO-SERVICES
│   │
│   ├── etl/                     # SERVICE 1 : DATA ENGINEERING (Spark)
│   │   ├── Dockerfile           # Image Docker avec Spark & Java pré-installés
│   │   ├── requirements.txt     # Libs Python (pyspark, pandas...)
│   │   └── src/                 # Scripts PySpark
│   │       ├── 01_build_master_data.py
│   │       ├── 02_build_interactions.py
│   │       └── utils/           # Fonctions communes (cleaning, mapping)
│   │
│   ├── backend/                 # SERVICE 2 : CORE API (NestJS)
│   │   ├── Dockerfile
│   │   ├── package.json
│   │   └── src/
│   │       ├── main.ts
│   │       ├── app.module.ts
│   │       ├── cds-hooks/       # Module de gestion du standard FHIR/CDS
│   │       ├── interactions/    # Module de logique métier (Règles)
│   │       ├── audit/           # Module de traçabilité
│   │       └── common/          # DTOs, Entités TypeORM, Constantes
│   │
│   ├── ai-engine/               # SERVICE 3 : IA & NLP (Python/FastAPI)
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── app/
│   │       ├── main.py          # Point d'entrée API
│   │       ├── models/          # Modèles ML (Pickle files)
│   │       └── nlp/             # Logique d'analyse de texte
│   │
│   └── frontend/                # SERVICE 4 : UI (Next.js)
│       ├── Dockerfile
│       ├── package.json
│       └── src/
│           ├── app/             # Pages (Next.js 14 App Router)
│           ├── components/      # Composants React (Cards, Forms)
│           └── lib/             # Appels API vers le Backend
│
└── infrastructure/              # CONFIGURATIONS INFRA
    ├── postgres/
    │   └── init.sql             # Script SQL exécuté au 1er lancement (Création Schémas)
    └── nginx/                   # (Optionnel) Reverse Proxy
        └── nginx.conf
```