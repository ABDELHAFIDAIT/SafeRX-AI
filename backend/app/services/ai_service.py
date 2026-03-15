from __future__ import annotations

import os
import logging
import json
import re
from typing import Optional

logger = logging.getLogger(__name__)

# Lecture des variables LLM depuis l'environnement
LLM_PROVIDER    = os.getenv("LLM_PROVIDER",    "ollama")
OLLAMA_MODEL    = os.getenv("OLLAMA_MODEL",    "llama3.1:8b")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
GEMINI_API_KEY  = os.getenv("GEMINI_API_KEY",  "")
GEMINI_MODEL    = os.getenv("GEMINI_MODEL",    "gemini-flash-latest")

# RAG actif si Ollama est le provider configuré ou si une clé Gemini est fournie
RAG_ENABLED = (LLM_PROVIDER == "ollama") or bool(GEMINI_API_KEY)

# Cache global du LLM initialisé et du provider actif
_llm             = None
_active_provider = None   # "ollama" | "gemini" | None


def _init_ollama():
    # Initialise Ollama et fait un ping de connectivité avant de valider
    try:
        from langchain_ollama import ChatOllama
        from langchain_core.messages import HumanMessage
        llm = ChatOllama(model=OLLAMA_MODEL, base_url=OLLAMA_BASE_URL, temperature=0.1)
        llm.invoke([HumanMessage(content="ping")])  # test réel de disponibilité
        logger.info(f"[RAG] Ollama actif : {OLLAMA_MODEL} @ {OLLAMA_BASE_URL}")
        return llm
    except Exception as e:
        logger.warning(f"[RAG] Ollama indisponible : {e}")
        return None


def _init_gemini():
    # Retourne None immédiatement si aucune clé API n'est configurée
    if not GEMINI_API_KEY:
        return None
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
        llm = ChatGoogleGenerativeAI(
            model             = GEMINI_MODEL,
            google_api_key    = GEMINI_API_KEY,
            temperature       = 0.1,
            max_output_tokens = 350,  # limite la longueur des réponses
        )
        logger.info(f"[RAG] Gemini actif : {GEMINI_MODEL} (fallback)")
        return llm
    except Exception as e:
        logger.warning(f"[RAG] Gemini indisponible : {e}")
        return None


def _get_llm():
    # Retourne le LLM en cache ou tente de l'initialiser (Ollama → Gemini → None)
    global _llm, _active_provider

    if _llm is not None:
        return _llm
    if not RAG_ENABLED:
        return None

    # Priorité 1 : Ollama local
    _llm = _init_ollama()
    if _llm:
        _active_provider = "ollama"
        return _llm

    # Priorité 2 : Gemini comme fallback automatique
    logger.info("[RAG] Ollama indisponible → tentative Gemini")
    _llm = _init_gemini()
    if _llm:
        _active_provider = "gemini"
        return _llm

    logger.error("[RAG] Aucun provider LLM disponible — enrichissement désactivé.")
    return None


# Prompts spécialisés par type d'alerte — en français médical clinique
PROMPT_INTERACTION = """\
Tu es un pharmacologue clinique expert. Explique en 3 phrases maximum, \
en français médical clair et concis, pourquoi l'association de {dci_a} \
et {dci_b} est classée "{level_fr}" par le Thésaurus ANSM.

Données disponibles :
- Mécanisme : {mechanism}
- Recommandation officielle : {recommendation}

Formule une explication pédagogique pour un médecin prescripteur, \
en indiquant le risque principal et le point de vigilance clinique. \
Ne cite pas de source. Réponds uniquement avec l'explication, \
sans titre ni bullet points."""

PROMPT_ALLERGY = """\
Tu es un pharmacologue clinique. En 2 phrases maximum en français médical, \
explique le risque pour un patient allergique à {allergen} \
qui se verrait prescrire {drug_name} ({dci}).
Mentionne le type de réaction allergique probable et l'urgence clinique. \
Réponds uniquement avec l'explication."""

PROMPT_CONTRA_INDICATION = """\
Tu es un pharmacologue clinique. En 2 phrases maximum en français médical, \
explique pourquoi {drug_name} ({dci}) est contre-indiqué chez un patient {context}.
Mentionne le mécanisme physiologique et le risque principal. \
Réponds uniquement avec l'explication."""

PROMPT_POSOLOGY = """\
Tu es un pharmacologue clinique. En 2 phrases maximum en français médical, \
explique le risque de prescrire {drug_name} à un patient de {patient_age} ans \
alors que ce médicament est autorisé à partir de {min_age}.
Mentionne les risques développementaux ou pharmacocinétiques. \
Réponds uniquement avec l'explication."""

PROMPT_REDUNDANT = """\
Tu es un pharmacologue clinique. En 2 phrases maximum en français médical, \
explique le risque de la double prescription de {dci} (présente dans {drug_list}).
Mentionne le risque de surdosage et l'effet pharmacologique cumulatif. \
Réponds uniquement avec l'explication."""


