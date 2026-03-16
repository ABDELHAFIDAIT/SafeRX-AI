import { useState, useEffect, useRef, useCallback } from "react";
import {
    Stethoscope, Search, Plus, Trash2, LogOut,
    ShieldAlert, ShieldCheck, AlertTriangle, Info,
    Pill, User, Activity, Clock, FileText,
    AlertCircle, Zap, FlaskConical, Heart, Baby,
    Brain, Siren, LayoutDashboard, ClipboardList,
    CheckCircle2, TriangleAlert, RefreshCw, Edit2,
    UserPlus, ChevronRight, X, Save, Calendar
} from "lucide-react";
import authService from "../services/AuthService";
import api from "../api/api";
import CdsResultPanel from "../components/CdsResultPanel";

/* ─────────────────────────────────────────────
   CONSTANTES
───────────────────────────────────────────── */
const ROUTES = ["orale", "intraveineuse", "intramusculaire", "sous-cutanée",
    "cutanée", "inhalée", "sublinguale", "rectale", "ophtalmique", "nasale"];

const FREQ_OPTIONS = ["1x/jour", "2x/jour", "3x/jour", "4x/jour",
    "toutes les 8h", "toutes les 12h", "toutes les 6h", "si besoin"];

/* ─────────────────────────────────────────────
   HELPERS
───────────────────────────────────────────── */
const Spinner = ({ size = 16 }) => (
    <svg style={{ width: size, height: size }} className="animate-spin" fill="none" viewBox="0 0 24 24">
        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
    </svg>
);

