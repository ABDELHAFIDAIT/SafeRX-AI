import json
import unittest
from unittest.mock import MagicMock, patch

from backend.tests.tests_conftest import make_cds_alert


# ─────────────────────────────────────────────────────────────────────────────
#  1. Tests des prompts — est-ce que le bon prompt est construit ?
# ─────────────────────────────────────────────────────────────────────────────

class TestPrompts(unittest.TestCase):
    """Vérifie que chaque type d'alerte génère un prompt approprié."""

    def setUp(self):
        # Recharger le module à chaque test pour repartir d'un état propre
        import importlib
        import backend.app.services.ai_service as ai_mod
        importlib.reload(ai_mod)
        self.build = ai_mod._build_prompt

    def test_prompt_interaction_contient_les_deux_medicaments(self):
        """Un prompt INTERACTION doit nommer les deux médicaments en cause."""
        contexte = {
            "dci_a": "ramipril", "dci_b": "spironolactone",
            "level_fr": "Précaution d'emploi",
            "mechanism": "Risque d'hyperkaliémie",
            "recommendation": "Surveiller kaliémie",
        }
        prompt = self.build("INTERACTION", "", contexte)
        self.assertIsNotNone(prompt)
        self.assertIn("ramipril",       prompt)
        self.assertIn("spironolactone", prompt)

    def test_prompt_allergie_croisee_mentionne_la_famille(self):
        """Allergie croisée → le prompt doit mentionner la famille (ex: Pénicillines)."""
        contexte = {
            "is_cross_allergy": True,
            "allergen_family": "Pénicillines",
            "drug_name": "AMOXICILLINE LLORENTE",
            "dci": "amoxicilline",
        }
        prompt = self.build("ALLERGY", "", contexte)
        self.assertIsNotNone(prompt)
        self.assertIn("Pénicillines", prompt)

    def test_prompt_renal_contient_les_valeurs_de_clairance(self):
        """Alerte rénale → le prompt doit inclure la clairance du patient et le seuil."""
        contexte = {
            "drug_name": "GLUCOPHAGE 1000MG", "dci": "metformine",
            "crcl": "42.5",    # clairance du patient
            "threshold": "45", # seuil de dangerosité
        }
        prompt = self.build("RENAL", "", contexte)
        self.assertIsNotNone(prompt)
        self.assertIn("42.5", prompt)
        self.assertIn("45",   prompt)

    def test_prompt_redondance_mentionne_acidose_lactique(self):
        """
        Bug corrigé : pour la metformine, le prompt doit parler d'acidose lactique
        et NON d'hypoglycémie (qui était une erreur dans la v1).
        """
        contexte = {
            "dci": "Metformine",
            "drug_list": "ACOL 1000MG, GLUCOPHAGE 500MG",
        }
        prompt = self.build("REDUNDANT_DCI", "", contexte)
        self.assertIsNotNone(prompt)
        self.assertIn("acidose lactique", prompt)

    def test_type_inconnu_retourne_none(self):
        """Un type d'alerte qui n'existe pas → None (pas de prompt)."""
        prompt = self.build("TYPE_QUI_NEXISTE_PAS", "", {})
        self.assertIsNone(prompt)


# ─────────────────────────────────────────────────────────────────────────────
#  2. Tests du RAG — est-ce que le LLM est appelé au bon moment ?
# ─────────────────────────────────────────────────────────────────────────────

class TestRAG(unittest.TestCase):
    """
    Vérifie quand le LLM est appelé ou non pour enrichir les alertes.
    Rappel : seules les alertes MAJOR et MODERATE sont enrichies.
    """

    def setUp(self):
        import importlib
        import backend.app.services.ai_service as ai_mod
        importlib.reload(ai_mod)
        self.ai = ai_mod

    def test_rag_desactive_retourne_none(self):
        """Si RAG_ENABLED = False (pas de LLM configuré) → toujours None."""
        with patch.object(self.ai, "RAG_ENABLED", False):
            result = self.ai.generate_rag_explanation("INTERACTION", "", {})
        self.assertIsNone(result)

    def test_rag_filtre_les_reponses_trop_courtes(self):
        """Si le LLM répond "Ok." (< 20 chars) → None. Réponse trop courte = erreur LLM."""
        llm_faux = MagicMock()
        llm_faux.invoke.return_value.content = "Ok."

        with patch.object(self.ai, "RAG_ENABLED", True), \
             patch.object(self.ai, "_get_llm", return_value=llm_faux):
            result = self.ai.generate_rag_explanation("INTERACTION", "", {
                "dci_a": "A", "dci_b": "B", "level_fr": "X",
                "mechanism": "", "recommendation": ""
            })
        self.assertIsNone(result)

    def test_rag_retourne_lexplication_si_valide(self):
        """Si le LLM donne une bonne explication → elle est retournée telle quelle."""
        explication = (
            "L'association ramipril-spironolactone présente un risque "
            "d'hyperkaliémie par double blocage du système rénine-angiotensine."
        )
        llm_faux = MagicMock()
        llm_faux.invoke.return_value.content = explication

        with patch.object(self.ai, "RAG_ENABLED", True), \
             patch.object(self.ai, "_get_llm", return_value=llm_faux):
            result = self.ai.generate_rag_explanation("INTERACTION", "", {
                "dci_a": "ramipril", "dci_b": "spironolactone",
                "level_fr": "Précaution", "mechanism": "", "recommendation": ""
            })
        self.assertEqual(result, explication)

    def test_alertes_minor_ne_sont_jamais_enrichies(self):
        """Les alertes MINOR (informatives) ne passent pas au LLM."""
        alerte = make_cds_alert(severity="MINOR", alert_type="POSOLOGY")
        alerte.rag_explanation = None

        llm_faux = MagicMock()
        with patch.object(self.ai, "RAG_ENABLED", True), \
             patch.object(self.ai, "_get_llm", return_value=llm_faux):
            self.ai.enrich_alerts_with_rag([alerte], {}, {}, 30)

        # MINOR → rag_explanation doit rester None
        self.assertIsNone(alerte.rag_explanation)

    def test_erreur_llm_ne_fait_pas_planter_la_prescription(self):
        """Si le LLM plante (timeout, etc.) → rag_explanation reste None, pas de crash."""
        alerte = make_cds_alert(severity="MAJOR", alert_type="ALLERGY",
                                title="Allergie croisée — TEST",
                                detail="Le patient est allergique aux Pénicilline. (DCI : amoxicilline).")
        alerte.rag_explanation = None

        llm_faux = MagicMock()
        llm_faux.invoke.side_effect = Exception("Ollama timeout")

        with patch.object(self.ai, "RAG_ENABLED", True), \
             patch.object(self.ai, "_get_llm", return_value=llm_faux):
            self.ai.enrich_alerts_with_rag([alerte], {}, {}, 30)

        self.assertIsNone(alerte.rag_explanation)


