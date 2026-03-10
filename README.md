# SafeRx-AI
SafeRx-AI est un système d’aide à la décision clinique (CDSS) qui analyse les prescriptions médicales en temps réel pour détecter surdosages, interactions et contre-indications. Il combine règles médicales, IA et RAG pour générer des alertes pertinentes, réduire l’alert-fatigue et améliorer la sécurité des prescriptions.

```bash
├── 📁 backend
│   ├── 📁 app
│   │   ├── 📁 api
│   │   │   ├── 📁 endpoints
│   │   │   │   ├── 🐍 account.py
│   │   │   │   └── 🐍 auth.py
│   │   │   ├── 🐍 deps.py
│   │   │   └── 🐍 router.py
│   │   ├── 📁 core
│   │   │   ├── 🐍 config.py
│   │   │   └── 🐍 security.py
│   │   ├── 📁 db
│   │   │   ├── 🐍 base.py
│   │   │   ├── 🐍 init_db.py
│   │   │   └── 🐍 session.py
│   │   ├── 📁 models
│   │   │   └── 🐍 user.py
│   │   ├── 📁 schemas
│   │   │   └── 🐍 user.py
│   │   └── 📁 services
│   │       ├── 🐍 email_service.py
│   │       └── 🐍 user_service.py
│   └── 🐍 main.py
├── 📁 data
│   ├── 📁 raw
│   └──  📁 processed
├── 📁 frontend
│   ├── 📁 public
│   │   └── 🖼️ vite.svg
│   ├── 📁 src
│   │   ├── 📁 api
│   │   │   └── 📄 api.js
│   │   ├── 📁 assets
│   │   │   └── 🖼️ react.svg
│   │   ├── 📁 pages
│   │   │   ├── 📄 adminDashboard.jsx
│   │   │   ├── 📄 changePassword.jsx
│   │   │   └── 📄 login.jsx
│   │   ├── 📁 services
│   │   │   └── 📄 authService.js
│   │   ├── 🎨 App.css
│   │   ├── 📄 App.jsx
│   │   ├── 🎨 index.css
│   │   └── 📄 main.jsx
│   ├── ⚙️ .gitignore
│   ├── 🐳 Dockerfile
│   ├── 📝 README.md
│   ├── 📄 eslint.config.js
│   ├── 🌐 index.html
│   ├── ⚙️ package-lock.json
│   ├── ⚙️ package.json
│   ├── 📄 postcss.config.js
│   ├── 📄 src - Raccourci.lnk
│   ├── 📄 tailwind.config.js
│   └── 📄 vite.config.js
├── 📁 scraping
│   └── 🐍 scraper_med_ma.py
├── ⚙️ .env.example
├── ⚙️ .gitignore
├── 🐳 Dockerfile
├── 📝 README.md
├── ⚙️ docker-compose.yml
└── 📄 requirements.txt
```