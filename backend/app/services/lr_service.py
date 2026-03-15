from __future__ import annotations
import os
import logging
import pickle
from datetime import datetime
from pathlib import Path
from typing import Optional
import numpy as np

logger = logging.getLogger(__name__)

# Chemin du fichier .pkl du modèle et seuil minimal d'échantillons pour l'entraînement
MODEL_PATH   = Path(os.getenv("LR_MODEL_PATH", "/app/data/models/lr_alert_fatigue.pkl"))
MIN_SAMPLES  = int(os.getenv("LR_MIN_SAMPLES", "20"))

# Encodages catégoriels pour les features du modèle (entiers ordonnés)
ALERT_TYPE_MAP = {
    "INTERACTION":        0,
    "ALLERGY":            1,
    "CONTRA_INDICATION":  2,
    "POSOLOGY":           3,
    "REDUNDANT_DCI":      4,
    "UNKNOWN":            5,
}

SEVERITY_MAP = {
    "MAJOR":    2,  # valeur la plus haute → plus susceptible d'être ignoré selon l'historique
    "MODERATE": 1,
    "MINOR":    0,
    "UNKNOWN":  0,
}


def _encode_row(
    alert_type:     str,
    alert_severity: str,
    created_at:     datetime,
) -> list[float]:
    # Encode une alerte en vecteur de 4 features numériques pour la LR
    type_enc     = ALERT_TYPE_MAP.get(alert_type,     ALERT_TYPE_MAP["UNKNOWN"])
    severity_enc = SEVERITY_MAP.get(alert_severity,   SEVERITY_MAP["UNKNOWN"])
    hour         = created_at.hour        if created_at else 12   # heure de la décision
    dow          = created_at.weekday()   if created_at else 0    # jour de la semaine (0=lundi)
    return [float(type_enc), float(severity_enc), float(hour), float(dow)]


# Modèle sklearn en mémoire + métadonnées de l'entraînement
_model      = None
_model_meta = {
    "trained":       False,
    "n_samples":     0,
    "accuracy":      None,
    "trained_at":    None,
}


def _load_model() -> bool:
    # Charge le modèle .pkl depuis le disque si disponible, retourne True si succès
    global _model, _model_meta
    if MODEL_PATH.exists():
        try:
            with open(MODEL_PATH, "rb") as f:
                saved = pickle.load(f)
            _model      = saved["model"]
            _model_meta = saved["meta"]
            logger.info(
                f"[LR] Modèle chargé — {_model_meta['n_samples']} samples, "
                f"accuracy={_model_meta['accuracy']:.3f}"
            )
            return True
        except Exception as e:
            logger.warning(f"[LR] Échec chargement modèle : {e}")
    return False


def _save_model() -> None:
    # Persiste le modèle + ses métadonnées dans un fichier pickle
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MODEL_PATH, "wb") as f:
        pickle.dump({"model": _model, "meta": _model_meta}, f)
    logger.info(f"[LR] Modèle sauvegardé → {MODEL_PATH}")


def train(db) -> dict:
    # Entraîne la Logistic Regression sur l'historique audit_cds_hooks
    global _model, _model_meta

    from app.models.audit_cds_hook import AuditCdsHook

    try:
        from sklearn.linear_model import LogisticRegression
        from sklearn.model_selection import train_test_split
        from sklearn.preprocessing import StandardScaler
        from sklearn.pipeline import Pipeline
        from sklearn.metrics import accuracy_score
    except ImportError:
        return {"status": "error", "detail": "scikit-learn non installé (pip install scikit-learn)"}

    rows = db.query(AuditCdsHook).all()

    if len(rows) < MIN_SAMPLES:
        return {
            "status":    "insufficient_data",
            "detail":    f"Seulement {len(rows)} entrées dans audit_cds_hooks. Minimum requis : {MIN_SAMPLES}.",
            "n_samples": len(rows),
        }

    # Construit X (features) et y (label : 1 = ignoré, 0 = accepté)
    X, y = [], []
    for row in rows:
        label = 1 if row.decision in ("IGNORED", "OVERRIDE") else 0  # binaire : ignoré vs accepté
        features = _encode_row(
            alert_type     = row.alert_type     or "UNKNOWN",
            alert_severity = row.alert_severity or "UNKNOWN",
            created_at     = row.created_at,
        )
        X.append(features)
        y.append(label)

    X = np.array(X)
    y = np.array(y)

    # Vérifie qu'il y a au moins 2 classes pour que la LR puisse s'entraîner
    unique_classes = np.unique(y)
    if len(unique_classes) < 2:
        return {
            "status": "insufficient_diversity",
            "detail": "Toutes les décisions sont identiques — impossible d'entraîner un classifieur.",
            "n_samples": len(rows),
        }

    # Split train/test uniquement si assez de données, sinon entraîne sur le tout
    if len(rows) >= 40:
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
    else:
        X_train, X_test, y_train, y_test = X, X, y, y

    # Pipeline : normalise les features puis applique la LR avec poids équilibrés
    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("lr",     LogisticRegression(
            C             = 1.0,
            max_iter      = 500,
            class_weight  = "balanced",  # compense le déséquilibre ACCEPTED >> IGNORED
            random_state  = 42,
            solver        = "lbfgs",
        )),
    ])

    pipeline.fit(X_train, y_train)
    accuracy = accuracy_score(y_test, pipeline.predict(X_test))

    _model = pipeline
    _model_meta = {
        "trained":    True,
        "n_samples":  len(rows),
        "accuracy":   round(float(accuracy), 4),
        "trained_at": datetime.utcnow().isoformat(),
    }

    _save_model()

    logger.info(f"[LR] Modèle entraîné — {len(rows)} samples, accuracy={accuracy:.3f}")

    return {
        "status":    "ok",
        "n_samples": len(rows),
        "accuracy":  _model_meta["accuracy"],
        "trained_at": _model_meta["trained_at"],
    }


def score_alert(
    alert_type:     str,
    alert_severity: str,
    created_at:     Optional[datetime] = None,
) -> Optional[float]:
    # Prédit la probabilité qu'un médecin ignore cette alerte (0.0 → 1.0)
    global _model

    if _model is None:
        _load_model()  # chargement lazy depuis le disque

    if _model is None:
        return None  # modèle pas encore entraîné

    try:
        features = _encode_row(
            alert_type     = alert_type,
            alert_severity = alert_severity,
            created_at     = created_at or datetime.utcnow(),
        )
        X = np.array([features])
        proba = _model.predict_proba(X)[0][1]  # probabilité de la classe "ignoré" (index 1)
        return round(float(proba), 3)
    except Exception as e:
        logger.warning(f"[LR] Scoring échoué : {e}")
        return None


def score_alerts(alerts: list) -> None:
    # Enrichit in-place une liste d'alertes avec ai_ignore_proba — appelé par prescription_service
    global _model

    if _model is None:
        _load_model()

    if _model is None:
        logger.info("[LR] Modèle non disponible — scoring ignoré (pas encore entraîné)")
        return

    now = datetime.utcnow()
    for alert in alerts:
        proba = score_alert(
            alert_type     = alert.alert_type     or "UNKNOWN",
            alert_severity = alert.severity       or "UNKNOWN",
            created_at     = now,
        )
        if proba is not None:
            alert.ai_ignore_proba = proba  # stocké directement sur l'objet ORM


def get_lr_status() -> dict:
    # Retourne l'état courant du modèle LR — utilisé par GET /ai/status
    global _model, _model_meta
    if _model is None:
        _load_model()
    return {
        "model_ready":  _model is not None,
        "model_path":   str(MODEL_PATH),
        **_model_meta,
    }