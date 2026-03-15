from __future__ import annotations
import logging
from datetime import date
from sqlalchemy.orm import Session, selectinload
from backend.app.models.cds_alert import CdsAlert
from backend.app.models.drug import Drug, DciComponent
from backend.app.models.drug_interaction import DrugInteraction
from backend.app.models.patient import Patient
from backend.app.models.prescription import Prescription, PrescriptionLine
from backend.app.models.user import User
from backend.app.schemas.clinical_schemas import PrescriptionCreate
from backend.app.services.cds_engine import analyse_prescription, _normalize_for_ansm
from backend.app.services.ai_service import enrich_alerts_with_rag, RAG_ENABLED
from backend.app.services.lr_service import score_alerts

logger = logging.getLogger(__name__)


def _age_years(birthdate: date) -> int | None:
    # Calcule l'âge en années à partir de la date de naissance
    if not birthdate:
        return None
    today = date.today()
    return today.year - birthdate.year - (
        (today.month, today.day) < (birthdate.month, birthdate.day)
    )


def create_prescription(db: Session, payload: PrescriptionCreate, doctor: User) -> Prescription:
    # Vérifie l'existence du patient avant toute création
    patient: Patient | None = db.query(Patient).get(payload.patient_id)
    if not patient:
        raise ValueError(f"Patient {payload.patient_id} introuvable.")

    # Valide que tous les médicaments référencés existent en base
    requested_drug_ids = {line.drug_id for line in payload.lines}
    found_ids = {
        d.id for d in db.query(Drug.id).filter(Drug.id.in_(requested_drug_ids))
    }
    missing = requested_drug_ids - found_ids
    if missing:
        raise ValueError(f"Médicaments introuvables : {missing}")

    # Crée l'en-tête de la prescription avec statut initial "draft"
    prescription = Prescription(
        patient_id    = payload.patient_id,
        doctor_id     = doctor.id,
        fhir_bundle_id= payload.fhir_bundle_id,
        hook_event    = payload.hook_event or "order-sign",
        status        = "draft",
    )
    db.add(prescription)
    db.flush()  # génère prescription.id sans commit

    # Crée chaque ligne de médicament et les ajoute à la session
    lines: list[PrescriptionLine] = []
    for line_data in payload.lines:
        line = PrescriptionLine(
            prescription_id = prescription.id,
            drug_id         = line_data.drug_id,
            dci             = line_data.dci,
            dose_mg         = line_data.dose_mg,
            dose_unit_raw   = line_data.dose_unit_raw,
            frequency       = line_data.frequency,
            route           = line_data.route,
            duration_days   = line_data.duration_days,
        )
        db.add(line)
        lines.append(line)

    db.flush()  # génère les IDs des lignes avant l'analyse CDS

    # Lance le moteur de règles CDS sur toutes les lignes de la prescription
    alerts = analyse_prescription(db=db, patient=patient, lines=lines)

    # Enrichissement RAG : best-effort, n'interrompt pas la prescription si le LLM échoue
    if RAG_ENABLED and alerts:
        try:
            drug_ids     = [l.drug_id for l in lines]
            drugs_by_id  = {
                d.id: d for d in db.query(Drug).filter(Drug.id.in_(drug_ids)).all()
            }
            # Collecte toutes les DCI normalisées ANSM pour chercher les interactions RAG
            all_dcis = set()
            for line in lines:
                comps = (
                    db.query(DciComponent)
                    .filter(DciComponent.drug_id == line.drug_id)
                    .all()
                )
                for comp in comps:
                    all_dcis.add(_normalize_for_ansm(comp.dci))

            # Charge les interactions pertinentes pour le contexte RAG (nécessite ≥2 DCI)
            interactions_raw = (
                db.query(DrugInteraction)
                .filter(
                    DrugInteraction.dci_a.in_(all_dcis) |
                    DrugInteraction.dci_b.in_(all_dcis)
                )
                .all()
            ) if len(all_dcis) >= 2 else []

            # Convertit en dict indexé par paire (dci_a, dci_b) pour accès O(1) dans le RAG
            interactions_ctx = {
                (_normalize_for_ansm(i.dci_a), _normalize_for_ansm(i.dci_b)): i
                for i in interactions_raw
            }

            patient_age = _age_years(patient.birthdate)

            enrich_alerts_with_rag(
                alerts            = alerts,
                interactions_ctx  = interactions_ctx,
                drugs_ctx         = drugs_by_id,
                patient_age       = patient_age,
            )
            logger.info(
                f"RAG enrichissement terminé — {sum(1 for a in alerts if a.rag_explanation)} "
                f"/ {len(alerts)} alertes enrichies"
            )
        except Exception as e:
            logger.error(f"RAG enrichissement échoué (non bloquant) : {e}")

    # Scoring LR : best-effort, n'interrompt pas la prescription si le modèle est absent
    try:
        score_alerts(alerts)
        scored = sum(1 for a in alerts if a.ai_ignore_proba is not None)
        if scored:
            logger.info(f"[LR] Scoring terminé — {scored}/{len(alerts)} alertes scorées")
    except Exception as e:
        logger.error(f"[LR] Scoring échoué (non bloquant) : {e}")

    # Persiste toutes les alertes (avec ou sans enrichissement IA)
    for alert in alerts:
        db.add(alert)

    # Statut final : "alerts" si des alertes ont été détectées, "safe" sinon
    prescription.status = "alerts" if alerts else "safe"

    db.commit()

    # Recharge la prescription avec ses relations pour construire la réponse JSON
    db.refresh(prescription)
    prescription = (
        db.query(Prescription)
        .options(
            selectinload(Prescription.lines).selectinload(PrescriptionLine.alerts)
        )
        .filter(Prescription.id == prescription.id)
        .one()
    )

    return prescription


def get_prescription(db: Session, prescription_id: int) -> Prescription | None:
    # Récupère une prescription avec ses lignes et alertes chargées en eager loading
    return (
        db.query(Prescription)
        .options(
            selectinload(Prescription.lines).selectinload(PrescriptionLine.alerts)
        )
        .filter(Prescription.id == prescription_id)
        .first()
    )


def list_prescriptions_for_patient(db: Session, patient_id: int, skip: int = 0, limit: int = 20) -> list[Prescription]:
    # Retourne les prescriptions d'un patient triées par date décroissante, avec pagination
    return (
        db.query(Prescription)
        .filter(Prescription.patient_id == patient_id)
        .order_by(Prescription.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )