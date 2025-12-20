import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const Login: React.FC = () => {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const { login } = useAuth();
    const navigate = useNavigate();

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        setLoading(true);

        const success = await login(email, password);

        if (success) {
            navigate('/');
        } else {
            setError('Invalid email or password');
        }

        setLoading(false);
    };

    return (
        <div style={{
            minHeight: '100vh',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '20px',
        }}>
            <div style={{
                background: 'rgba(255, 255, 255, 0.85)',
                backdropFilter: 'blur(20px)',
                borderRadius: '24px',
                padding: '44px',
                width: '100%',
                maxWidth: '420px',
                boxShadow: '0 16px 48px rgba(6, 78, 59, 0.12)',
                border: '1px solid rgba(255, 255, 255, 0.9)',
            }}>
                {/* Header */}
                <div style={{ marginBottom: '32px', textAlign: 'center' }}>
                    <div style={{
                        width: '56px',
                        height: '56px',
                        background: 'linear-gradient(135deg, #059669, #10b981)',
                        borderRadius: '14px',
                        margin: '0 auto 16px',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        boxShadow: '0 4px 14px rgba(5, 150, 105, 0.3)',
                    }}>
                        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5">
                            <path d="M12 2L2 7l10 5 10-5-10-5z" />
                            <path d="M2 17l10 5 10-5" />
                            <path d="M2 12l10 5 10-5" />
                        </svg>
                    </div>
                    <h1 style={{
                        fontSize: '1.75rem',
                        fontWeight: '700',
                        color: '#065f46',
                        marginBottom: '8px',
                        letterSpacing: '-0.02em',
                    }}>
                        Catalyze
                    </h1>
                    <p style={{ color: '#78716c', fontSize: '14px' }}>
                        Sign in to your account
                    </p>
                </div>

                {error && (
                    <div style={{
                        background: 'linear-gradient(135deg, #fee2e2, #fecaca)',
                        border: '1px solid #fca5a5',
                        borderRadius: '10px',
                        padding: '12px 16px',
                        marginBottom: '20px',
                        color: '#b91c1c',
                        fontSize: '14px',
                    }}>
                        {error}
                    </div>
                )}

                <form onSubmit={handleSubmit}>
                    <div style={{ marginBottom: '18px' }}>
                        <label style={{
                            display: 'block',
                            marginBottom: '6px',
                            fontWeight: '500',
                            color: '#374151',
                            fontSize: '14px',
                        }}>
                            Email
                        </label>
                        <input
                            type="email"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            placeholder="you@example.com"
                            required
                        />
                    </div>

                    <div style={{ marginBottom: '24px' }}>
                        <label style={{
                            display: 'block',
                            marginBottom: '6px',
                            fontWeight: '500',
                            color: '#374151',
                            fontSize: '14px',
                        }}>
                            Password
                        </label>
                        <input
                            type="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            placeholder="Enter your password"
                            required
                        />
                    </div>

                    <button
                        type="submit"
                        disabled={loading}
                        style={{
                            width: '100%',
                            padding: '14px',
                            background: 'linear-gradient(135deg, #059669, #10b981)',
                            color: 'white',
                            border: 'none',
                            borderRadius: '12px',
                            fontSize: '15px',
                            fontWeight: '600',
                            cursor: loading ? 'not-allowed' : 'pointer',
                            opacity: loading ? 0.7 : 1,
                            boxShadow: '0 4px 14px rgba(5, 150, 105, 0.3)',
                            transition: 'all 0.25s ease',
                        }}
                    >
                        {loading ? 'Signing in...' : 'Sign in'}
                    </button>
                </form>

                <div style={{
                    marginTop: '24px',
                    textAlign: 'center',
                    paddingTop: '20px',
                    borderTop: '1px solid #e5e7eb',
                }}>
                    <p style={{ color: '#78716c', fontSize: '14px' }}>
                        Don't have an account?{' '}
                        <Link to="/register" style={{
                            color: '#059669',
                            fontWeight: '600',
                            textDecoration: 'none',
                        }}>
                            Create account
                        </Link>
                    </p>
                </div>
            </div>
        </div>
    );
};

export default Login;
