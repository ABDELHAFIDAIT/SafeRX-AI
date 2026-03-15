/**
 * SafeRx AI — CdsResultPanel (thème clair)
 * ──────────────────────────────────────────
 * Modal d'analyse CDS cohérent avec le design system AdminDashboard :
 *   bg-white, border-slate-100, textes slate-700/800, accents colorés légers
 */
import { useState } from "react";
import {
    ShieldAlert, ShieldCheck, X, CheckCircle2,
    XCircle, AlertTriangle, Info, ChevronDown,
    Siren, TriangleAlert, Send, FileText, Plus,
    AlertCircle, ClipboardCheck, Sparkles, TrendingDown
} from "lucide-react";
import api from "../api/api";

/* ── Config sévérité — version light ────────────────────────────────── */
const SEVERITY_CONFIG = {
    MAJOR: {
        label:      "Critique",
        bg:         "bg-red-50",
        border:     "border-red-200",
        text:       "text-red-700",
        badge:      "bg-red-100 text-red-700 border-red-200",
        headerBg:   "bg-red-50 border-b border-red-100",
        icon:       Siren,
    },
    MODERATE: {
        label:      "Modérée",
        bg:         "bg-amber-50",
        border:     "border-amber-200",
        text:       "text-amber-700",
        badge:      "bg-amber-100 text-amber-700 border-amber-200",
        headerBg:   "bg-amber-50 border-b border-amber-100",
        icon:       TriangleAlert,
    },
    MINOR: {
        label:      "Mineure",
        bg:         "bg-blue-50",
        border:     "border-blue-200",
        text:       "text-blue-700",
        badge:      "bg-blue-100 text-blue-700 border-blue-200",
        headerBg:   "bg-blue-50 border-b border-blue-100",
        icon:       Info,
    },
};

const ALERT_TYPE_LABEL = {
    INTERACTION:        "Interaction",
    ALLERGY:            "Allergie",
    CONTRA_INDICATION:  "Contre-indication",
    REDUNDANT_DCI:      "Redondance DCI",
    POSOLOGY:           "Posologie",
    RENAL:              "Insuffisance rénale",
};

const DECISION_CONFIG = {
    ACCEPTED: {
        label:       "Pris en compte",
        icon:        CheckCircle2,
        style:       "bg-emerald-50 border-emerald-200 text-emerald-700 hover:bg-emerald-100",
        activeStyle: "bg-emerald-600 border-emerald-600 text-white shadow-md shadow-emerald-200",
    },
    IGNORED: {
        label:       "Ignorer",
        icon:        XCircle,
        style:       "bg-slate-50 border-slate-200 text-slate-600 hover:bg-slate-100",
        activeStyle: "bg-slate-700 border-slate-700 text-white shadow-md",
    },
    OVERRIDE: {
        label:       "Maintenir quand même",
        icon:        AlertTriangle,
        style:       "bg-amber-50 border-amber-200 text-amber-700 hover:bg-amber-100",
        activeStyle: "bg-amber-500 border-amber-500 text-white shadow-md shadow-amber-200",
    },
};

const Spinner = ({ size = 16 }) => (
    <svg style={{ width: size, height: size }} className="animate-spin" fill="none" viewBox="0 0 24 24">
        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
    </svg>
);

