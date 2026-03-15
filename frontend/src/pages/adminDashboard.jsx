import { useState, useEffect } from "react";
import {
    ShieldCheck, Users, LayoutDashboard, ClipboardList,
    LogOut, Plus, Search, CheckCircle2, AlertCircle,
    XCircle, Eye, EyeOff, ArrowRight, Activity, Stethoscope,
    ChevronDown, Bell, UserCheck, UserX, Pill, TrendingUp,
    Clock, Filter, MoreVertical, Mail, Lock, RefreshCw,
    AlertTriangle, BarChart3, Shield, Siren
} from "lucide-react";
import authService from "../services/AuthService";
import api from "../api/api";

/* ─────────────────────────────────────────────────────────
   HELPERS — mapping données API → format UI
───────────────────────────────────────────────────────── */
// Décision backend → label action UI
const decisionToAction = {
    ACCEPTED: "ALERT_ACCEPTED",
    IGNORED:  "ALERT_IGNORED",
    OVERRIDE: "OVERRIDE",
};

const formatDate = (iso) => {
    if (!iso) return "—";
    const d = new Date(iso);
    return d.toISOString().slice(0, 10);
};

const formatDateTime = (iso) => {
    if (!iso) return { date: "—", time: "—" };
    const d = new Date(iso);
    return {
        date: d.toLocaleDateString("fr-FR"),
        time: d.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit", second: "2-digit" }),
    };
};

// TOP_ERRORS reste statique (nécessiterait un endpoint dédié)
const TOP_ERRORS = [
    { drug: "Warfarine",    count: 24, type: "Interaction" },
    { drug: "Métformine",   count: 18, type: "Posologie rénale" },
    { drug: "Digoxine",     count: 11, type: "Contre-indication" },
    { drug: "Amoxicilline", count:  9, type: "Redondance DCI" },
    { drug: "Clopidogrel",  count:  7, type: "Interaction AVK" },
];

/* ─────────────────────────────────────────────────────────
   HELPERS
───────────────────────────────────────────────────────── */
const roleLabel = { doctor: "Médecin", pharmacist: "Pharmacien", admin: "Administrateur" };
const roleColor = { doctor: "bg-blue-100 text-blue-700", pharmacist: "bg-emerald-100 text-emerald-700", admin: "bg-purple-100 text-purple-700" };

const severityColor = {
    MAJOR:    "text-red-600 bg-red-50 border-red-200",
    MODERATE: "text-amber-600 bg-amber-50 border-amber-200",
    MINOR:    "text-blue-600 bg-blue-50 border-blue-200",
    NONE:     "text-slate-500 bg-slate-50 border-slate-200",
};
const actionIcon = {
    ALERT_ACCEPTED:  <CheckCircle2 size={13} className="text-emerald-500" />,
    OVERRIDE:        <AlertTriangle size={13} className="text-amber-500" />,
    ALERT_IGNORED:   <XCircle size={13} className="text-red-400" />,
    PRESCRIPTION_OK: <ShieldCheck size={13} className="text-blue-400" />,
};

const Spinner = () => (
    <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
    </svg>
);

/* ─────────────────────────────────────────────────────────
   SIDEBAR NAV ITEMS
───────────────────────────────────────────────────────── */
const NAV = [
    { id: "overview",  icon: LayoutDashboard, label: "Vue d'ensemble" },
    { id: "users",     icon: Users,           label: "Utilisateurs"   },
    { id: "audit",     icon: ClipboardList,   label: "Audit Trail"    },
];

/* ─────────────────────────────────────────────────────────
   SUB-COMPONENT — KPI CARD
───────────────────────────────────────────────────────── */
const KpiCard = ({ icon, label, value, sub, accent, trend }) => (
    <div className="bg-white rounded-2xl border border-slate-100 shadow-sm shadow-slate-100 p-5 flex flex-col gap-3">
        <div className="flex items-center justify-between">
            <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${accent}`}>
                {icon}
            </div>
            {trend !== undefined && (
                <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${trend >= 0 ? "bg-emerald-50 text-emerald-600" : "bg-red-50 text-red-500"}`}>
                    {trend >= 0 ? "+" : ""}{trend}%
                </span>
            )}
        </div>
        <div>
            <p className="text-2xl font-bold text-slate-800">{value}</p>
            <p className="text-xs text-slate-500 mt-0.5">{label}</p>
            {sub && <p className="text-xs text-slate-400 mt-1">{sub}</p>}
        </div>
    </div>
);

