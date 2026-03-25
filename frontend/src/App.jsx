import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";
import Login          from "./pages/Login";
import ChangePassword from "./pages/ChangePassword";
import AdminDashboard from "./pages/AdminDashboard";
import DoctorDashboard from "./pages/DoctorDashboard";
import PharmacistDashboard from "./pages/PharmacistDashboard";
import authService    from "./services/AuthService";
import "./App.css";



function PrivateRoute({ children, allowedRoles }) {
    if (!authService.isAuthenticated()) {
        return <Navigate to="/login" replace />;
    }
    if (allowedRoles) {
        const user = authService.getUser();
        if (!user || !allowedRoles.includes(user.role?.toLowerCase())) {
            return <Navigate to="/login" replace />;
        }
    }
    return children;
}

function App() {
    return (
        <Router>
            <Routes>
                {/* ── Publiques ────────────────────────────────────── */}
                <Route path="/"       element={<Navigate to="/login" replace />} />
                <Route path="/login"  element={<Login />} />

                {/* ── Première connexion ───────────────────────────── */}
                <Route path="/change-password" element={
                    <PrivateRoute>
                        <ChangePassword />
                    </PrivateRoute>
                } />

                {/* ── Dashboard Admin ──────────────────────────────── */}
                <Route path="/dashboard/admin" element={
                    <PrivateRoute allowedRoles={["admin"]}>
                        <AdminDashboard />
                    </PrivateRoute>
                } />

                {/* ── Dashboard Médecin ───────────────── */}
                <Route path="/dashboard/doctor" element={
                    <PrivateRoute allowedRoles={["doctor"]}>
                        <DoctorDashboard />
                    </PrivateRoute>
                } />

                {/* ── Dashboard Pharmacien ───────────────── */}
                <Route path="/dashboard/pharmacist" element={
                    <PrivateRoute allowedRoles={["pharmacist"]}>
                        <PharmacistDashboard />
                    </PrivateRoute>
                } />

                {/* ── Fallback ─────────────────────────────────────── */}
                <Route path="*" element={<Navigate to="/login" replace />} />
            </Routes>
        </Router>
    );
}

export default App;