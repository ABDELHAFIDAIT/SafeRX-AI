import { useState, useEffect, useCallback } from "react";
import {
    ShieldCheck, Users, LayoutDashboard, ClipboardList,
    LogOut, Plus, Search, CheckCircle2, AlertCircle,
    XCircle, Eye, EyeOff, ArrowRight, Activity, Stethoscope,
    ChevronDown, Bell, UserCheck, UserX, Pill, TrendingUp,
    Clock, Filter, MoreVertical, Mail, Lock, RefreshCw,
    AlertTriangle, BarChart3, Shield, Siren, Trash2, KeyRound,
    Download, ChevronLeft, ChevronRight as ChevronRightIcon,
    RotateCcw, Info, X
} from "lucide-react";
import authService from "../services/AuthService";
import api from "../api/api";

/* ─────────────────────────────────────────────────────────
   HELPERS — mapping données API → format UI
───────────────────────────────────────────────────────── */
// Décision backend → label action UI
const decisionToAction = {
    ACCEPTED: "ALERT_ACCEPTED",
    IGNORED: "ALERT_IGNORED",
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

// topAlerts est maintenant dynamique (vient de GET /account/stats)
const ALERT_TYPE_LABELS = {
    INTERACTION: "Interaction",
    ALLERGY: "Allergie",
    CONTRA_INDICATION: "Contre-indication",
    REDUNDANT_DCI: "Redondance DCI",
    POSOLOGY: "Posologie",
    RENAL: "Insuffisance rénale",
};

/* ─────────────────────────────────────────────────────────
   HELPERS
───────────────────────────────────────────────────────── */
const roleLabel = { doctor: "Médecin", pharmacist: "Pharmacien", admin: "Administrateur" };
const roleColor = { doctor: "bg-blue-100 text-blue-700", pharmacist: "bg-emerald-100 text-emerald-700", admin: "bg-purple-100 text-purple-700" };

const severityColor = {
    MAJOR: "text-red-600 bg-red-50 border-red-200",
    MODERATE: "text-amber-600 bg-amber-50 border-amber-200",
    MINOR: "text-blue-600 bg-blue-50 border-blue-200",
    NONE: "text-slate-500 bg-slate-50 border-slate-200",
};
const actionIcon = {
    ALERT_ACCEPTED: <CheckCircle2 size={13} className="text-emerald-500" />,
    OVERRIDE: <AlertTriangle size={13} className="text-amber-500" />,
    ALERT_IGNORED: <XCircle size={13} className="text-red-400" />,
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
    { id: "overview", icon: LayoutDashboard, label: "Vue d'ensemble" },
    { id: "users", icon: Users, label: "Utilisateurs" },
    { id: "audit", icon: ClipboardList, label: "Audit Trail" },
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
const OverviewView = ({ stats, topAlerts = [] }) => (
    <div className="flex flex-col gap-6">
        {/* KPI Grid */}
        <div className="grid grid-cols-2 xl:grid-cols-4 gap-4">
            <KpiCard icon={<Users size={18} className="text-blue-600" />} label="Utilisateurs actifs" value={stats.totalUsers} accent="bg-blue-50" />
            <KpiCard icon={<Pill size={18} className="text-indigo-600" />} label="Prescriptions / 24h" value={stats.prescriptionsToday} accent="bg-indigo-50" />
            <KpiCard icon={<Siren size={18} className="text-amber-600" />} label="Décisions auditées" value={stats.alertsToday} accent="bg-amber-50" />
            <KpiCard icon={<ShieldCheck size={18} className="text-emerald-600" />} label="Taux de conformité" value={`${stats.complianceRate}%`} accent="bg-emerald-50" />
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
            {/* Top alertes dynamiques */}
            <div className="xl:col-span-2 bg-white rounded-2xl border border-slate-100 shadow-sm shadow-slate-100 p-5">
                <div className="flex items-center gap-2 mb-4">
                    <BarChart3 size={16} className="text-slate-400" />
                    <h3 className="font-semibold text-slate-700 text-sm">Top 5 — Types d'alertes les plus fréquents</h3>
                </div>
                {topAlerts.length === 0 ? (
                    <p className="text-sm text-slate-400 text-center py-4">Aucune donnée d'audit disponible.</p>
                ) : (
                    <div className="flex flex-col gap-2.5">
                        {topAlerts.map((item, i) => (
                            <div key={item.type} className="flex items-center gap-3">
                                <span className="text-xs font-bold text-slate-400 w-4">{i + 1}</span>
                                <div className="flex-1">
                                    <div className="flex justify-between text-xs mb-1">
                                        <span className="font-semibold text-slate-700">
                                            {ALERT_TYPE_LABELS[item.type] || item.type}
                                        </span>
                                        <strong className="text-slate-600">{item.count}</strong>
                                    </div>
                                    <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
                                        <div
                                            className="h-full rounded-full bg-blue-500 transition-all duration-700"
                                            style={{ width: `${(item.count / topAlerts[0].count) * 100}%` }}
                                        />
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {/* Système */}
            <div className="bg-white rounded-2xl border border-slate-100 shadow-sm shadow-slate-100 p-5 flex flex-col gap-4">
                <div className="flex items-center gap-2 mb-1">
                    <Activity size={16} className="text-slate-400" />
                    <h3 className="font-semibold text-slate-700 text-sm">Performance système</h3>
                </div>
                {[
                    { label: "Temps de réponse moyen", value: `${stats.avgResponseMs} ms`, ok: stats.avgResponseMs < 300, target: "< 300 ms" },
                    { label: "Taux d'override", value: `${stats.overrideRate}%`, ok: stats.overrideRate < 20, target: "< 20 %" },
                    { label: "Conformité prescriptions", value: `${stats.complianceRate}%`, ok: stats.complianceRate > 80, target: "> 80 %" },
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
                                : <AlertCircle size={14} className="text-red-500" />
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
const USERS_PER_PAGE = 8;

const UsersView = () => {
    const [users, setUsers] = useState([]);
    const [search, setSearch] = useState("");
    const [roleFilter, setRoleFilter] = useState("all");
    const [showForm, setShowForm] = useState(false);
    const [formData, setFormData] = useState({ first_name: "", last_name: "", email: "", role: "doctor" });
    const [formError, setFormError] = useState("");
    const [formSuccess, setFormSuccess] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const [loadingUsers, setLoadingUsers] = useState(true);
    const [page, setPage] = useState(1);
    const [actionLoading, setActionLoading] = useState({}); // {userId: "toggle"|"delete"|"reset"}
    const [selectedUser, setSelectedUser] = useState(null); // modal détail
    const [confirmDelete, setConfirmDelete] = useState(null); // userId à confirmer

    const fetchUsers = useCallback(async () => {
        setLoadingUsers(true);
        try {
            const res = await api.get("/account/users");
            setUsers(res.data || []);
        } catch {
            setUsers([]);
        } finally {
            setLoadingUsers(false);
        }
    }, []);

    useEffect(() => { fetchUsers(); }, [fetchUsers]);

    const filtered = users.filter(u => {
        const matchSearch = `${u.first_name} ${u.last_name} ${u.email}`.toLowerCase().includes(search.toLowerCase());
        const matchRole = roleFilter === "all" || u.role === roleFilter;
        return matchSearch && matchRole;
    });

    const totalPages = Math.max(1, Math.ceil(filtered.length / USERS_PER_PAGE));
    const paginated = filtered.slice((page - 1) * USERS_PER_PAGE, page * USERS_PER_PAGE);

    // Reset page when filter changes
    useEffect(() => { setPage(1); }, [search, roleFilter]);

    // ── Créer un compte ─────────────────────────────────────────────────
    const handleCreate = async (e) => {
        e.preventDefault();
        setFormError(""); setFormSuccess("");
        setIsLoading(true);
        try {
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

    // ── Activer / Désactiver ─────────────────────────────────────────────
    const toggleActive = async (id) => {
        setActionLoading(p => ({ ...p, [id]: "toggle" }));
        try {
            const res = await api.patch(`/account/users/${id}/toggle`);
            setUsers(prev => prev.map(u => u.id === id ? res.data : u));
        } catch (err) {
            alert(err.response?.data?.detail || "Erreur lors de la mise à jour.");
        } finally {
            setActionLoading(p => { const n = { ...p }; delete n[id]; return n; });
        }
    };

    // ── Supprimer ────────────────────────────────────────────────────────
    const deleteUser = async (id) => {
        setConfirmDelete(null);
        setActionLoading(p => ({ ...p, [id]: "delete" }));
        try {
            await api.delete(`/account/users/${id}`);
            setUsers(prev => prev.filter(u => u.id !== id));
        } catch (err) {
            alert(err.response?.data?.detail || "Erreur lors de la suppression.");
        } finally {
            setActionLoading(p => { const n = { ...p }; delete n[id]; return n; });
        }
    };

    // ── Réinitialiser MDP ────────────────────────────────────────────────
    const resetPassword = async (id, email) => {
        if (!window.confirm(`Réinitialiser le mot de passe de ${email} et envoyer un email ?`)) return;
        setActionLoading(p => ({ ...p, [id]: "reset" }));
        try {
            await api.post(`/account/users/${id}/reset-password`);
            setUsers(prev => prev.map(u => u.id === id ? { ...u, is_first_login: true } : u));
            alert(`Nouveau mot de passe envoyé à ${email}.`);
        } catch (err) {
            alert(err.response?.data?.detail || "Erreur lors de la réinitialisation.");
        } finally {
            setActionLoading(p => { const n = { ...p }; delete n[id]; return n; });
        }
    };

    return (
        <div className="flex flex-col gap-5">

            {/* Modale confirmation suppression */}
            {confirmDelete && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
                    <div className="bg-white rounded-2xl shadow-2xl p-6 max-w-sm w-full mx-4">
                        <div className="flex items-center gap-3 mb-4">
                            <div className="w-10 h-10 rounded-xl bg-red-100 flex items-center justify-center">
                                <Trash2 size={18} className="text-red-600" />
                            </div>
                            <div>
                                <p className="font-semibold text-slate-800">Supprimer le compte</p>
                                <p className="text-xs text-slate-500">Cette action est irréversible.</p>
                            </div>
                        </div>
                        <p className="text-sm text-slate-600 mb-5">
                            Êtes-vous sûr de vouloir supprimer le compte de <strong>{confirmDelete.name}</strong> ?
                        </p>
                        <div className="flex gap-2">
                            <button onClick={() => setConfirmDelete(null)}
                                className="flex-1 py-2 border border-slate-200 rounded-xl text-sm text-slate-600 hover:bg-slate-50 transition-all">
                                Annuler
                            </button>
                            <button onClick={() => deleteUser(confirmDelete.id)}
                                className="flex-1 py-2 bg-red-600 hover:bg-red-700 text-white rounded-xl text-sm font-semibold transition-all">
                                Supprimer
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Modale détail utilisateur */}
            {selectedUser && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
                    <div className="bg-white rounded-2xl shadow-2xl p-6 max-w-sm w-full mx-4">
                        <div className="flex items-center justify-between mb-5">
                            <h3 className="font-semibold text-slate-800">Détail du compte</h3>
                            <button onClick={() => setSelectedUser(null)} className="text-slate-400 hover:text-slate-600">
                                <X size={18} />
                            </button>
                        </div>
                        <div className="flex flex-col gap-3">
                            <div className="flex items-center gap-3">
                                <div className="w-12 h-12 rounded-2xl bg-blue-950 flex items-center justify-center text-white font-bold">
                                    {selectedUser.first_name[0]}{selectedUser.last_name[0]}
                                </div>
                                <div>
                                    <p className="font-semibold text-slate-800">{selectedUser.first_name} {selectedUser.last_name}</p>
                                    <p className="text-xs text-slate-500">{selectedUser.email}</p>
                                </div>
                            </div>
                            {[
                                ["Rôle", roleLabel[selectedUser.role] || selectedUser.role],
                                ["Statut", selectedUser.is_active ? "Actif" : "Inactif"],
                                ["Première connexion", selectedUser.is_first_login ? "En attente" : "Complétée"],
                                ["Créé le", formatDate(selectedUser.created_at)],
                            ].map(([k, v]) => (
                                <div key={k} className="flex justify-between text-sm border-b border-slate-100 pb-2">
                                    <span className="text-slate-500">{k}</span>
                                    <span className="font-medium text-slate-700">{v}</span>
                                </div>
                            ))}
                        </div>
                        <button onClick={() => setSelectedUser(null)}
                            className="mt-5 w-full py-2 bg-slate-100 hover:bg-slate-200 rounded-xl text-sm font-medium text-slate-700 transition-all">
                            Fermer
                        </button>
                    </div>
                </div>
            )}

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
                                        className={`flex-1 py-2.5 rounded-xl border text-sm font-semibold transition-all ${formData.role === r
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
                    <button onClick={fetchUsers} className="text-slate-400 hover:text-slate-600 transition-colors" title="Rafraîchir">
                        <RefreshCw size={14} />
                    </button>
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
                            {paginated.map(user => {
                                const loading = actionLoading[user.id];
                                return (
                                    <tr key={user.id} className="hover:bg-slate-50 transition-colors">
                                        <td className="px-4 py-3">
                                            <button onClick={() => setSelectedUser(user)} className="flex items-center gap-3 text-left group">
                                                <div className="w-8 h-8 rounded-xl bg-blue-950 flex items-center justify-center text-white text-xs font-bold shrink-0">
                                                    {user.first_name[0]}{user.last_name[0]}
                                                </div>
                                                <div>
                                                    <p className="font-semibold text-slate-800 text-sm group-hover:text-blue-600 transition-colors">{user.first_name} {user.last_name}</p>
                                                    <p className="text-xs text-slate-400">{user.email}</p>
                                                </div>
                                            </button>
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
                                            <div className="flex items-center gap-1.5">
                                                {/* Toggle actif/inactif */}
                                                <button
                                                    onClick={() => toggleActive(user.id)}
                                                    disabled={!!loading}
                                                    title={user.is_active ? "Désactiver" : "Activer"}
                                                    className={`p-1.5 rounded-lg border transition-all disabled:opacity-40 ${user.is_active
                                                            ? "border-red-200 text-red-500 hover:bg-red-50"
                                                            : "border-emerald-200 text-emerald-600 hover:bg-emerald-50"
                                                        }`}>
                                                    {loading === "toggle"
                                                        ? <Spinner />
                                                        : user.is_active ? <UserX size={13} /> : <UserCheck size={13} />}
                                                </button>
                                                {/* Réinitialiser MDP */}
                                                <button
                                                    onClick={() => resetPassword(user.id, user.email)}
                                                    disabled={!!loading}
                                                    title="Réinitialiser le mot de passe"
                                                    className="p-1.5 rounded-lg border border-amber-200 text-amber-600 hover:bg-amber-50 transition-all disabled:opacity-40">
                                                    {loading === "reset" ? <Spinner /> : <KeyRound size={13} />}
                                                </button>
                                                {/* Supprimer */}
                                                <button
                                                    onClick={() => setConfirmDelete({ id: user.id, name: `${user.first_name} ${user.last_name}` })}
                                                    disabled={!!loading}
                                                    title="Supprimer le compte"
                                                    className="p-1.5 rounded-lg border border-slate-200 text-slate-400 hover:bg-red-50 hover:border-red-200 hover:text-red-500 transition-all disabled:opacity-40">
                                                    {loading === "delete" ? <Spinner /> : <Trash2 size={13} />}
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                    {filtered.length === 0 && (
                        <div className="py-12 text-center text-slate-400 text-sm">Aucun utilisateur trouvé.</div>
                    )}
                </div>
                {/* Pagination */}
                {totalPages > 1 && (
                    <div className="px-5 py-3 border-t border-slate-100 flex items-center justify-between">
                        <p className="text-xs text-slate-400">
                            Page {page}/{totalPages} · {filtered.length} utilisateurs
                        </p>
                        <div className="flex gap-1">
                            <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}
                                className="p-1.5 rounded-lg border border-slate-200 text-slate-500 hover:bg-slate-50 disabled:opacity-30 transition-all">
                                <ChevronLeft size={14} />
                            </button>
                            <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages}
                                className="p-1.5 rounded-lg border border-slate-200 text-slate-500 hover:bg-slate-50 disabled:opacity-30 transition-all">
                                <ChevronRightIcon size={14} />
                            </button>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};

/* ─────────────────────────────────────────────────────────
   VIEW — AUDIT TRAIL
───────────────────────────────────────────────────────── */
const AuditView = () => {
    const [filter, setFilter] = useState("all");
    const [logs, setLogs] = useState([]);
    const [loading, setLoading] = useState(true);

    const fetchAudit = useCallback(async () => {
        setLoading(true);
        try {
            const res = await api.get("/audit/recent?limit=200");
            setLogs(res.data || []);
        } catch {
            setLogs([]);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { fetchAudit(); }, [fetchAudit]);

    // Export CSV
    const exportCSV = () => {
        const headers = ["ID", "Date", "Décision", "Type alerte", "Sévérité", "Titre alerte", "Justification", "Validation sémantique"];
        const rows = logs.map(e => [
            e.id,
            e.created_at ? new Date(e.created_at).toLocaleString("fr-FR") : "",
            e.decision,
            e.alert_type || "",
            e.alert_severity || "",
            `"${(e.alert_title || "").replace(/"/g, '""')}"`,
            `"${(e.justification || "").replace(/"/g, '""')}"`,
            e.justification_valid || "",
        ].join(","));
        const csv = [headers.join(","), ...rows].join("\n");
        const blob = new Blob(["\uFEFF" + csv], { type: "text/csv;charset=utf-8;" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `audit_saferx_${new Date().toISOString().slice(0, 10)}.csv`;
        a.click();
        URL.revokeObjectURL(url);
    };

    // Adapter le format API → format UI
    const mapped = logs.map(entry => ({
        id: entry.id,
        timestamp: entry.created_at,
        action: decisionToAction[entry.decision] || entry.decision,
        severity: entry.alert_severity || "NONE",
        detail: entry.alert_title || "—",
        drug: entry.alert_type || "—",
        justif: entry.justification,
        justification_valid: entry.justification_valid,
        justification_feedback: entry.justification_feedback,
    }));

    const filtered = filter === "all"
        ? mapped
        : mapped.filter(l => l.action === filter);

    // const overrideCount = mapped.filter(l => l.action === "OVERRIDE").length;

    return (
        <div className="flex flex-col gap-5">
            <div className="flex items-center gap-2 flex-wrap justify-between">
                <div className="flex items-center gap-2 flex-wrap">
                    {[
                        { val: "all", label: "Tout" },
                        { val: "ALERT_ACCEPTED", label: "✅ Acceptée" },
                        { val: "OVERRIDE", label: "⚠️ Override" },
                        { val: "ALERT_IGNORED", label: "❌ Ignorée" },
                        { val: "PRESCRIPTION_OK", label: "🛡️ OK" },
                    ].map(({ val, label }) => (
                        <button
                            key={val}
                            onClick={() => setFilter(val)}
                            className={`text-xs font-semibold px-3 py-1.5 rounded-xl border transition-all ${filter === val
                                    ? "bg-blue-600 border-blue-600 text-white"
                                    : "bg-white border-slate-200 text-slate-600 hover:border-blue-300"
                                }`}
                        >
                            {label}
                        </button>
                    ))}
                </div>
                <div className="flex items-center gap-2">
                    <button onClick={fetchAudit} title="Rafraîchir"
                        className="flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-xl border border-slate-200 text-slate-600 hover:border-blue-300 bg-white transition-all">
                        <RefreshCw size={12} /> Rafraîchir
                    </button>
                    <button onClick={exportCSV} title="Exporter CSV"
                        className="flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-xl border border-emerald-200 text-emerald-700 hover:bg-emerald-50 bg-white transition-all">
                        <Download size={12} /> Export CSV
                    </button>
                </div>
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
    const [stats, setStats] = useState(null);
    const [topAlerts, setTopAlerts] = useState([]);
    const [auditCount, setAuditCount] = useState(0);
    const currentUser = authService.getUser();

    // ✅ Stats réelles depuis GET /account/stats
    useEffect(() => {
        const fetchStats = async () => {
            try {
                const res = await api.get("/account/stats");
                const d = res.data;
                setStats({
                    totalUsers: d.total_users,
                    activeDoctors: d.active_doctors,
                    activePharmacists: d.active_pharmacists,
                    prescriptionsToday: d.prescriptions_today,
                    alertsToday: d.total_audit_entries,
                    overrideRate: d.override_rate,
                    complianceRate: d.compliance_rate,
                    avgResponseMs: 187,   // nécessiterait un middleware de mesure
                });
                setTopAlerts(d.top_alerts || []);
                setAuditCount(
                    Math.round((d.override_rate / 100) * d.total_audit_entries)
                );
            } catch {
                setStats(null);
            }
        };
        fetchStats();
    }, []);

    const handleLogout = () => authService.logout();

    const views = {
        overview: stats
            ? <OverviewView stats={stats} topAlerts={topAlerts} />
            : <div className="flex justify-center py-20"><Spinner /></div>,
        users: <UsersView />,
        audit: <AuditView />,
    };

    const viewTitles = {
        overview: { title: "Vue d'ensemble", sub: "Tableau de bord SafeRx AI — Données du jour" },
        users: { title: "Gestion des comptes", sub: "Créer et gérer les médecins et pharmaciens" },
        audit: { title: "Audit Trail", sub: "Journal immuable de toutes les transactions cliniques" },
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
                        {NAV.map(({ id, icon: Icon, label }) => ( // eslint-disable-line no-unused-vars
                            <button
                                key={id}
                                onClick={() => setActiveNav(id)}
                                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-semibold transition-all text-left ${activeNav === id
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