def generate_rag_explanation(
    alert_type:   str,
    alert_detail: str,
    context:      dict,
) -> Optional[str]:
    # Génère une explication LLM pour une alerte ; retourne None si LLM absent
    if not RAG_ENABLED:
        return None

    llm = _get_llm()
    if llm is None:
        return None

    try:
        prompt = _build_prompt(alert_type, alert_detail, context)
        if not prompt:
            return None

        from langchain_core.messages import HumanMessage
        response    = llm.invoke([HumanMessage(content=prompt)])
        explanation = response.content.strip()

        # Filtre les réponses trop courtes ou anormalement longues
        if len(explanation) < 20 or len(explanation) > 800:
            return None

        return explanation

    except Exception as e:
        global _llm, _active_provider
        # Si Ollama tombe en cours d'exécution, réinitialise vers Gemini au prochain appel
        if _active_provider == "ollama":
            logger.warning(f"[RAG] Ollama erreur runtime : {e} — reset vers Gemini au prochain appel")
            _llm, _active_provider = None, None
        else:
            logger.warning(f"[RAG] Erreur {_active_provider} : {e}")
        return None


def _build_prompt(alert_type: str, alert_detail: str, ctx: dict) -> Optional[str]:
    # Sélectionne et formate le prompt selon le type d'alerte
    if alert_type == "INTERACTION":
        return PROMPT_INTERACTION.format(
            dci_a          = ctx.get("dci_a",          "molécule A"),
            dci_b          = ctx.get("dci_b",          "molécule B"),
            level_fr       = ctx.get("level_fr",       "interaction"),
            mechanism      = ctx.get("mechanism")      or "Non précisé dans le Thésaurus ANSM.",
            recommendation = ctx.get("recommendation") or "Surveiller le patient.",
        )
    if alert_type == "ALLERGY":
        return PROMPT_ALLERGY.format(
            allergen  = ctx.get("allergen",  "la molécule"),
            drug_name = ctx.get("drug_name", "ce médicament"),
            dci       = ctx.get("dci",       "DCI inconnue"),
        )
    if alert_type == "CONTRA_INDICATION":
        return PROMPT_CONTRA_INDICATION.format(
            drug_name = ctx.get("drug_name", "ce médicament"),
            dci       = ctx.get("dci",       "DCI inconnue"),
            context   = ctx.get("context",   "profil clinique particulier"),
        )
    if alert_type == "POSOLOGY":
        return PROMPT_POSOLOGY.format(
            drug_name   = ctx.get("drug_name",   "ce médicament"),
            patient_age = ctx.get("patient_age", "?"),
            min_age     = ctx.get("min_age",     "un certain âge"),
        )
    if alert_type == "REDUNDANT_DCI":
        return PROMPT_REDUNDANT.format(
            dci       = ctx.get("dci",       "cette molécule"),
            drug_list = ctx.get("drug_list", "plusieurs médicaments"),
        )
    return None


def enrich_alerts_with_rag(
    alerts:           list,
    interactions_ctx: dict,
    drugs_ctx:        dict,
    patient_age:      int | None,
) -> None:
    # Enrichit in-place uniquement les alertes MAJOR et MODERATE avec une explication LLM
    if not RAG_ENABLED:
        return

    for alert in alerts:
        if alert.severity not in ("MAJOR", "MODERATE"):
            continue  # les alertes MINOR ne sont pas enrichies
        ctx = _extract_context(alert, interactions_ctx, drugs_ctx, patient_age)
        explanation = generate_rag_explanation(
            alert_type   = alert.alert_type,
            alert_detail = alert.detail or "",
            context      = ctx,
        )
        if explanation:
            alert.rag_explanation = explanation  # stocké directement sur l'objet ORM


