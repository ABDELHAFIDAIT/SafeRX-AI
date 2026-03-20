import unittest
from unittest.mock import MagicMock
from datetime import date

from backend.tests.tests_conftest import make_patient, make_drug, make_line
from backend.app.services.cds_engine import analyse_prescription

# ─────────────────────────────────────────────────────────────────────────────
#  Fonction utilitaire : créer une fausse base de données
# ─────────────────────────────────────────────────────────────────────────────


def fausse_db(drug, dcis):
    """
    Crée une fausse DB qui retourne le médicament et ses DCI.
    Paramètres :
      drug  → le médicament (créé avec make_drug)
      dcis  → liste des molécules du médicament, ex: ["amoxicilline"]
    """
    db = MagicMock()

    comps = []
    for dci in dcis:
        c = MagicMock()
        c.drug_id = drug.id
        c.dci = dci
        c.position = 1
        comps.append(c)

    def simuler_query(model):
        from backend.app.models.drug import Drug, DciComponent

        q = MagicMock()
        if model is Drug:
            q.filter.return_value.all.return_value = [drug]
        elif model is DciComponent:
            q.filter.return_value.all.return_value = comps
        else:
            q.filter.return_value.all.return_value = []
        return q

    db.query.side_effect = simuler_query
    return db


# ─────────────────────────────────────────────────────────────────────────────
#  Règle 1 — ALLERGY : allergie connue du patient
# ─────────────────────────────────────────────────────────────────────────────


class TestAllergie(unittest.TestCase):
    def test_allergie_directe_genere_une_alerte(self):
        """
        Scénario : le patient est allergique à l'amoxicilline.
        On lui prescrit de l'amoxicilline.
        → Le moteur doit générer une alerte ALLERGY de sévérité MAJOR.
        """
        patient = make_patient(known_allergies=["amoxicilline"])
        drug = make_drug(id=1, dci="amoxicilline", brand_name="AMOXIL 500MG")
        line = make_line(drug_id=1, dci="amoxicilline")
        db = fausse_db(drug, ["amoxicilline"])

        alertes = analyse_prescription(db=db, patient=patient, lines=[line])
        allergies = [a for a in alertes if a.alert_type == "ALLERGY"]

        self.assertGreater(len(allergies), 0)
        self.assertEqual(allergies[0].severity, "MAJOR")

    def test_allergie_famille_penicilline(self):
        """
        Scénario : patient allergique aux "Pénicillines" (famille).
        L'amoxicilline appartient à cette famille.
        → Alerte d'allergie CROISÉE attendue.
        """
        patient = make_patient(known_allergies=["Pénicilline"])
        drug = make_drug(id=1, dci="amoxicilline")
        line = make_line(drug_id=1, dci="amoxicilline")
        db = fausse_db(drug, ["amoxicilline"])

        alertes = analyse_prescription(db=db, patient=patient, lines=[line])
        allergies = [a for a in alertes if a.alert_type == "ALLERGY"]

        self.assertGreater(
            len(allergies), 0, "Allergie croisée Pénicilline→Amoxicilline attendue"
        )

    def test_pas_dalerte_sans_allergie(self):
        """
        Scénario : patient sans allergie connue.
        → Aucune alerte ALLERGY.
        """
        patient = make_patient(known_allergies=[])
        drug = make_drug(id=1, dci="amoxicilline")
        line = make_line(drug_id=1, dci="amoxicilline")
        db = fausse_db(drug, ["amoxicilline"])

        alertes = analyse_prescription(db=db, patient=patient, lines=[line])
        allergies = [a for a in alertes if a.alert_type == "ALLERGY"]

        self.assertEqual(len(allergies), 0)


# ─────────────────────────────────────────────────────────────────────────────
#  Règle 2 — REDUNDANT_DCI : même molécule prescrite deux fois
# ─────────────────────────────────────────────────────────────────────────────


class TestRedondance(unittest.TestCase):
    def test_deux_fois_paracetamol(self):
        """
        Scénario : Doliprane + Dafalgan = même DCI (paracétamol) prescrite deux fois.
        → Alerte REDUNDANT_DCI MODERATE.
        """
        patient = make_patient()
        drug1 = make_drug(id=1, brand_name="DOLIPRANE", dci="paracétamol")
        drug2 = make_drug(id=2, brand_name="DAFALGAN", dci="paracétamol")
        line1 = make_line(id=1, drug_id=1, dci="paracétamol")
        line2 = make_line(id=2, drug_id=2, dci="paracétamol")

        db = MagicMock()
        c1 = MagicMock()
        c1.drug_id = 1
        c1.dci = "paracétamol"
        c1.position = 1
        c2 = MagicMock()
        c2.drug_id = 2
        c2.dci = "paracétamol"
        c2.position = 1

        def simuler_query(model):
            from backend.app.models.drug import Drug, DciComponent

            q = MagicMock()
            if model is Drug:
                q.filter.return_value.all.return_value = [drug1, drug2]
            elif model is DciComponent:
                q.filter.return_value.all.return_value = [c1, c2]
            else:
                q.filter.return_value.all.return_value = []
            return q

        db.query.side_effect = simuler_query

        alertes = analyse_prescription(db=db, patient=patient, lines=[line1, line2])
        redondant = [a for a in alertes if a.alert_type == "REDUNDANT_DCI"]

        self.assertGreater(len(redondant), 0)
        self.assertEqual(redondant[0].severity, "MODERATE")


# ─────────────────────────────────────────────────────────────────────────────
#  Règle 3 — POSOLOGY : patient trop jeune pour le médicament
# ─────────────────────────────────────────────────────────────────────────────


