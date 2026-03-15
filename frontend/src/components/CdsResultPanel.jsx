/**
 * SafeRx AI — CdsResultPanel avec Audit Trail
 * ─────────────────────────────────────────────
 * Remplace le composant CdsResultPanel dans DoctorDashboard.jsx
 *
 * Flux utilisateur :
 *   1. Prescription soumise → modal s'ouvre avec les alertes
 *   2. Pour chaque alerte, le médecin choisit : ACCEPTED / IGNORED / OVERRIDE
 *   3. OVERRIDE → champ justification obligatoire
 *   4. Bouton "Confirmer les décisions" → POST /audit/bulk
 *   5. Toutes les décisions loggées → modal se ferme
 *
 * Import dans DoctorDashboard.jsx :
 *   import CdsResultPanel from "./CdsResultPanel";
 */
import { useState } from "react";
import {
    ShieldAlert, ShieldCheck, X, CheckCircle2,
    XCircle, AlertTriangle, Info, ChevronDown,
    Siren, TriangleAlert, Send, FileText, Plus,
    AlertCircle, ClipboardCheck, Sparkles, TrendingDown
} from "lucide-react";
import api from "../api/api";

/* ── Config sévérité ─────────────────────────────────────────────────────── */
const SEVERITY_CONFIG = {
    MAJOR:    {
        label: "Critique",
        bg: "bg-red-950/60",
        border: "border-red-500/40",
        text: "text-red-300",
        badge: "bg-red-500/20 text-red-300 border-red-500/30",
        icon: Siren,
    },
    MODERATE: {
        label: "Modérée",
        bg: "bg-amber-950/60",
        border: "border-amber-500/40",
        text: "text-amber-300",
        badge: "bg-amber-500/20 text-amber-300 border-amber-500/30",
        icon: TriangleAlert,
    },
    MINOR: {
        label: "Mineure",
        bg: "bg-blue-950/60",
        border: "border-blue-500/40",
        text: "text-blue-300",
        badge: "bg-blue-500/20 text-blue-300 border-blue-500/30",
        icon: Info,
    },
};

const ALERT_TYPE_LABEL = {
    INTERACTION:        "Interaction",
    ALLERGY:            "Allergie",
    CONTRA_INDICATION:  "Contre-indication",
    REDUNDANT_DCI:      "Redondance DCI",
    POSOLOGY:           "Posologie",
};

/* ── Décisions ───────────────────────────────────────────────────────────── */
const DECISION_CONFIG = {
    ACCEPTED: {
        label: "Pris en compte",
        icon: CheckCircle2,
        style: "bg-emerald-500/10 border-emerald-500/30 text-emerald-300 hover:bg-emerald-500/20",
        activeStyle: "bg-emerald-500/25 border-emerald-400/50 text-emerald-200 ring-1 ring-emerald-500/30",
    },
    IGNORED: {
        label: "Ignorer",
        icon: XCircle,
        style: "bg-slate-700/30 border-slate-600/30 text-slate-400 hover:bg-slate-700/50",
        activeStyle: "bg-slate-600/40 border-slate-500/50 text-slate-200 ring-1 ring-slate-500/30",
    },
    OVERRIDE: {
        label: "Maintenir quand même",
        icon: AlertTriangle,
        style: "bg-amber-500/10 border-amber-500/30 text-amber-400 hover:bg-amber-500/20",
        activeStyle: "bg-amber-500/20 border-amber-400/50 text-amber-300 ring-1 ring-amber-500/30",
    },
};

const Spinner = ({ size = 16 }) => (
    <svg style={{ width: size, height: size }} className="animate-spin" fill="none" viewBox="0 0 24 24">
        <circle className="opacity-20" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
        <path className="opacity-80" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
    </svg>
);