def _extract_context(alert, interactions_ctx: dict, drugs_ctx: dict, patient_age) -> dict:
    # Construit le dict de contexte à injecter dans le prompt selon le type d'alerte
    ctx = {}

    if alert.alert_type == "INTERACTION":
        # Cherche la paire DCI dans le contexte d'interactions déjà chargé
        for (dci_a, dci_b), inter in interactions_ctx.items():
            if dci_a.upper() in (alert.title or "").upper() or \
               dci_b.upper() in (alert.title or "").upper():
                ctx = {
                    "dci_a":          inter.dci_a,
                    "dci_b":          inter.dci_b,
                    "level_fr":       inter.level_fr,
                    "mechanism":      inter.mechanism,
                    "recommendation": inter.recommendation,
                }
                break
        if not ctx and "—" in (alert.title or ""):
            # Fallback : parse le titre si l'interaction n'est pas dans le contexte
            parts = alert.title.split("—")[-1].strip().split("/")
            ctx = {
                "dci_a":          parts[0].strip() if len(parts) > 0 else "molécule A",
                "dci_b":          parts[1].strip() if len(parts) > 1 else "molécule B",
                "level_fr":       "interaction",
                "mechanism":      "",
                "recommendation": alert.detail or "",
            }

    elif alert.alert_type == "ALLERGY":
        detail = alert.detail or ""
        ctx = {
            "allergen":  detail.split("allergie documentée à :")[1].split(".")[0].strip()
                         if "allergie documentée à :" in detail else "l'allergène",
            "drug_name": alert.title.split("—")[-1].strip() if "—" in (alert.title or "") else "ce médicament",
            "dci":       alert.title.split("—")[-1].strip() if "—" in (alert.title or "") else "",
        }

    elif alert.alert_type == "CONTRA_INDICATION":
        ctx = {
            "drug_name": alert.title.split("—")[-1].strip() if "—" in (alert.title or "") else "ce médicament",
            "dci":       "",
            # Déduit le contexte clinique depuis le titre de l'alerte
            "context":   "femme enceinte" if "grossesse" in (alert.title or "").lower()
                         else "patiente allaitante",
        }

    elif alert.alert_type == "POSOLOGY":
        detail = alert.detail or ""
        ctx = {
            "drug_name":   alert.title.split("—")[-1].strip() if "—" in (alert.title or "") else "ce médicament",
            "patient_age": patient_age or "inconnu",
            # Extrait l'âge minimal depuis le détail textuel de l'alerte
            "min_age":     detail.split("à partir de")[1].split(".")[0].strip()
                           if "à partir de" in detail else "un certain âge",
        }

    elif alert.alert_type == "REDUNDANT_DCI":
        detail = alert.detail or ""
        ctx = {
            "dci":       alert.title.split("—")[-1].strip() if "—" in (alert.title or "") else "cette molécule",
            "drug_list": detail.split(":")[1].strip() if ":" in detail else "plusieurs médicaments",
        }

    return ctx


def get_ai_status() -> dict:
    # Retourne l'état courant du module RAG — utilisé par GET /ai/status
    return {
        "rag_enabled":         RAG_ENABLED,
        "configured_provider": LLM_PROVIDER,
        "active_provider":     _active_provider,
        "ollama_url":          OLLAMA_BASE_URL,
        "ollama_model":        OLLAMA_MODEL,
        "gemini_model":        GEMINI_MODEL if GEMINI_API_KEY else None,
    }


# Prompt de validation sémantique d'un override — retourne un JSON {valid, feedback}
PROMPT_OVERRIDE_VALIDATION = """\
Tu es un médecin expert en pharmacovigilance chargé de valider les justifications \
cliniques d'override dans un système CDSS.

Un médecin a maintenu une prescription malgré l'alerte suivante :
- Type d'alerte : {alert_type}
- Sévérité : {alert_severity}
- Alerte : {alert_title}

Justification fournie par le médecin :
"{justification}"

Évalue si cette justification est médicalement valide ou du bruit.

Réponds UNIQUEMENT avec un objet JSON strict, sans aucun texte avant ou après :
{{
  "valid": true ou false,
  "feedback": "explication courte en 1 phrase (max 120 caractères)"
}}

Exemples de justification VALIDE :
- "Bénéfice/risque favorable chez ce patient sous corticothérapie chronique"
- "Clairance rénale surveillée, adaptation posologique réalisée"
- "Allergie croisée improbable selon le profil clinique du patient"

Exemples de bruit (NON VALIDE) :
- "ok", "je sais", "pas grave", "c'est bon", "vu", "d'accord", "volontaire"
"""


def validate_override_justification(
    justification:  str,
    alert_type:     str,
    alert_severity: str,
    alert_title:    str,
) -> dict:
    # Valide sémantiquement la justification d'un override via le LLM
    if not RAG_ENABLED or not justification or not justification.strip():
        return {"valid": None, "feedback": None}

    llm = _get_llm()
    if llm is None:
        return {"valid": None, "feedback": None}

    # Justification trop courte → bruit automatique sans appel LLM
    if len(justification.strip()) < 10:
        return {
            "valid":    False,
            "feedback": "Justification trop courte pour être médicalement valide.",
        }

    try:
        prompt = PROMPT_OVERRIDE_VALIDATION.format(
            alert_type     = alert_type     or "inconnue",
            alert_severity = alert_severity or "inconnue",
            alert_title    = alert_title    or "inconnue",
            justification  = justification.strip(),
        )

        from langchain_core.messages import HumanMessage
        response = llm.invoke([HumanMessage(content=prompt)])
        raw      = response.content.strip()

        # Extrait le bloc JSON même si le LLM a ajouté du texte avant/après
        json_match = re.search(r'\{.*\}', raw, re.DOTALL)
        if not json_match:
            raise ValueError(f"Réponse non parseable : {raw[:100]}")

        parsed   = json.loads(json_match.group())
        is_valid = bool(parsed.get("valid", False))
        feedback = str(parsed.get("feedback", ""))[:200]  # limite le feedback à 200 chars

        logger.info(
            f"[§3.3] Override validation — valid={is_valid} | "
            f"justif='{justification[:50]}...'"
        )
        return {"valid": is_valid, "feedback": feedback}

    except Exception as e:
        logger.warning(f"[§3.3] Validation sémantique échouée : {e}")
        return {"valid": None, "feedback": None}