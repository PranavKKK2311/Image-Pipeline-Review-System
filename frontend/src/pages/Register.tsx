import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const Register: React.FC = () => {
    const [name, setName] = useState('');
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [role, setRole] = useState<'vendor' | 'official'>('vendor');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const { register } = useAuth();
    const navigate = useNavigate();

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        setLoading(true);

        const success = await register(name, email, password, role);

        if (success) {
            navigate('/');
        } else {
            setError('Registration failed. Email may already be in use.');
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
                maxWidth: '460px',
                boxShadow: '0 16px 48px rgba(6, 78, 59, 0.12)',
                border: '1px solid rgba(255, 255, 255, 0.9)',
            }}>
                {/* Header */}
                <div style={{ marginBottom: '28px', textAlign: 'center' }}>
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
                            <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
                            <circle cx="9" cy="7" r="4" />
                            <path d="M22 21v-2a4 4 0 0 0-3-3.87" />
                            <path d="M16 3.13a4 4 0 0 1 0 7.75" />
                        </svg>
                    </div>
                    <h1 style={{
                        fontSize: '1.5rem',
                        fontWeight: '700',
                        color: '#065f46',
                        marginBottom: '8px',
                    }}>
                        Create account
                    </h1>
                    <p style={{ color: '#78716c', fontSize: '14px' }}>
                        Join the SKU Image Pipeline
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
                    {/* Role Selection */}
                    <div style={{ marginBottom: '22px' }}>
                        <label style={{
                            display: 'block',
                            marginBottom: '10px',
                            fontWeight: '500',
                            color: '#374151',
                            fontSize: '14px',
                        }}>
                            Account type
                        </label>
                        <div style={{ display: 'flex', gap: '12px' }}>
                            <button
                                type="button"
                                onClick={() => setRole('vendor')}
                                style={{
                                    flex: 1,
                                    padding: '16px 14px',
                                    borderRadius: '12px',
                                    border: role === 'vendor' ? '2px solid #059669' : '2px solid #e5e7eb',
                                    background: role === 'vendor'
                                        ? 'linear-gradient(135deg, #ecfdf5, #d1fae5)'
                                        : 'white',
                                    cursor: 'pointer',
                                    textAlign: 'left',
                                    transition: 'all 0.25s ease',
                                }}
                            >
                                <div style={{
                                    fontWeight: '600',
                                    color: role === 'vendor' ? '#065f46' : '#374151',
                                    marginBottom: '4px',
                                    fontSize: '15px',
                                }}>
                                    Vendor
                                </div>
                                <div style={{ fontSize: '12px', color: '#78716c' }}>
                                    Upload product images
                                </div>
                            </button>

                            <button
                                type="button"
                                onClick={() => setRole('official')}
                                style={{
                                    flex: 1,
                                    padding: '16px 14px',
                                    borderRadius: '12px',
                                    border: role === 'official' ? '2px solid #7c3aed' : '2px solid #e5e7eb',
                                    background: role === 'official'
                                        ? 'linear-gradient(135deg, #f3e8ff, #e9d5ff)'
                                        : 'white',
                                    cursor: 'pointer',
                                    textAlign: 'left',
                                    transition: 'all 0.25s ease',
                                }}
                            >
                                <div style={{
                                    fontWeight: '600',
                                    color: role === 'official' ? '#5b21b6' : '#374151',
                                    marginBottom: '4px',
                                    fontSize: '15px',
                                }}>
                                    Official
                                </div>
                                <div style={{ fontSize: '12px', color: '#78716c' }}>
                                    Review & approve images
                                </div>
                            </button>
                        </div>
                    </div>

                    <div style={{ marginBottom: '16px' }}>
                        <label style={{
                            display: 'block',
                            marginBottom: '6px',
                            fontWeight: '500',
                            color: '#374151',
                            fontSize: '14px',
                        }}>
                            Full name
                        </label>
                        <input
                            type="text"
                            value={name}
                            onChange={(e) => setName(e.target.value)}
                            placeholder="John Doe"
                            required
                        />
                    </div>

                    <div style={{ marginBottom: '16px' }}>
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
                            placeholder="At least 6 characters"
                            required
                            minLength={6}
                        />
                    </div>

                    <button
                        type="submit"
                        disabled={loading}
                        style={{
                            width: '100%',
                            padding: '14px',
                            background: role === 'vendor'
                                ? 'linear-gradient(135deg, #059669, #10b981)'
                                : 'linear-gradient(135deg, #7c3aed, #8b5cf6)',
                            color: 'white',
                            border: 'none',
                            borderRadius: '12px',
                            fontSize: '15px',
                            fontWeight: '600',
                            cursor: loading ? 'not-allowed' : 'pointer',
                            opacity: loading ? 0.7 : 1,
                            boxShadow: role === 'vendor'
                                ? '0 4px 14px rgba(5, 150, 105, 0.3)'
                                : '0 4px 14px rgba(124, 58, 237, 0.3)',
                            transition: 'all 0.25s ease',
                        }}
                    >
                        {loading ? 'Creating account...' : 'Create account'}
                    </button>
                </form>

                <div style={{
                    marginTop: '24px',
                    textAlign: 'center',
                    paddingTop: '20px',
                    borderTop: '1px solid #e5e7eb',
                }}>
                    <p style={{ color: '#78716c', fontSize: '14px' }}>
                        Already have an account?{' '}
                        <Link to="/login" style={{
                            color: '#059669',
                            fontWeight: '600',
                            textDecoration: 'none',
                        }}>
                            Sign in
                        </Link>
                    </p>
                </div>
            </div>
        </div>
    );
};

export default Register;
