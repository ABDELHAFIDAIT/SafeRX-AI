import { useState, useEffect, useCallback, useRef } from "react";
import {
    Pill, ClipboardList, LogOut, Search, Clock,
    Shield, Printer, Download, RefreshCw, ChevronDown, ChevronUp,
    AlertCircle, User, Calendar, Hash, AlertTriangle, CheckCircle2
} from "lucide-react";
import jsPDF from "jspdf";
import html2canvas from "html2canvas";
import authService from "../services/AuthService";
import api from "../api/api";

/* ── Helpers ─────────────────────────────────────────────────────────────── */
const getAge = (birthdate) => {
    if (!birthdate) return "?";
    return new Date().getFullYear() - new Date(birthdate).getFullYear();
};

const Spinner = ({ size = 16 }) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
        className="animate-spin" stroke="currentColor" strokeWidth="2">
        <circle cx="12" cy="12" r="10" strokeOpacity=".25" />
        <path d="M12 2a10 10 0 0 1 10 10" strokeLinecap="round" />
    </svg>
);

const Tag = ({ color = "slate", children }) => {
    const c = {
        green: "bg-green-50  text-green-700  border-green-200",
        red: "bg-red-50    text-red-700    border-red-200",
        amber: "bg-amber-50  text-amber-700  border-amber-200",
        blue: "bg-blue-50   text-blue-700   border-blue-200",
        slate: "bg-slate-100 text-slate-600  border-slate-200",
    }[color] ?? "bg-slate-100 text-slate-600 border-slate-200";
    return (
        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-lg border text-xs font-medium ${c}`}>
            {children}
        </span>
    );
};

/* ── Composant Alerte Détaillée (Phase 2) ─────────────────────────────────── */
const AlertDetailCard = ({ alert }) => {
    const [expanded, setExpanded] = useState(false);

    const severityColor = {
        MAJOR: "bg-red-50 text-red-700 border-red-200",
        MODERATE: "bg-amber-50 text-amber-700 border-amber-200",
        MINOR: "bg-blue-50 text-blue-700 border-blue-200",
    };

    const severityIcon = {
        MAJOR: <AlertTriangle size={14} className="text-red-600" />,
        MODERATE: <AlertCircle size={14} className="text-amber-600" />,
        MINOR: <AlertCircle size={14} className="text-blue-600" />,
    };

    const alertTypeLabel = {
        INTERACTION: "Interaction",
        ALLERGY: "Allergie",
        CONTRA_INDICATION: "Contre-indication",
        POSOLOGY: "Posologie",
        REDUNDANT_DCI: "Redondance DCI",
    };

    return (
        <div className={`border rounded-xl p-3 ${severityColor[alert.severity] || "bg-slate-50 text-slate-700 border-slate-200"}`}>
            <button
                onClick={() => setExpanded(!expanded)}
                className="w-full flex items-start gap-2"
            >
                <div className="mt-0.5 shrink-0">{severityIcon[alert.severity]}</div>
                <div className="flex-1 text-left min-w-0">
                    <div className="flex items-center justify-between gap-2">
                        <p className="text-xs font-semibold">{alertTypeLabel[alert.alert_type] || alert.alert_type}</p>
                        {alert.rag_explanation && (
                            expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />
                        )}
                    </div>
                    <p className="text-xs font-medium mt-0.5">{alert.title}</p>
                </div>
            </button>

            {expanded && (
                <div className="mt-3 pt-3 border-t border-current border-opacity-20">
                    {alert.detail && (
                        <div className="mb-2">
                            <p className="text-xs font-medium mb-1">Détails:</p>
                            <p className="text-xs opacity-90">{alert.detail}</p>
                        </div>
                    )}
                    {alert.rag_explanation && (
                        <div>
                            <p className="text-xs font-medium mb-1">Explication IA:</p>
                            <p className="text-xs opacity-90 italic">{alert.rag_explanation}</p>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
};

/* ── Composant d'impression ──────────────────────────────────────────────── */
const PrintablePrescription = ({ presc, patient }) => {
    if (!presc) return null;
    const date = new Date(presc.created_at).toLocaleDateString("fr-FR", {
        year: "numeric", month: "long", day: "numeric"
    });
    return (
        <div id="print-zone" className="hidden print:block p-8 font-sans text-sm text-slate-900">
            <div className="border-b-2 border-slate-900 pb-4 mb-6">
                <h1 className="text-2xl font-bold">SafeRx AI</h1>
                <p className="text-slate-500 text-xs mt-1">Système de prescription médicale</p>
            </div>
            <div className="flex justify-between mb-6">
                <div>
                    <p className="text-xs text-slate-500 uppercase tracking-wide font-semibold">Prescription</p>
                    <p className="font-bold text-lg">#{presc.id}</p>
                </div>
                <div className="text-right">
                    <p className="text-xs text-slate-500 uppercase tracking-wide font-semibold">Date</p>
                    <p className="font-medium">{date}</p>
                </div>
            </div>
            {patient && (
                <div className="bg-slate-100 rounded-lg p-4 mb-6">
                    <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Patient</p>
                    <p className="font-semibold">Patient #{patient.id}</p>
                    <p className="text-slate-600 text-xs mt-0.5">
                        {getAge(patient.birthdate)} ans ·{" "}
                        {patient.gender === "M" ? "Homme" : patient.gender === "F" ? "Femme" : "Autre"}
                        {patient.known_allergies?.length > 0
                            ? ` · Allergies : ${patient.known_allergies.join(", ")}`
                            : ""}
                    </p>
                </div>
            )}
            <table className="w-full border-collapse text-sm">
                <thead>
                    <tr className="border-b-2 border-slate-900">
                        <th className="text-left py-2 pr-4 font-semibold">Médicament (DCI)</th>
                        <th className="text-left py-2 pr-4 font-semibold">Dose</th>
                        <th className="text-left py-2 pr-4 font-semibold">Fréquence</th>
                        <th className="text-left py-2 pr-4 font-semibold">Voie</th>
                        <th className="text-left py-2 font-semibold">Durée</th>
                    </tr>
                </thead>
                <tbody>
                    {presc.lines?.map((line, i) => (
                        <tr key={line.id} className="border-b border-slate-200">
                            <td className="py-3 pr-4 font-medium">{line.dci}</td>
                            <td className="py-3 pr-4">{line.dose_mg} {line.dose_unit_raw || "mg"}</td>
                            <td className="py-3 pr-4">{line.frequency || "—"}</td>
                            <td className="py-3 pr-4">{line.route || "—"}</td>
                            <td className="py-3">{line.duration_days ? `${line.duration_days} j` : "—"}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
            <div className="mt-8 pt-4 border-t border-slate-300 text-xs text-slate-400 flex justify-between">
                <span>Imprimé le {new Date().toLocaleDateString("fr-FR")} via SafeRx AI</span>
                <span>Document confidentiel — Usage médical uniquement</span>
            </div>
        </div>
    );
};

/* ═══════════════════════════════════════════════════════════════════════════
   COMPOSANT PRINCIPAL
═══════════════════════════════════════════════════════════════════════════ */
export default function PharmacistDashboard() {
    const user = authService.getUser();
    const [activeNav, setActiveNav] = useState("prescriptions");

    const NAV = [
        { id: "prescriptions", icon: ClipboardList, label: "Prescriptions" },
        { id: "drugs", icon: Pill, label: "Médicaments" },
    ];

    /* ── État Prescriptions ────────────────────────────────────────────── */
    const [patientId, setPatientId] = useState("");
    const [patient, setPatient] = useState(null);
    const [prescriptions, setPrescriptions] = useState([]);
    const [prescLoading, setPrescLoading] = useState(false);
    const [prescErr, setPrescErr] = useState("");
    const [selectedPresc, setSelectedPresc] = useState(null);

    /* ── État Médicaments ──────────────────────────────────────────────── */
    const [drugQuery, setDrugQuery] = useState("");
    const [drugResults, setDrugResults] = useState([]);
    const [drugLoading, setDrugLoading] = useState(false);
    const [selectedDrug, setSelectedDrug] = useState(null);
    const [drugComponentsTab, setDrugComponentsTab] = useState("composition");
    const [drugFullData, setDrugFullData] = useState(null);

    /* ── Charger prescriptions + patient ───────────────────────────────── */
    const loadPrescriptions = useCallback(async () => {
        if (!patientId.trim()) return;
        setPrescLoading(true); setPrescErr(""); setPrescriptions([]);
        setSelectedPresc(null); setPatient(null);
        try {
            // Charger le patient
            const pRes = await api.get(`/patients/search?q=${encodeURIComponent(patientId.trim())}`);
            if (pRes.data?.length) setPatient(pRes.data[0]);

            // Charger les prescriptions
            const id = pRes.data?.[0]?.id || patientId.trim();
            const res = await api.get(`/prescriptions/patient/${id}`);
            const data = res.data || [];
            setPrescriptions(data);
            if (!data.length) setPrescErr("Aucune prescription trouvée pour ce patient.");
        } catch {
            setPrescErr("Patient introuvable ou erreur serveur.");
        } finally {
            setPrescLoading(false);
        }
    }, [patientId]);

    /* ── Impression ────────────────────────────────────────────────────── */
    const handlePrint = () => window.print();

    /* ── Téléchargement PDF (Phase 1) ──────────────────────────────────── */
    const handleDownloadPDF = async () => {
        if (!selectedPresc || !patient) return;

        try {
            const element = document.getElementById("print-zone");
            if (!element) {
                alert("Élément de prescription non trouvé");
                return;
            }

            // ✅ FIX: Rendre l'élément temporairement visible (classe 'hidden' bloque html2canvas)
            const originalDisplay = element.style.display;
            element.style.display = "block";

            const canvas = await html2canvas(element, {
                scale: 2,
                useCORS: true,
                logging: false,
                allowTaint: true
            });

            // ✅ Restaurer le style original
            element.style.display = originalDisplay;

            const imgData = canvas.toDataURL("image/png");
            const pdf = new jsPDF("p", "mm", "a4");

            const pageWidth = pdf.internal.pageSize.getWidth();
            const pageHeight = pdf.internal.pageSize.getHeight();
            const imgWidth = pageWidth - 20;
            const imgHeight = (canvas.height * imgWidth) / canvas.width;

            let heightLeft = imgHeight;
            let position = 10;

            pdf.addImage(imgData, "PNG", 10, position, imgWidth, imgHeight);
            heightLeft -= pageHeight - 20;

            while (heightLeft > 0) {
                position = heightLeft - imgHeight;
                pdf.addPage();
                pdf.addImage(imgData, "PNG", 10, position, imgWidth, imgHeight);
                heightLeft -= pageHeight - 20;
            }

            const dateStr = new Date(selectedPresc.created_at).toISOString().split("T")[0];
            pdf.save(`prescription_${selectedPresc.id}_${dateStr}.pdf`);
        } catch (err) {
            console.error("Erreur génération PDF:", err);
            alert("Erreur lors de la génération du PDF: " + (err.message || err));
        }
    };

    /* ── Recherche médicaments ─────────────────────────────────────────── */
    useEffect(() => {
        if (!drugQuery.trim()) {
            setDrugResults([]);
            setSelectedDrug(null);
            setDrugFullData(null);
            return;
        }
        const t = setTimeout(async () => {
            setDrugLoading(true);
            try {
                const res = await api.get(`/drugs/search?q=${encodeURIComponent(drugQuery.trim())}&limit=15`);
                setDrugResults(res.data || []);
            } catch {
                setDrugResults([]);
            }
            finally {
                setDrugLoading(false);
            }
        }, 300);
        return () => clearTimeout(t);
    }, [drugQuery]);

    /* ── Charger détails complets du médicament (Phase 3) ────────────── */
    const loadDrugDetails = useCallback(async (drugId) => {
        try {
            const res = await api.get(`/drugs/${drugId}`);
            setDrugFullData(res.data);
            setDrugComponentsTab("composition");
        } catch (err) {
            console.error("Erreur chargement médicament:", err);
            setDrugFullData(null);
        }
    }, []);

    const handleSelectDrug = (drug) => {
        setSelectedDrug(drug);
        loadDrugDetails(drug.id);
    };

    /* ─────────────────────────────────────────────────────────────────────
       RENDU
    ───────────────────────────────────────────────────────────────────── */
    return (
        <>
            {/* Zone imprimable (invisible à l'écran, visible à l'impression) */}
            <style>{`
            @media print {
                body > * { display: none !important; }
                #print-zone { display: block !important; }
            }
        `}</style>
            <PrintablePrescription presc={selectedPresc} patient={patient} />

            <div className="flex h-screen bg-slate-50 font-sans">

                {/* ── Sidebar ───────────────────────────────────────────────── */}
                <aside className="w-56 bg-slate-900 flex flex-col shrink-0">
                    <div className="px-5 py-5 border-b border-slate-800">
                        <div className="flex items-center gap-2">
                            <div className="w-7 h-7 rounded-lg bg-emerald-500 flex items-center justify-center">
                                <Shield size={14} className="text-white" />
                            </div>
                            <span className="text-white font-bold text-sm tracking-tight">SafeRx AI</span>
                        </div>
                        <p className="text-emerald-400 text-xs mt-1 font-medium">Pharmacien</p>
                    </div>

                    <nav className="flex-1 p-3 space-y-1">
                        {NAV.map(({ id, icon: Icon, label }) => (
                            <button key={id} onClick={() => setActiveNav(id)}
                                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all ${activeNav === id
                                        ? "bg-emerald-500 text-white"
                                        : "text-slate-400 hover:text-white hover:bg-slate-800"
                                    }`}>
                                <Icon size={16} />{label}
                            </button>
                        ))}
                    </nav>

                    <div className="p-3 border-t border-slate-800">
                        <div className="px-3 py-2 mb-2">
                            <p className="text-white text-xs font-semibold truncate">
                                {user?.first_name} {user?.last_name}
                            </p>
                            <p className="text-slate-500 text-xs truncate">{user?.email}</p>
                        </div>
                        <button onClick={() => { authService.logout(); window.location.href = "/login"; }}
                            className="w-full flex items-center gap-2 px-3 py-2 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800 text-sm transition-all">
                            <LogOut size={14} /> Déconnexion
                        </button>
                    </div>
                </aside>

                {/* ── Main ──────────────────────────────────────────────────── */}
                <main className="flex-1 overflow-y-auto">

                    {/* Topbar */}
                    <header className="sticky top-0 z-20 bg-slate-50 border-b border-slate-200 px-6 py-4 flex items-center justify-between">
                        <div>
                            <h1 className="text-lg font-bold text-slate-800">
                                {activeNav === "prescriptions" ? "Prescriptions" : "Médicaments"}
                            </h1>
                            <p className="text-xs text-slate-400">
                                {activeNav === "prescriptions"
                                    ? "Historique des prescriptions par patient — lecture et impression"
                                    : "Catalogue médicamentaire SafeRx"}
                            </p>
                        </div>
                        <div className="flex items-center gap-3">
                            {activeNav === "prescriptions" && selectedPresc && (
                                <>
                                    <button onClick={handlePrint}
                                        className="flex items-center gap-2 px-4 py-2 border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-sm font-medium rounded-xl transition-all">
                                        <Printer size={14} /> Imprimer
                                    </button>
                                    <button onClick={handleDownloadPDF}
                                        className="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-semibold rounded-xl transition-all shadow-md shadow-emerald-200">
                                        <Download size={14} /> PDF
                                    </button>
                                </>
                            )}
                            <div className="flex items-center gap-2 bg-white border border-slate-200 rounded-xl px-3 py-2">
                                <Clock size={13} className="text-slate-400" />
                                <span className="text-xs text-slate-600 font-medium">
                                    {new Date().toLocaleDateString("fr-FR", { weekday: "long", day: "numeric", month: "long" })}
                                </span>
                            </div>
                        </div>
                    </header>

                    {/* ══════════════════════════════════════════════════════════
                    VUE PRESCRIPTIONS
                ══════════════════════════════════════════════════════════ */}
                    {activeNav === "prescriptions" && (
                        <div className="p-6 flex gap-6">

                            {/* Panneau gauche : recherche + liste */}
                            <div className="w-72 shrink-0 space-y-4">

                                {/* Recherche patient */}
                                <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-4">
                                    <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">
                                        Recherche patient
                                    </p>
                                    <div className="flex gap-2">
                                        <div className="relative flex-1">
                                            <Hash size={13} className="absolute left-3 top-3 text-slate-400" />
                                            <input value={patientId}
                                                onChange={e => setPatientId(e.target.value)}
                                                onKeyDown={e => e.key === "Enter" && loadPrescriptions()}
                                                placeholder="ID patient…"
                                                className="w-full pl-8 pr-3 py-2.5 border border-slate-200 rounded-xl bg-slate-50 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:bg-white transition-all" />
                                        </div>
                                        <button onClick={loadPrescriptions} disabled={prescLoading}
                                            className="px-3 py-2 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-60 text-white rounded-xl transition-all flex items-center justify-center">
                                            {prescLoading ? <Spinner size={14} /> : <Search size={14} />}
                                        </button>
                                    </div>

                                    {/* Fiche patient résumée */}
                                    {patient && (
                                        <div className="mt-3 p-3 bg-emerald-50 border border-emerald-100 rounded-xl">
                                            <div className="flex items-center gap-2">
                                                <div className="w-8 h-8 rounded-lg bg-slate-900 flex items-center justify-center text-white text-xs font-bold shrink-0">
                                                    P{patient.id}
                                                </div>
                                                <div>
                                                    <p className="text-xs font-semibold text-slate-800">Patient #{patient.id}</p>
                                                    <p className="text-xs text-slate-500">
                                                        {getAge(patient.birthdate)} ans ·{" "}
                                                        {patient.gender === "M" ? "Homme" : patient.gender === "F" ? "Femme" : "Autre"}
                                                    </p>
                                                </div>
                                            </div>
                                            {patient.known_allergies?.length > 0 && (
                                                <div className="mt-2 flex flex-wrap gap-1">
                                                    {patient.known_allergies.map(a => (
                                                        <span key={a} className="text-xs bg-red-50 text-red-700 border border-red-200 px-1.5 py-0.5 rounded-md">
                                                            {a}
                                                        </span>
                                                    ))}
                                                </div>
                                            )}
                                        </div>
                                    )}

                                    {prescErr && (
                                        <p className="mt-2 text-xs text-amber-600 flex items-center gap-1">
                                            <AlertCircle size={12} /> {prescErr}
                                        </p>
                                    )}
                                </div>

                                {/* Liste des prescriptions */}
                                {prescriptions.length > 0 && (
                                    <div className="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden">
                                        <p className="px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide border-b border-slate-100">
                                            {prescriptions.length} prescription(s)
                                        </p>
                                        {prescriptions.map(p => (
                                            <button key={p.id} onClick={() => setSelectedPresc(p)}
                                                className={`w-full text-left px-4 py-3 border-b border-slate-100 last:border-0 transition-all ${selectedPresc?.id === p.id
                                                        ? "bg-emerald-50"
                                                        : "hover:bg-slate-50"
                                                    }`}>
                                                <div className="flex items-center justify-between">
                                                    <span className="text-sm font-semibold text-slate-800">
                                                        #{p.id}
                                                    </span>
                                                    <Tag color={p.status === "safe" ? "green" : "red"}>
                                                        {p.status === "safe" ? "Sûre" : "Alertes"}
                                                    </Tag>
                                                </div>
                                                <div className="flex items-center gap-2 mt-0.5">
                                                    <Calendar size={10} className="text-slate-400" />
                                                    <span className="text-xs text-slate-400">
                                                        {new Date(p.created_at).toLocaleDateString("fr-FR")}
                                                    </span>
                                                    <span className="text-xs text-slate-400">·</span>
                                                    <span className="text-xs text-slate-400">
                                                        {p.lines?.length || 0} ligne(s)
                                                    </span>
                                                </div>
                                            </button>
                                        ))}
                                    </div>
                                )}
                            </div>

                            {/* Panneau droit : détail de la prescription */}
                            <div className="flex-1 min-w-0">
                                {!selectedPresc ? (
                                    <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-16 text-center">
                                        <ClipboardList size={36} className="mx-auto text-slate-200 mb-3" />
                                        <p className="text-slate-400 text-sm font-medium">Recherchez un patient</p>
                                        <p className="text-slate-300 text-xs mt-1">puis sélectionnez une prescription</p>
                                    </div>
                                ) : (
                                    <div className="space-y-4">
                                        {/* En-tête prescription */}
                                        <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-5">
                                            <div className="flex items-center justify-between">
                                                <div>
                                                    <h2 className="font-bold text-slate-800 text-base">
                                                        Prescription #{selectedPresc.id}
                                                    </h2>
                                                    <p className="text-xs text-slate-500 mt-0.5">
                                                        Créée le{" "}
                                                        {new Date(selectedPresc.created_at).toLocaleString("fr-FR")}
                                                    </p>
                                                </div>
                                                <Tag color={selectedPresc.status === "safe" ? "green" : "amber"}>
                                                    {selectedPresc.status === "safe" ? "Prescription sûre" : "Vérifiée par médecin"}
                                                </Tag>
                                            </div>
                                        </div>

                                        {/* Lignes de prescription avec alertes (Phase 2) */}
                                        {selectedPresc.lines?.map((line, i) => {
                                            const hasAlerts = line.alerts && line.alerts.length > 0;
                                            return (
                                                <div key={line.id}
                                                    className="bg-white rounded-2xl border border-slate-100 shadow-sm p-5">
                                                    <div className="flex items-start gap-4">
                                                        <div className="w-8 h-8 rounded-xl bg-emerald-50 flex items-center justify-center shrink-0">
                                                            <span className="text-xs font-bold text-emerald-700">{i + 1}</span>
                                                        </div>
                                                        <div className="flex-1 min-w-0">
                                                            <p className="font-bold text-slate-800">{line.dci}</p>
                                                            <div className="grid grid-cols-2 gap-3 mt-3">
                                                                {[
                                                                    ["Dose", `${line.dose_mg} ${line.dose_unit_raw || "mg"}`],
                                                                    ["Fréquence", line.frequency || "—"],
                                                                    ["Voie", line.route || "—"],
                                                                    ["Durée", line.duration_days ? `${line.duration_days} jours` : "—"],
                                                                ].map(([label, val]) => (
                                                                    <div key={label} className="bg-slate-50 rounded-xl p-2.5">
                                                                        <p className="text-xs text-slate-400 font-medium">{label}</p>
                                                                        <p className="text-sm text-slate-800 font-semibold mt-0.5">{val}</p>
                                                                    </div>
                                                                ))}
                                                            </div>

                                                            {/* Section Alertes (Phase 2) */}
                                                            {hasAlerts ? (
                                                                <div className="mt-4 pt-4 border-t border-slate-200">
                                                                    <p className="text-xs font-semibold text-slate-600 mb-2 flex items-center gap-1">
                                                                        <AlertCircle size={12} /> Alertes associées ({line.alerts.length})
                                                                    </p>
                                                                    <div className="space-y-2">
                                                                        {line.alerts.map(alert => (
                                                                            <AlertDetailCard key={alert.id} alert={alert} />
                                                                        ))}
                                                                    </div>
                                                                </div>
                                                            ) : (
                                                                <div className="mt-4 pt-4 border-t border-slate-200">
                                                                    <Tag color="green">
                                                                        <CheckCircle2 size={12} /> Aucune alerte
                                                                    </Tag>
                                                                </div>
                                                            )}
                                                        </div>
                                                    </div>
                                                </div>
                                            );
                                        })}
                                    </div>
                                )}
                            </div>
                        </div>
                    )}

                    {/* ══════════════════════════════════════════════════════════
                    VUE MÉDICAMENTS (enrichie avec DCI - Phase 3)
                ══════════════════════════════════════════════════════════ */}
                    {activeNav === "drugs" && (
                        <div className="p-6 flex gap-6">

                            {/* Recherche */}
                            <div className="w-72 shrink-0 space-y-4">
                                <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-4">
                                    <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">
                                        Catalogue médicamentaire
                                    </p>
                                    <div className="relative">
                                        <Search size={14} className="absolute left-3 top-3 text-slate-400" />
                                        <input value={drugQuery}
                                            onChange={e => { setDrugQuery(e.target.value); setSelectedDrug(null); }}
                                            placeholder="Nom commercial ou DCI…"
                                            className="w-full pl-9 pr-3 py-2.5 border border-slate-200 rounded-xl bg-slate-50 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:bg-white transition-all" />
                                    </div>
                                    {drugLoading && (
                                        <div className="mt-2 flex justify-center"><Spinner size={14} /></div>
                                    )}
                                </div>

                                {drugResults.length > 0 && (
                                    <div className="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden max-h-112 overflow-y-auto">
                                        {drugResults.map(d => (
                                            <button key={d.id} onClick={() => handleSelectDrug(d)}
                                                className={`w-full text-left px-4 py-3 border-b border-slate-100 last:border-0 transition-all ${selectedDrug?.id === d.id ? "bg-emerald-50" : "hover:bg-slate-50"
                                                    }`}>
                                                <p className="text-sm font-semibold text-slate-800">{d.brand_name}</p>
                                                {d.dosage_raw && <p className="text-xs text-slate-600">{d.dosage_raw}</p>}
                                                <p className="text-xs text-slate-500 mt-0.5">{d.dci}</p>
                                                <div className="mt-2 flex flex-wrap gap-1">
                                                    {d.labo_name && <Tag color="slate">{d.labo_name}</Tag>}
                                                    {d.product_type && <Tag color="blue">{d.product_type}</Tag>}
                                                    {d.is_psychoactive && <Tag color="red">Psychoactif</Tag>}
                                                </div>
                                                {d.min_age && <p className="text-xs text-amber-600 mt-1">Min: {d.min_age}</p>}
                                                {(d.price_ppv || d.price_hospital) && (
                                                    <p className="text-xs text-slate-400 mt-1">
                                                        {d.price_ppv && `PPV: ${d.price_ppv} MAD`}
                                                        {d.price_ppv && d.price_hospital && " · "}
                                                        {d.price_hospital && `Hôpital: ${d.price_hospital} MAD`}
                                                    </p>
                                                )}
                                            </button>
                                        ))}
                                    </div>
                                )}
                            </div>

                            {/* Fiche médicament enrichie (Phase 3) */}
                            <div className="flex-1 min-w-0">
                                {!selectedDrug ? (
                                    <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-16 text-center">
                                        <Pill size={36} className="mx-auto text-slate-200 mb-3" />
                                        <p className="text-slate-400 text-sm font-medium">Recherchez un médicament</p>
                                        <p className="text-slate-300 text-xs mt-1">pour afficher sa fiche complète</p>
                                    </div>
                                ) : (
                                    <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-6 space-y-5">
                                        {/* En-tête */}
                                        <div>
                                            <h2 className="text-xl font-bold text-slate-800">{selectedDrug.brand_name}</h2>
                                            <p className="text-slate-500 mt-0.5 text-sm">{selectedDrug.dci}</p>
                                            {selectedDrug.labo_name && (
                                                <p className="text-xs text-slate-400 mt-1">Labo: {selectedDrug.labo_name}</p>
                                            )}
                                        </div>

                                        {/* Infos rapides */}
                                        <div className="flex flex-wrap gap-2">
                                            {selectedDrug.is_psychoactive && (
                                                <Tag color="amber">Psychoactif</Tag>
                                            )}
                                            {selectedDrug.min_age && (
                                                <Tag color="blue">À partir de {selectedDrug.min_age}</Tag>
                                            )}
                                        </div>

                                        {/* Onglets Composition / Infos Cliniques (Phase 3) */}
                                        <div>
                                            <div className="flex gap-0 border-b border-slate-200">
                                                <button
                                                    onClick={() => setDrugComponentsTab("composition")}
                                                    className={`px-4 py-2 text-sm font-medium border-b-2 transition-all ${drugComponentsTab === "composition"
                                                            ? "border-emerald-500 text-emerald-600"
                                                            : "border-transparent text-slate-600 hover:text-slate-800"
                                                        }`}
                                                >
                                                    Composition
                                                </button>
                                                <button
                                                    onClick={() => setDrugComponentsTab("clinical")}
                                                    className={`px-4 py-2 text-sm font-medium border-b-2 transition-all ${drugComponentsTab === "clinical"
                                                            ? "border-emerald-500 text-emerald-600"
                                                            : "border-transparent text-slate-600 hover:text-slate-800"
                                                        }`}
                                                >
                                                    Infos Cliniques
                                                </button>
                                            </div>

                                            {/* Onglet Composition */}
                                            {drugComponentsTab === "composition" && (
                                                <div className="mt-4">
                                                    <p className="text-xs font-semibold text-slate-600 mb-3">Composants actifs</p>
                                                    {drugFullData?.dci_components && drugFullData.dci_components.length > 0 ? (
                                                        <div className="space-y-2">
                                                            {drugFullData.dci_components
                                                                .sort((a, b) => a.position - b.position)
                                                                .map(comp => (
                                                                    <div
                                                                        key={comp.id}
                                                                        className={`p-3 rounded-xl border ${comp.position === 1
                                                                                ? "bg-emerald-50 border-emerald-200"
                                                                                : "bg-slate-50 border-slate-200"
                                                                            }`}
                                                                    >
                                                                        <div className="flex items-center justify-between">
                                                                            <div>
                                                                                <p className="text-xs font-semibold text-slate-600">
                                                                                    {comp.position === 1 ? "DCI Primaire" : `DCI Secondaire ${comp.position - 1}`}
                                                                                </p>
                                                                                <p className="text-sm font-medium text-slate-800 mt-0.5">{comp.dci}</p>
                                                                            </div>
                                                                            {comp.position === 1 && (
                                                                                <Tag color="green">Principal</Tag>
                                                                            )}
                                                                        </div>
                                                                    </div>
                                                                ))}
                                                        </div>
                                                    ) : (
                                                        <p className="text-xs text-slate-500 italic">Aucun composant détecté</p>
                                                    )}
                                                </div>
                                            )}

                                            {/* Onglet Infos Cliniques */}
                                            {drugComponentsTab === "clinical" && (
                                                <div className="mt-4 space-y-4">
                                                    {selectedDrug.contraindications && (
                                                        <div className="bg-red-50 border border-red-100 rounded-xl p-4">
                                                            <p className="text-xs font-semibold text-red-700 uppercase tracking-wide mb-2">
                                                                Contre-indications
                                                            </p>
                                                            <p className="text-sm text-red-900 leading-relaxed">
                                                                {selectedDrug.contraindications}
                                                            </p>
                                                        </div>
                                                    )}

                                                    {selectedDrug.indications && (
                                                        <div className="bg-blue-50 border border-blue-100 rounded-xl p-4">
                                                            <p className="text-xs font-semibold text-blue-700 uppercase tracking-wide mb-2">
                                                                Indications
                                                            </p>
                                                            <p className="text-sm text-blue-900 leading-relaxed">
                                                                {selectedDrug.indications}
                                                            </p>
                                                        </div>
                                                    )}

                                                    {selectedDrug.therapeutic_class && (
                                                        <div className="bg-slate-50 border border-slate-200 rounded-xl p-4">
                                                            <p className="text-xs font-semibold text-slate-600 uppercase tracking-wide mb-2">
                                                                Classe thérapeutique
                                                            </p>
                                                            <p className="text-sm text-slate-800">{selectedDrug.therapeutic_class}</p>
                                                        </div>
                                                    )}

                                                    {(selectedDrug.price_ppv || selectedDrug.price_hospital) && (
                                                        <div className="bg-slate-50 border border-slate-200 rounded-xl p-4">
                                                            <p className="text-xs font-semibold text-slate-600 uppercase tracking-wide mb-2">
                                                                Tarification
                                                            </p>
                                                            <div className="text-sm text-slate-800 space-y-1">
                                                                {selectedDrug.price_ppv && (
                                                                    <p>Prix public: <span className="font-semibold">{selectedDrug.price_ppv} MAD</span></p>
                                                                )}
                                                                {selectedDrug.price_hospital && (
                                                                    <p>Prix hôpital: <span className="font-semibold">{selectedDrug.price_hospital} MAD</span></p>
                                                                )}
                                                            </div>
                                                        </div>
                                                    )}
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>
                    )}
                </main>
            </div>
        </>
    );
}
