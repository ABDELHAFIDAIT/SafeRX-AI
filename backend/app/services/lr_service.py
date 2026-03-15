from __future__ import annotations
import os
import logging
import pickle
from datetime import datetime
from pathlib import Path
from typing import Optional
import numpy as np


logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
#  Configuration
# ─────────────────────────────────────────────────────────────────────────────

MODEL_PATH   = Path(os.getenv("LR_MODEL_PATH", "/app/data/models/lr_alert_fatigue.pkl"))
MIN_SAMPLES  = int(os.getenv("LR_MIN_SAMPLES", "20"))   # minimum pour entraîner

# ─────────────────────────────────────────────────────────────────────────────
#  Encodage des features catégorielles
# ─────────────────────────────────────────────────────────────────────────────

ALERT_TYPE_MAP = {
    "INTERACTION":        0,
    "ALLERGY":            1,
    "CONTRA_INDICATION":  2,
    "POSOLOGY":           3,
    "REDUNDANT_DCI":      4,
    "UNKNOWN":            5,
}

SEVERITY_MAP = {
    "MAJOR":    2,
    "MODERATE": 1,
    "MINOR":    0,
    "UNKNOWN":  0,
}


def _encode_row(
    alert_type:     str,
    alert_severity: str,
    created_at:     datetime,
) -> list[float]:
    """
    Encode une observation en vecteur de features numériques.
    Features : [alert_type_enc, severity_enc, hour_of_day, day_of_week]
    """
    type_enc     = ALERT_TYPE_MAP.get(alert_type,     ALERT_TYPE_MAP["UNKNOWN"])
    severity_enc = SEVERITY_MAP.get(alert_severity,   SEVERITY_MAP["UNKNOWN"])
    hour         = created_at.hour        if created_at else 12
    dow          = created_at.weekday()   if created_at else 0
    return [float(type_enc), float(severity_enc), float(hour), float(dow)]


# ─────────────────────────────────────────────────────────────────────────────
#  Modèle global (chargé en mémoire une fois)
# ─────────────────────────────────────────────────────────────────────────────

_model      = None   # sklearn LogisticRegression
_model_meta = {
    "trained":       False,
    "n_samples":     0,
    "accuracy":      None,
    "trained_at":    None,
}


def _load_model() -> bool:
    """Charge le modèle depuis le disque si disponible. Retourne True si succès."""
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
    """Persiste le modèle + métadonnées sur le disque."""
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MODEL_PATH, "wb") as f:
        pickle.dump({"model": _model, "meta": _model_meta}, f)
    logger.info(f"[LR] Modèle sauvegardé → {MODEL_PATH}")


# ─────────────────────────────────────────────────────────────────────────────
#  Entraînement
# ─────────────────────────────────────────────────────────────────────────────

def train(db) -> dict:
    """
    Entraîne la Logistic Regression sur l'historique audit_cds_hooks.

    Retourne :
        dict avec n_samples, accuracy, status
    """
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

    # ── Charger les données ───────────────────────────────────────────────
    rows = db.query(AuditCdsHook).all()

    if len(rows) < MIN_SAMPLES:
        return {
            "status":    "insufficient_data",
            "detail":    f"Seulement {len(rows)} entrées dans audit_cds_hooks. Minimum requis : {MIN_SAMPLES}.",
            "n_samples": len(rows),
        }

    # ── Construire X et y ─────────────────────────────────────────────────
    X, y = [], []
    for row in rows:
        # Label : 1 = ignoré (IGNORED ou OVERRIDE), 0 = accepté
        label = 1 if row.decision in ("IGNORED", "OVERRIDE") else 0
        features = _encode_row(
            alert_type     = row.alert_type     or "UNKNOWN",
            alert_severity = row.alert_severity or "UNKNOWN",
            created_at     = row.created_at,
        )
        X.append(features)
        y.append(label)

    X = np.array(X)
    y = np.array(y)

    # ── Vérifier qu'il y a les deux classes ──────────────────────────────
    unique_classes = np.unique(y)
    if len(unique_classes) < 2:
        return {
            "status": "insufficient_diversity",
            "detail": "Toutes les décisions sont identiques — impossible d'entraîner un classifieur.",
            "n_samples": len(rows),
        }

    # ── Split train/test ──────────────────────────────────────────────────
    # Si moins de 40 samples → pas de split, on entraîne sur tout
    if len(rows) >= 40:
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
    else:
        X_train, X_test, y_train, y_test = X, X, y, y

    # ── Pipeline : StandardScaler + LogisticRegression ───────────────────
    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("lr",     LogisticRegression(
            C             = 1.0,
            max_iter      = 500,
            class_weight  = "balanced",   # compense le déséquilibre ACCEPTED >> IGNORED
            random_state  = 42,
            solver        = "lbfgs",
        )),
    ])

    pipeline.fit(X_train, y_train)
    accuracy = accuracy_score(y_test, pipeline.predict(X_test))

    # ── Mettre à jour le modèle global ───────────────────────────────────
    _model = pipeline
    _model_meta = {
        "trained":    True,
        "n_samples":  len(rows),
        "accuracy":   round(float(accuracy), 4),
        "trained_at": datetime.utcnow().isoformat(),
    }

    _save_model()

    logger.info(
        f"[LR] Modèle entraîné — {len(rows)} samples, "
        f"accuracy={accuracy:.3f}"
    )

    return {
        "status":    "ok",
        "n_samples": len(rows),
        "accuracy":  _model_meta["accuracy"],
        "trained_at": _model_meta["trained_at"],
    }


# ─────────────────────────────────────────────────────────────────────────────
#  Scoring
# ─────────────────────────────────────────────────────────────────────────────

def score_alert(
    alert_type:     str,
    alert_severity: str,
    created_at:     Optional[datetime] = None,
) -> Optional[float]:
    """
    Prédit la probabilité qu'un médecin ignore cette alerte.
    Retourne un float entre 0 et 1, ou None si le modèle n'est pas prêt.
    """
    global _model

    # Charger le modèle depuis le disque si pas encore en mémoire
    if _model is None:
        _load_model()

    if _model is None:
        return None

    try:
        features = _encode_row(
            alert_type     = alert_type,
            alert_severity = alert_severity,
            created_at     = created_at or datetime.utcnow(),
        )
        X = np.array([features])
        # proba[:, 1] = probabilité de la classe "ignoré"
        proba = _model.predict_proba(X)[0][1]
        return round(float(proba), 3)
    except Exception as e:
        logger.warning(f"[LR] Scoring échoué : {e}")
        return None


def score_alerts(alerts: list) -> None:
    """
    Enrichit in-place une liste d'alertes CdsAlert avec ai_ignore_proba.
    Appelé par prescription_service après le RAG.
    Ne lève jamais d'exception.
    """
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
            alert.ai_ignore_proba = proba


# ─────────────────────────────────────────────────────────────────────────────
#  Statut du modèle (exposé dans GET /ai/status)
# ─────────────────────────────────────────────────────────────────────────────

def get_lr_status() -> dict:
    global _model, _model_meta
    if _model is None:
        _load_model()
    return {
        "model_ready":  _model is not None,
        "model_path":   str(MODEL_PATH),
        **_model_meta,
    }