const Tag = ({ children, color = "slate" }) => {
    const colors = {
        blue:    "bg-blue-50 text-blue-700 border border-blue-200",
        emerald: "bg-emerald-50 text-emerald-700 border border-emerald-200",
        red:     "bg-red-50 text-red-600 border border-red-200",
        amber:   "bg-amber-50 text-amber-700 border border-amber-200",
        slate:   "bg-slate-100 text-slate-600 border border-slate-200",
    };
    return (
        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium ${colors[color] || colors.slate}`}>
            {children}
        </span>
    );
};

const NAV = [
    { id: "prescription", icon: LayoutDashboard, label: "Nouvelle prescription" },
    { id: "history",      icon: ClipboardList,   label: "Mes prescriptions"    },
    { id: "patients",     icon: User,            label: "Patients"             },
];

/* ─────────────────────────────────────────────
   COMPOSANT : Recherche de médicament
───────────────────────────────────────────── */
function DrugSearchInput({ onSelect }) {
    const [query,   setQuery]   = useState("");
    const [results, setResults] = useState([]);
    const [loading, setLoading] = useState(false);
    const [open,    setOpen]    = useState(false);
    const ref = useRef(null);

    useEffect(() => {
        const handleClick = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
        document.addEventListener("mousedown", handleClick);
        return () => document.removeEventListener("mousedown", handleClick);
    }, []);

    useEffect(() => {
        if (query.length < 2) { setResults([]); return; }
        const timer = setTimeout(async () => {
            setLoading(true);
            try {
                const res = await api.get(`/drugs/search?q=${encodeURIComponent(query)}&limit=8`);
                setResults(res.data || []);
                setOpen(true);
            } catch { setResults([]); }
            finally { setLoading(false); }
        }, 300);
        return () => clearTimeout(timer);
    }, [query]);

    const handleSelect = (drug) => {
        onSelect(drug);
        setQuery(""); setResults([]); setOpen(false);
    };

    return (
        <div ref={ref} className="relative">
            <div className="flex items-center gap-2 bg-white border border-slate-200 rounded-xl px-3 py-2.5 focus-within:ring-2 focus-within:ring-blue-500 focus-within:border-transparent transition-all shadow-sm">
                {loading ? <Spinner size={14} /> : <Search size={14} className="text-slate-400" />}
                <input
                    type="text"
                    value={query}
                    onChange={e => setQuery(e.target.value)}
                    onFocus={() => results.length > 0 && setOpen(true)}
                    placeholder="Rechercher un médicament (nom ou DCI)…"
                    className="flex-1 bg-transparent text-sm text-slate-800 placeholder-slate-400 outline-none"
                />
            </div>
            {open && results.length > 0 && (
                <div className="absolute top-full left-0 right-0 mt-1.5 rounded-xl border border-slate-200 overflow-hidden shadow-xl z-30 bg-white">
                    {results.map((drug) => (
                        <button key={drug.id} onClick={() => handleSelect(drug)}
                            className="w-full px-4 py-3 text-left hover:bg-slate-50 transition-colors border-b border-slate-100 last:border-0">
                            <div className="flex items-center justify-between gap-2">
                                <div>
                                    <p className="text-sm font-semibold text-slate-800">{drug.brand_name}</p>
                                    <p className="text-xs text-slate-500 mt-0.5">{drug.dci} · {drug.presentation}</p>
                                </div>
                                {drug.is_psychoactive && (
                                    <Tag color="amber"><Brain size={10} /> Psychoactif</Tag>
                                )}
                            </div>
                        </button>
                    ))}
                </div>
            )}
        </div>
    );
}

/* ─────────────────────────────────────────────
   COMPOSANT PRINCIPAL : Dashboard Médecin
───────────────────────────────────────────── */
export default function DoctorDashboard() {
    const user = authService.getUser();

    // ── Prescription ─────────────────────────────────────────────────────
    const [patientId,   setPatientId]   = useState("");
    const [patientData, setPatientData] = useState(null);
    const [patientLoad, setPatientLoad] = useState(false);
    const [patientErr,  setPatientErr]  = useState("");
    const [lines,       setLines]       = useState([]);
    const [submitting,  setSubmitting]  = useState(false);
    const [cdsResult,   setCdsResult]   = useState(null);
    const [submitErr,   setSubmitErr]   = useState("");
    const [activeTab,   setActiveTab]   = useState("new");

    // ── Navigation ────────────────────────────────────────────────────────
    const [activeNav,   setActiveNav]   = useState("prescription");

    // ── Mes prescriptions (vue "history") ────────────────────────────────
    const [myPrescriptions,     setMyPrescriptions]     = useState([]);
    const [myPrescLoad,         setMyPrescLoad]         = useState(false);
    const [selectedPrescDetail, setSelectedPrescDetail] = useState(null); // prescription cliquée

    // ── Patients (vue "patients") ─────────────────────────────────────────
    const [patientSearch,  setPatientSearch]  = useState("");
    const [searchResults,  setSearchResults]  = useState([]);
    const [searchLoading,  setSearchLoading]  = useState(false);
    const [showPatientForm,setShowPatientForm] = useState(false); // créer/modifier
    const [editPatient,    setEditPatient]    = useState(null);   // null = création
    const [patientForm,    setPatientForm]    = useState({
        birthdate: "", gender: "M", weight_kg: "", height_cm: "",
        creatinine_clearance: "", is_pregnant: false, gestational_weeks: "",
        is_breastfeeding: false, known_allergies: "", pathologies_cim10: "",
        fhir_patient_id: "",
    });
    const [patientFormErr,  setPatientFormErr]  = useState("");
    const [patientFormLoad, setPatientFormLoad] = useState(false);

    // ── Historique patient (tab dans vue prescription) ────────────────────
    const [patientHistory, setPatientHistory] = useState([]);
    const [historyLoad,    setHistoryLoad]    = useState(false);

    /* ── Chargement prescriptions médecin ────────────────────────────── */
    const loadMyPrescriptions = useCallback(async () => {
        setMyPrescLoad(true);
        try {
            const res = await api.get("/prescriptions/doctor/mine?limit=30");
            setMyPrescriptions(res.data || []);
        } catch { setMyPrescriptions([]); }
        finally { setMyPrescLoad(false); }
    }, []);

    useEffect(() => {
        if (activeNav === "history") loadMyPrescriptions();
    }, [activeNav, loadMyPrescriptions]);

    /* ── Recherche patient ───────────────────────────────────────────── */
    useEffect(() => {
        if (patientSearch.trim().length < 1) { setSearchResults([]); return; }
        const timer = setTimeout(async () => {
            setSearchLoading(true);
            try {
                const res = await api.get(`/patients/search?q=${encodeURIComponent(patientSearch.trim())}`);
                setSearchResults(res.data || []);
            } catch { setSearchResults([]); }
            finally { setSearchLoading(false); }
        }, 400);
        return () => clearTimeout(timer);
    }, [patientSearch]);

    /* ── Charger patient par ID ──────────────────────────────────────── */
    const loadPatient = async () => {
        if (!patientId.trim()) return;
        setPatientLoad(true); setPatientErr(""); setPatientData(null);
        try {
            const res = await api.get(`/patients/search?q=${encodeURIComponent(patientId.trim())}`);
            if (res.data?.length > 0) setPatientData(res.data[0]);
            else setPatientErr("Patient introuvable (ID numérique ou FHIR UUID).");
        } catch { setPatientErr("Erreur lors du chargement."); }
        finally { setPatientLoad(false); }
    };

    /* ── Historique du patient sélectionné ──────────────────────────── */
    const loadPatientHistory = async () => {
        if (!patientData) return;
        setHistoryLoad(true);
        try {
            const res = await api.get(`/prescriptions/patient/${patientData.id}`);
            setPatientHistory(res.data || []);
        } catch { setPatientHistory([]); }
        finally { setHistoryLoad(false); }
    };
    useEffect(() => {
        if (activeTab === "history" && patientData) loadPatientHistory();
    }, [activeTab, patientData]);

    /* ── Formulaire patient (créer / modifier) ───────────────────────── */
    const openCreatePatient = () => {
        setEditPatient(null);
        setPatientForm({ birthdate: "", gender: "M", weight_kg: "", height_cm: "",
            creatinine_clearance: "", is_pregnant: false, gestational_weeks: "",
            is_breastfeeding: false, known_allergies: "", pathologies_cim10: "", fhir_patient_id: "" });
        setPatientFormErr("");
        setShowPatientForm(true);
    };

    const openEditPatient = (p) => {
        setEditPatient(p);
        setPatientForm({
            birthdate:            p.birthdate || "",
            gender:               p.gender || "M",
            weight_kg:            p.weight_kg || "",
            height_cm:            p.height_cm || "",
            creatinine_clearance: p.creatinine_clearance || "",
            is_pregnant:          p.is_pregnant || false,
            gestational_weeks:    p.gestational_weeks || "",
            is_breastfeeding:     p.is_breastfeeding || false,
            known_allergies:      (p.known_allergies || []).join(", "),
            pathologies_cim10:    (p.pathologies_cim10 || []).join(", "),
            fhir_patient_id:      p.fhir_patient_id || "",
        });
        setPatientFormErr("");
        setShowPatientForm(true);
    };

    const submitPatientForm = async (e) => {
        e.preventDefault();
        setPatientFormErr(""); setPatientFormLoad(true);
        try {
            const payload = {
                birthdate:            patientForm.birthdate,
                gender:               patientForm.gender,
                weight_kg:            patientForm.weight_kg     ? parseFloat(patientForm.weight_kg)     : null,
                height_cm:            patientForm.height_cm     ? parseFloat(patientForm.height_cm)     : null,
                creatinine_clearance: patientForm.creatinine_clearance ? parseFloat(patientForm.creatinine_clearance) : null,
                is_pregnant:          patientForm.is_pregnant,
                gestational_weeks:    patientForm.gestational_weeks ? parseInt(patientForm.gestational_weeks) : null,
                is_breastfeeding:     patientForm.is_breastfeeding,
                known_allergies:      patientForm.known_allergies.split(",").map(s => s.trim()).filter(Boolean),
                pathologies_cim10:    patientForm.pathologies_cim10.split(",").map(s => s.trim()).filter(Boolean),
                fhir_patient_id:      patientForm.fhir_patient_id || null,
            };
            if (editPatient) {
                const res = await api.patch(`/patients/${editPatient.id}`, payload);
                // Mettre à jour dans les résultats de recherche
                setSearchResults(prev => prev.map(p => p.id === editPatient.id ? res.data : p));
                if (patientData?.id === editPatient.id) setPatientData(res.data);
            } else {
                const res = await api.post("/patients/", payload);
                setPatientData(res.data);
                setPatientId(String(res.data.id));
                setActiveNav("prescription");
            }
            setShowPatientForm(false);
        } catch (err) {
            setPatientFormErr(err.response?.data?.detail || "Erreur lors de l'enregistrement.");
        } finally { setPatientFormLoad(false); }
    };

    /* ── Prescription ────────────────────────────────────────────────── */
    const addLine = (drug) => {
        setLines(prev => [...prev, {
            _id: Date.now(), drug_id: drug.id, brand_name: drug.brand_name,
            dci: drug.dci || "", dose_mg: "", dose_unit_raw: "mg",
            frequency: "1x/jour", route: "orale", duration_days: 7,
        }]);
    };

    const updateLine = (id, field, value) =>
        setLines(prev => prev.map(l => l._id === id ? { ...l, [field]: value } : l));
    const removeLine = (id) => setLines(prev => prev.filter(l => l._id !== id));

    const submit = async () => {
        if (!patientData)         { setSubmitErr("Veuillez sélectionner un patient."); return; }
        if (lines.length === 0)   { setSubmitErr("Ajoutez au moins un médicament."); return; }
        const incomplete = lines.find(l => !l.dose_mg || isNaN(parseFloat(l.dose_mg)));
        if (incomplete)           { setSubmitErr(`Dosage manquant pour ${incomplete.brand_name}.`); return; }

        setSubmitting(true); setSubmitErr("");
        try {
            const res = await api.post("/prescriptions/", {
                patient_id: patientData.id,
                hook_event: "order-sign",
                lines: lines.map(l => ({
                    drug_id: l.drug_id, dci: l.dci,
                    dose_mg: parseFloat(l.dose_mg), dose_unit_raw: l.dose_unit_raw,
                    frequency: l.frequency, route: l.route,
                    duration_days: parseInt(l.duration_days) || 7,
                })),
            });
            setCdsResult(res.data);
        } catch (e) {
            setSubmitErr(e.response?.data?.detail || "Erreur lors de l'analyse CDS.");
        } finally { setSubmitting(false); }
    };

    const resetForm = () => { setLines([]); setCdsResult(null); setSubmitErr(""); };

    const getAge = (birthdate) => {
        if (!birthdate) return "?";
        return new Date().getFullYear() - new Date(birthdate).getFullYear();
    };

    /* ── RENDER ───────────────────────────────────────────────────────── */
    return (
        <div className="h-screen w-full overflow-hidden flex bg-slate-50">

            {/* ── Sidebar (identique à Admin) ──────────────────────── */}
            <aside className="hidden md:flex w-64 bg-blue-950 flex-col relative overflow-hidden shrink-0">
                {/* Blobs décoratifs */}
                <div className="absolute -top-16 -right-16 w-56 h-56 bg-blue-500 rounded-full opacity-10 blur-3xl pointer-events-none" />
                <div className="absolute -bottom-12 -left-12 w-48 h-48 bg-blue-400 rounded-full opacity-10 blur-3xl pointer-events-none" />
                <div className="absolute inset-0 opacity-[0.06] pointer-events-none"
                    style={{ backgroundImage: "radial-gradient(circle, rgba(255,255,255,0.9) 1px, transparent 1px)", backgroundSize: "20px 20px" }} />

                <div className="relative z-10 flex flex-col h-full">
                    {/* Logo */}
                    <div className="px-5 py-6 border-b border-white border-opacity-10">
                        <div className="flex items-center gap-2.5">
                            <div className="w-9 h-9 rounded-xl bg-blue-500 bg-opacity-30 border border-blue-400 border-opacity-30 flex items-center justify-center">
                                <Stethoscope size={18} className="text-blue-300" strokeWidth={1.5} />
                            </div>
                            <div>
                                <p className="text-white font-bold text-sm leading-none">SafeRx AI</p>
                                <p className="text-blue-400 text-xs mt-0.5">Espace Médecin</p>
                            </div>
                        </div>
                    </div>

                    {/* User badge */}
                    <div className="px-5 py-4 border-b border-white border-opacity-10">
                        <div className="flex items-center gap-2.5">
                            <div className="w-8 h-8 rounded-xl bg-white bg-opacity-10 flex items-center justify-center text-white text-xs font-bold">
                                {user?.first_name?.[0]}{user?.last_name?.[0]}
                            </div>
                            <div>
                                <p className="text-white text-xs font-semibold">
                                    Dr. {user?.first_name} {user?.last_name}
                                </p>
                                <p className="text-blue-400 text-xs">Médecin</p>
                            </div>
                        </div>
                    </div>

                    {/* Nav */}
                    <nav className="flex-1 px-3 py-4 flex flex-col gap-1">
                        {NAV.map(({ id, icon: Icon, label }) => (
                            <button key={id} onClick={() => setActiveNav(id)}
                                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-semibold transition-all text-left
                                    ${activeNav === id
                                        ? "bg-white bg-opacity-15 text-white"
                                        : "text-slate-400 hover:text-white hover:bg-white hover:bg-opacity-5"}`}>
                                <Icon size={16} className={activeNav === id ? "text-blue-300" : ""} />
                                {label}
                            </button>
                        ))}
                    </nav>

                    {/* CDS Status */}
                    <div className="px-5 py-3 mx-3 mb-2 rounded-xl bg-white bg-opacity-5 border border-white border-opacity-10">
                        <div className="flex items-center gap-2">
                            <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                            <span className="text-xs text-emerald-400 font-medium">CDS actif · 7 règles</span>
                        </div>
                        <p className="text-[10px] text-blue-400 opacity-60 mt-1">
                            ANSM · 3 168 interactions
                        </p>
                    </div>

                    {/* Logout */}
                    <div className="px-3 py-4 border-t border-white border-opacity-10">
                        <button onClick={authService.logout}
                            className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-semibold text-slate-400 hover:text-red-400 hover:bg-white hover:bg-opacity-5 transition-all">
                            <LogOut size={16} /> Déconnexion
                        </button>
                    </div>
                </div>
            </aside>

            {/* ── Main ─────────────────────────────────────────────── */}
            <main className="flex-1 overflow-y-auto">

                {/* Topbar dynamique selon la vue */}
                <header className="sticky top-0 z-20 bg-slate-50 border-b border-slate-200 px-6 py-4 flex items-center justify-between">
                    <div>
                        <h1 className="text-lg font-bold text-slate-800">
                            { activeNav === "prescription" ? "Nouvelle prescription"
                            : activeNav === "history"      ? "Mes prescriptions"
                            :                               "Gestion des patients" }
                        </h1>
                        <p className="text-xs text-slate-400">
                            { activeNav === "prescription" ? "Moteur CDS SafeRx — Analyse temps réel"
                            : activeNav === "history"      ? "Toutes vos prescriptions, plus récentes en premier"
                            :                               "Créer, rechercher et modifier les dossiers patients" }
                        </p>
                    </div>
                    <div className="flex items-center gap-3">
                        {activeNav === "patients" && (
                            <button onClick={openCreatePatient}
                                className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-xl transition-all shadow-md shadow-blue-200">
                                <UserPlus size={14} /> Nouveau patient
                            </button>
                        )}
                        {activeNav === "history" && (
                            <button onClick={loadMyPrescriptions}
                                className="p-2 rounded-xl border border-slate-200 bg-white text-slate-500 hover:text-slate-700 transition-all">
                                <RefreshCw size={14} />
                            </button>
                        )}
                        <div className="flex items-center gap-2 bg-white border border-slate-200 rounded-xl px-3 py-2">
                            <Clock size={13} className="text-slate-400" />
                            <span className="text-xs text-slate-600 font-medium">
                                {new Date().toLocaleDateString("fr-FR", { weekday: "long", day: "numeric", month: "long" })}
                            </span>
                        </div>
                    </div>
                </header>

                {/* ════════════════════════════════════════════════════
                    VUE 1 : PRESCRIPTION
                ════════════════════════════════════════════════════ */}
                {activeNav === "prescription" && (
                <div className="p-6 flex gap-6">

                    {/* Colonne gauche */}
                    <div className="flex-1 flex flex-col gap-5 min-w-0">

                        {/* Section Patient */}
                        <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-5">
                            <div className="flex items-center gap-2 mb-4">
                                <div className="w-8 h-8 rounded-xl bg-blue-50 flex items-center justify-center">
                                    <User size={15} className="text-blue-600" />
                                </div>
                                <h3 className="font-semibold text-slate-700 text-sm">Identification du patient</h3>
                            </div>
                            <div className="flex gap-2">
                                <input type="text" value={patientId}
                                    onChange={e => setPatientId(e.target.value)}
                                    onKeyDown={e => e.key === "Enter" && loadPatient()}
                                    placeholder="ID numérique ou FHIR UUID…"
                                    className="flex-1 px-3 py-2.5 border border-slate-200 rounded-xl bg-slate-50 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white transition-all" />
                                <button onClick={loadPatient} disabled={patientLoad}
                                    className="px-4 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 disabled:opacity-60 text-white text-sm font-semibold transition-all flex items-center gap-2 shadow-md shadow-blue-200">
                                    {patientLoad ? <Spinner size={14} /> : <Search size={14} />} Charger
                                </button>
                            </div>
                            {patientErr && (
                                <div className="mt-2 flex items-center gap-2 text-xs text-red-600 bg-red-50 border border-red-200 rounded-xl px-3 py-2">
                                    <AlertCircle size={12} /> {patientErr}
                                </div>
                            )}
                            {patientData && (
                                <div className="mt-4 p-4 rounded-xl bg-slate-50 border border-slate-200">
                                    <div className="flex items-start justify-between gap-3">
                                        <div className="flex items-center gap-3">
                                            <div className="w-10 h-10 rounded-xl bg-blue-950 flex items-center justify-center text-white text-sm font-bold shrink-0">
                                                P{patientData.id}
                                            </div>
                                            <div>
                                                <p className="text-sm font-semibold text-slate-800">Patient #{patientData.id}</p>
                                                <p className="text-xs text-slate-500 mt-0.5">
                                                    {getAge(patientData.birthdate)} ans · {patientData.gender === "M" ? "Homme" : patientData.gender === "F" ? "Femme" : "Autre"}
                                                </p>
                                            </div>
                                        </div>
                                        <div className="flex items-center gap-2">
                                            <button onClick={() => openEditPatient(patientData)}
                                                className="p-1.5 rounded-lg border border-slate-200 text-slate-500 hover:bg-blue-50 hover:border-blue-200 hover:text-blue-600 transition-all"
                                                title="Modifier le dossier">
                                                <Edit2 size={13} />
                                            </button>
                                            <div className="flex items-center gap-1.5 flex-wrap">
                                                {patientData.is_pregnant     && <Tag color="red"><Baby size={10} /> Enceinte</Tag>}
                                                {patientData.is_breastfeeding && <Tag color="amber">Allaitement</Tag>}
                                                {patientData.known_allergies?.length > 0 && (
                                                    <Tag color="red">⚠ {patientData.known_allergies.length} allergie{patientData.known_allergies.length > 1 ? "s" : ""}</Tag>
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                    <div className="mt-4 flex gap-1 p-1 bg-white border border-slate-200 rounded-xl">
                                        {[["new", "Nouvelle prescription"], ["history", "Historique"]].map(([tab, label]) => (
                                            <button key={tab} onClick={() => setActiveTab(tab)}
                                                className={`flex-1 text-xs py-1.5 rounded-lg font-semibold transition-all
                                                    ${activeTab === tab ? "bg-blue-600 text-white shadow-md shadow-blue-200" : "text-slate-500 hover:text-slate-700"}`}>
                                                {label}
                                            </button>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>

                        {/* Historique patient */}
                        {activeTab === "history" && patientData && (
                            <div className="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden">
                                <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
                                    <h3 className="font-semibold text-slate-700 text-sm">Prescriptions de ce patient</h3>
                                    <button onClick={loadPatientHistory} className="text-slate-400 hover:text-slate-600 transition-colors"><RefreshCw size={14} /></button>
                                </div>
                                {historyLoad ? (
                                    <div className="flex justify-center py-10"><Spinner size={20} /></div>
                                ) : patientHistory.length === 0 ? (
                                    <div className="py-10 text-center text-slate-400 text-sm">Aucune prescription trouvée.</div>
                                ) : (
                                    <div className="divide-y divide-slate-50">
                                        {patientHistory.map(p => {
                                            const alertCount = p.lines?.reduce((n, l) => n + (l.alerts?.length || 0), 0) || 0;
                                            return (
                                                <button key={p.id} onClick={() => setSelectedPrescDetail(p)}
                                                    className="w-full px-5 py-4 hover:bg-slate-50 transition-colors text-left flex items-center justify-between">
                                                    <div>
                                                        <p className="text-sm font-semibold text-slate-800">Prescription #{p.id}</p>
                                                        <p className="text-xs text-slate-400 mt-0.5">
                                                            {new Date(p.created_at).toLocaleString("fr-FR")} · {p.lines?.length || 0} médicament(s)
                                                        </p>
                                                    </div>
                                                    <div className="flex items-center gap-2">
                                                        {alertCount > 0
                                                            ? <Tag color="red"><ShieldAlert size={10} /> {alertCount}</Tag>
                                                            : <Tag color="emerald"><ShieldCheck size={10} /> Sûr</Tag>}
                                                        <ChevronRight size={14} className="text-slate-400" />
                                                    </div>
                                                </button>
                                            );
                                        })}
                                    </div>
                                )}
                            </div>
                        )}

                        {/* Nouvelle prescription */}
                        {activeTab === "new" && (<>
                            {patientData && (
                                <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-5">
                                    <div className="flex items-center gap-2 mb-4">
                                        <div className="w-8 h-8 rounded-xl bg-indigo-50 flex items-center justify-center">
                                            <Pill size={15} className="text-indigo-600" />
                                        </div>
                                        <h3 className="font-semibold text-slate-700 text-sm">Ajouter un médicament</h3>
                                    </div>
                                    <DrugSearchInput onSelect={addLine} />
                                </div>
                            )}
                            {lines.length > 0 && (
                                <div className="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden">
                                    <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
                                        <div className="flex items-center gap-2">
                                            <div className="w-8 h-8 rounded-xl bg-purple-50 flex items-center justify-center">
                                                <FlaskConical size={15} className="text-purple-600" />
                                            </div>
                                            <h3 className="font-semibold text-slate-700 text-sm">Lignes de prescription</h3>
                                        </div>
                                        <span className="text-xs text-slate-500 bg-slate-100 px-2 py-0.5 rounded-full font-medium">
                                            {lines.length} médicament{lines.length > 1 ? "s" : ""}
                                        </span>
                                    </div>
                                    <div className="p-5 space-y-3">
                                        {lines.map((line, idx) => (
                                            <div key={line._id} className="p-4 rounded-xl border border-slate-200 bg-slate-50 group hover:border-blue-200 transition-colors">
                                                <div className="flex items-start justify-between gap-2 mb-3">
                                                    <div className="flex items-center gap-2">
                                                        <span className="text-xs font-mono text-slate-400 bg-white border border-slate-200 px-1.5 py-0.5 rounded">{String(idx + 1).padStart(2, "0")}</span>
                                                        <div>
                                                            <p className="text-sm font-semibold text-slate-800">{line.brand_name}</p>
                                                            <p className="text-xs text-slate-400">{line.dci}</p>
                                                        </div>
                                                    </div>
                                                    <button onClick={() => removeLine(line._id)} className="text-slate-300 hover:text-red-500 transition-colors opacity-0 group-hover:opacity-100">
                                                        <Trash2 size={14} />
                                                    </button>
                                                </div>
                                                <div className="grid grid-cols-2 gap-2">
                                                    <div>
                                                        <label className="text-[10px] text-slate-500 uppercase tracking-wider mb-1 block font-semibold">Dose</label>
                                                        <div className="flex gap-1">
                                                            <input type="number" value={line.dose_mg} onChange={e => updateLine(line._id, "dose_mg", e.target.value)} placeholder="0"
                                                                className="flex-1 min-w-0 px-3 py-1.5 border border-slate-200 rounded-lg bg-white text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all" />
                                                            <select value={line.dose_unit_raw} onChange={e => updateLine(line._id, "dose_unit_raw", e.target.value)}
                                                                className="px-2 py-1.5 border border-slate-200 rounded-lg bg-white text-xs text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all">
                                                                {["mg","µg","g","ml","UI","mg/kg"].map(u => <option key={u}>{u}</option>)}
                                                            </select>
                                                        </div>
                                                    </div>
                                                    <div>
                                                        <label className="text-[10px] text-slate-500 uppercase tracking-wider mb-1 block font-semibold">Fréquence</label>
                                                        <select value={line.frequency} onChange={e => updateLine(line._id, "frequency", e.target.value)}
                                                            className="w-full px-3 py-1.5 border border-slate-200 rounded-lg bg-white text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all">
                                                            {FREQ_OPTIONS.map(f => <option key={f}>{f}</option>)}
                                                        </select>
                                                    </div>
                                                    <div>
                                                        <label className="text-[10px] text-slate-500 uppercase tracking-wider mb-1 block font-semibold">Voie</label>
                                                        <select value={line.route} onChange={e => updateLine(line._id, "route", e.target.value)}
                                                            className="w-full px-3 py-1.5 border border-slate-200 rounded-lg bg-white text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all">
                                                            {ROUTES.map(r => <option key={r}>{r}</option>)}
                                                        </select>
                                                    </div>
                                                    <div>
                                                        <label className="text-[10px] text-slate-500 uppercase tracking-wider mb-1 block font-semibold">Durée (jours)</label>
                                                        <input type="number" value={line.duration_days} min="1" onChange={e => updateLine(line._id, "duration_days", e.target.value)}
                                                            className="w-full px-3 py-1.5 border border-slate-200 rounded-lg bg-white text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all" />
                                                    </div>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}
                            {patientData && (
                                <div>
                                    {submitErr && (
                                        <div className="mb-3 flex items-center gap-2 bg-red-50 border border-red-200 rounded-xl px-4 py-3 text-red-600 text-sm">
                                            <AlertCircle size={14} className="shrink-0" /> {submitErr}
                                        </div>
                                    )}
                                    <button onClick={submit} disabled={submitting || lines.length === 0}
                                        className="w-full flex items-center justify-center gap-2.5 py-3 rounded-xl text-white text-sm font-bold bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-lg shadow-blue-200">
                                        {submitting ? <><Spinner size={16} /> Analyse en cours…</> : <><Zap size={16} /> Analyser avec SafeRx CDS</>}
                                    </button>
                                </div>
                            )}
                        </>)}
                    </div>

                    {/* Colonne droite */}
                    <div className="w-72 shrink-0 flex flex-col gap-4">
                        <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-5">
                            <div className="flex items-center gap-2 mb-4">
                                <div className="w-8 h-8 rounded-xl bg-emerald-50 flex items-center justify-center">
                                    <ShieldCheck size={15} className="text-emerald-600" />
                                </div>
                                <h3 className="font-semibold text-slate-700 text-sm">Règles CDS actives</h3>
                            </div>
                            <div className="space-y-1.5">
                                {[
                                    { label: "Allergies directes",  dot: "bg-red-500"   },
                                    { label: "Allergies croisées",  dot: "bg-red-400"   },
                                    { label: "Interactions ANSM",   dot: "bg-red-500"   },
                                    { label: "Contre-indications",  dot: "bg-amber-500" },
                                    { label: "Redondance DCI",      dot: "bg-amber-400" },
                                    { label: "Posologie / âge",     dot: "bg-blue-500"  },
                                    { label: "Insuffisance rénale", dot: "bg-blue-400"  },
                                ].map(({ label, dot }) => (
                                    <div key={label} className="flex items-center gap-2.5 px-3 py-2 rounded-lg hover:bg-slate-50 transition-colors">
                                        <div className={`w-1.5 h-1.5 rounded-full ${dot}`} />
                                        <span className="text-xs text-slate-700">{label}</span>
                                        <CheckCircle2 size={11} className="text-emerald-500 ml-auto" />
                                    </div>
                                ))}
                            </div>
                        </div>
                        {patientData && (
                            <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-5">
                                <div className="flex items-center gap-2 mb-4">
                                    <div className="w-8 h-8 rounded-xl bg-pink-50 flex items-center justify-center">
                                        <Heart size={15} className="text-pink-600" />
                                    </div>
                                    <h3 className="font-semibold text-slate-700 text-sm">Profil de risque</h3>
                                </div>
                                <div className="space-y-2.5">
                                    {[
                                        ["Âge",        `${getAge(patientData.birthdate)} ans`],
                                        ["Genre",      patientData.gender === "M" ? "Homme" : "Femme"],
                                        ["CrCl",       patientData.creatinine_clearance ? `${patientData.creatinine_clearance} mL/min` : "—"],
                                        ["Grossesse",  patientData.is_pregnant ? "Oui ⚠️" : "Non"],
                                        ["Allergies",  patientData.known_allergies?.length > 0 ? patientData.known_allergies.join(", ") : "Aucune"],
                                    ].map(([k, v]) => (
                                        <div key={k} className="flex justify-between gap-2 pb-2 border-b border-slate-50 last:border-0 last:pb-0">
                                            <span className="text-xs text-slate-500 shrink-0">{k}</span>
                                            <span className="text-xs font-medium text-slate-700 text-right">{v}</span>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}
                        {lines.length > 0 && (
                            <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-5">
                                <div className="flex items-center gap-2 mb-3">
                                    <div className="w-8 h-8 rounded-xl bg-indigo-50 flex items-center justify-center">
                                        <Pill size={15} className="text-indigo-600" />
                                    </div>
                                    <h3 className="font-semibold text-slate-700 text-sm">Prescription en cours</h3>
                                </div>
                                <div className="space-y-2">
                                    {lines.map((line, i) => (
                                        <div key={line._id} className="flex items-center gap-2 text-xs">
                                            <span className="text-slate-400 font-mono w-5 shrink-0">{i + 1}.</span>
                                            <span className="text-slate-700 font-medium truncate">{line.brand_name}</span>
                                            <span className="ml-auto text-slate-400 shrink-0">{line.dose_mg || "—"} {line.dose_unit_raw}</span>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>
                </div>
                )}

                {/* ════════════════════════════════════════════════════
                    VUE 2 : MES PRESCRIPTIONS
                ════════════════════════════════════════════════════ */}
                {activeNav === "history" && (
                <div className="p-6">
                    {myPrescLoad ? (
                        <div className="flex justify-center py-20"><Spinner size={24} /></div>
                    ) : myPrescriptions.length === 0 ? (
                        <div className="flex flex-col items-center justify-center py-20 text-center">
                            <div className="w-14 h-14 rounded-full bg-slate-100 flex items-center justify-center mb-4">
                                <ClipboardList size={22} className="text-slate-400" />
                            </div>
                            <p className="font-semibold text-slate-600 mb-1">Aucune prescription trouvée</p>
                            <p className="text-sm text-slate-400">Vos prescriptions apparaîtront ici.</p>
                        </div>
                    ) : (
                        <div className="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden">
                            <div className="px-5 py-4 border-b border-slate-100">
                                <span className="text-sm font-semibold text-slate-700">{myPrescriptions.length} prescription{myPrescriptions.length > 1 ? "s" : ""}</span>
                            </div>
                            <div className="divide-y divide-slate-50">
                                {myPrescriptions.map(p => {
                                    const alertCount = p.lines?.reduce((n, l) => n + (l.alerts?.length || 0), 0) || 0;
                                    return (
                                        <button key={p.id} onClick={() => setSelectedPrescDetail(p)}
                                            className="w-full px-5 py-4 hover:bg-slate-50 transition-colors text-left flex items-center gap-4">
                                            <div className={`w-2 h-8 rounded-full shrink-0 ${p.status === "safe" ? "bg-emerald-400" : p.status === "alerts" ? "bg-amber-400" : "bg-slate-300"}`} />
                                            <div className="flex-1 min-w-0">
                                                <div className="flex items-center gap-2 mb-0.5">
                                                    <p className="text-sm font-semibold text-slate-800">Prescription #{p.id}</p>
                                                    <span className={`text-[10px] px-1.5 py-0.5 rounded-full border font-semibold
                                                        ${p.status === "safe" ? "text-emerald-700 border-emerald-200 bg-emerald-50" :
                                                          p.status === "alerts" ? "text-amber-700 border-amber-200 bg-amber-50" :
                                                                                  "text-slate-500 border-slate-200 bg-slate-50"}`}>
                                                        {p.status}
                                                    </span>
                                                </div>
                                                <p className="text-xs text-slate-400">
                                                    Patient #{p.patient_id} · {new Date(p.created_at).toLocaleString("fr-FR")} · {p.lines?.length || 0} médicament(s)
                                                </p>
                                            </div>
                                            <div className="flex items-center gap-2">
                                                {alertCount > 0 && <Tag color="red"><ShieldAlert size={10} /> {alertCount}</Tag>}
                                                <ChevronRight size={14} className="text-slate-400" />
                                            </div>
                                        </button>
                                    );
                                })}
                            </div>
                        </div>
                    )}
                </div>
                )}

                {/* ════════════════════════════════════════════════════
                    VUE 3 : PATIENTS
                ════════════════════════════════════════════════════ */}
                {activeNav === "patients" && (
                <div className="p-6 flex flex-col gap-5">
                    {/* Recherche */}
                    <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-5">
                        <div className="flex items-center gap-2 mb-4">
                            <div className="w-8 h-8 rounded-xl bg-blue-50 flex items-center justify-center">
                                <Search size={15} className="text-blue-600" />
                            </div>
                            <h3 className="font-semibold text-slate-700 text-sm">Rechercher un patient</h3>
                        </div>
                        <div className="relative">
                            <div className="flex items-center gap-2 bg-slate-50 border border-slate-200 rounded-xl px-3 py-2.5 focus-within:ring-2 focus-within:ring-blue-500 focus-within:border-transparent transition-all">
                                {searchLoading ? <Spinner size={14} /> : <Search size={14} className="text-slate-400" />}
                                <input type="text" value={patientSearch}
                                    onChange={e => setPatientSearch(e.target.value)}
                                    placeholder="ID numérique ou FHIR UUID…"
                                    className="flex-1 bg-transparent text-sm text-slate-800 placeholder-slate-400 outline-none" />
                            </div>
                            {searchResults.length > 0 && (
                                <div className="mt-2 rounded-xl border border-slate-200 overflow-hidden shadow-lg bg-white">
                                    {searchResults.map(p => (
                                        <div key={p.id} className="px-4 py-3 border-b border-slate-100 last:border-0 flex items-center justify-between hover:bg-slate-50 transition-colors">
                                            <div>
                                                <p className="text-sm font-semibold text-slate-800">Patient #{p.id}</p>
                                                <p className="text-xs text-slate-500 mt-0.5">
                                                    {getAge(p.birthdate)} ans · {p.gender === "M" ? "Homme" : "Femme"}
                                                    {p.known_allergies?.length > 0 && ` · ⚠ ${p.known_allergies.length} allergie(s)`}
                                                </p>
                                            </div>
                                            <div className="flex gap-2">
                                                <button onClick={() => openEditPatient(p)}
                                                    className="p-1.5 rounded-lg border border-slate-200 text-slate-500 hover:bg-blue-50 hover:border-blue-200 hover:text-blue-600 transition-all">
                                                    <Edit2 size={13} />
                                                </button>
                                                <button onClick={() => { setPatientData(p); setPatientId(String(p.id)); setActiveNav("prescription"); }}
                                                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold transition-all">
                                                    <Zap size={11} /> Prescrire
                                                </button>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    </div>
                </div>
                )}
            </main>

            {/* ════════════════════════════════════════════════════
                MODAL : DÉTAIL PRESCRIPTION
            ════════════════════════════════════════════════════ */}
            {selectedPrescDetail && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/30 backdrop-blur-sm">
                    <div className="w-full max-w-2xl max-h-[90vh] overflow-hidden rounded-2xl border border-slate-100 shadow-2xl bg-white flex flex-col">
                        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
                            <div>
                                <h2 className="font-bold text-slate-800">Prescription #{selectedPrescDetail.id}</h2>
                                <p className="text-xs text-slate-500 mt-0.5">
                                    {new Date(selectedPrescDetail.created_at).toLocaleString("fr-FR")} · Patient #{selectedPrescDetail.patient_id}
                                </p>
                            </div>
                            <button onClick={() => setSelectedPrescDetail(null)}
                                className="w-8 h-8 rounded-lg hover:bg-slate-100 flex items-center justify-center text-slate-400 hover:text-slate-600 transition-all">
                                <X size={16} />
                            </button>
                        </div>
                        <div className="overflow-y-auto flex-1 p-5 space-y-4">
                            {/* Médicaments */}
                            <div>
                                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Médicaments prescrits</p>
                                <div className="space-y-2">
                                    {(selectedPrescDetail.lines || []).map((line, i) => (
                                        <div key={line.id} className="flex items-center gap-3 p-3 rounded-xl bg-slate-50 border border-slate-200">
                                            <span className="text-xs font-mono text-slate-400 bg-white border border-slate-200 px-1.5 py-0.5 rounded">{String(i+1).padStart(2,"0")}</span>
                                            <div className="flex-1">
                                                <p className="text-sm font-semibold text-slate-800">{line.dci}</p>
                                                <p className="text-xs text-slate-500">{line.dose_mg} {line.dose_unit_raw} · {line.frequency} · {line.route} · {line.duration_days}j</p>
                                            </div>
                                            {(line.alerts?.length > 0) && (
                                                <Tag color="red">{line.alerts.length} alerte{line.alerts.length > 1 ? "s" : ""}</Tag>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            </div>
                            {/* Alertes CDS */}
                            {selectedPrescDetail.lines?.some(l => l.alerts?.length > 0) && (
                                <div>
                                    <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Alertes CDS détectées</p>
                                    <div className="space-y-2">
                                        {selectedPrescDetail.lines?.flatMap(l => l.alerts || []).map(alert => {
                                            const colors = {
                                                MAJOR:    "bg-red-50 border-red-200 text-red-700",
                                                MODERATE: "bg-amber-50 border-amber-200 text-amber-700",
                                                MINOR:    "bg-blue-50 border-blue-200 text-blue-700",
                                            };
                                            return (
                                                <div key={alert.id} className={`p-3 rounded-xl border text-xs ${colors[alert.severity] || colors.MINOR}`}>
                                                    <p className="font-semibold">{alert.title}</p>
                                                    <p className="mt-1 opacity-80">{alert.detail}</p>
                                                    {alert.rag_explanation && (
                                                        <div className="mt-2 p-2 rounded-lg bg-purple-50 border border-purple-200">
                                                            <p className="text-[10px] font-bold text-purple-700 uppercase tracking-wider mb-1">Analyse SafeRx AI</p>
                                                            <p className="text-purple-800">{alert.rag_explanation}</p>
                                                        </div>
                                                    )}
                                                </div>
                                            );
                                        })}
                                    </div>
                                </div>
                            )}
                        </div>
                        <div className="px-6 py-4 border-t border-slate-100 flex justify-between items-center">
                            <span className={`text-xs px-2.5 py-1 rounded-full border font-semibold
                                ${selectedPrescDetail.status === "safe" ? "text-emerald-700 border-emerald-200 bg-emerald-50" :
                                  "text-amber-700 border-amber-200 bg-amber-50"}`}>
                                {selectedPrescDetail.status === "safe" ? "✓ Prescription sûre" : "⚠ Alertes présentes"}
                            </span>
                            <button onClick={() => setSelectedPrescDetail(null)}
                                className="px-4 py-2 rounded-xl text-sm font-semibold text-slate-600 border border-slate-200 hover:bg-slate-50 transition-all">
                                Fermer
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* ════════════════════════════════════════════════════
                MODAL : CRÉER / MODIFIER PATIENT
            ════════════════════════════════════════════════════ */}
            {showPatientForm && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/30 backdrop-blur-sm">
                    <div className="w-full max-w-lg max-h-[90vh] overflow-hidden rounded-2xl border border-slate-100 shadow-2xl bg-white flex flex-col">
                        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
                            <div className="flex items-center gap-3">
                                <div className="w-9 h-9 rounded-xl bg-blue-50 flex items-center justify-center">
                                    {editPatient ? <Edit2 size={16} className="text-blue-600" /> : <UserPlus size={16} className="text-blue-600" />}
                                </div>
                                <div>
                                    <h2 className="font-bold text-slate-800 text-sm">{editPatient ? "Modifier le patient" : "Nouveau patient"}</h2>
                                    <p className="text-xs text-slate-500">{editPatient ? `Dossier #${editPatient.id}` : "Créer un dossier"}</p>
                                </div>
                            </div>
                            <button onClick={() => setShowPatientForm(false)}
                                className="w-8 h-8 rounded-lg hover:bg-slate-100 flex items-center justify-center text-slate-400 hover:text-slate-600 transition-all">
                                <X size={16} />
                            </button>
                        </div>
                        <form onSubmit={submitPatientForm} className="overflow-y-auto flex-1 p-5">
                            <div className="grid grid-cols-2 gap-3">
                                <div className="col-span-2 flex flex-col gap-1.5">
                                    <label className="text-xs font-semibold text-slate-600 uppercase tracking-wide">Date de naissance *</label>
                                    <input type="date" value={patientForm.birthdate} required
                                        onChange={e => setPatientForm(p => ({...p, birthdate: e.target.value}))}
                                        className="px-3 py-2.5 border border-slate-200 rounded-xl bg-slate-50 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white transition-all" />
                                </div>
                                <div className="flex flex-col gap-1.5">
                                    <label className="text-xs font-semibold text-slate-600 uppercase tracking-wide">Genre *</label>
                                    <div className="flex gap-2">
                                        {[["M","Homme"],["F","Femme"],["O","Autre"]].map(([v,l]) => (
                                            <button key={v} type="button" onClick={() => setPatientForm(p => ({...p, gender: v}))}
                                                className={`flex-1 py-2 rounded-xl border text-xs font-semibold transition-all
                                                    ${patientForm.gender === v ? "bg-blue-600 border-blue-600 text-white shadow-md shadow-blue-200" : "bg-white border-slate-200 text-slate-600 hover:border-blue-300"}`}>
                                                {l}
                                            </button>
                                        ))}
                                    </div>
                                </div>
                                <div className="flex flex-col gap-1.5">
                                    <label className="text-xs font-semibold text-slate-600 uppercase tracking-wide">Clairance créatinine (mL/min)</label>
                                    <input type="number" step="0.1" value={patientForm.creatinine_clearance}
                                        onChange={e => setPatientForm(p => ({...p, creatinine_clearance: e.target.value}))}
                                        placeholder="ex: 90.5"
                                        className="px-3 py-2.5 border border-slate-200 rounded-xl bg-slate-50 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white transition-all" />
                                </div>
                                <div className="flex flex-col gap-1.5">
                                    <label className="text-xs font-semibold text-slate-600 uppercase tracking-wide">Poids (kg)</label>
                                    <input type="number" step="0.1" value={patientForm.weight_kg}
                                        onChange={e => setPatientForm(p => ({...p, weight_kg: e.target.value}))}
                                        placeholder="ex: 70.5"
                                        className="px-3 py-2.5 border border-slate-200 rounded-xl bg-slate-50 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white transition-all" />
                                </div>
                                <div className="flex flex-col gap-1.5">
                                    <label className="text-xs font-semibold text-slate-600 uppercase tracking-wide">Taille (cm)</label>
                                    <input type="number" value={patientForm.height_cm}
                                        onChange={e => setPatientForm(p => ({...p, height_cm: e.target.value}))}
                                        placeholder="ex: 170"
                                        className="px-3 py-2.5 border border-slate-200 rounded-xl bg-slate-50 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white transition-all" />
                                </div>
                                <div className="col-span-2 flex gap-4">
                                    {[["is_pregnant","Enceinte"],["is_breastfeeding","Allaitement"]].map(([field, label]) => (
                                        <label key={field} className="flex items-center gap-2 cursor-pointer">
                                            <input type="checkbox" checked={patientForm[field]}
                                                onChange={e => setPatientForm(p => ({...p, [field]: e.target.checked}))}
                                                className="w-4 h-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500" />
                                            <span className="text-sm text-slate-700 font-medium">{label}</span>
                                        </label>
                                    ))}
                                </div>
                                <div className="col-span-2 flex flex-col gap-1.5">
                                    <label className="text-xs font-semibold text-slate-600 uppercase tracking-wide">Allergies connues (séparées par virgule)</label>
                                    <input type="text" value={patientForm.known_allergies}
                                        onChange={e => setPatientForm(p => ({...p, known_allergies: e.target.value}))}
                                        placeholder="ex: Pénicilline, Sulfamides, Arachides"
                                        className="px-3 py-2.5 border border-slate-200 rounded-xl bg-slate-50 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white transition-all" />
                                </div>
                                <div className="col-span-2 flex flex-col gap-1.5">
                                    <label className="text-xs font-semibold text-slate-600 uppercase tracking-wide">Pathologies CIM-10 (séparées par virgule)</label>
                                    <input type="text" value={patientForm.pathologies_cim10}
                                        onChange={e => setPatientForm(p => ({...p, pathologies_cim10: e.target.value}))}
                                        placeholder="ex: I10, E11.9, N18.3"
                                        className="px-3 py-2.5 border border-slate-200 rounded-xl bg-slate-50 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white transition-all" />
                                </div>
                                <div className="col-span-2 flex flex-col gap-1.5">
                                    <label className="text-xs font-semibold text-slate-600 uppercase tracking-wide">FHIR Patient ID (UUID)</label>
                                    <input type="text" value={patientForm.fhir_patient_id}
                                        onChange={e => setPatientForm(p => ({...p, fhir_patient_id: e.target.value}))}
                                        placeholder="ex: a8b2c4d6-e8f0-4123-9456-789abcdef012"
                                        className="px-3 py-2.5 border border-slate-200 rounded-xl bg-slate-50 text-sm text-slate-800 font-mono focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white transition-all" />
                                </div>
                            </div>
                            {patientFormErr && (
                                <div className="mt-3 flex items-center gap-2 bg-red-50 border border-red-200 rounded-xl px-4 py-3 text-red-600 text-sm">
                                    <AlertCircle size={14} className="shrink-0" /> {patientFormErr}
                                </div>
                            )}
                            <div className="flex gap-2 mt-5">
                                <button type="button" onClick={() => setShowPatientForm(false)}
                                    className="flex-1 py-2.5 border border-slate-200 rounded-xl text-sm font-semibold text-slate-600 hover:bg-slate-50 transition-all">
                                    Annuler
                                </button>
                                <button type="submit" disabled={patientFormLoad}
                                    className="flex-1 flex items-center justify-center gap-2 py-2.5 bg-blue-600 hover:bg-blue-700 disabled:opacity-60 text-white text-sm font-semibold rounded-xl shadow-md shadow-blue-200 transition-all">
                                    {patientFormLoad ? <><Spinner size={14} /> Enregistrement…</> : <><Save size={14} /> {editPatient ? "Enregistrer" : "Créer le patient"}</>}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {/* ── Modal CDS ─────────────────────────────────────── */}
            {cdsResult && (
                <CdsResultPanel
                    result={cdsResult}
                    onClose={() => setCdsResult(null)}
                    onNewPrescription={resetForm}
                />
            )}
        </div>
    );
}