/* ─────────────────────────────────────────────────────────
   VIEW — OVERVIEW
───────────────────────────────────────────────────────── */
const OverviewView = ({ stats }) => (
    <div className="flex flex-col gap-6">
        {/* KPI Grid */}
        <div className="grid grid-cols-2 xl:grid-cols-4 gap-4">
            <KpiCard icon={<Users size={18} className="text-blue-600" />}        label="Utilisateurs actifs"   value={stats.totalUsers}            accent="bg-blue-50"    trend={8}   />
            <KpiCard icon={<Pill size={18} className="text-indigo-600" />}        label="Prescriptions / 24h"   value={stats.prescriptionsToday}    accent="bg-indigo-50"  trend={3}   />
            <KpiCard icon={<Siren size={18} className="text-amber-600" />}        label="Alertes déclenchées"   value={stats.alertsToday}           accent="bg-amber-50"   trend={-5}  />
            <KpiCard icon={<ShieldCheck size={18} className="text-emerald-600" />}label="Taux de conformité"   value={`${stats.complianceRate}%`}  accent="bg-emerald-50" trend={1.2} />
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
            {/* Top erreurs */}
            <div className="xl:col-span-2 bg-white rounded-2xl border border-slate-100 shadow-sm shadow-slate-100 p-5">
                <div className="flex items-center gap-2 mb-4">
                    <BarChart3 size={16} className="text-slate-400" />
                    <h3 className="font-semibold text-slate-700 text-sm">Top 5 — Alertes les plus fréquentes</h3>
                </div>
                <div className="flex flex-col gap-2.5">
                    {TOP_ERRORS.map((item, i) => (
                        <div key={item.drug} className="flex items-center gap-3">
                            <span className="text-xs font-bold text-slate-400 w-4">{i + 1}</span>
                            <div className="flex-1">
                                <div className="flex justify-between text-xs mb-1">
                                    <span className="font-semibold text-slate-700">{item.drug}</span>
                                    <span className="text-slate-400">{item.type} · <strong className="text-slate-600">{item.count}</strong></span>
                                </div>
                                <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
                                    <div
                                        className="h-full rounded-full bg-blue-500 transition-all duration-700"
                                        style={{ width: `${(item.count / TOP_ERRORS[0].count) * 100}%` }}
                                    />
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            {/* Système */}
            <div className="bg-white rounded-2xl border border-slate-100 shadow-sm shadow-slate-100 p-5 flex flex-col gap-4">
                <div className="flex items-center gap-2 mb-1">
                    <Activity size={16} className="text-slate-400" />
                    <h3 className="font-semibold text-slate-700 text-sm">Performance système</h3>
                </div>
                {[
                    { label: "Temps de réponse moyen", value: `${stats.avgResponseMs} ms`, ok: stats.avgResponseMs < 300, target: "< 300 ms" },
                    { label: "Taux d'override",         value: `${stats.overrideRate}%`,  ok: stats.overrideRate < 20,   target: "< 20 %" },
                    { label: "Conformité prescriptions", value: `${stats.complianceRate}%`,ok: stats.complianceRate > 80, target: "> 80 %" },
                ].map(({ label, value, ok, target }) => (
                    <div key={label} className="flex items-start justify-between gap-2">
                        <div>
                            <p className="text-xs font-medium text-slate-600">{label}</p>
                            <p className="text-sm font-bold text-slate-800 mt-0.5">{value}</p>
                            <p className="text-xs text-slate-400">Objectif : {target}</p>
                        </div>
                        <div className={`mt-0.5 w-6 h-6 rounded-full flex items-center justify-center shrink-0 ${ok ? "bg-emerald-50" : "bg-red-50"}`}>
                            {ok
                                ? <CheckCircle2 size={14} className="text-emerald-500" />
                                : <AlertCircle  size={14} className="text-red-500" />
                            }
                        </div>
                    </div>
                ))}

                <div className="mt-auto pt-4 border-t border-slate-100">
                    <div className="flex items-center gap-2">
                        <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                        <span className="text-xs text-slate-500">API FastAPI · opérationnelle</span>
                    </div>
                </div>
            </div>
        </div>
    </div>
);

/* ─────────────────────────────────────────────────────────
   VIEW — USERS
───────────────────────────────────────────────────────── */
const UsersView = () => {
    const [users, setUsers]               = useState([]);
    const [search, setSearch]             = useState("");
    const [roleFilter, setRoleFilter]     = useState("all");
    const [showForm, setShowForm]         = useState(false);
    const [formData, setFormData]         = useState({ first_name: "", last_name: "", email: "", role: "doctor" });
    const [formError, setFormError]       = useState("");
    const [formSuccess, setFormSuccess]   = useState("");
    const [isLoading, setIsLoading]       = useState(false);
    const [loadingUsers, setLoadingUsers] = useState(true);

    // ✅ Charger les vrais utilisateurs depuis l'API
    useEffect(() => {
        const fetchUsers = async () => {
            setLoadingUsers(true);
            try {
                const res = await api.get("/account/users");
                setUsers(res.data || []);
            } catch {
                setUsers([]);
            } finally {
                setLoadingUsers(false);
            }
        };
        fetchUsers();
    }, []);

    const filtered = users.filter(u => {
        const matchSearch = `${u.first_name} ${u.last_name} ${u.email}`.toLowerCase().includes(search.toLowerCase());
        const matchRole   = roleFilter === "all" || u.role === roleFilter;
        return matchSearch && matchRole;
    });

    const handleCreate = async (e) => {
        e.preventDefault();
        setFormError(""); setFormSuccess("");
        setIsLoading(true);
        try {
            // ✅ Vrai appel API
            const res = await api.post("/account/create", formData);
            setUsers(prev => [res.data, ...prev]);
            setFormSuccess(`Compte créé. Un email a été envoyé à ${formData.email}.`);
            setFormData({ first_name: "", last_name: "", email: "", role: "doctor" });
            setTimeout(() => { setFormSuccess(""); setShowForm(false); }, 3000);
        } catch (err) {
            setFormError(err.response?.data?.detail || "Une erreur est survenue.");
        } finally {
            setIsLoading(false);
        }
    };

    // ✅ toggleActive sans appel API dédié pour l'instant (UI optimiste)
    const toggleActive = (id) =>
        setUsers(prev => prev.map(u => u.id === id ? { ...u, is_active: !u.is_active } : u));

    return (
        <div className="flex flex-col gap-5">
            {/* Header actions */}
            <div className="flex flex-col sm:flex-row gap-3 items-start sm:items-center justify-between">
                <div className="flex gap-2 flex-wrap">
                    {/* Search */}
                    <div className="relative">
                        <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
                        <input
                            className="pl-9 pr-4 py-2 border border-slate-200 rounded-xl bg-white text-sm text-slate-700 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent w-52"
                            placeholder="Rechercher…"
                            value={search}
                            onChange={e => setSearch(e.target.value)}
                        />
                    </div>
                    {/* Role filter */}
                    <div className="relative">
                        <Filter size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
                        <select
                            className="pl-9 pr-4 py-2 border border-slate-200 rounded-xl bg-white text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500 appearance-none cursor-pointer"
                            value={roleFilter}
                            onChange={e => setRoleFilter(e.target.value)}
                        >
                            <option value="all">Tous les rôles</option>
                            <option value="doctor">Médecins</option>
                            <option value="pharmacist">Pharmaciens</option>
                        </select>
                    </div>
                </div>
                <button
                    onClick={() => { setShowForm(f => !f); setFormError(""); setFormSuccess(""); }}
                    className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold px-4 py-2 rounded-xl shadow-md shadow-blue-200 transition-all shrink-0"
                >
                    <Plus size={15} />
                    Créer un compte
                </button>
            </div>

            {/* Create form */}
            {showForm && (
                <div className="bg-white rounded-2xl border border-slate-100 shadow-sm shadow-slate-100 p-6">
                    <div className="flex items-center gap-2 mb-5">
                        <div className="w-8 h-8 rounded-xl bg-blue-50 flex items-center justify-center">
                            <Plus size={15} className="text-blue-600" />
                        </div>
                        <h3 className="font-semibold text-slate-700">Nouveau compte</h3>
                    </div>

                    <form onSubmit={handleCreate} className="flex flex-col gap-4">
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                            {/* Prénom */}
                            <div className="flex flex-col gap-1.5">
                                <label className="text-xs font-semibold text-slate-600 uppercase tracking-wide">Prénom</label>
                                <input
                                    className="px-3 py-2.5 border border-slate-200 rounded-xl bg-slate-50 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white transition-all"
                                    placeholder="Youssef"
                                    value={formData.first_name}
                                    onChange={e => setFormData(p => ({ ...p, first_name: e.target.value }))}
                                    required
                                />
                            </div>
                            {/* Nom */}
                            <div className="flex flex-col gap-1.5">
                                <label className="text-xs font-semibold text-slate-600 uppercase tracking-wide">Nom</label>
                                <input
                                    className="px-3 py-2.5 border border-slate-200 rounded-xl bg-slate-50 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white transition-all"
                                    placeholder="Benali"
                                    value={formData.last_name}
                                    onChange={e => setFormData(p => ({ ...p, last_name: e.target.value }))}
                                    required
                                />
                            </div>
                        </div>

                        {/* Email */}
                        <div className="flex flex-col gap-1.5">
                            <label className="text-xs font-semibold text-slate-600 uppercase tracking-wide">Email professionnel</label>
                            <div className="relative">
                                <Mail size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
                                <input
                                    type="email"
                                    className="w-full pl-9 pr-4 py-2.5 border border-slate-200 rounded-xl bg-slate-50 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white transition-all"
                                    placeholder="docteur@hopital.ma"
                                    value={formData.email}
                                    onChange={e => setFormData(p => ({ ...p, email: e.target.value }))}
                                    required
                                />
                            </div>
                        </div>

                        {/* Rôle */}
                        <div className="flex flex-col gap-1.5">
                            <label className="text-xs font-semibold text-slate-600 uppercase tracking-wide">Rôle</label>
                            <div className="flex gap-2">
                                {["doctor", "pharmacist"].map(r => (
                                    <button
                                        key={r}
                                        type="button"
                                        onClick={() => setFormData(p => ({ ...p, role: r }))}
                                        className={`flex-1 py-2.5 rounded-xl border text-sm font-semibold transition-all ${
                                            formData.role === r
                                                ? "bg-blue-600 border-blue-600 text-white shadow-md shadow-blue-200"
                                                : "bg-white border-slate-200 text-slate-600 hover:border-blue-300"
                                        }`}
                                    >
                                        {r === "doctor" ? "🩺 Médecin" : "💊 Pharmacien"}
                                    </button>
                                ))}
                            </div>
                        </div>

                        {/* Info mot de passe */}
                        <div className="flex items-start gap-2 bg-blue-50 border border-blue-100 rounded-xl px-4 py-3">
                            <Lock size={13} className="text-blue-500 mt-0.5 shrink-0" />
                            <p className="text-xs text-blue-600">
                                Un mot de passe sécurisé sera généré automatiquement et envoyé par email à l'utilisateur.
                            </p>
                        </div>

                        {formError && (
                            <div className="flex items-center gap-2 bg-red-50 border border-red-200 rounded-xl px-4 py-3 text-red-600 text-sm">
                                <AlertCircle size={14} className="shrink-0" />
                                {formError}
                            </div>
                        )}
                        {formSuccess && (
                            <div className="flex items-center gap-2 bg-emerald-50 border border-emerald-200 rounded-xl px-4 py-3 text-emerald-700 text-sm">
                                <CheckCircle2 size={14} className="shrink-0" />
                                {formSuccess}
                            </div>
                        )}

                        <div className="flex gap-2 pt-1">
                            <button
                                type="button"
                                onClick={() => setShowForm(false)}
                                className="flex-1 py-2.5 border border-slate-200 rounded-xl text-sm font-semibold text-slate-600 hover:bg-slate-50 transition-all"
                            >
                                Annuler
                            </button>
                            <button
                                type="submit"
                                disabled={isLoading}
                                className="flex-1 flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-60 text-white text-sm font-semibold py-2.5 rounded-xl shadow-md shadow-blue-200 transition-all"
                            >
                                {isLoading ? <><Spinner />Création…</> : <><Plus size={15} />Créer & envoyer email</>}
                            </button>
                        </div>
                    </form>
                </div>
            )}

            {/* Users table */}
            <div className="bg-white rounded-2xl border border-slate-100 shadow-sm shadow-slate-100 overflow-hidden">
                <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
                    <h3 className="font-semibold text-slate-700 text-sm">
                        {loadingUsers ? "Chargement…" : `${filtered.length} utilisateur${filtered.length > 1 ? "s" : ""}`}
                    </h3>
                </div>
                <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                        <thead>
                            <tr className="bg-slate-50 border-b border-slate-100">
                                {["Utilisateur", "Rôle", "Statut", "Première connexion", "Créé le", "Actions"].map(h => (
                                    <th key={h} className="text-left text-xs font-semibold text-slate-500 px-4 py-3 uppercase tracking-wide whitespace-nowrap">{h}</th>
                                ))}
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-50">
                            {filtered.map(user => (
                                <tr key={user.id} className="hover:bg-slate-50 transition-colors">
                                    <td className="px-4 py-3">
                                        <div className="flex items-center gap-3">
                                            <div className="w-8 h-8 rounded-xl bg-blue-950 flex items-center justify-center text-white text-xs font-bold shrink-0">
                                                {user.first_name[0]}{user.last_name[0]}
                                            </div>
                                            <div>
                                                <p className="font-semibold text-slate-800 text-sm">{user.first_name} {user.last_name}</p>
                                                <p className="text-xs text-slate-400">{user.email}</p>
                                            </div>
                                        </div>
                                    </td>
                                    <td className="px-4 py-3">
                                        <span className={`text-xs font-semibold px-2.5 py-1 rounded-full ${roleColor[user.role]}`}>
                                            {roleLabel[user.role]}
                                        </span>
                                    </td>
                                    <td className="px-4 py-3">
                                        <span className={`text-xs font-semibold px-2.5 py-1 rounded-full flex items-center gap-1 w-fit ${user.is_active ? "bg-emerald-50 text-emerald-700" : "bg-slate-100 text-slate-500"}`}>
                                            <span className={`w-1.5 h-1.5 rounded-full ${user.is_active ? "bg-emerald-500" : "bg-slate-400"}`} />
                                            {user.is_active ? "Actif" : "Inactif"}
                                        </span>
                                    </td>
                                    <td className="px-4 py-3">
                                        {user.is_first_login
                                            ? <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-amber-50 text-amber-600">En attente</span>
                                            : <span className="text-xs text-slate-400 flex items-center gap-1"><CheckCircle2 size={12} className="text-emerald-500" />Complété</span>
                                        }
                                    </td>
                                    <td className="px-4 py-3 text-xs text-slate-400">{formatDate(user.created_at)}</td>
                                    <td className="px-4 py-3">
                                        <button
                                            onClick={() => toggleActive(user.id)}
                                            className={`text-xs font-semibold px-3 py-1.5 rounded-lg border transition-all ${
                                                user.is_active
                                                    ? "border-red-200 text-red-500 hover:bg-red-50"
                                                    : "border-emerald-200 text-emerald-600 hover:bg-emerald-50"
                                            }`}
                                        >
                                            {user.is_active ? "Désactiver" : "Activer"}
                                        </button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                    {filtered.length === 0 && (
                        <div className="py-12 text-center text-slate-400 text-sm">Aucun utilisateur trouvé.</div>
                    )}
                </div>
            </div>
        </div>
    );
};

/* ─────────────────────────────────────────────────────────
   VIEW — AUDIT TRAIL
───────────────────────────────────────────────────────── */
const AuditView = () => {
    const [filter, setFilter]   = useState("all");
    const [logs, setLogs]       = useState([]);
    const [loading, setLoading] = useState(true);

    // ✅ Charger le vrai journal d'audit
    useEffect(() => {
        const fetchAudit = async () => {
            setLoading(true);
            try {
                const res = await api.get("/audit/recent?limit=100");
                setLogs(res.data || []);
            } catch {
                setLogs([]);
            } finally {
                setLoading(false);
            }
        };
        fetchAudit();
    }, []);

    // Adapter le format API → format UI
    const mapped = logs.map(entry => ({
        id:                     entry.id,
        timestamp:              entry.created_at,
        action:                 decisionToAction[entry.decision] || entry.decision,
        severity:               entry.alert_severity || "NONE",
        detail:                 entry.alert_title    || "—",
        drug:                   entry.alert_type     || "—",
        justif:                 entry.justification,
        justification_valid:    entry.justification_valid,
        justification_feedback: entry.justification_feedback,
    }));

    const filtered = filter === "all"
        ? mapped
        : mapped.filter(l => l.action === filter);

    const overrideCount = mapped.filter(l => l.action === "OVERRIDE").length;

    return (
        <div className="flex flex-col gap-5">
            <div className="flex items-center gap-2 flex-wrap">
                {[
                    { val: "all",              label: "Tout" },
                    { val: "ALERT_ACCEPTED",   label: "✅ Acceptée" },
                    { val: "OVERRIDE",         label: "⚠️ Override" },
                    { val: "ALERT_IGNORED",    label: "❌ Ignorée" },
                    { val: "PRESCRIPTION_OK",  label: "🛡️ OK" },
                ].map(({ val, label }) => (
                    <button
                        key={val}
                        onClick={() => setFilter(val)}
                        className={`text-xs font-semibold px-3 py-1.5 rounded-xl border transition-all ${
                            filter === val
                                ? "bg-blue-600 border-blue-600 text-white"
                                : "bg-white border-slate-200 text-slate-600 hover:border-blue-300"
                        }`}
                    >
                        {label}
                    </button>
                ))}
            </div>

            <div className="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden">
                <div className="px-5 py-4 border-b border-slate-100 flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                    <span className="text-sm font-semibold text-slate-700">
                        {loading ? "Chargement…" : `Journal immuable · ${filtered.length} entrée${filtered.length > 1 ? "s" : ""}`}
                    </span>
                </div>

                {loading ? (
                    <div className="flex justify-center py-12">
                        <Spinner />
                    </div>
                ) : filtered.length === 0 ? (
                    <div className="py-12 text-center text-slate-400 text-sm">Aucune entrée d'audit.</div>
                ) : (
                <div className="divide-y divide-slate-50">
                    {filtered.map(log => {
                        const { date, time } = formatDateTime(log.timestamp);
                        return (
                        <div key={log.id} className="px-5 py-4 flex items-start gap-4 hover:bg-slate-50 transition-colors">
                            <div className="shrink-0 w-36">
                                <p className="text-xs font-mono text-slate-500">{date}</p>
                                <p className="text-xs font-mono font-bold text-slate-700">{time}</p>
                            </div>
                            <div className="shrink-0 mt-0.5">{actionIcon[log.action] || actionIcon["PRESCRIPTION_OK"]}</div>
                            <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2 flex-wrap mb-1">
                                    <span className="text-sm font-semibold text-slate-800">{log.action}</span>
                                    <span className={`text-xs font-semibold px-2 py-0.5 rounded-full border ${severityColor[log.severity] || severityColor["NONE"]}`}>
                                        {log.severity === "NONE" ? "Aucune alerte" : log.severity}
                                    </span>
                                </div>
                                <p className="text-xs text-slate-500">{log.detail}</p>
                                {log.justif && (
                                    <div className="mt-1.5 space-y-1">
                                        <p className="text-xs text-amber-600 italic">
                                            Justification : {log.justif}
                                        </p>
                                        {/* Badge validation sémantique §3.3 */}
                                        {log.justification_valid && (
                                            <span className={`inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full border
                                                ${log.justification_valid === "valid"
                                                    ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                                                    : "bg-red-50 text-red-600 border-red-200"}`}>
                                                {log.justification_valid === "valid" ? "✓ Justification valide" : "✗ Justification insuffisante"}
                                                {log.justification_feedback && (
                                                    <span className="font-normal opacity-80">— {log.justification_feedback}</span>
                                                )}
                                            </span>
                                        )}
                                    </div>
                                )}
                            </div>
                            <div className="shrink-0 text-right hidden sm:block">
                                <span className="text-xs font-semibold bg-slate-100 text-slate-600 px-2.5 py-1 rounded-lg">
                                    {log.drug}
                                </span>
                            </div>
                        </div>
                        );
                    })}
                </div>
                )}
            </div>
        </div>
    );
};

/* ─────────────────────────────────────────────────────────
   ROOT DASHBOARD
───────────────────────────────────────────────────────── */
const AdminDashboard = () => {
    const [activeNav, setActiveNav] = useState("overview");
    const [stats,     setStats]     = useState(null);
    const [auditCount, setAuditCount] = useState(0);
    const currentUser = authService.getUser();

    // ✅ Charger les stats réelles au montage
    useEffect(() => {
        const fetchStats = async () => {
            try {
                const [usersRes, auditRes] = await Promise.all([
                    api.get("/account/users"),
                    api.get("/audit/recent?limit=200"),
                ]);

                const users     = usersRes.data  || [];
                const auditLogs = auditRes.data   || [];

                const activeDoctors      = users.filter(u => u.role === "doctor"      && u.is_active).length;
                const activePharmacists  = users.filter(u => u.role === "pharmacist"  && u.is_active).length;
                const overrides          = auditLogs.filter(l => l.decision === "OVERRIDE").length;
                const accepted           = auditLogs.filter(l => l.decision === "ACCEPTED").length;
                const total              = auditLogs.length;
                const overrideRate       = total > 0 ? +((overrides / total) * 100).toFixed(1) : 0;
                const complianceRate     = total > 0 ? +((accepted  / total) * 100).toFixed(1) : 100;

                setStats({
                    totalUsers:        users.length,
                    activeDoctors,
                    activePharmacists,
                    prescriptionsToday: "—",   // nécessiterait un endpoint dédié
                    alertsToday:        total,
                    overrideRate,
                    complianceRate,
                    avgResponseMs:      187,    // placeholder
                });
                setAuditCount(auditLogs.filter(l => l.decision === "OVERRIDE").length);
            } catch {
                setStats(null);
            }
        };
        fetchStats();
    }, []);

    const handleLogout = () => authService.logout();

    const views = {
        overview: stats
            ? <OverviewView stats={stats} />
            : <div className="flex justify-center py-20"><Spinner /></div>,
        users:    <UsersView />,
        audit:    <AuditView />,
    };

    const viewTitles = {
        overview: { title: "Vue d'ensemble",  sub: "Tableau de bord SafeRx AI — Données du jour" },
        users:    { title: "Gestion des comptes", sub: "Créer et gérer les médecins et pharmaciens" },
        audit:    { title: "Audit Trail",     sub: "Journal immuable de toutes les transactions cliniques" },
    };

    return (
        <div className="h-screen w-full overflow-hidden flex bg-slate-50">

            {/* ── SIDEBAR ── */}
            <aside className="hidden md:flex w-64 bg-blue-950 flex-col relative overflow-hidden shrink-0">
                {/* Blobs décoratifs */}
                <div className="absolute -top-16 -right-16 w-56 h-56 bg-blue-500 rounded-full opacity-10 blur-3xl pointer-events-none" />
                <div className="absolute -bottom-12 -left-12 w-48 h-48 bg-blue-400 rounded-full opacity-10 blur-3xl pointer-events-none" />
                {/* Motif points */}
                <div className="absolute inset-0 opacity-[0.06] pointer-events-none"
                    style={{ backgroundImage: "radial-gradient(circle, rgba(255,255,255,0.9) 1px, transparent 1px)", backgroundSize: "20px 20px" }}
                />

                <div className="relative z-10 flex flex-col h-full">
                    {/* Logo */}
                    <div className="px-5 py-6 border-b border-white border-opacity-10">
                        <div className="flex items-center gap-2.5">
                            <div className="w-9 h-9 rounded-xl bg-blue-500 bg-opacity-30 border border-blue-400 border-opacity-30 flex items-center justify-center">
                                <ShieldCheck size={18} className="text-blue-300" strokeWidth={1.5} />
                            </div>
                            <div>
                                <p className="text-white font-bold text-sm leading-none">SafeRx AI</p>
                                <p className="text-blue-400 text-xs mt-0.5">Administration</p>
                            </div>
                        </div>
                    </div>

                    {/* Admin badge */}
                    <div className="px-5 py-4 border-b border-white border-opacity-10">
                        <div className="flex items-center gap-2.5">
                            <div className="w-8 h-8 rounded-xl bg-white bg-opacity-10 flex items-center justify-center text-white text-xs font-bold">
                                {currentUser?.first_name?.[0]}{currentUser?.last_name?.[0]}
                            </div>
                            <div>
                                <p className="text-white text-xs font-semibold">
                                    {currentUser?.first_name} {currentUser?.last_name}
                                </p>
                                <p className="text-blue-400 text-xs">Administrateur</p>
                            </div>
                        </div>
                    </div>

                    {/* Nav */}
                    <nav className="flex-1 px-3 py-4 flex flex-col gap-1">
                        {NAV.map(({ id, icon: Icon, label }) => (
                            <button
                                key={id}
                                onClick={() => setActiveNav(id)}
                                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-semibold transition-all text-left ${
                                    activeNav === id
                                        ? "bg-white bg-opacity-15 text-white"
                                        : "text-slate-400 hover:text-white hover:bg-white hover:bg-opacity-5"
                                }`}
                            >
                                <Icon size={16} className={activeNav === id ? "text-blue-300" : ""} />
                                {label}
                                {id === "audit" && auditCount > 0 && (
                                    <span className="ml-auto bg-amber-500 text-white text-xs font-bold px-1.5 py-0.5 rounded-md">
                                        {auditCount}
                                    </span>
                                )}
                            </button>
                        ))}
                    </nav>

                    {/* Logout */}
                    <div className="px-3 py-4 border-t border-white border-opacity-10">
                        <button
                            onClick={handleLogout}
                            className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-semibold text-slate-400 hover:text-red-400 hover:bg-white hover:bg-opacity-5 transition-all"
                        >
                            <LogOut size={16} />
                            Déconnexion
                        </button>
                        <p className="text-center text-blue-900 text-opacity-60 text-xs mt-3 flex items-center justify-center gap-1">
                            <ShieldCheck size={10} className="text-blue-700" />
                            <span className="text-blue-700 opacity-60">TLS 1.3 · Conforme HDS</span>
                        </p>
                    </div>
                </div>
            </aside>

            {/* ── MAIN CONTENT ── */}
            <main className="flex-1 overflow-y-auto">
                {/* Topbar */}
                <header className="sticky top-0 z-20 bg-slate-50 border-b border-slate-200 px-6 py-4 flex items-center justify-between">
                    <div>
                        <h1 className="text-lg font-bold text-slate-800">{viewTitles[activeNav].title}</h1>
                        <p className="text-xs text-slate-400">{viewTitles[activeNav].sub}</p>
                    </div>
                    <div className="flex items-center gap-3">
                        <div className="flex items-center gap-2 bg-white border border-slate-200 rounded-xl px-3 py-2">
                            <Clock size={13} className="text-slate-400" />
                            <span className="text-xs text-slate-600 font-medium">
                                {new Date().toLocaleDateString("fr-FR", { weekday: "long", day: "numeric", month: "long" })}
                            </span>
                        </div>
                        <div className="relative">
                            <button className="w-9 h-9 bg-white border border-slate-200 rounded-xl flex items-center justify-center text-slate-500 hover:text-blue-600 transition-colors">
                                <Bell size={15} />
                            </button>
                            <span className="absolute -top-1 -right-1 w-4 h-4 bg-red-500 rounded-full text-white text-xs flex items-center justify-center font-bold">3</span>
                        </div>
                    </div>
                </header>

                {/* Page content */}
                <div className="p-6">
                    {views[activeNav]}
                </div>
            </main>
        </div>
    );
};

export default AdminDashboard;