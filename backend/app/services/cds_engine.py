from __future__ import annotations
import re
import unicodedata
from datetime import date
from typing import List
from sqlalchemy import func
from sqlalchemy.orm import Session
from backend.app.models.cds_alert import CdsAlert
from backend.app.models.drug import Drug, DciComponent
from backend.app.models.drug_interaction import DrugInteraction
from backend.app.models.patient import Patient
from backend.app.models.prescription import PrescriptionLine

# ─────────────────────────────────────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _age_years(birthdate: date) -> int:
    today = date.today()
    return (
        today.year
        - birthdate.year
        - ((today.month, today.day) < (birthdate.month, birthdate.day))
    )


def _normalize_dci(dci: str) -> str:
    # Normalise en minuscules pour la comparaison interne
    return dci.strip().lower()


def _normalize_for_ansm(dci: str) -> str:
    # Normalise en MAJUSCULES sans accents pour matcher le format du Thésaurus ANSM
    # ex: "métoprolol" → "METOPROLOL", robuste aux variantes d'encodage
    nfd = unicodedata.normalize("NFD", dci.strip().upper())
    return "".join(c for c in nfd if unicodedata.category(c) != "Mn")


def _parse_min_age_years(raw: str | None) -> int | None:
    if not raw:
        return None
    s = raw.lower().strip()
    if any(k in s for k in ("nouveau-né", "neonatal", "nourrisson")):
        return 0
    m = re.search(r"(\d+)\s*mois", s)
    if m:
        return max(0, int(m.group(1)) // 12)
    m = re.search(r"(\d+)\s*(?:ans?|years?)", s)
    if m:
        return int(m.group(1))
    m = re.search(r"^(\d+)$", s)
    if m:
        return int(m.group(1))
    return None


def _mentions_pregnancy(text: str | None) -> bool:
    if not text:
        return False
    kw = (
        "grossesse",
        "enceinte",
        "pregnant",
        "pregnancy",
        "tératogène",
        "teratogen",
        "foetus",
        "fœtus",
    )
    return any(k in text.lower() for k in kw)


def _mentions_breastfeeding(text: str | None) -> bool:
    if not text:
        return False
    kw = ("allaitement", "allaiter", "breastfeed", "lactation", "lait maternel")
    return any(k in text.lower() for k in kw)


# ─────────────────────────────────────────────────────────────────────────────
#  Règle 6 — INTERACTION
# ─────────────────────────────────────────────────────────────────────────────


def _check_interactions(
    db: Session,
    lines: List[PrescriptionLine],
    primary_dcis: dict[int, List[str]],
    drugs_by_id: dict[int, Drug],
) -> List[CdsAlert]:
    # Détecte toutes les interactions DCI×DCI en une seule requête SQL sur le Thésaurus ANSM
    alerts: List[CdsAlert] = []

    if len(lines) < 2:
        return alerts

    # ── Construire l'index line_id → {dci_ansm_normalisé} ────────────────
    line_dcis_ansm: dict[int, set[str]] = {}
    for line in lines:
        raw_dcis = primary_dcis.get(line.drug_id, [_normalize_dci(line.dci)])
        line_dcis_ansm[line.id] = {_normalize_for_ansm(d) for d in raw_dcis}

    all_dcis_ansm = set().union(*line_dcis_ansm.values())

    if len(all_dcis_ansm) < 2:
        return alerts

    # ── Requête SQL : chercher les paires dont les deux DCI sont présentes ─
    # drug_interactions.dci_a/dci_b sont déjà en majuscules (stockées par le loader)
    # On normalise aussi côté SQL avec UPPER() pour être sûr
    interactions = (
        db.query(DrugInteraction)
        .filter(
            func.upper(DrugInteraction.dci_a).in_(all_dcis_ansm),
            func.upper(DrugInteraction.dci_b).in_(all_dcis_ansm),
        )
        .all()
    )

    if not interactions:
        return alerts

    # ── Index inversé : dci_normalisé → ligne(s) ─────────────────────────
    ansm_to_lines: dict[str, List[PrescriptionLine]] = {}
    for line in lines:
        for dci_norm in line_dcis_ansm[line.id]:
            ansm_to_lines.setdefault(dci_norm, []).append(line)

    seen_pairs: set[frozenset] = set()

    for inter in interactions:
        dci_a_norm = _normalize_for_ansm(inter.dci_a)
        dci_b_norm = _normalize_for_ansm(inter.dci_b)

        lines_a = ansm_to_lines.get(dci_a_norm, [])
        lines_b = ansm_to_lines.get(dci_b_norm, [])

        for line_a in lines_a:
            for line_b in lines_b:
                if line_a.id == line_b.id:
                    continue

                # Éviter les alertes dupliquées pour la même paire de lignes
                pair_key = frozenset([line_a.id, line_b.id, inter.dci_a, inter.dci_b])
                if pair_key in seen_pairs:
                    continue
                seen_pairs.add(pair_key)

                drug_a = drugs_by_id.get(line_a.drug_id)
                drug_b = drugs_by_id.get(line_b.drug_id)
                name_a = drug_a.brand_name if drug_a else inter.dci_a
                name_b = drug_b.brand_name if drug_b else inter.dci_b

                # Construire le détail clinique
                detail_parts = [
                    f"{inter.level_fr} : {inter.dci_a} + {inter.dci_b}.",
                ]
                if inter.mechanism:
                    detail_parts.append(f"Risque : {inter.mechanism}")
                if inter.recommendation:
                    detail_parts.append(f"Conduite : {inter.recommendation}")

                # Alerte rattachée à la ligne "partenaire" (line_b)
                alerts.append(
                    CdsAlert(
                        prescription_line_id=line_b.id,
                        alert_type="INTERACTION",
                        severity=inter.severity,
                        title=f"Interaction médicamenteuse — {name_a} / {name_b}",
                        detail=" ".join(detail_parts),
                    )
                )

    return alerts


# ─────────────────────────────────────────────────────────────────────────────
#  Moteur principal
# ─────────────────────────────────────────────────────────────────────────────


def analyse_prescription(
    db: Session,
    patient: Patient,
    lines: List[PrescriptionLine],
) -> List[CdsAlert]:
    # Analyse toutes les lignes et retourne les CdsAlert à persister (sans commit)
    alerts: List[CdsAlert] = []
    patient_age = _age_years(patient.birthdate) if patient.birthdate else None

    # ── Chargement en batch ───────────────────────────────────────────────
    drug_ids = [line.drug_id for line in lines]

    drugs_by_id: dict[int, Drug] = {
        d.id: d for d in db.query(Drug).filter(Drug.id.in_(drug_ids)).all()
    }

    # primary_dcis : TOUTES les DCI (pour ALLERGY — couvre tous les composants)
    primary_dcis: dict[int, List[str]] = {}
    for comp in db.query(DciComponent).filter(DciComponent.drug_id.in_(drug_ids)).all():
        primary_dcis.setdefault(comp.drug_id, []).append(_normalize_dci(comp.dci))

    # main_dci : DCI PRIMAIRE uniquement (position=1) — pour REDUNDANT_DCI
    # Évite de signaler comme "redondance" les excipients ou DCI secondaires
    # Ex: ALGIK contient paracétamol (pos1) + caféine (pos2)
    #     → on ne détecte la redondance que sur paracétamol, pas caféine
    main_dcis: dict[int, str] = {}
    for comp in (
        db.query(DciComponent)
        .filter(
            DciComponent.drug_id.in_(drug_ids),
            DciComponent.position == 1,
        )
        .all()
    ):
        main_dcis[comp.drug_id] = _normalize_dci(comp.dci)

    # ── Table de correspondance allergie → familles/mots-clés associés ──────
    # Quand un patient est allergique à "Pénicilline", tout médicament dont
    # la DCI contient "cilline", "cillin", "pénam", "amoxicilline", etc. doit alerter.
    ALLERGY_FAMILY_MAP: dict[str, List[str]] = {
        # ── Bêta-lactamines / Pénicillines ──────────────────────────────────
        # Inclut les céphalosporines (allergie croisée ~1-10%)
        "pénicilline": [
            "cilline",
            "cillin",
            "amoxicilline",
            "ampicilline",
            "oxacilline",
            "cloxacilline",
            "flucloxacilline",
            "pivmécillinam",
            "pénicilline",
            "bêta-lactamine",
            # Céphalosporines (croisée)
            "céfixime",
            "cefixime",
            "céfazoline",
            "cefazoline",
            "céfalexine",
            "cefalexine",
            "ceftriaxone",
            "cefotaxime",
            "céfuroxime",
            "cefuroxime",
            "ceftazidime",
        ],
        "penicilline": [
            "cilline",
            "cillin",
            "amoxicilline",
            "ampicilline",
            "oxacilline",
            "cloxacilline",
            "pénicilline",
            "céfixime",
            "cefixime",
            "ceftriaxone",
            "céfazoline",
        ],
        # Molécules individuelles → leur famille entière
        "amoxicilline": [
            "cilline",
            "cillin",
            "ampicilline",
            "oxacilline",
            "céfixime",
            "cefixime",
            "ceftriaxone",
        ],
        "ampicilline": [
            "cilline",
            "cillin",
            "amoxicilline",
            "oxacilline",
            "céfixime",
            "cefixime",
        ],
        # ── Sulfamides ───────────────────────────────────────────────────────
        "sulfamide": [
            "sulfaméthoxazole",
            "sulfamethoxazole",
            "sulfamide",
            "cotrimoxazole",
            "triméthoprime",
            "trimethoprime",
            "sulfadiazine",
            "sulfadoxine",
            "sulfasalazine",
        ],
        "sulfamides": [
            "sulfaméthoxazole",
            "sulfamethoxazole",
            "sulfamide",
            "cotrimoxazole",
            "sulfadiazine",
            "sulfasalazine",
        ],
        "sulfaméthoxazole": [
            "sulfaméthoxazole",
            "sulfamethoxazole",
            "sulfamide",
            "cotrimoxazole",
            "sulfadiazine",
        ],
        # ── Céphalosporines ──────────────────────────────────────────────────
        "céphalosporine": [
            "céfazoline",
            "céfalexine",
            "cefazoline",
            "cefalexine",
            "céfixime",
            "cefixime",
            "ceftriaxone",
            "cefotaxime",
            "céfuroxime",
            "cefuroxime",
        ],
        "cephalosporine": [
            "céfazoline",
            "céfalexine",
            "cefazoline",
            "cefalexine",
            "céfixime",
            "cefixime",
            "ceftriaxone",
        ],
        # ── AINS ─────────────────────────────────────────────────────────────
        "aspirine": [
            "acide acétylsalicylique",
            "acetylsalicylique",
            "ibuprofène",
            "ibuprofene",
            "naproxène",
            "naproxene",
            "diclofénac",
            "diclofenac",
            "kétorolac",
            "ketorolac",
            "méloxicam",
            "meloxicam",
        ],
        "ibuprofène": [
            "acide acétylsalicylique",
            "naproxène",
            "diclofénac",
            "kétorolac",
            "méloxicam",
        ],
        "ibuprofene": ["acide acetylsalicylique", "naproxene", "diclofenac"],
        # ── Iode ─────────────────────────────────────────────────────────────
        "iode": [
            "iode",
            "iodé",
            "iodée",
            "povidone",
            "levothyroxine",
            "lévothyroxine",
            "amiodarone",
        ],
        # ── Latex ────────────────────────────────────────────────────────────
        "latex": ["latex"],
        # ── Arachide / soja ──────────────────────────────────────────────────
        "arachide": ["arachide", "huile d'arachide", "soja", "lécithine de soja"],
        "arachides": ["arachide", "huile d'arachide", "soja", "lécithine de soja"],
        # ── Gluten / lactose (excipients) ────────────────────────────────────
        "gluten": ["gluten", "blé", "orge", "seigle"],
        "lactose": ["lactose", "lactulose"],
        # ── Quinolones ───────────────────────────────────────────────────────
        "quinolone": [
            "floxacine",
            "floxacin",
            "ofloxacine",
            "ciprofloxacine",
            "lévofloxacine",
            "moxifloxacine",
            "norfloxacine",
        ],
        "quinolones": [
            "floxacine",
            "floxacin",
            "ofloxacine",
            "ciprofloxacine",
            "lévofloxacine",
            "moxifloxacine",
        ],
        # ── Macrolides ───────────────────────────────────────────────────────
        "macrolide": [
            "azithromycine",
            "clarithromycine",
            "érythromycine",
            "spiramycine",
            "roxithromycine",
        ],
        "macrolides": [
            "azithromycine",
            "clarithromycine",
            "érythromycine",
            "spiramycine",
        ],
    }

    patient_allergies: set[str] = set()
    if patient.known_allergies:
        for a in patient.known_allergies:
            norm = _normalize_dci(a)
            patient_allergies.add(norm)
            if norm.endswith("s"):
                patient_allergies.add(norm[:-1])
            else:
                patient_allergies.add(norm + "s")

    # Index DCI primaire → lignes (pour REDUNDANT_DCI uniquement)
    dci_to_lines: dict[str, List[PrescriptionLine]] = {}
    for line in lines:
        dci_principale = main_dcis.get(line.drug_id) or _normalize_dci(line.dci)
        dci_to_lines.setdefault(dci_principale, []).append(line)

    # ── Règle 1 : ALLERGY ────────────────────────────────────────────────
    # Vérification sur 3 niveaux :
    #   1. DCI exacte           → "allergie à l'amoxicilline" → amoxicilline prescrit
    #   2. Texte libre          → excipients dans contraindications / dci brut
    #   3. Famille pharmacologique → "allergie pénicilline" → amoxicilline = pénicilline
    for line in lines:
        drug = drugs_by_id.get(line.drug_id)
        line_dcis = primary_dcis.get(line.drug_id, [_normalize_dci(line.dci)])
        already_alerted = False

        # Niveau 1 : match DCI exacte
        hit_dci = patient_allergies & set(line_dcis)
        if hit_dci:
            alerts.append(
                CdsAlert(
                    prescription_line_id=line.id,
                    alert_type="ALLERGY",
                    severity="MAJOR",
                    title=f"Allergie connue — {line.dci}",
                    detail=(
                        f"Le patient a une allergie documentée à : "
                        f"{', '.join(hit_dci)}. "
                        f"Médicament prescrit : {drug.brand_name if drug else line.dci}."
                    ),
                )
            )
            already_alerted = True

        # Niveau 2 : chercher l'allergène dans le texte libre
        if not already_alerted and drug:
            searchable_text = " ".join(
                filter(
                    None,
                    [
                        drug.contraindications or "",
                        drug.dci or "",
                        drug.indications or "",
                        drug.brand_name or "",
                    ],
                )
            ).lower()

            for allergen in patient_allergies:
                pattern = r"\b" + re.escape(allergen) + r"\b"
                if re.search(pattern, searchable_text):
                    alerts.append(
                        CdsAlert(
                            prescription_line_id=line.id,
                            alert_type="ALLERGY",
                            severity="MAJOR",
                            title=f"Allergie potentielle — {drug.brand_name}",
                            detail=(
                                f"Le médicament {drug.brand_name} peut contenir ou être associé à "
                                f"'{allergen}' (excipient ou contre-indication). "
                                f"Allergie documentée : {allergen}. "
                                f"Vérifier la composition complète avant de dispenser."
                            ),
                        )
                    )
                    already_alerted = True
                    break

        # Niveau 3 : détection par famille pharmacologique
        # Ex: "Pénicilline" dans les allergies → "amoxicilline" dans la DCI → ALERTE
        if not already_alerted and drug:
            drug_dci_full = " ".join(line_dcis).lower()
            for allergen in patient_allergies:
                related_keywords = ALLERGY_FAMILY_MAP.get(allergen, [])
                for keyword in related_keywords:
                    if keyword in drug_dci_full:
                        allergen_display = allergen.capitalize()
                        # Récupérer l'allergie originale (avant singulier/pluriel)
                        allergen_original = next(
                            (
                                a
                                for a in (patient.known_allergies or [])
                                if _normalize_dci(a) == allergen
                                or _normalize_dci(a).rstrip("s") == allergen
                                or _normalize_dci(a) + "s" == allergen
                            ),
                            allergen_display,
                        )
                        # DCI affichée = celle qui a matché le keyword (plus précis)
                        matched_dci = next(
                            (d for d in line_dcis if keyword in d.lower()), line.dci
                        )
                        alerts.append(
                            CdsAlert(
                                prescription_line_id=line.id,
                                alert_type="ALLERGY",
                                severity="MAJOR",
                                title=f"Allergie croisée — {drug.brand_name if drug else line.dci}",
                                detail=(
                                    f"Le patient est allergique aux {allergen_original}. "
                                    f"Le médicament prescrit ({drug.brand_name if drug else line.dci}) "
                                    f"appartient à cette famille ou présente un risque de réaction croisée "
                                    f"(DCI : {matched_dci.capitalize()}). Vérifier avant administration."
                                ),
                            )
                        )
                        already_alerted = True
                        break
                if already_alerted:
                    break

    # ── Règle 2 : REDUNDANT_DCI ──────────────────────────────────────────
    seen_redondances: set[str] = set()
    for dci_norm, dup_lines in dci_to_lines.items():
        if len(dup_lines) > 1 and dci_norm not in seen_redondances:
            seen_redondances.add(dci_norm)

            # Construire la liste des médicaments avec dose pour les différencier
            # Si même brand_name (même drug_id × 2), afficher avec la dose prescrite
            def _line_label(l):
                drug = drugs_by_id.get(l.drug_id)
                name = drug.brand_name if drug else l.dci
                if l.dose_mg:
                    return f"{name} ({l.dose_mg} {l.dose_unit_raw or 'mg'})"
                return name

            drug_labels = list(dict.fromkeys(_line_label(l) for l in dup_lines))
            # Si toujours un seul label (même drug, même dose) → indiquer ×N
            if len(drug_labels) == 1:
                drug_labels = [f"{drug_labels[0]} × {len(dup_lines)}"]

            dci_display = dci_norm.capitalize()
            for line in dup_lines[1:]:
                alerts.append(
                    CdsAlert(
                        prescription_line_id=line.id,
                        alert_type="REDUNDANT_DCI",
                        severity="MODERATE",
                        title=f"Redondance de DCI — {dci_display}",
                        detail=(
                            f"La molécule '{dci_display}' est présente dans plusieurs "
                            f"lignes de la prescription : {', '.join(drug_labels)}. "
                            f"Risque de surdosage cumulatif."
                        ),
                    )
                )

    # ── Règle 3 : POSOLOGY (âge minimal) ────────────────────────────────
    if patient_age is not None:
        for line in lines:
            drug = drugs_by_id.get(line.drug_id)
            if not drug or not drug.min_age:
                continue
            min_years = _parse_min_age_years(drug.min_age)
            if min_years is not None and patient_age < min_years:
                alerts.append(
                    CdsAlert(
                        prescription_line_id=line.id,
                        alert_type="POSOLOGY",
                        severity="MAJOR",
                        title=f"Âge insuffisant — {drug.brand_name}",
                        detail=(
                            f"Ce médicament est autorisé à partir de {drug.min_age}. "
                            f"Âge du patient : {patient_age} an(s)."
                        ),
                    )
                )

    # ── Règle 4 : CONTRA_INDICATION (grossesse / allaitement) ────────────
    for line in lines:
        drug = drugs_by_id.get(line.drug_id)
        if not drug:
            continue
        if patient.is_pregnant and _mentions_pregnancy(drug.contraindications):
            alerts.append(
                CdsAlert(
                    prescription_line_id=line.id,
                    alert_type="CONTRA_INDICATION",
                    severity="MAJOR",
                    title=f"Contre-indication grossesse — {drug.brand_name}",
                    detail=(
                        "La fiche du médicament mentionne une contre-indication "
                        "liée à la grossesse."
                        + (
                            f" Semaine gestationelle : {patient.gestational_weeks}."
                            if patient.gestational_weeks
                            else ""
                        )
                    ),
                )
            )
        if patient.is_breastfeeding and _mentions_breastfeeding(drug.contraindications):
            alerts.append(
                CdsAlert(
                    prescription_line_id=line.id,
                    alert_type="CONTRA_INDICATION",
                    severity="MODERATE",
                    title=f"Contre-indication allaitement — {drug.brand_name}",
                    detail=(
                        "La fiche du médicament mentionne une contre-indication "
                        "liée à l'allaitement."
                    ),
                )
            )

    # ── Règle 5 : PSYCHOACTIVE (informatif) ─────────────────────────────
    for line in lines:
        drug = drugs_by_id.get(line.drug_id)
        if drug and drug.is_psychoactive:
            alerts.append(
                CdsAlert(
                    prescription_line_id=line.id,
                    alert_type="POSOLOGY",
                    severity="MINOR",
                    title=f"Substance psychoactive — {drug.brand_name}",
                    detail=(
                        "Ce médicament contient une ou plusieurs substances "
                        "psychoactives. Vérifier l'absence de co-prescription "
                        "sédative et informer le patient."
                    ),
                )
            )

    # ── Règle 6 : INTERACTION (Thésaurus ANSM) ───────────────────────────
    alerts.extend(_check_interactions(db, lines, primary_dcis, drugs_by_id))

    # ── Règle 7 : RENAL — médicaments CI ou à ajuster en IRC ─────────────
    # Détecte les médicaments néphrotoxiques ou contre-indiqués selon la
    # clairance rénale du patient (creatinine_clearance en mL/min)
    if patient.creatinine_clearance is not None:
        crcl = float(patient.creatinine_clearance)

        # Table des médicaments à risque rénal avec seuils de clairance
        # Format: {keyword_dci: (seuil_mL/min, sévérité, message_risque)}
        RENAL_RISK_DRUGS: dict[str, tuple] = {
            # Metformine : CI si CrCl < 30, précaution si < 45
            "metformine": (
                45,
                "MAJOR",
                "contre-indication (risque d'acidose lactique)",
            ),
            "metformin": (45, "MAJOR", "contre-indication (risque d'acidose lactique)"),
            # AINS : néphrotoxiques, CI si IRC sévère
            "ibuprofène": (30, "MAJOR", "néphrotoxicité aggravée en IRC"),
            "ibuprofene": (30, "MAJOR", "néphrotoxicité aggravée en IRC"),
            "naproxène": (30, "MAJOR", "néphrotoxicité aggravée en IRC"),
            "diclofénac": (30, "MAJOR", "néphrotoxicité aggravée en IRC"),
            "kétorolac": (30, "MAJOR", "néphrotoxicité aggravée en IRC"),
            # Antibiotiques néphrotoxiques
            "gentamicine": (60, "MAJOR", "accumulation et néphrotoxicité"),
            "vancomycine": (50, "MAJOR", "accumulation et néphrotoxicité"),
            "amikacine": (60, "MAJOR", "accumulation et néphrotoxicité"),
            # Anticoagulants à élimination rénale
            "dabigatran": (30, "MAJOR", "accumulation — risque hémorragique"),
            "rivaroxaban": (15, "MAJOR", "accumulation — risque hémorragique"),
            "apixaban": (25, "MODERATE", "précaution, adapter la dose"),
            # Hypoglycémiants
            "glyburide": (60, "MAJOR", "risque d'hypoglycémie prolongée"),
            "glibenclamide": (60, "MAJOR", "risque d'hypoglycémie prolongée"),
            "sitagliptine": (
                45,
                "MODERATE",
                "adapter la posologie à la fonction rénale",
            ),
            # Diurétiques
            "spironolactone": (30, "MAJOR", "risque d'hyperkaliémie en IRC"),
            "triamtérène": (30, "MAJOR", "risque d'hyperkaliémie en IRC"),
            # Lithium
            "lithium": (50, "MAJOR", "accumulation — fenêtre thérapeutique étroite"),
            # Colchicine
            "colchicine": (
                30,
                "MAJOR",
                "accumulation — risque de myopathie/neuropathie",
            ),
            # Aciclovir
            "aciclovir": (25, "MODERATE", "adapter la posologie"),
            "valaciclovir": (30, "MODERATE", "adapter la posologie"),
        }

        for line in lines:
            drug = drugs_by_id.get(line.drug_id)
            line_dcis_list = primary_dcis.get(line.drug_id, [_normalize_dci(line.dci)])
            renal_alerted = False  # ← une seule alerte RENAL par ligne de prescription

            for dci in line_dcis_list:
                if renal_alerted:
                    break
                for keyword, (
                    threshold,
                    severity,
                    risk_msg,
                ) in RENAL_RISK_DRUGS.items():
                    if keyword in dci and crcl < threshold:
                        irc_label = (
                            "sévère (stade 4-5)"
                            if crcl < 30
                            else (
                                "modérée (stade 3)"
                                if crcl < 45
                                else "légère (stade 2)" if crcl < 60 else "débutante"
                            )
                        )
                        alerts.append(
                            CdsAlert(
                                prescription_line_id=line.id,
                                alert_type="RENAL",
                                severity=severity,
                                title=f"Insuffisance rénale — {drug.brand_name if drug else line.dci}",
                                detail=(
                                    f"Ce médicament est {risk_msg} "
                                    f"lorsque la clairance rénale est < {threshold} mL/min. "
                                    f"Clairance du patient : {crcl:.1f} mL/min "
                                    f"(IRC {irc_label}). "
                                    f"Adapter la posologie ou substituer."
                                ),
                            )
                        )
                        renal_alerted = True
                        break

    return alerts
