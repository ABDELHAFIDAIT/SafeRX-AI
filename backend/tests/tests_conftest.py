import sys
import os
from datetime import date
from unittest.mock import MagicMock
from typing import Optional

_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _root not in sys.path:
    sys.path.insert(0, _root)


def _ensure_model_mock(module_path: str):
    if module_path not in sys.modules:
        sys.modules[module_path] = MagicMock()


for _mod in [
    "backend.app.models.audit_cds_hook",
    "backend.app.models.cds_alert",
    "backend.app.models.drug",
    "backend.app.models.drug_interaction",
    "backend.app.models.patient",
    "backend.app.models.prescription",
    "backend.app.models.user",
]:
    _ensure_model_mock(_mod)

import enum as _enum


class _Role(str, _enum.Enum):
    DOCTOR = "doctor"
    PHARMACIST = "pharmacist"
    ADMIN = "admin"


sys.modules["backend.app.models.user"].Role = _Role
sys.modules["backend.app.models.user"].User = MagicMock()


class _AuditCdsHook:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


sys.modules["backend.app.models.audit_cds_hook"].AuditCdsHook = _AuditCdsHook


class _CdsAlert:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

        if not hasattr(self, "rag_explanation"):
            self.rag_explanation = None
        if not hasattr(self, "ai_ignore_proba"):
            self.ai_ignore_proba = None


sys.modules["backend.app.models.cds_alert"].CdsAlert = _CdsAlert


def make_patient(
    id: int = 1,
    birthdate: date = date(1980, 6, 15),
    gender: str = "M",
    weight_kg: float = 75.0,
    creatinine_clearance: Optional[float] = 90.0,
    is_pregnant: bool = False,
    is_breastfeeding: bool = False,
    known_allergies: list = None,
    pathologies_cim10: list = None,
) -> MagicMock:
    p = MagicMock()
    p.id = id
    p.birthdate = birthdate
    p.gender = gender
    p.weight_kg = weight_kg
    p.creatinine_clearance = creatinine_clearance
    p.is_pregnant = is_pregnant
    p.is_breastfeeding = is_breastfeeding
    p.known_allergies = known_allergies or []
    p.pathologies_cim10 = pathologies_cim10 or []
    return p


def make_drug(
    id: int = 1,
    brand_name: str = "AMOXICILLINE 500MG",
    dci: str = "amoxicilline",
    min_age: Optional[str] = None,
    is_psychoactive: bool = False,
    contraindications: Optional[str] = None,
    indications: Optional[str] = None,
) -> MagicMock:
    d = MagicMock()
    d.id = id
    d.brand_name = brand_name
    d.dci = dci
    d.min_age = min_age
    d.is_psychoactive = is_psychoactive
    d.contraindications = contraindications or ""
    d.indications = indications or ""
    return d


def make_line(
    id: int = 1,
    drug_id: int = 1,
    dci: str = "amoxicilline",
    dose_mg: float = 500.0,
    dose_unit_raw: str = "mg",
    frequency: str = "3x/jour",
    route: str = "orale",
    duration_days: int = 7,
) -> MagicMock:
    line = MagicMock()
    line.id = id
    line.drug_id = drug_id
    line.dci = dci
    line.dose_mg = dose_mg
    line.dose_unit_raw = dose_unit_raw
    line.frequency = frequency
    line.route = route
    line.duration_days = duration_days
    return line


def make_cds_alert(
    id: int = 1,
    alert_type: str = "INTERACTION",
    severity: str = "MAJOR",
    title: str = "Test alerte",
    detail: str = "Détail de test",
    rag_explanation: Optional[str] = None,
    ai_ignore_proba: Optional[float] = None,
) -> _CdsAlert:
    return _CdsAlert(
        id=id,
        alert_type=alert_type,
        severity=severity,
        title=title,
        detail=detail,
        rag_explanation=rag_explanation,
        ai_ignore_proba=ai_ignore_proba,
    )


def make_user(
    id: int = 1,
    email: str = "doctor@saferx.ma",
    role: str = "doctor",
    is_active: bool = True,
    first_name: str = "Ahmed",
    last_name: str = "Benali",
) -> MagicMock:
    from backend.app.models.user import Role

    u = MagicMock()
    u.id = id
    u.email = email
    u.role = Role(role)
    u.is_active = is_active
    u.first_name = first_name
    u.last_name = last_name
    return u


def make_db_session() -> MagicMock:
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    db.query.return_value.all.return_value = []
    db.query.return_value.get.return_value = None
    db.add = MagicMock()
    db.flush = MagicMock()
    db.commit = MagicMock()
    db.refresh = MagicMock()
    return db


class _ColDescriptor:
    def __init__(self, name):
        self.name = name

    def __eq__(self, other):
        return MagicMock()

    def __ne__(self, other):
        return MagicMock()

    def __lt__(self, other):
        return MagicMock()

    def __le__(self, other):
        return MagicMock()

    def __gt__(self, other):
        return MagicMock()

    def __ge__(self, other):
        return MagicMock()

    def in_(self, other):
        return MagicMock()

    def isnot(self, other):
        return MagicMock()

    def desc(self):
        return MagicMock()

    def asc(self):
        return MagicMock()

    def __hash__(self):
        return hash(self.name)

    def __repr__(self):
        return f"<Col:{self.name}>"


_CdsAlert.id = _ColDescriptor("id")
_CdsAlert.alert_type = _ColDescriptor("alert_type")
_CdsAlert.severity = _ColDescriptor("severity")
_CdsAlert.prescription_line_id = _ColDescriptor("prescription_line_id")

_AuditCdsHook.id = _ColDescriptor("id")
_AuditCdsHook.prescription_id = _ColDescriptor("prescription_id")
_AuditCdsHook.doctor_id = _ColDescriptor("doctor_id")
_AuditCdsHook.decision = _ColDescriptor("decision")
_AuditCdsHook.alert_type = _ColDescriptor("alert_type")
_AuditCdsHook.created_at = _ColDescriptor("created_at")

sys.modules["backend.app.models.cds_alert"].CdsAlert = _CdsAlert
sys.modules["backend.app.models.audit_cds_hook"].AuditCdsHook = _AuditCdsHook