class TestAge(unittest.TestCase):
    def test_enfant_trop_jeune(self):
        """
        Scénario : Doxycycline autorisée à partir de 8 ans. Patient = 5 ans.
        → Alerte POSOLOGY MAJOR.
        """
        patient = make_patient(birthdate=date(date.today().year - 5, 1, 1))
        drug = make_drug(id=1, dci="doxycycline", min_age="8 ans")
        line = make_line(drug_id=1, dci="doxycycline")
        db = fausse_db(drug, ["doxycycline"])

        alertes = analyse_prescription(db=db, patient=patient, lines=[line])
        posologie = [
            a for a in alertes if a.alert_type == "POSOLOGY" and "Âge" in a.title
        ]

        self.assertGreater(len(posologie), 0)
        self.assertEqual(posologie[0].severity, "MAJOR")

    def test_adulte_pas_dalerte(self):
        """
        Scénario : même médicament, patient de 30 ans.
        → Aucune alerte d'âge.
        """
        patient = make_patient(birthdate=date(date.today().year - 30, 1, 1))
        drug = make_drug(id=1, dci="doxycycline", min_age="8 ans")
        line = make_line(drug_id=1, dci="doxycycline")
        db = fausse_db(drug, ["doxycycline"])

        alertes = analyse_prescription(db=db, patient=patient, lines=[line])
        posologie = [
            a for a in alertes if a.alert_type == "POSOLOGY" and "Âge" in a.title
        ]

        self.assertEqual(len(posologie), 0)


# ─────────────────────────────────────────────────────────────────────────────
#  Règle 4 — CONTRA_INDICATION : grossesse / allaitement
# ─────────────────────────────────────────────────────────────────────────────


class TestContraIndication(unittest.TestCase):
    def test_roaccutane_interdit_pendant_grossesse(self):
        """
        Scénario : patiente enceinte + Roaccutane (CI grossesse).
        → Alerte CONTRA_INDICATION MAJOR.
        """
        patient = make_patient(is_pregnant=True, gender="F")
        drug = make_drug(
            id=1,
            dci="isotrétinoïne",
            contraindications="Contre-indiqué pendant la grossesse.",
        )
        line = make_line(drug_id=1, dci="isotrétinoïne")
        db = fausse_db(drug, ["isotrétinoïne"])

        alertes = analyse_prescription(db=db, patient=patient, lines=[line])
        ci = [a for a in alertes if a.alert_type == "CONTRA_INDICATION"]

        self.assertGreater(len(ci), 0)
        self.assertEqual(ci[0].severity, "MAJOR")

    def test_lithium_interdit_pendant_allaitement(self):
        """
        Scénario : patiente allaitante + Lithium (CI allaitement).
        → Alerte CONTRA_INDICATION MODERATE.
        """
        patient = make_patient(is_breastfeeding=True, gender="F")
        drug = make_drug(
            id=1, dci="lithium", contraindications="Éviter pendant l'allaitement."
        )
        line = make_line(drug_id=1, dci="lithium")
        db = fausse_db(drug, ["lithium"])

        alertes = analyse_prescription(db=db, patient=patient, lines=[line])
        ci = [a for a in alertes if a.alert_type == "CONTRA_INDICATION"]

        self.assertGreater(len(ci), 0)
        self.assertEqual(ci[0].severity, "MODERATE")


# ─────────────────────────────────────────────────────────────────────────────
#  Règle 7 — RENAL : insuffisance rénale
# ─────────────────────────────────────────────────────────────────────────────


class TestRenal(unittest.TestCase):
    def test_metformine_ci_si_irc(self):
        """
        Scénario : Metformine interdite si clairance < 45 mL/min.
        Patient avec clairance = 42.5 mL/min.
        → Alerte RENAL MAJOR (risque d'acidose lactique).
        """
        patient = make_patient(creatinine_clearance=42.5)
        drug = make_drug(id=1, dci="metformine", brand_name="GLUCOPHAGE 1000MG")
        line = make_line(drug_id=1, dci="metformine")
        db = fausse_db(drug, ["metformine"])

        alertes = analyse_prescription(db=db, patient=patient, lines=[line])
        renal = [a for a in alertes if a.alert_type == "RENAL"]

        self.assertGreater(len(renal), 0)
        self.assertEqual(renal[0].severity, "MAJOR")
        self.assertIn("acidose lactique", renal[0].detail.lower())

    def test_metformine_ok_si_rein_normal(self):
        """
        Scénario : même médicament, clairance normale (90 mL/min).
        → Aucune alerte RENAL.
        """
        patient = make_patient(creatinine_clearance=90.0)
        drug = make_drug(id=1, dci="metformine")
        line = make_line(drug_id=1, dci="metformine")
        db = fausse_db(drug, ["metformine"])

        alertes = analyse_prescription(db=db, patient=patient, lines=[line])
        renal = [a for a in alertes if a.alert_type == "RENAL"]

        self.assertEqual(len(renal), 0)

    def test_pas_de_crash_si_crcl_absent(self):
        """
        Scénario : clairance non renseignée dans le dossier patient (None).
        → Aucune erreur, aucune alerte RENAL.
        """
        patient = make_patient(creatinine_clearance=None)
        drug = make_drug(id=1, dci="metformine")
        line = make_line(drug_id=1, dci="metformine")
        db = fausse_db(drug, ["metformine"])

        alertes = analyse_prescription(db=db, patient=patient, lines=[line])
        renal = [a for a in alertes if a.alert_type == "RENAL"]

        self.assertEqual(len(renal), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
