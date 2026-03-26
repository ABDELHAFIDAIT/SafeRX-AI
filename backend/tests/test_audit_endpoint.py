import sys
import unittest
from unittest.mock import MagicMock, patch
from backend.tests.tests_conftest import make_cds_alert, make_user, make_db_session
from backend.app.models.user import Role

# ─────────────────────────────────────────────────────────────────────────────
#  Technique pour récupérer les vraies fonctions des routes FastAPI
# ─────────────────────────────────────────────────────────────────────────────


class _CapturingRouter:
    """
    Remplace APIRouter de FastAPI pour capturer les handlers décorés.
    Exemple : @router.post("/") → on capture la fonction create_audit_entry
    """

    def __init__(self):
        self._routes = {}

    def _capturer(self, methode, chemin):
        def decorator(fn):
            self._routes[(methode, chemin)] = fn
            return fn

        return decorator

    def post(self, chemin, **kw):
        return self._capturer("POST", chemin)

    def get(self, chemin, **kw):
        return self._capturer("GET", chemin)

    def patch(self, chemin, **kw):
        return self._capturer("PATCH", chemin)

    def delete(self, chemin, **kw):
        return self._capturer("DELETE", chemin)


def charger_handlers():
    """Charge le module audit et retourne les vraies fonctions de chaque route."""
    router = _CapturingRouter()
    sys.modules["fastapi"].APIRouter = lambda: router

    # Forcer le rechargement pour capturer les nouvelles fonctions
    cle = "backend.app.api.endpoints.audit"
    if cle in sys.modules:
        del sys.modules[cle]

    import backend.app.api.endpoints.audit  # déclenche les @router.post/get → capture

    return router._routes


# Charger les handlers une seule fois
_HANDLERS = charger_handlers()
_creer_audit = _HANDLERS.get(("POST", "/"))  # POST /audit
_creer_bulk = _HANDLERS.get(("POST", "/bulk"))  # POST /audit/bulk
_audit_recent = _HANDLERS.get(("GET", "/recent"))  # GET  /audit/recent


# ─────────────────────────────────────────────────────────────────────────────
#  Fonctions utilitaires pour les tests
# ─────────────────────────────────────────────────────────────────────────────


def payload_simple(decision="ACCEPTED", justification=None, alert_id=1):
    """Crée un faux payload pour POST /audit."""
    p = MagicMock()
    p.alert_id = alert_id
    p.prescription_id = 1
    p.decision = decision
    p.justification = justification
    return p


def payload_bulk(decisions):
    """Crée un faux payload pour POST /audit/bulk."""
    p = MagicMock()
    p.prescription_id = 1
    p.decisions = decisions
    return p


def decision_item(alert_id, decision, justification=None):
    """Crée une décision individuelle dans un bulk."""
    d = MagicMock()
    d.alert_id = alert_id
    d.decision = decision
    d.justification = justification
    return d


def db_avec_alerte(alerte):
    """Fausse DB qui retourne l'alerte donnée."""
    db = make_db_session()
    db.query.return_value.filter.return_value.first.return_value = alerte
    return db


def db_sequence(alertes):
    """Fausse DB qui retourne les alertes dans l'ordre (pour les bulk)."""
    db = make_db_session()
    idx = [0]

    def suivant():
        v = alertes[idx[0]] if idx[0] < len(alertes) else None
        idx[0] += 1
        return v

    db.query.return_value.filter.return_value.first.side_effect = suivant
    return db


# ─────────────────────────────────────────────────────────────────────────────
#  Tests POST /audit — décision unique
# ─────────────────────────────────────────────────────────────────────────────