# ─────────────────────────────────────────────────────────────────────────────
#  3. Tests de la validation des justifications (§3.3)
# ─────────────────────────────────────────────────────────────────────────────

class TestValidationJustification(unittest.TestCase):
    """
    Quand un médecin passe outre (OVERRIDE) une alerte critique,
    il doit donner une justification. Le LLM vérifie si elle est valide.

    Résultats possibles :
      valid = True  → justification médicalement pertinente
      valid = False → bruit (ex: "ok je sais ce que je fais")
      valid = None  → LLM indisponible, pas de validation
    """

    def setUp(self):
        import importlib
        import backend.app.services.ai_service as ai_mod
        importlib.reload(ai_mod)
        self.ai       = ai_mod
        self.valider  = ai_mod.validate_override_justification

    def test_justification_vide_retourne_none(self):
        """Chaîne vide → pas de validation possible."""
        result = self.valider("", "ALLERGY", "MAJOR", "Test")
        self.assertIsNone(result["valid"])
        self.assertIsNone(result["feedback"])

    def test_justification_trop_courte_est_du_bruit(self):
        """'ok' = trop court (< 10 chars) → automatiquement refusé, sans appeler le LLM."""
        with patch.object(self.ai, "RAG_ENABLED", True), \
             patch.object(self.ai, "_get_llm", return_value=MagicMock()):
            result = self.valider("ok", "ALLERGY", "MAJOR", "Test")
        self.assertFalse(result["valid"])
        self.assertIn("courte", result["feedback"].lower())

    def test_llm_valide_une_bonne_justification(self):
        """Le LLM reçoit une vraie justification médicale → valid = True."""
        llm_faux = MagicMock()
        llm_faux.invoke.return_value.content = json.dumps({
            "valid": True,
            "feedback": "Justification médicalement pertinente."
        })

        with patch.object(self.ai, "RAG_ENABLED", True), \
             patch.object(self.ai, "_get_llm", return_value=llm_faux):
            result = self.valider(
                "Bénéfice/risque favorable, patient sous corticothérapie "
                "avec surveillance biologique hebdomadaire.",
                "INTERACTION", "MAJOR", "Interaction ibuprofène/ramipril"
            )

        self.assertTrue(result["valid"])

    def test_llm_rejette_du_bruit(self):
        """Le LLM détecte une justification vague → valid = False."""
        llm_faux = MagicMock()
        llm_faux.invoke.return_value.content = json.dumps({
            "valid": False,
            "feedback": "Justification vague, aucun contexte clinique."
        })

        with patch.object(self.ai, "RAG_ENABLED", True), \
             patch.object(self.ai, "_get_llm", return_value=llm_faux):
            result = self.valider(
                "pas grave je sais ce que je fais",
                "ALLERGY", "MAJOR", "Allergie pénicilline"
            )

        self.assertFalse(result["valid"])

    def test_json_malformé_ne_plante_pas(self):
        """Si le LLM répond du texte non-JSON → valid = None, feedback = None, pas de crash."""
        llm_faux = MagicMock()
        llm_faux.invoke.return_value.content = "Voici mon analyse : bla bla"

        with patch.object(self.ai, "RAG_ENABLED", True), \
             patch.object(self.ai, "_get_llm", return_value=llm_faux):
            result = self.valider(
                "Justification suffisamment longue pour passer le filtre longueur",
                "ALLERGY", "MAJOR", "Test"
            )

        self.assertIsNone(result["valid"])
        self.assertIsNone(result["feedback"])


if __name__ == "__main__":
    unittest.main(verbosity=2)