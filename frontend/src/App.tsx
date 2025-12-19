import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import Login from './pages/Login';
import Register from './pages/Register';
import VendorDashboard from './pages/VendorDashboard';
import ReviewQueue from '../pages/ReviewQueue';
import './index.css';

// Protected route wrapper
const ProtectedRoute = ({ children, allowedRoles }: { children: React.ReactNode; allowedRoles?: string[] }) => {
    const { user, isLoading } = useAuth();

    if (isLoading) {
        return (
            <div style={{
                minHeight: '100vh',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '1.5rem',
            }}>
                🍵 Loading...
            </div>
        );
    }

    if (!user) {
        return <Navigate to="/login" replace />;
    }

    if (allowedRoles && !allowedRoles.includes(user.role)) {
        return <Navigate to="/" replace />;
    }

    return <>{children}</>;
};

// Dashboard router based on role
const Dashboard = () => {
    const { user } = useAuth();

    if (user?.role === 'official') {
        return <ReviewQueue />;
    }

    return <VendorDashboard />;
};

// Main App Content
const AppContent = () => {
    const { user } = useAuth();

    return (
        <Routes>
            <Route path="/login" element={
                user ? <Navigate to="/" replace /> : <Login />
            } />
            <Route path="/register" element={
                user ? <Navigate to="/" replace /> : <Register />
            } />
            <Route path="/" element={
                <ProtectedRoute>
                    <Dashboard />
                </ProtectedRoute>
            } />
            <Route path="/vendor" element={
                <ProtectedRoute allowedRoles={['vendor']}>
                    <VendorDashboard />
                </ProtectedRoute>
            } />
            <Route path="/review" element={
                <ProtectedRoute allowedRoles={['official']}>
                    <ReviewQueue />
                </ProtectedRoute>
            } />
            <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
    );
};

function App() {
    return (
        <AuthProvider>
            <Router>
                <div className="app">
                    <AppContent />
                </div>
            </Router>
        </AuthProvider>
    );
}

export default App;