class TestDecisionUnique(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(_creer_audit, "Handler POST /audit introuvable")

    def _appeler(self, payload, alerte):
        """Helper : appelle le handler avec l'alerte et un médecin fictif."""
        db = db_avec_alerte(alerte)
        medecin = make_user(role="doctor")
        medecin.id = 1
        _creer_audit(payload=payload, db=db, current_user=medecin)
        return db

    def test_accepted_cree_une_entree_sans_validation(self):
        """
        Décision ACCEPTED → l'entrée est créée en DB.
        Pas besoin de valider la justification (pas d'override).
        """
        alerte = make_cds_alert(id=1, alert_type="INTERACTION", severity="MAJOR")

        with patch(
            "backend.app.api.endpoints.audit.validate_override_justification"
        ) as mock_val:
            db = self._appeler(payload_simple("ACCEPTED"), alerte)
            mock_val.assert_not_called()  # ← pas de validation pour ACCEPTED

        db.add.assert_called_once()  # 1 entrée créée
        db.commit.assert_called_once()  # sauvegardée en DB

    def test_override_appelle_la_validation_semantique(self):
        """
        Décision OVERRIDE + justification → le LLM est appelé pour vérifier
        si la justification est médicalement valide (§3.3).
        """
        alerte = make_cds_alert(
            id=1,
            alert_type="INTERACTION",
            severity="MAJOR",
            title="Interaction RAMIPRIL / SPIRONOLACTONE",
        )
        justif = "Bénéfice/risque évalué, surveillance biologique renforcée."
        resultat_llm = {"valid": True, "feedback": "Pertinent."}

        with patch(
            "backend.app.api.endpoints.audit.validate_override_justification",
            return_value=resultat_llm,
        ) as mock_val:
            db = self._appeler(payload_simple("OVERRIDE", justification=justif), alerte)

        # La validation a été appelée avec les bons paramètres
        mock_val.assert_called_once_with(
            justification=justif,
            alert_type="INTERACTION",
            alert_severity="MAJOR",
            alert_title=alerte.title,
        )
        # L'entrée enregistrée en DB porte le résultat de la validation
        entree = db.add.call_args[0][0]
        self.assertEqual(entree.justification_valid, "valid")
        self.assertEqual(entree.justification_feedback, "Pertinent.")

    def test_override_bruit_sauvegarde_noise(self):
        """
        OVERRIDE avec justification vague → LLM retourne valid=False.
        → L'entrée est sauvegardée avec justification_valid = 'noise'.
        """
        alerte = make_cds_alert(id=1, alert_type="ALLERGY", severity="MAJOR")
        resultat_llm = {"valid": False, "feedback": "Insuffisant."}

        with patch(
            "backend.app.api.endpoints.audit.validate_override_justification",
            return_value=resultat_llm,
        ):
            db = self._appeler(payload_simple("OVERRIDE", justification="ok"), alerte)

        entree = db.add.call_args[0][0]
        self.assertEqual(entree.justification_valid, "noise")

    def test_alerte_introuvable_retourne_404(self):
        """
        Si l'alerte demandée n'existe pas en DB → erreur 404.
        """
        from fastapi import HTTPException

        db = make_db_session()
        db.query.return_value.filter.return_value.first.return_value = (
            None  # ← introuvable
        )
        medecin = make_user(role="doctor")
        medecin.id = 1

        with self.assertRaises(HTTPException) as ctx:
            _creer_audit(
                payload=payload_simple(alert_id=9999), db=db, current_user=medecin
            )

        self.assertEqual(ctx.exception.status_code, 404)

    def test_snapshot_des_donnees_de_lalerte(self):
        """
        Les informations de l'alerte (type, sévérité, titre) sont copiées
        dans l'entrée d'audit pour garder un historique même si l'alerte change.
        """
        alerte = make_cds_alert(
            id=1,
            alert_type="RENAL",
            severity="MAJOR",
            title="Insuffisance rénale — METFORMINE",
        )
        db = self._appeler(payload_simple("ACCEPTED"), alerte)

        entree = db.add.call_args[0][0]
        self.assertEqual(entree.alert_type, "RENAL")
        self.assertEqual(entree.alert_severity, "MAJOR")
        self.assertEqual(entree.alert_title, "Insuffisance rénale — METFORMINE")


# ─────────────────────────────────────────────────────────────────────────────
#  Tests POST /audit/bulk — toutes les décisions d'une prescription
# ─────────────────────────────────────────────────────────────────────────────


class TestDecisionsBulk(unittest.TestCase):
    """
    POST /audit/bulk permet d'enregistrer d'un coup toutes les décisions
    du médecin pour une prescription entière.
    """

    def setUp(self):
        self.assertIsNotNone(_creer_bulk, "Handler POST /audit/bulk introuvable")
        self.medecin = make_user(role="doctor")
        self.medecin.id = 1

    def test_trois_decisions_creent_trois_entrees(self):
        """3 décisions → 3 entrées en DB, 1 seul commit."""
        a1 = make_cds_alert(id=1, alert_type="INTERACTION", severity="MAJOR")
        a2 = make_cds_alert(id=2, alert_type="ALLERGY", severity="MAJOR")
        a3 = make_cds_alert(id=3, alert_type="RENAL", severity="MAJOR")
        db = db_sequence([a1, a2, a3])

        with patch(
            "backend.app.api.endpoints.audit.validate_override_justification",
            return_value={"valid": True, "feedback": "OK."},
        ):
            _creer_bulk(
                payload=payload_bulk(
                    [
                        decision_item(1, "ACCEPTED"),
                        decision_item(2, "IGNORED"),
                        decision_item(3, "OVERRIDE", "Surveillance renforcée."),
                    ]
                ),
                db=db,
                current_user=self.medecin,
            )

        self.assertEqual(db.add.call_count, 3)  # 3 entrées créées
        self.assertEqual(db.commit.call_count, 1)  # 1 seul commit

    def test_alerte_inconnue_est_ignoree_sans_bloquer(self):
        """
        Si une alerte n'existe pas (introuvable) → on la saute
        sans bloquer les autres décisions.
        """
        a1 = make_cds_alert(id=1, alert_type="INTERACTION", severity="MAJOR")
        db = db_sequence([a1, None])  # 2e appel → introuvable

        _creer_bulk(
            payload=payload_bulk(
                [
                    decision_item(1, "ACCEPTED"),  # ← trouvée
                    decision_item(9999, "ACCEPTED"),  # ← introuvable → skip
                ]
            ),
            db=db,
            current_user=self.medecin,
        )
        # Seule l'alerte trouvée est enregistrée
        self.assertEqual(db.add.call_count, 1)


# ─────────────────────────────────────────────────────────────────────────────
#  Tests GET /audit/recent — accès réservé aux admins
# ─────────────────────────────────────────────────────────────────────────────


class TestAccesAdmin(unittest.TestCase):
    """Vérifie que seul un administrateur peut voir le flux d'audit récent."""

    def setUp(self):
        self.assertIsNotNone(_audit_recent, "Handler GET /audit/recent introuvable")

    def test_admin_peut_acceder(self):
        """Un administrateur → accès autorisé, retourne une liste."""
        admin = make_user()
        admin.role = Role.ADMIN
        db = make_db_session()
        db.query.return_value.order_by.return_value.limit.return_value.all.return_value = (
            []
        )

        resultat = _audit_recent(limit=50, db=db, current_user=admin)
        self.assertIsInstance(resultat, list)

    def test_medecin_obtient_403(self):
        """Un médecin (pas admin) → erreur 403 Accès interdit."""
        from fastapi import HTTPException

        medecin = make_user()
        medecin.role = Role.DOCTOR

        with self.assertRaises(HTTPException) as ctx:
            _audit_recent(limit=50, db=make_db_session(), current_user=medecin)

        self.assertEqual(ctx.exception.status_code, 403)

    def test_pharmacien_obtient_403(self):
        """Un pharmacien (pas admin) → erreur 403."""
        from fastapi import HTTPException

        pharmacien = make_user()
        pharmacien.role = Role.PHARMACIST

        with self.assertRaises(HTTPException) as ctx:
            _audit_recent(limit=50, db=make_db_session(), current_user=pharmacien)

        self.assertEqual(ctx.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main(verbosity=2)
