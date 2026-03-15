import { useState, useEffect, useRef } from "react";
import {
    Stethoscope, Search, Plus, Trash2, LogOut,
    ShieldAlert, ShieldCheck, AlertTriangle, Info,
    Pill, User, Activity, Clock, FileText,
    AlertCircle, Zap, FlaskConical, Heart, Baby,
    Brain, Siren, LayoutDashboard, ClipboardList,
    CheckCircle2, TriangleAlert, RefreshCw
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
    { id: "prescription", icon: LayoutDashboard, label: "Prescription" },
    { id: "history",      icon: ClipboardList,   label: "Historique"   },
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

    const [patientId,   setPatientId]   = useState("");
    const [patientData, setPatientData] = useState(null);
    const [patientLoad, setPatientLoad] = useState(false);
    const [patientErr,  setPatientErr]  = useState("");
    const [lines,       setLines]       = useState([]);
    const [submitting,  setSubmitting]  = useState(false);
    const [cdsResult,   setCdsResult]   = useState(null);
    const [submitErr,   setSubmitErr]   = useState("");
    const [history,     setHistory]     = useState([]);
    const [historyLoad, setHistoryLoad] = useState(false);
    const [activeNav,   setActiveNav]   = useState("prescription");
    const [activeTab,   setActiveTab]   = useState("new");

    const loadPatient = async () => {
        if (!patientId.trim()) return;
        setPatientLoad(true); setPatientErr(""); setPatientData(null);
        try {
            const res = await api.get(`/patients/${patientId}`);
            setPatientData(res.data);
        } catch (e) {
            setPatientErr(e.response?.status === 404 ? "Patient introuvable." : "Erreur lors du chargement.");
        } finally { setPatientLoad(false); }
    };

    const loadHistory = async () => {
        if (!patientData) return;
        setHistoryLoad(true);
        try {
            const res = await api.get(`/prescriptions/patient/${patientData.id}`);
            setHistory(res.data || []);
        } catch { setHistory([]); }
        finally { setHistoryLoad(false); }
    };

    useEffect(() => {
        if (activeTab === "history" && patientData) loadHistory();
    }, [activeTab, patientData]);

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

                {/* Topbar */}
                <header className="sticky top-0 z-20 bg-slate-50 border-b border-slate-200 px-6 py-4 flex items-center justify-between">
                    <div>
                        <h1 className="text-lg font-bold text-slate-800">Analyse de prescription</h1>
                        <p className="text-xs text-slate-400">Moteur CDS SafeRx — Analyse temps réel</p>
                    </div>
                    <div className="flex items-center gap-3">
                        <div className="flex items-center gap-2 bg-white border border-slate-200 rounded-xl px-3 py-2">
                            <Clock size={13} className="text-slate-400" />
                            <span className="text-xs text-slate-600 font-medium">
                                {new Date().toLocaleDateString("fr-FR", { weekday: "long", day: "numeric", month: "long" })}
                            </span>
                        </div>
                    </div>
                </header>

                <div className="p-6 flex gap-6">

                    {/* ── Colonne gauche : formulaire ──────────────── */}
                    <div className="flex-1 flex flex-col gap-5 min-w-0">

                        {/* Section Patient */}
                        <div className="bg-white rounded-2xl border border-slate-100 shadow-sm shadow-slate-100 p-5">
                            <div className="flex items-center gap-2 mb-4">
                                <div className="w-8 h-8 rounded-xl bg-blue-50 flex items-center justify-center">
                                    <User size={15} className="text-blue-600" />
                                </div>
                                <h3 className="font-semibold text-slate-700 text-sm">Identification du patient</h3>
                            </div>

                            <div className="flex gap-2">
                                <input
                                    type="number"
                                    value={patientId}
                                    onChange={e => setPatientId(e.target.value)}
                                    onKeyDown={e => e.key === "Enter" && loadPatient()}
                                    placeholder="ID du patient…"
                                    className="flex-1 px-3 py-2.5 border border-slate-200 rounded-xl bg-slate-50 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent focus:bg-white transition-all"
                                />
                                <button onClick={loadPatient} disabled={patientLoad}
                                    className="px-4 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 disabled:opacity-60 text-white text-sm font-semibold transition-all flex items-center gap-2 shadow-md shadow-blue-200">
                                    {patientLoad ? <Spinner size={14} /> : <Search size={14} />}
                                    Charger
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
                                                    {getAge(patientData.birthdate)} ans ·{" "}
                                                    {patientData.gender === "M" ? "Homme" : patientData.gender === "F" ? "Femme" : "Autre"}
                                                </p>
                                            </div>
                                        </div>
                                        <div className="flex items-center gap-1.5 flex-wrap justify-end">
                                            {patientData.is_pregnant     && <Tag color="red"><Baby size={10} /> Enceinte</Tag>}
                                            {patientData.is_breastfeeding && <Tag color="amber">Allaitement</Tag>}
                                            {patientData.known_allergies?.length > 0 && (
                                                <Tag color="red">⚠ {patientData.known_allergies.length} allergie{patientData.known_allergies.length > 1 ? "s" : ""}</Tag>
                                            )}
                                        </div>
                                    </div>

                                    {/* Tabs */}
                                    <div className="mt-4 flex gap-1 p-1 bg-white border border-slate-200 rounded-xl">
                                        {[["new", "Nouvelle prescription"], ["history", "Historique"]].map(([tab, label]) => (
                                            <button key={tab} onClick={() => setActiveTab(tab)}
                                                className={`flex-1 text-xs py-1.5 rounded-lg font-semibold transition-all
                                                    ${activeTab === tab
                                                        ? "bg-blue-600 text-white shadow-md shadow-blue-200"
                                                        : "text-slate-500 hover:text-slate-700"}`}>
                                                {label}
                                            </button>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>

                        {/* Historique */}
                        {activeTab === "history" && patientData && (
                            <div className="bg-white rounded-2xl border border-slate-100 shadow-sm shadow-slate-100 overflow-hidden">
                                <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
                                    <h3 className="font-semibold text-slate-700 text-sm">Historique des prescriptions</h3>
                                    <button onClick={loadHistory} className="text-slate-400 hover:text-slate-600 transition-colors">
                                        <RefreshCw size={14} />
                                    </button>
                                </div>
                                {historyLoad ? (
                                    <div className="flex justify-center py-10"><Spinner size={20} /></div>
                                ) : history.length === 0 ? (
                                    <div className="py-10 text-center text-slate-400 text-sm">Aucune prescription trouvée.</div>
                                ) : (
                                    <div className="divide-y divide-slate-50">
                                        {history.map(p => {
                                            const alertCount = p.lines?.reduce((n, l) => n + (l.alerts?.length || 0), 0) || 0;
                                            return (
                                                <div key={p.id} className="px-5 py-4 hover:bg-slate-50 transition-colors">
                                                    <div className="flex items-center justify-between">
                                                        <div>
                                                            <p className="text-sm font-semibold text-slate-800">Prescription #{p.id}</p>
                                                            <p className="text-xs text-slate-400 mt-0.5">
                                                                {new Date(p.created_at).toLocaleString("fr-FR")} · {p.lines?.length || 0} médicament(s)
                                                            </p>
                                                        </div>
                                                        <div className="flex items-center gap-2">
                                                            {alertCount > 0
                                                                ? <Tag color="red"><ShieldAlert size={10} /> {alertCount} alerte{alertCount > 1 ? "s" : ""}</Tag>
                                                                : <Tag color="emerald"><ShieldCheck size={10} /> Sûr</Tag>}
                                                            <span className={`text-xs px-2 py-0.5 rounded-full border font-semibold
                                                                ${p.status === "safe"   ? "text-emerald-700 border-emerald-200 bg-emerald-50" :
                                                                  p.status === "alerts" ? "text-amber-700 border-amber-200 bg-amber-50" :
                                                                                          "text-slate-500 border-slate-200 bg-slate-50"}`}>
                                                                {p.status}
                                                            </span>
                                                        </div>
                                                    </div>
                                                </div>
                                            );
                                        })}
                                    </div>
                                )}
                            </div>
                        )}

                        {/* Nouvelle prescription */}
                        {activeTab === "new" && (
                            <>
                                {/* Recherche médicament */}
                                {patientData && (
                                    <div className="bg-white rounded-2xl border border-slate-100 shadow-sm shadow-slate-100 p-5">
                                        <div className="flex items-center gap-2 mb-4">
                                            <div className="w-8 h-8 rounded-xl bg-indigo-50 flex items-center justify-center">
                                                <Pill size={15} className="text-indigo-600" />
                                            </div>
                                            <h3 className="font-semibold text-slate-700 text-sm">Ajouter un médicament</h3>
                                        </div>
                                        <DrugSearchInput onSelect={addLine} />
                                    </div>
                                )}

                                {/* Lignes de prescription */}
                                {lines.length > 0 && (
                                    <div className="bg-white rounded-2xl border border-slate-100 shadow-sm shadow-slate-100 overflow-hidden">
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
                                                            <span className="text-xs font-mono text-slate-400 bg-white border border-slate-200 px-1.5 py-0.5 rounded">
                                                                {String(idx + 1).padStart(2, "0")}
                                                            </span>
                                                            <div>
                                                                <p className="text-sm font-semibold text-slate-800">{line.brand_name}</p>
                                                                <p className="text-xs text-slate-400">{line.dci}</p>
                                                            </div>
                                                        </div>
                                                        <button onClick={() => removeLine(line._id)}
                                                            className="text-slate-300 hover:text-red-500 transition-colors opacity-0 group-hover:opacity-100">
                                                            <Trash2 size={14} />
                                                        </button>
                                                    </div>
                                                    <div className="grid grid-cols-2 gap-2">
                                                        <div>
                                                            <label className="text-[10px] text-slate-500 uppercase tracking-wider mb-1 block font-semibold">Dose</label>
                                                            <div className="flex gap-1">
                                                                <input type="number" value={line.dose_mg}
                                                                    onChange={e => updateLine(line._id, "dose_mg", e.target.value)}
                                                                    placeholder="0"
                                                                    className="flex-1 min-w-0 px-3 py-1.5 border border-slate-200 rounded-lg bg-white text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all" />
                                                                <select value={line.dose_unit_raw}
                                                                    onChange={e => updateLine(line._id, "dose_unit_raw", e.target.value)}
                                                                    className="px-2 py-1.5 border border-slate-200 rounded-lg bg-white text-xs text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all">
                                                                    {["mg", "µg", "g", "ml", "UI", "mg/kg"].map(u => <option key={u}>{u}</option>)}
                                                                </select>
                                                            </div>
                                                        </div>
                                                        <div>
                                                            <label className="text-[10px] text-slate-500 uppercase tracking-wider mb-1 block font-semibold">Fréquence</label>
                                                            <select value={line.frequency}
                                                                onChange={e => updateLine(line._id, "frequency", e.target.value)}
                                                                className="w-full px-3 py-1.5 border border-slate-200 rounded-lg bg-white text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all">
                                                                {FREQ_OPTIONS.map(f => <option key={f}>{f}</option>)}
                                                            </select>
                                                        </div>
                                                        <div>
                                                            <label className="text-[10px] text-slate-500 uppercase tracking-wider mb-1 block font-semibold">Voie</label>
                                                            <select value={line.route}
                                                                onChange={e => updateLine(line._id, "route", e.target.value)}
                                                                className="w-full px-3 py-1.5 border border-slate-200 rounded-lg bg-white text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all">
                                                                {ROUTES.map(r => <option key={r}>{r}</option>)}
                                                            </select>
                                                        </div>
                                                        <div>
                                                            <label className="text-[10px] text-slate-500 uppercase tracking-wider mb-1 block font-semibold">Durée (jours)</label>
                                                            <input type="number" value={line.duration_days} min="1"
                                                                onChange={e => updateLine(line._id, "duration_days", e.target.value)}
                                                                className="w-full px-3 py-1.5 border border-slate-200 rounded-lg bg-white text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all" />
                                                        </div>
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}

                                {/* Bouton analyser */}
                                {patientData && (
                                    <div>
                                        {submitErr && (
                                            <div className="mb-3 flex items-center gap-2 bg-red-50 border border-red-200 rounded-xl px-4 py-3 text-red-600 text-sm">
                                                <AlertCircle size={14} className="shrink-0" /> {submitErr}
                                            </div>
                                        )}
                                        <button onClick={submit}
                                            disabled={submitting || lines.length === 0}
                                            className="w-full flex items-center justify-center gap-2.5 py-3 rounded-xl text-white text-sm font-bold bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-lg shadow-blue-200">
                                            {submitting
                                                ? <><Spinner size={16} /> Analyse en cours…</>
                                                : <><Zap size={16} /> Analyser avec SafeRx CDS</>}
                                        </button>
                                    </div>
                                )}
                            </>
                        )}
                    </div>

                    {/* ── Colonne droite : contexte ────────────────── */}
                    <div className="w-72 shrink-0 flex flex-col gap-4">

                        {/* Règles CDS */}
                        <div className="bg-white rounded-2xl border border-slate-100 shadow-sm shadow-slate-100 p-5">
                            <div className="flex items-center gap-2 mb-4">
                                <div className="w-8 h-8 rounded-xl bg-emerald-50 flex items-center justify-center">
                                    <ShieldCheck size={15} className="text-emerald-600" />
                                </div>
                                <h3 className="font-semibold text-slate-700 text-sm">Règles CDS actives</h3>
                            </div>
                            <div className="space-y-1.5">
                                {[
                                    { label: "Allergies directes",     dot: "bg-red-500",    text: "text-slate-700" },
                                    { label: "Allergies croisées",     dot: "bg-red-400",    text: "text-slate-700" },
                                    { label: "Interactions ANSM",      dot: "bg-red-500",    text: "text-slate-700" },
                                    { label: "Contre-indications",     dot: "bg-amber-500",  text: "text-slate-700" },
                                    { label: "Redondance DCI",         dot: "bg-amber-400",  text: "text-slate-700" },
                                    { label: "Posologie / âge",        dot: "bg-blue-500",   text: "text-slate-700" },
                                    { label: "Insuffisance rénale",    dot: "bg-blue-400",   text: "text-slate-700" },
                                ].map(({ label, dot, text }) => (
                                    <div key={label} className="flex items-center gap-2.5 px-3 py-2 rounded-lg hover:bg-slate-50 transition-colors">
                                        <div className={`w-1.5 h-1.5 rounded-full ${dot}`} />
                                        <span className={`text-xs ${text}`}>{label}</span>
                                        <CheckCircle2 size={11} className="text-emerald-500 ml-auto" />
                                    </div>
                                ))}
                            </div>
                        </div>

                        {/* Profil de risque patient */}
                        {patientData && (
                            <div className="bg-white rounded-2xl border border-slate-100 shadow-sm shadow-slate-100 p-5">
                                <div className="flex items-center gap-2 mb-4">
                                    <div className="w-8 h-8 rounded-xl bg-pink-50 flex items-center justify-center">
                                        <Heart size={15} className="text-pink-600" />
                                    </div>
                                    <h3 className="font-semibold text-slate-700 text-sm">Profil de risque</h3>
                                </div>
                                <div className="space-y-2.5">
                                    {[
                                        ["Âge",         `${getAge(patientData.birthdate)} ans`],
                                        ["Genre",       patientData.gender === "M" ? "Homme" : patientData.gender === "F" ? "Femme" : "Autre"],
                                        ["Grossesse",   patientData.is_pregnant ? "Oui ⚠️" : "Non"],
                                        ["Allaitement", patientData.is_breastfeeding ? "Oui ⚠️" : "Non"],
                                        ["Allergies",   patientData.known_allergies?.length > 0 ? patientData.known_allergies.join(", ") : "Aucune"],
                                    ].map(([k, v]) => (
                                        <div key={k} className="flex items-start justify-between gap-2 pb-2 border-b border-slate-50 last:border-0 last:pb-0">
                                            <span className="text-xs text-slate-500 shrink-0">{k}</span>
                                            <span className="text-xs font-medium text-slate-700 text-right">{v}</span>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}

                        {/* Résumé prescription */}
                        {lines.length > 0 && (
                            <div className="bg-white rounded-2xl border border-slate-100 shadow-sm shadow-slate-100 p-5">
                                <div className="flex items-center gap-2 mb-4">
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
                                {lines.length > 1 && (
                                    <div className="mt-3 pt-3 border-t border-slate-100 flex justify-between text-xs">
                                        <span className="text-slate-500">Paires à vérifier</span>
                                        <span className="font-semibold text-slate-700">
                                            {lines.length * (lines.length - 1) / 2} interaction{lines.length * (lines.length - 1) / 2 > 1 ? "s" : ""}
                                        </span>
                                    </div>
                                )}
                            </div>
                        )}

                        {/* Source */}
                        <p className="text-[10px] text-slate-400 leading-relaxed px-1">
                            Base interactions : Thésaurus ANSM sept. 2023 · 3 168 paires DCI<br />
                            Base médicaments : medicament.ma · 5 006 spécialités
                        </p>
                    </div>
                </div>
            </main>

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