import React, { useState } from "react";
import {
    Lock, Eye, EyeOff, ShieldCheck, ArrowRight,
    AlertCircle, CheckCircle2, KeyRound, RefreshCw,
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import authService from "../services/AuthService";

/* ─── Règles de force du mot de passe ─────────────────────────── */
const rules = [
    { id: "length", label: "8 caractères minimum", test: (v) => v.length >= 8 },
    { id: "upper", label: "Une lettre majuscule", test: (v) => /[A-Z]/.test(v) },
    { id: "digit", label: "Un chiffre", test: (v) => /\d/.test(v) },
    { id: "special", label: "Un caractère spécial (!@#$%&*)", test: (v) => /[!@#$%&*]/.test(v) },
];

const getStrength = (password) => {
    const passed = rules.filter((r) => r.test(password)).length;
    if (passed === 0) return { level: 0, label: "", color: "" };
    if (passed === 1) return { level: 1, label: "Faible", color: "bg-red-400" };
    if (passed === 2) return { level: 2, label: "Moyen", color: "bg-amber-400" };
    if (passed === 3) return { level: 3, label: "Bien", color: "bg-blue-400" };
    return { level: 4, label: "Fort", color: "bg-emerald-500" };
};

/* ─── Composant principal ──────────────────────────────────────── */
const ChangePassword = () => {
    const navigate = useNavigate();

    const [newPassword, setNewPassword] = useState("");
    const [confirmPassword, setConfirmPassword] = useState("");
    const [showNew, setShowNew] = useState(false);
    const [showConfirm, setShowConfirm] = useState(false);
    const [error, setError] = useState("");
    const [success, setSuccess] = useState(false);
    const [isLoading, setIsLoading] = useState(false);

    const strength = getStrength(newPassword);
    const allRulesMet = rules.every((r) => r.test(newPassword));
    const passwordsMatch = newPassword === confirmPassword && confirmPassword.length > 0;

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError("");

        if (!allRulesMet) {
            setError("Votre mot de passe ne respecte pas toutes les règles.");
            return;
        }
        if (newPassword !== confirmPassword) {
            setError("Les deux mots de passe ne correspondent pas.");
            return;
        }

        setIsLoading(true);
        try {
            await authService.changePassword(newPassword);
            setSuccess(true);
            // ✅ FIX : navigate selon le rôle au lieu d'un alert()
            setTimeout(() => {
                const user = authService.getUser();
                const role = user?.role?.toLowerCase();
                if (role === "admin") navigate("/dashboard/admin");
                else navigate("/dashboard/doctor");
            }, 2500);
        } catch (err) {
            setError(err.response?.data?.detail || "Une erreur est survenue.");
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="h-screen w-full overflow-hidden flex">

            <div className="hidden md:flex md:w-1/2 bg-blue-950 flex-col items-center justify-center p-12 relative overflow-hidden">
                <div className="absolute -top-24 -right-24 w-96 h-96 bg-blue-500 rounded-full opacity-10 blur-3xl" />
                <div className="absolute -bottom-16 -left-16 w-72 h-72 bg-blue-400 rounded-full opacity-10 blur-3xl" />
                <div
                    className="absolute inset-0 opacity-10"
                    style={{
                        backgroundImage: "radial-gradient(circle, rgba(255,255,255,0.8) 1px, transparent 1px)",
                        backgroundSize: "24px 24px",
                    }}
                />

                <div className="relative z-10 w-full max-w-sm">
                    <div className="w-14 h-14 rounded-2xl bg-blue-500 bg-opacity-30 border border-blue-400 border-opacity-30 flex items-center justify-center mb-6">
                        <KeyRound size={28} className="text-blue-300" strokeWidth={1.5} />
                    </div>

                    <h2 className="text-3xl font-bold text-white leading-snug mb-3">
                        Sécurisez votre<br />
                        <span className="text-blue-300">accès clinique.</span>
                    </h2>
                    <p className="text-slate-400 text-sm leading-relaxed mb-10">
                        C'est votre première connexion. Définissez un mot de passe
                        personnel fort pour protéger l'accès à SafeRx AI.
                    </p>

                    <div className="flex flex-col gap-3">
                        {[
                            {
                                icon: <ShieldCheck size={18} className="text-blue-300" />,
                                bg: "bg-blue-500 bg-opacity-25",
                                title: "Mot de passe unique",
                                sub: "N'utilisez pas un mot de passe déjà utilisé ailleurs.",
                            },
                            {
                                icon: <RefreshCw size={18} className="text-emerald-300" />,
                                bg: "bg-emerald-500 bg-opacity-20",
                                title: "Renouvelez régulièrement",
                                sub: "Changez votre mot de passe tous les 90 jours.",
                            },
                        ].map(({ icon, bg, title, sub }) => (
                            <div
                                key={title}
                                className="flex items-start gap-3 bg-white bg-opacity-5 border border-white border-opacity-10 rounded-2xl px-4 py-3 backdrop-blur-sm"
                            >
                                <div className={`w-10 h-10 rounded-xl ${bg} flex items-center justify-center shrink-0 mt-0.5`}>
                                    {icon}
                                </div>
                                <div>
                                    <div className="text-white font-semibold text-sm leading-tight">{title}</div>
                                    <div className="text-slate-400 text-xs mt-0.5 leading-relaxed">{sub}</div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            <div className="w-full md:w-1/2 flex flex-col items-center justify-center h-screen bg-slate-50 px-6">
                <div className="w-full max-w-sm">

                    <div className="text-center mb-8">
                        <span className="inline-flex items-center gap-1.5 bg-amber-50 border border-amber-200 text-amber-600 text-xs font-semibold px-3 py-1.5 rounded-full uppercase tracking-wide mb-4">
                            <KeyRound size={11} />
                            Première connexion
                        </span>
                        <h1 className="text-2xl font-bold text-slate-800 mb-1">
                            Créez votre mot de passe
                        </h1>
                        <p className="text-slate-500 text-sm">
                            Ce mot de passe remplacera celui généré automatiquement.
                        </p>
                    </div>

                    <div className="bg-white rounded-2xl shadow-xl shadow-slate-200 border border-slate-100 p-8">

                        {success ? (
                            <div className="flex flex-col items-center gap-4 py-4">
                                <div className="w-14 h-14 rounded-full bg-emerald-100 flex items-center justify-center">
                                    <CheckCircle2 size={30} className="text-emerald-500" />
                                </div>
                                <div className="text-center">
                                    <p className="font-semibold text-slate-800 text-base">Mot de passe mis à jour !</p>
                                    <p className="text-slate-500 text-sm mt-1">
                                        Vous allez être redirigé vers le tableau de bord…
                                    </p>
                                </div>
                                <div className="w-full bg-slate-100 rounded-full h-1 overflow-hidden mt-1">
                                    <div className="h-1 bg-emerald-500 rounded-full animate-[shrink_2.5s_linear_forwards]"
                                        style={{ animation: "progress 2.5s linear forwards" }} />
                                </div>
                            </div>
                        ) : (
                            <form className="flex flex-col gap-5" onSubmit={handleSubmit}>

                                <div className="flex flex-col gap-1.5">
                                    <label className="text-sm font-semibold text-slate-700">
                                        Nouveau mot de passe
                                    </label>
                                    <div className="relative">
                                        <Lock size={16} className="absolute left-3.5 top-1/2 -translate-y-1/4 text-slate-400 pointer-events-none" />
                                        <input
                                            type={showNew ? "text" : "password"}
                                            className="w-full pl-10 pr-10 py-2.5 border border-slate-200 rounded-xl bg-slate-50 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent focus:bg-white transition-all"
                                            placeholder="••••••••"
                                            value={newPassword}
                                            onChange={(e) => setNewPassword(e.target.value)}
                                            required
                                        />
                                        <button
                                            type="button"
                                            onClick={() => setShowNew(!showNew)}
                                            className="absolute right-3.5 top-1/2 -translate-y-1/4 text-slate-400 hover:text-slate-600 transition-colors"
                                        >
                                            {showNew ? <EyeOff size={16} /> : <Eye size={16} />}
                                        </button>
                                    </div>

                                    {newPassword.length > 0 && (
                                        <div className="mt-1.5">
                                            <div className="flex gap-1 mb-1.5">
                                                {[1, 2, 3, 4].map((lvl) => (
                                                    <div
                                                        key={lvl}
                                                        className={`h-1 flex-1 rounded-full transition-all duration-300 ${lvl <= strength.level
                                                            ? strength.color
                                                            : "bg-slate-200"
                                                            }`}
                                                    />
                                                ))}
                                            </div>
                                            {strength.label && (
                                                <p className="text-xs text-slate-500">
                                                    Force :
                                                    <span className={`font-semibold ml-1 ${strength.level <= 1 ? "text-red-500" :
                                                        strength.level === 2 ? "text-amber-500" :
                                                            strength.level === 3 ? "text-blue-500" :
                                                                "text-emerald-500"
                                                        }`}>
                                                        {strength.label}
                                                    </span>
                                                </p>
                                            )}
                                        </div>
                                    )}

                                    {newPassword.length > 0 && (
                                        <ul className="mt-1 flex flex-col gap-1">
                                            {rules.map((rule) => {
                                                const ok = rule.test(newPassword);
                                                return (
                                                    <li key={rule.id} className={`flex items-center gap-1.5 text-xs transition-colors ${ok ? "text-emerald-600" : "text-slate-400"}`}>
                                                        <CheckCircle2 size={12} className={ok ? "text-emerald-500" : "text-slate-300"} />
                                                        {rule.label}
                                                    </li>
                                                );
                                            })}
                                        </ul>
                                    )}
                                </div>

                                <div className="flex flex-col gap-1.5">
                                    <label className="text-sm font-semibold text-slate-700">
                                        Confirmer le mot de passe
                                    </label>
                                    <div className="relative">
                                        <Lock size={16} className="absolute left-3.5 top-1/2 -translate-y-1/4 text-slate-400 pointer-events-none" />
                                        <input
                                            type={showConfirm ? "text" : "password"}
                                            className={`w-full pl-10 pr-10 py-2.5 border rounded-xl bg-slate-50 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:border-transparent focus:bg-white transition-all ${confirmPassword.length > 0
                                                ? passwordsMatch
                                                    ? "border-emerald-300 focus:ring-emerald-400"
                                                    : "border-red-300 focus:ring-red-400"
                                                : "border-slate-200 focus:ring-blue-500"
                                                }`}
                                            placeholder="••••••••"
                                            value={confirmPassword}
                                            onChange={(e) => setConfirmPassword(e.target.value)}
                                            required
                                        />
                                        <button
                                            type="button"
                                            onClick={() => setShowConfirm(!showConfirm)}
                                            className="absolute right-3.5 top-1/2 -translate-y-1/4 text-slate-400 hover:text-slate-600 transition-colors"
                                        >
                                            {showConfirm ? <EyeOff size={16} /> : <Eye size={16} />}
                                        </button>
                                    </div>

                                    {confirmPassword.length > 0 && (
                                        <p className={`text-xs flex items-center gap-1 mt-0.5 ${passwordsMatch ? "text-emerald-600" : "text-red-500"}`}>
                                            {passwordsMatch
                                                ? <><CheckCircle2 size={12} /> Les mots de passe correspondent.</>
                                                : <><AlertCircle size={12} /> Les mots de passe ne correspondent pas.</>
                                            }
                                        </p>
                                    )}
                                </div>

                                {error && (
                                    <div className="flex items-center gap-2 bg-red-50 border border-red-200 rounded-xl px-4 py-3 text-red-600 text-sm">
                                        <AlertCircle size={15} className="shrink-0" />
                                        {error}
                                    </div>
                                )}

                                <button
                                    type="submit"
                                    disabled={isLoading || !allRulesMet || !passwordsMatch}
                                    className="w-full flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 active:bg-blue-800 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold text-sm py-3 rounded-xl shadow-lg shadow-blue-200 hover:shadow-blue-300 transition-all"
                                >
                                    {isLoading ? (
                                        <>
                                            <svg className="animate-spin h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
                                            </svg>
                                            Enregistrement…
                                        </>
                                    ) : (
                                        <>
                                            Confirmer le mot de passe
                                            <ArrowRight size={16} />
                                        </>
                                    )}
                                </button>

                            </form>
                        )}
                    </div>

                    <p className="text-center text-slate-400 text-xs mt-3 flex items-center justify-center gap-1.5">
                        <ShieldCheck size={12} />
                        Connexion chiffrée TLS 1.3 · Conforme HDS
                    </p>
                </div>
            </div>

            <style>{`
                @keyframes progress {
                    from { width: 100%; }
                    to   { width: 0%; }
                }
            `}</style>
        </div>
    );
};

export default ChangePassword;