/* ── Composant principal ─────────────────────────────────────────────── */
export default function CdsResultPanel({ result, onClose, onNewPrescription }) {
    const [expanded,    setExpanded]    = useState({});
    const [decisions,   setDecisions]   = useState({});
    const [justifs,     setJustifs]     = useState({});
    const [submitting,  setSubmitting]  = useState(false);
    const [submitted,   setSubmitted]   = useState(false);
    const [submitError, setSubmitError] = useState("");

    const isSafe     = result.alert_count === 0;
    const alerts     = result.alerts || [];
    const majorAlerts    = alerts.filter(a => a.severity === "MAJOR");
    const moderateAlerts = alerts.filter(a => a.severity === "MODERATE");
    const minorAlerts    = alerts.filter(a => a.severity === "MINOR");

    const toggle     = (id) => setExpanded(p => ({ ...p, [id]: !p[id] }));
    const setDecision = (alertId, decision) => {
        setDecisions(p => ({ ...p, [alertId]: decision }));
        if (decision !== "OVERRIDE") setJustifs(p => { const n = { ...p }; delete n[alertId]; return n; });
    };

    const allDecided             = alerts.every(a => decisions[a.id]);
    const overridesMissingJustif = alerts.filter(a => decisions[a.id] === "OVERRIDE" && !justifs[a.id]?.trim());
    const canConfirm             = allDecided && overridesMissingJustif.length === 0;

    const confirmDecisions = async () => {
        setSubmitting(true); setSubmitError("");
        try {
            await api.post("/audit/bulk", {
                prescription_id: result.prescription_id,
                decisions: alerts.map(alert => ({
                    alert_id:        alert.id,
                    prescription_id: result.prescription_id,
                    decision:        decisions[alert.id],
                    justification:   justifs[alert.id] || null,
                })),
            });
            setSubmitted(true);
        } catch (e) {
            setSubmitError(e.response?.data?.detail || "Erreur lors de l'enregistrement de l'audit.");
        } finally { setSubmitting(false); }
    };

    /* ── Écran succès audit ──────────────────────────────────────────── */
    if (submitted) {
        return (
            <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/30 backdrop-blur-sm">
                <div className="w-full max-w-md rounded-2xl border border-slate-100 shadow-2xl bg-white overflow-hidden">
                    <div className="px-8 py-10 text-center">
                        <div className="w-16 h-16 rounded-full bg-emerald-100 flex items-center justify-center mx-auto mb-5">
                            <ClipboardCheck size={28} className="text-emerald-600" />
                        </div>
                        <h2 className="text-lg font-bold text-slate-800 mb-2">Décisions enregistrées</h2>
                        <p className="text-sm text-slate-500 mb-8">
                            {alerts.length} décision{alerts.length > 1 ? "s" : ""} loggée{alerts.length > 1 ? "s" : ""} dans le journal d'audit — prescription #{result.prescription_id}
                        </p>
                        <div className="flex gap-3 justify-center">
                            <button onClick={onNewPrescription}
                                className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold bg-blue-600 hover:bg-blue-700 text-white transition-all shadow-md shadow-blue-200">
                                <Plus size={14} /> Nouvelle prescription
                            </button>
                            <button onClick={onClose}
                                className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold text-slate-600 border border-slate-200 hover:bg-slate-50 transition-all">
                                <FileText size={14} /> Fermer
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/30 backdrop-blur-sm">
            <div className="w-full max-w-2xl max-h-[92vh] overflow-hidden rounded-2xl border border-slate-100 shadow-2xl flex flex-col bg-white">

                {/* ── Header ───────────────────────────────────────── */}
                <div className={`px-6 py-4 flex items-center justify-between
                    ${isSafe ? "bg-emerald-50 border-b border-emerald-100" : "bg-white border-b border-slate-100"}`}>
                    <div className="flex items-center gap-3">
                        {isSafe
                            ? <div className="w-9 h-9 rounded-xl bg-emerald-100 flex items-center justify-center">
                                <ShieldCheck size={18} className="text-emerald-600" />
                              </div>
                            : <div className="w-9 h-9 rounded-xl bg-red-100 flex items-center justify-center">
                                <ShieldAlert size={18} className="text-red-600" />
                              </div>}
                        <div>
                            <h2 className={`font-bold text-base ${isSafe ? "text-emerald-800" : "text-slate-800"}`}>
                                {isSafe ? "Prescription sûre" : `${result.alert_count} alerte${result.alert_count > 1 ? "s" : ""} détectée${result.alert_count > 1 ? "s" : ""}`}
                            </h2>
                            <p className="text-xs text-slate-500">
                                Prescription #{result.prescription_id} · Analyse CDS SafeRx
                            </p>
                        </div>
                    </div>
                    <button onClick={onClose} className="text-slate-400 hover:text-slate-600 transition-colors w-8 h-8 rounded-lg hover:bg-slate-100 flex items-center justify-center">
                        <X size={16} />
                    </button>
                </div>

                {/* ── Barre de comptage ─────────────────────────────── */}
                {!isSafe && (
                    <div className="px-6 py-2.5 flex items-center gap-3 border-b border-slate-100 bg-slate-50">
                        {majorAlerts.length > 0 && (
                            <span className="flex items-center gap-1.5 text-xs font-semibold text-red-700 bg-red-100 border border-red-200 px-2.5 py-1 rounded-full">
                                <Siren size={11} /> {majorAlerts.length} critique{majorAlerts.length > 1 ? "s" : ""}
                            </span>
                        )}
                        {moderateAlerts.length > 0 && (
                            <span className="flex items-center gap-1.5 text-xs font-semibold text-amber-700 bg-amber-100 border border-amber-200 px-2.5 py-1 rounded-full">
                                <TriangleAlert size={11} /> {moderateAlerts.length} modérée{moderateAlerts.length > 1 ? "s" : ""}
                            </span>
                        )}
                        {minorAlerts.length > 0 && (
                            <span className="flex items-center gap-1.5 text-xs font-semibold text-blue-700 bg-blue-100 border border-blue-200 px-2.5 py-1 rounded-full">
                                <Info size={11} /> {minorAlerts.length} mineure{minorAlerts.length > 1 ? "s" : ""}
                            </span>
                        )}
                        <span className="ml-auto text-xs text-slate-400">
                            {Object.keys(decisions).length}/{alerts.length} décidé{Object.keys(decisions).length > 1 ? "s" : ""}
                        </span>
                    </div>
                )}

                {/* ── Corps ────────────────────────────────────────── */}
                <div className="overflow-y-auto flex-1 px-4 py-4 space-y-2 bg-slate-50">
                    {isSafe ? (
                        <div className="flex flex-col items-center justify-center py-12 text-center">
                            <div className="w-16 h-16 rounded-full bg-emerald-100 flex items-center justify-center mb-4">
                                <ShieldCheck size={28} className="text-emerald-600" />
                            </div>
                            <p className="font-semibold text-slate-800 mb-1">Aucune alerte détectée</p>
                            <p className="text-slate-500 text-sm">Prescription conforme aux règles CDS SafeRx.</p>
                        </div>
                    ) : (
                        alerts.map((alert) => {
                            const cfg        = SEVERITY_CONFIG[alert.severity] || SEVERITY_CONFIG.MINOR;
                            const Icon       = cfg.icon;
                            const isOpen     = expanded[alert.id];
                            const myDecision = decisions[alert.id];

                            return (
                                <div key={alert.id}
                                    className={`rounded-xl border ${cfg.border} bg-white overflow-hidden transition-all shadow-sm`}>

                                    {/* En-tête alerte */}
                                    <button onClick={() => toggle(alert.id)}
                                        className="w-full px-4 py-3 flex items-start gap-3 text-left hover:bg-slate-50 transition-colors">
                                        <div className={`w-7 h-7 rounded-lg ${cfg.bg} border ${cfg.border} flex items-center justify-center shrink-0 mt-0.5`}>
                                            <Icon size={13} className={cfg.text} />
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-center gap-2 flex-wrap">
                                                <span className="text-sm font-semibold text-slate-800">{alert.title}</span>
                                                <span className={`text-[10px] px-1.5 py-0.5 rounded border font-semibold ${cfg.badge}`}>
                                                    {ALERT_TYPE_LABEL[alert.alert_type] || alert.alert_type}
                                                </span>
                                                {/* Badge LR */}
                                                {alert.ai_ignore_proba !== null && alert.ai_ignore_proba !== undefined && (
                                                    <span className={`text-[10px] px-1.5 py-0.5 rounded border font-medium flex items-center gap-1
                                                        ${alert.ai_ignore_proba >= 0.7
                                                            ? "bg-slate-100 text-slate-500 border-slate-200"
                                                            : "bg-purple-50 text-purple-700 border-purple-200"}`}
                                                        title={`Score IA : ${Math.round(alert.ai_ignore_proba * 100)}% de probabilité d'être ignoré`}>
                                                        <TrendingDown size={9} />
                                                        {alert.ai_ignore_proba >= 0.7
                                                            ? `Souvent ignoré (${Math.round(alert.ai_ignore_proba * 100)}%)`
                                                            : `Pertinent (${Math.round((1 - alert.ai_ignore_proba) * 100)}%)`}
                                                    </span>
                                                )}
                                                {/* Badge décision */}
                                                {myDecision && (
                                                    <span className={`text-[10px] px-1.5 py-0.5 rounded border font-semibold
                                                        ${myDecision === "ACCEPTED" ? "bg-emerald-100 text-emerald-700 border-emerald-200" :
                                                          myDecision === "OVERRIDE" ? "bg-amber-100 text-amber-700 border-amber-200" :
                                                                                       "bg-slate-100 text-slate-600 border-slate-200"}`}>
                                                        {DECISION_CONFIG[myDecision].label}
                                                    </span>
                                                )}
                                            </div>
                                        </div>
                                        <ChevronDown size={14} className={`text-slate-400 shrink-0 mt-0.5 transition-transform ${isOpen ? "rotate-180" : ""}`} />
                                    </button>

                                    {/* Détails */}
                                    {isOpen && (
                                        <div className="px-4 pb-4 border-t border-slate-100 pt-3 bg-white">
                                            {/* Détail clinique */}
                                            <p className="text-xs text-slate-600 leading-relaxed mb-3">{alert.detail}</p>

                                            {/* ── Explication RAG ──────────────────── */}
                                            {alert.rag_explanation && (
                                                <div className="mb-4 p-3 rounded-xl border border-purple-200 bg-purple-50">
                                                    <div className="flex items-center gap-1.5 mb-1.5">
                                                        <Sparkles size={11} className="text-purple-600" />
                                                        <span className="text-[10px] font-bold text-purple-700 uppercase tracking-wider">
                                                            Analyse SafeRx AI
                                                        </span>
                                                    </div>
                                                    <p className="text-xs text-purple-800 leading-relaxed">{alert.rag_explanation}</p>
                                                </div>
                                            )}

                                            {/* Décision */}
                                            <div>
                                                <p className="text-[10px] text-slate-400 uppercase tracking-wider mb-2 font-semibold">Votre décision</p>
                                                <div className="flex gap-2 flex-wrap">
                                                    {Object.entries(DECISION_CONFIG).map(([key, dcfg]) => {
                                                        const DIcon    = dcfg.icon;
                                                        const isActive = myDecision === key;
                                                        return (
                                                            <button key={key} onClick={() => setDecision(alert.id, key)}
                                                                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-semibold transition-all
                                                                    ${isActive ? dcfg.activeStyle : dcfg.style}`}>
                                                                <DIcon size={12} /> {dcfg.label}
                                                            </button>
                                                        );
                                                    })}
                                                </div>

                                                {/* Justification */}
                                                {(myDecision === "OVERRIDE" || myDecision === "IGNORED") && (
                                                    <div className="mt-3">
                                                        <textarea
                                                            value={justifs[alert.id] || ""}
                                                            onChange={e => setJustifs(p => ({ ...p, [alert.id]: e.target.value }))}
                                                            placeholder={myDecision === "OVERRIDE"
                                                                ? "Justification obligatoire (contexte clinique, bénéfice/risque…)"
                                                                : "Justification facultative…"}
                                                            rows={2}
                                                            className={`w-full bg-slate-50 border rounded-xl px-3 py-2 text-xs text-slate-700
                                                                placeholder-slate-400 outline-none resize-none transition-colors
                                                                ${myDecision === "OVERRIDE" && !justifs[alert.id]?.trim()
                                                                    ? "border-amber-300 focus:border-amber-400 focus:ring-2 focus:ring-amber-100"
                                                                    : "border-slate-200 focus:border-blue-300 focus:ring-2 focus:ring-blue-50"}`}
                                                        />
                                                        {myDecision === "OVERRIDE" && !justifs[alert.id]?.trim() && (
                                                            <p className="text-[10px] text-amber-600 mt-1 flex items-center gap-1 font-medium">
                                                                <AlertTriangle size={9} /> Justification requise pour un override
                                                            </p>
                                                        )}
                                                    </div>
                                                )}

                                                {/* Feedback validation sémantique */}
                                                {alert.justification_valid && (
                                                    <div className={`mt-3 px-3 py-2 rounded-xl border text-xs flex items-start gap-2
                                                        ${alert.justification_valid === "valid"
                                                            ? "bg-emerald-50 border-emerald-200 text-emerald-700"
                                                            : "bg-red-50 border-red-200 text-red-700"}`}>
                                                        {alert.justification_valid === "valid"
                                                            ? <CheckCircle2 size={11} className="shrink-0 mt-0.5" />
                                                            : <AlertTriangle size={11} className="shrink-0 mt-0.5" />}
                                                        <span>
                                                            <strong>{alert.justification_valid === "valid" ? "Justification valide" : "Justification insuffisante"}</strong>
                                                            {alert.justification_feedback && ` — ${alert.justification_feedback}`}
                                                        </span>
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    )}
                                </div>
                            );
                        })
                    )}
                </div>

                {/* ── Footer ───────────────────────────────────────── */}
                <div className="px-6 py-4 border-t border-slate-100 bg-white">
                    {submitError && (
                        <div className="mb-3 flex items-center gap-2 bg-red-50 border border-red-200 rounded-xl px-3 py-2 text-xs text-red-700">
                            <AlertCircle size={12} /> {submitError}
                        </div>
                    )}

                    {isSafe ? (
                        <div className="flex gap-3 justify-end">
                            <button onClick={onNewPrescription}
                                className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold text-slate-600 border border-slate-200 hover:bg-slate-50 transition-all">
                                <Plus size={14} /> Nouvelle prescription
                            </button>
                            <button onClick={onClose}
                                className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold bg-blue-600 hover:bg-blue-700 text-white transition-all shadow-md shadow-blue-200">
                                <FileText size={14} /> Fermer
                            </button>
                        </div>
                    ) : (
                        <div className="flex items-center justify-between gap-4">
                            <p className="text-xs text-slate-400">
                                {!allDecided
                                    ? "Décidez de chaque alerte avant de confirmer"
                                    : overridesMissingJustif.length > 0
                                        ? `Justification manquante pour ${overridesMissingJustif.length} override${overridesMissingJustif.length > 1 ? "s" : ""}`
                                        : `Prêt à enregistrer ${alerts.length} décision${alerts.length > 1 ? "s" : ""}`}
                            </p>
                            <div className="flex gap-2 shrink-0">
                                <button onClick={onNewPrescription}
                                    className="flex items-center gap-2 px-3 py-2 rounded-xl text-sm font-semibold text-slate-600 border border-slate-200 hover:bg-slate-50 transition-all">
                                    <Plus size={13} /> Nouvelle
                                </button>
                                <button onClick={confirmDecisions}
                                    disabled={!canConfirm || submitting}
                                    className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold bg-blue-600 hover:bg-blue-700 text-white transition-all disabled:opacity-40 disabled:cursor-not-allowed shadow-md shadow-blue-200">
                                    {submitting
                                        ? <><Spinner size={13} /> Enregistrement…</>
                                        : <><Send size={13} /> Confirmer les décisions</>}
                                </button>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}