import React, { useState } from "react";
import { Mail, Lock, Eye, EyeOff, ShieldCheck, ArrowRight, Stethoscope, Activity, AlertCircle } from "lucide-react";
import { useNavigate } from "react-router-dom";
import authService from "../services/AuthService";

const Login = () => {
    const navigate = useNavigate();
    const [email,        setEmail]        = useState("");
    const [password,     setPassword]     = useState("");
    const [error,        setError]        = useState("");
    const [showPassword, setShowPassword] = useState(false);
    const [isLoading,    setIsLoading]    = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError("");
        setIsLoading(true);

        try {
            const data = await authService.login(email, password);

            if (data.is_first_login) {
                navigate("/change-password");
                return;
            }

            // ── Redirection selon le rôle ─────────────────
            const role = data.role?.toLowerCase();
            if (role === "admin") {
                navigate("/dashboard/admin");
            } else if (role === "doctor") {
                navigate("/dashboard/doctor");
            } else if (role === "pharmacist") {
                navigate("/dashboard/pharmacist");
            } else {
                navigate("/dashboard/doctor"); // fallback pour rôles inconnus
            }

        } catch (err) {
            const message = err.response?.data?.detail || "Échec de la connexion";
            setError(message);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="h-screen w-full overflow-hidden flex">

            <div className="hidden md:flex md:w-1/2 bg-blue-950 flex-col items-center justify-center p-12 relative overflow-hidden">
                <div className="absolute -top-24 -right-24 w-96 h-96 bg-blue-500 rounded-full opacity-10 blur-3xl" />
                <div className="absolute -bottom-16 -left-16 w-72 h-72 bg-blue-400 rounded-full opacity-10 blur-3xl" />
                <div className="absolute inset-0 opacity-10"
                    style={{
                        backgroundImage: "radial-gradient(circle, rgba(255,255,255,0.8) 1px, transparent 1px)",
                        backgroundSize: "24px 24px"
                    }}
                />
                <div className="relative z-10 w-full max-w-sm">
                    <div className="w-14 h-14 rounded-2xl bg-blue-500 bg-opacity-30 border border-blue-400 border-opacity-30 flex items-center justify-center mb-6">
                        <ShieldCheck size={28} className="text-blue-300" strokeWidth={1.5} />
                    </div>
                    <h2 className="text-3xl font-bold text-white leading-snug mb-3">
                        Décisions cliniques<br />
                        <span className="text-blue-300">plus sûres.</span>
                    </h2>
                    <p className="text-slate-400 text-sm leading-relaxed mb-10">
                        SafeRx AI analyse les ordonnances en temps réel et prévient
                        les erreurs médicamenteuses avant qu'elles ne surviennent.
                    </p>
                    <div className="flex flex-col gap-3">
                        <div className="flex items-center gap-3 bg-white bg-opacity-5 border border-white border-opacity-10 rounded-2xl px-4 py-3 backdrop-blur-sm">
                            <div className="w-10 h-10 rounded-xl bg-blue-500 bg-opacity-25 flex items-center justify-center shrink-0">
                                <Activity size={18} className="text-blue-300" />
                            </div>
                            <div className="text-white font-bold text-lg leading-none">Précision de détection</div>
                        </div>
                        <div className="flex items-center gap-3 bg-white bg-opacity-5 border border-white border-opacity-10 rounded-2xl px-4 py-3 backdrop-blur-sm">
                            <div className="w-10 h-10 rounded-xl bg-emerald-500 bg-opacity-20 flex items-center justify-center shrink-0">
                                <Stethoscope size={18} className="text-emerald-300" />
                            </div>
                            <div className="text-white font-bold text-lg leading-none">Médecins actifs</div>
                        </div>
                    </div>
                </div>
            </div>

            <div className="w-full md:w-1/2 flex flex-col items-center justify-center h-screen bg-slate-50 px-6">
                <div className="w-full max-w-sm">
                    <div className="text-center mb-8">
                        <span className="inline-flex items-center gap-1.5 bg-blue-50 border border-blue-100 text-blue-600 text-xs font-semibold px-3 py-1.5 rounded-full uppercase tracking-wide mb-4">
                            <ShieldCheck size={11} />
                            Accès sécurisé
                        </span>
                        <h1 className="text-2xl font-bold text-slate-800 mb-1">Bienvenue</h1>
                        <p className="text-slate-500 text-sm">Connectez-vous à votre espace SafeRx AI</p>
                    </div>

                    <div className="bg-white rounded-2xl shadow-xl shadow-slate-200 border border-slate-100 p-8">
                        <form className="flex flex-col gap-5" onSubmit={handleSubmit}>

                            <div className="flex flex-col gap-1.5">
                                <label className="text-sm font-semibold text-slate-700">Adresse email</label>
                                <div className="relative">
                                    <Mail size={16} className="absolute left-3.5 top-1/2 -translate-y-1/4 text-slate-400 pointer-events-none" />
                                    <input
                                        type="email"
                                        className="w-full pl-10 pr-4 py-2.5 border border-slate-200 rounded-xl bg-slate-50 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent focus:bg-white transition-all"
                                        placeholder="docteur@hopital.ma"
                                        value={email}
                                        onChange={e => setEmail(e.target.value)}
                                        required
                                    />
                                </div>
                            </div>

                            <div className="flex flex-col gap-1.5">
                                <div className="flex justify-between items-center">
                                    <label className="text-sm font-semibold text-slate-700">Mot de passe</label>
                                </div>
                                <div className="relative">
                                    <Lock size={16} className="absolute left-3.5 top-1/2 -translate-y-1/4 text-slate-400 pointer-events-none" />
                                    <input
                                        type={showPassword ? "text" : "password"}
                                        className="w-full pl-10 pr-10 py-2.5 border border-slate-200 rounded-xl bg-slate-50 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent focus:bg-white transition-all"
                                        placeholder="••••••••"
                                        value={password}
                                        onChange={e => setPassword(e.target.value)}
                                        required
                                    />
                                    <button
                                        type="button"
                                        onClick={() => setShowPassword(!showPassword)}
                                        className="absolute right-3.5 top-1/2 -translate-y-1/4 text-slate-400 hover:text-slate-600 transition-colors">
                                        {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                                    </button>
                                </div>
                            </div>

                            {error && (
                                <div className="flex items-center gap-2 bg-red-50 border border-red-200 rounded-xl px-4 py-3 text-red-600 text-sm">
                                    <AlertCircle size={15} className="shrink-0" />
                                    {error}
                                </div>
                            )}

                            <button
                                type="submit"
                                disabled={isLoading}
                                className="w-full flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 active:bg-blue-800 disabled:opacity-70 disabled:cursor-not-allowed text-white font-semibold text-sm py-3 rounded-xl shadow-lg shadow-blue-200 hover:shadow-blue-300 transition-all">
                                {isLoading ? (
                                    <>
                                        <svg className="animate-spin h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
                                        </svg>
                                        Connexion en cours…
                                    </>
                                ) : (
                                    <>Se connecter <ArrowRight size={16} /></>
                                )}
                            </button>
                        </form>
                    </div>

                    <p className="text-center text-slate-400 text-xs mt-3 flex items-center justify-center gap-1.5">
                        <ShieldCheck size={12} />
                        Connexion chiffrée TLS 1.3 · Conforme HDS
                    </p>
                </div>
            </div>
        </div>
    );
};

export default Login;