/* ── Composant principal ─────────────────────────────────────────────────── */
export default function CdsResultPanel({ result, onClose, onNewPrescription }) {
    const [expanded,     setExpanded]     = useState({});
    const [decisions,    setDecisions]    = useState({});     // alertId → "ACCEPTED" | "IGNORED" | "OVERRIDE"
    const [justifs,      setJustifs]      = useState({});     // alertId → string
    const [submitting,   setSubmitting]   = useState(false);
    const [submitted,    setSubmitted]    = useState(false);
    const [submitError,  setSubmitError]  = useState("");

    const isSafe     = result.alert_count === 0;
    const alerts     = result.alerts || [];
    const majorAlerts    = alerts.filter(a => a.severity === "MAJOR");
    const moderateAlerts = alerts.filter(a => a.severity === "MODERATE");
    const minorAlerts    = alerts.filter(a => a.severity === "MINOR");

    const toggle = (id) => setExpanded(p => ({ ...p, [id]: !p[id] }));

    const setDecision = (alertId, decision) => {
        setDecisions(p => ({ ...p, [alertId]: decision }));
        // Reset justif si on passe d'OVERRIDE à autre chose
        if (decision !== "OVERRIDE") {
            setJustifs(p => { const n = { ...p }; delete n[alertId]; return n; });
        }
    };

    /* ── Validation avant confirmation ──────────────────────────────────── */
    const allDecided = alerts.every(a => decisions[a.id]);
    const overridesMissingJustif = alerts.filter(
        a => decisions[a.id] === "OVERRIDE" && !(justifs[a.id]?.trim())
    );
    const canConfirm = allDecided && overridesMissingJustif.length === 0;

    /* ── Soumettre l'audit bulk ──────────────────────────────────────────── */
    const confirmDecisions = async () => {
        setSubmitting(true);
        setSubmitError("");
        try {
            const payload = {
                prescription_id: result.prescription_id,
                decisions: alerts.map(alert => ({
                    alert_id:       alert.id,
                    prescription_id: result.prescription_id,
                    decision:       decisions[alert.id],
                    justification:  justifs[alert.id] || null,
                })),
            };
            await api.post("/audit/bulk", payload);
            setSubmitted(true);
        } catch (e) {
            setSubmitError(
                e.response?.data?.detail || "Erreur lors de l'enregistrement de l'audit."
            );
        } finally {
            setSubmitting(false);
        }
    };

    /* ── Vue "succès audit" ─────────────────────────────────────────────── */
    if (submitted) {
        return (
            <div className="fixed inset-0 z-50 flex items-center justify-center p-4"
                 style={{ background: "rgba(2,8,20,0.85)", backdropFilter: "blur(8px)" }}>
                <div className="w-full max-w-md rounded-2xl border border-emerald-700/30 overflow-hidden"
                     style={{ background: "#0d1520" }}>
                    <div className="px-8 py-10 text-center">
                        <div className="w-16 h-16 rounded-full bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center mx-auto mb-5">
                            <ClipboardCheck size={28} className="text-emerald-400" />
                        </div>
                        <h2 className="text-lg font-semibold text-slate-100 mb-2">
                            Décisions enregistrées
                        </h2>
                        <p className="text-sm text-slate-400 mb-8">
                            {alerts.length} décision{alerts.length > 1 ? "s" : ""} loggée{alerts.length > 1 ? "s" : ""}
                            dans le journal d'audit — prescription #{result.prescription_id}
                        </p>
                        <div className="flex gap-3 justify-center">
                            <button
                                onClick={onNewPrescription}
                                className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-medium bg-blue-600 hover:bg-blue-500 text-white transition-all">
                                <Plus size={14} /> Nouvelle prescription
                            </button>
                            <button
                                onClick={onClose}
                                className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-medium text-slate-300 border border-slate-600/50 hover:border-slate-500/70 transition-all">
                                <FileText size={14} /> Fermer
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4"
             style={{ background: "rgba(2,8,20,0.85)", backdropFilter: "blur(8px)" }}>
            <div className="w-full max-w-2xl max-h-[92vh] overflow-hidden rounded-2xl border border-slate-700/60 flex flex-col"
                 style={{ background: "#0d1520" }}>

                {/* ── Header ───────────────────────────────────────────── */}
                <div className={`px-6 py-4 flex items-center justify-between border-b
                    ${isSafe ? "border-emerald-700/40 bg-emerald-950/30" : "border-red-700/30 bg-red-950/20"}`}>
                    <div className="flex items-center gap-3">
                        {isSafe
                            ? <ShieldCheck size={22} className="text-emerald-400" />
                            : <ShieldAlert size={22} className="text-red-400" />}
                        <div>
                            <h2 className={`font-semibold text-base ${isSafe ? "text-emerald-300" : "text-red-300"}`}>
                                {isSafe
                                    ? "Prescription sûre"
                                    : `${result.alert_count} alerte${result.alert_count > 1 ? "s" : ""} détectée${result.alert_count > 1 ? "s" : ""}`}
                            </h2>
                            <p className="text-xs text-slate-500 mt-0.5">
                                Prescription #{result.prescription_id} · Analyse CDS SafeRx
                            </p>
                        </div>
                    </div>
                    <button onClick={onClose}
                            className="text-slate-500 hover:text-slate-300 transition-colors">
                        <X size={18} />
                    </button>
                </div>

                {/* ── Barre de comptage ─────────────────────────────────── */}
                {!isSafe && (
                    <div className="px-6 py-2.5 flex items-center gap-3 border-b border-slate-700/40 bg-slate-900/20">
                        {majorAlerts.length > 0 && (
                            <span className="flex items-center gap-1.5 text-xs font-medium text-red-300 bg-red-500/10 border border-red-500/20 px-2.5 py-1 rounded-full">
                                <Siren size={11} /> {majorAlerts.length} critique{majorAlerts.length > 1 ? "s" : ""}
                            </span>
                        )}
                        {moderateAlerts.length > 0 && (
                            <span className="flex items-center gap-1.5 text-xs font-medium text-amber-300 bg-amber-500/10 border border-amber-500/20 px-2.5 py-1 rounded-full">
                                <TriangleAlert size={11} /> {moderateAlerts.length} modérée{moderateAlerts.length > 1 ? "s" : ""}
                            </span>
                        )}
                        {minorAlerts.length > 0 && (
                            <span className="flex items-center gap-1.5 text-xs font-medium text-blue-300 bg-blue-500/10 border border-blue-500/20 px-2.5 py-1 rounded-full">
                                <Info size={11} /> {minorAlerts.length} mineure{minorAlerts.length > 1 ? "s" : ""}
                            </span>
                        )}
                        {/* Progression des décisions */}
                        <span className="ml-auto text-xs text-slate-500">
                            {Object.keys(decisions).length}/{alerts.length} décidé{Object.keys(decisions).length > 1 ? "s" : ""}
                        </span>
                    </div>
                )}

                {/* ── Corps ────────────────────────────────────────────── */}
                <div className="overflow-y-auto flex-1 px-4 py-4 space-y-3">
                    {isSafe ? (
                        <div className="flex flex-col items-center justify-center py-12 text-center">
                            <div className="w-16 h-16 rounded-full bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center mb-4">
                                <ShieldCheck size={28} className="text-emerald-400" />
                            </div>
                            <p className="text-emerald-300 font-medium mb-1">Aucune alerte détectée</p>
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
                                     className={`rounded-xl border ${cfg.border} ${cfg.bg} overflow-hidden transition-all`}>

                                    {/* En-tête alerte */}
                                    <button
                                        onClick={() => toggle(alert.id)}
                                        className="w-full px-4 py-3 flex items-start gap-3 text-left">
                                        <Icon size={15} className={`${cfg.text} mt-0.5 shrink-0`} />
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-center gap-2 flex-wrap">
                                                <span className={`text-sm font-medium ${cfg.text}`}>
                                                    {alert.title}
                                                </span>
                                                <span className={`text-[10px] px-1.5 py-0.5 rounded border font-medium ${cfg.badge}`}>
                                                    {ALERT_TYPE_LABEL[alert.alert_type] || alert.alert_type}
                                                </span>
                                                {/* Badge LR — probabilité d'ignorance */}
                                                {alert.ai_ignore_proba !== null &&
                                                 alert.ai_ignore_proba !== undefined && (
                                                    <span className={`text-[10px] px-1.5 py-0.5 rounded border font-medium flex items-center gap-1
                                                        ${alert.ai_ignore_proba >= 0.7
                                                            ? "bg-slate-700/40 text-slate-400 border-slate-600/30"   // probablement ignoré
                                                            : "bg-violet-500/10 text-violet-300 border-violet-500/20" // probablement pris en compte
                                                        }`}
                                                        title={`Score IA : ${Math.round(alert.ai_ignore_proba * 100)}% de probabilité d'être ignoré`}>
                                                        <TrendingDown size={9} />
                                                        {alert.ai_ignore_proba >= 0.7
                                                            ? `Souvent ignoré (${Math.round(alert.ai_ignore_proba * 100)}%)`
                                                            : `Pertinent (${Math.round((1 - alert.ai_ignore_proba) * 100)}%)`}
                                                    </span>
                                                )}
                                                {/* Badge décision si déjà choisie */}
                                                {myDecision && (
                                                    <span className={`text-[10px] px-1.5 py-0.5 rounded border font-medium
                                                        ${myDecision === "ACCEPTED" ? "bg-emerald-500/15 text-emerald-300 border-emerald-500/25" :
                                                          myDecision === "OVERRIDE" ? "bg-amber-500/15 text-amber-300 border-amber-500/25" :
                                                                                       "bg-slate-600/30 text-slate-400 border-slate-500/25"}`}>
                                                        {DECISION_CONFIG[myDecision].label}
                                                    </span>
                                                )}
                                            </div>
                                        </div>
                                        <ChevronDown size={13}
                                            className={`text-slate-500 shrink-0 mt-0.5 transition-transform ${isOpen ? "rotate-180" : ""}`} />
                                    </button>

                                    {/* Détails + décision */}
                                    {isOpen && (
                                        <div className="px-4 pb-4 border-t border-white/5 pt-3">
                                            {/* Texte clinique */}
                                            <p className="text-xs text-slate-400 leading-relaxed mb-3">
                                                {alert.detail}
                                            </p>

                                            {/* ── Explication RAG ──────────────────── */}
                                            {alert.rag_explanation && (
                                                <div className="mb-4 p-3 rounded-lg border border-violet-500/20 bg-violet-950/30">
                                                    <div className="flex items-center gap-1.5 mb-1.5">
                                                        <Sparkles size={11} className="text-violet-400" />
                                                        <span className="text-[10px] font-semibold text-violet-400 uppercase tracking-wider">
                                                            Analyse SafeRx AI
                                                        </span>
                                                    </div>
                                                    <p className="text-xs text-violet-200 leading-relaxed">
                                                        {alert.rag_explanation}
                                                    </p>
                                                </div>
                                            )}

                                            {/* Boutons de décision */}
                                            <div className="space-y-2">
                                                <p className="text-[10px] text-slate-500 uppercase tracking-wider mb-2">
                                                    Votre décision
                                                </p>
                                                <div className="flex gap-2 flex-wrap">
                                                    {Object.entries(DECISION_CONFIG).map(([key, cfg]) => {
                                                        const DIcon = cfg.icon;
                                                        const isActive = myDecision === key;
                                                        return (
                                                            <button
                                                                key={key}
                                                                onClick={() => setDecision(alert.id, key)}
                                                                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-medium transition-all
                                                                    ${isActive ? cfg.activeStyle : cfg.style}`}>
                                                                <DIcon size={12} />
                                                                {cfg.label}
                                                            </button>
                                                        );
                                                    })}
                                                </div>

                                                {/* Justification (OVERRIDE obligatoire, IGNORED optionnel) */}
                                                {(myDecision === "OVERRIDE" || myDecision === "IGNORED") && (
                                                    <div className="mt-3">
                                                        <textarea
                                                            value={justifs[alert.id] || ""}
                                                            onChange={e => setJustifs(p => ({ ...p, [alert.id]: e.target.value }))}
                                                            placeholder={
                                                                myDecision === "OVERRIDE"
                                                                    ? "Justification obligatoire (contexte clinique, bénéfice/risque…)"
                                                                    : "Justification facultative…"
                                                            }
                                                            rows={2}
                                                            className={`w-full bg-slate-900/60 border rounded-lg px-3 py-2 text-xs text-slate-300
                                                                placeholder-slate-600 outline-none resize-none transition-colors
                                                                ${myDecision === "OVERRIDE" && !justifs[alert.id]?.trim()
                                                                    ? "border-amber-500/40 focus:border-amber-400/60"
                                                                    : "border-slate-600/40 focus:border-slate-500/60"}`}
                                                        />
                                                        {myDecision === "OVERRIDE" && !justifs[alert.id]?.trim() && (
                                                            <p className="text-[10px] text-amber-400 mt-1 flex items-center gap-1">
                                                                <AlertTriangle size={9} /> Justification requise pour un override
                                                            </p>
                                                        )}
                                                        {/* Hint pédagogique pour guider le médecin */}
                                                        {myDecision === "OVERRIDE" && justifs[alert.id]?.trim().length > 0 &&
                                                         justifs[alert.id].trim().length < 10 && (
                                                            <p className="text-[10px] text-slate-500 mt-1 flex items-center gap-1">
                                                                <Info size={9} /> Précisez le contexte clinique (bénéfice/risque, adaptation posologique…)
                                                            </p>
                                                        )}
                                                    </div>
                                                )}

                                                {/* ── Feedback validation sémantique (post-soumission) ── */}
                                                {alert.justification_valid && (
                                                    <div className={`mt-3 px-3 py-2 rounded-lg border text-xs flex items-start gap-2
                                                        ${alert.justification_valid === "valid"
                                                            ? "bg-emerald-950/40 border-emerald-500/25 text-emerald-300"
                                                            : "bg-red-950/40 border-red-500/25 text-red-300"}`}>
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

                {/* ── Footer ───────────────────────────────────────────── */}
                <div className="px-6 py-4 border-t border-slate-700/40 bg-slate-900/20">

                    {submitError && (
                        <div className="mb-3 px-3 py-2 rounded-lg bg-red-950/40 border border-red-500/30 text-xs text-red-300 flex items-center gap-2">
                            <AlertCircle size={12} /> {submitError}
                        </div>
                    )}

                    {isSafe ? (
                        /* Prescription safe → pas d'audit nécessaire */
                        <div className="flex gap-3 justify-end">
                            <button
                                onClick={onNewPrescription}
                                className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium text-slate-300 border border-slate-600/50 hover:border-slate-500/70 transition-all">
                                <Plus size={14} /> Nouvelle prescription
                            </button>
                            <button
                                onClick={onClose}
                                className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium bg-blue-600 hover:bg-blue-500 text-white transition-all">
                                <FileText size={14} /> Fermer
                            </button>
                        </div>
                    ) : (
                        /* Alertes → confirmer les décisions */
                        <div className="flex items-center justify-between gap-4">
                            <p className="text-xs text-slate-500">
                                {!allDecided
                                    ? `Décidez de chaque alerte avant de confirmer`
                                    : overridesMissingJustif.length > 0
                                        ? `Justification manquante pour ${overridesMissingJustif.length} override${overridesMissingJustif.length > 1 ? "s" : ""}`
                                        : `Prêt à enregistrer ${alerts.length} décision${alerts.length > 1 ? "s" : ""}`}
                            </p>
                            <div className="flex gap-2 shrink-0">
                                <button
                                    onClick={onNewPrescription}
                                    className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium text-slate-400 border border-slate-700/50 hover:text-slate-300 transition-all">
                                    <Plus size={13} /> Nouvelle
                                </button>
                                <button
                                    onClick={confirmDecisions}
                                    disabled={!canConfirm || submitting}
                                    className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium bg-blue-600 hover:bg-blue-500 text-white transition-all disabled:opacity-40 disabled:cursor-not-allowed">
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