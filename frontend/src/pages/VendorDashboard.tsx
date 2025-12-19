import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../context/AuthContext';

// Get API base URL from environment variable
const API_BASE = import.meta.env.VITE_API_URL || '';

interface Submission {
    id: number;
    product_name: string;
    vendor_code: string;
    image_url: string;
    status: string;
    feedback: string | null;
    reviewed_by: string | null;
    created_at: string;
    reviewed_at: string | null;
}

const VendorDashboard: React.FC = () => {
    const { user, token, logout } = useAuth();
    const [submissions, setSubmissions] = useState<Submission[]>([]);
    const [productName, setProductName] = useState('');
    const [vendorCode, setVendorCode] = useState('');
    const [selectedFile, setSelectedFile] = useState<File | null>(null);
    const [preview, setPreview] = useState<string | null>(null);
    const [uploading, setUploading] = useState(false);
    const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);

    useEffect(() => {
        fetchSubmissions();
        const interval = setInterval(fetchSubmissions, 10000);
        return () => clearInterval(interval);
    }, [token]);

    const fetchSubmissions = async () => {
        try {
            const response = await fetch(`${API_BASE}/api/v1/images/my-submissions`, {
                headers: { 'Authorization': `Bearer ${token}` },
            });
            if (response.ok) {
                const data = await response.json();
                setSubmissions(data.submissions || []);
            }
        } catch (error) {
            console.error('Failed to fetch submissions:', error);
        }
    };

    const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (file) {
            if (!['image/jpeg', 'image/png'].includes(file.type)) {
                setMessage({ type: 'error', text: 'Only JPG and PNG images are allowed' });
                return;
            }
            setSelectedFile(file);
            setPreview(URL.createObjectURL(file));
            setMessage(null);
        }
    };

    const handleUpload = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!selectedFile || !productName || !vendorCode) {
            setMessage({ type: 'error', text: 'Please fill all fields and select an image' });
            return;
        }

        setUploading(true);
        try {
            const formData = new FormData();
            formData.append('file', selectedFile);
            formData.append('product_name', productName);
            formData.append('vendor_code', vendorCode);

            const response = await fetch(`${API_BASE}/api/v1/images/upload`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}` },
                body: formData,
            });

            if (response.ok) {
                setMessage({ type: 'success', text: 'Image uploaded successfully. Awaiting review.' });
                setProductName('');
                setVendorCode('');
                setSelectedFile(null);
                setPreview(null);
                if (fileInputRef.current) fileInputRef.current.value = '';
                fetchSubmissions();
            } else {
                const error = await response.json();
                setMessage({ type: 'error', text: error.detail || 'Upload failed' });
            }
        } catch (error) {
            setMessage({ type: 'error', text: 'Upload failed. Please try again.' });
        }
        setUploading(false);
    };

    const getStatusStyle = (status: string) => {
        switch (status) {
            case 'accepted':
                return { bg: 'linear-gradient(135deg, #d1fae5, #a7f3d0)', color: '#065f46', dot: '#10b981' };
            case 'rejected':
                return { bg: 'linear-gradient(135deg, #fee2e2, #fecaca)', color: '#991b1b', dot: '#ef4444' };
            default:
                return { bg: 'linear-gradient(135deg, #fef3c7, #fde68a)', color: '#92400e', dot: '#f59e0b' };
        }
    };

    return (
        <div style={{ minHeight: '100vh' }}>
            {/* Header */}
            <header style={{
                background: 'rgba(255, 255, 255, 0.9)',
                backdropFilter: 'blur(12px)',
                borderBottom: '1px solid rgba(6, 95, 70, 0.1)',
                padding: '16px 32px',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
            }}>
                <div>
                    <h1 style={{ fontSize: '18px', fontWeight: '700', color: '#065f46' }}>
                        Vendor Dashboard
                    </h1>
                    <p style={{ fontSize: '13px', color: '#78716c' }}>Upload and manage product images</p>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                    <span style={{ fontSize: '14px', color: '#475569' }}>{user?.name}</span>
                    <button
                        onClick={logout}
                        style={{
                            padding: '8px 16px',
                            background: 'white',
                            border: '1px solid #d1d5db',
                            borderRadius: '8px',
                            cursor: 'pointer',
                            fontSize: '14px',
                            color: '#374151',
                            fontWeight: '500',
                        }}
                    >
                        Sign out
                    </button>
                </div>
            </header>

            <div style={{ maxWidth: '1100px', margin: '0 auto', padding: '32px' }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
                    {/* Upload Form */}
                    <div style={{
                        background: 'rgba(255, 255, 255, 0.85)',
                        backdropFilter: 'blur(20px)',
                        borderRadius: '20px',
                        padding: '28px',
                        border: '1px solid rgba(255, 255, 255, 0.9)',
                        boxShadow: '0 8px 32px rgba(6, 78, 59, 0.08)',
                    }}>
                        <h2 style={{ fontSize: '16px', fontWeight: '600', color: '#065f46', marginBottom: '20px' }}>
                            Upload Product Image
                        </h2>

                        {message && (
                            <div style={{
                                background: message.type === 'success'
                                    ? 'linear-gradient(135deg, #d1fae5, #a7f3d0)'
                                    : 'linear-gradient(135deg, #fee2e2, #fecaca)',
                                border: `1px solid ${message.type === 'success' ? '#6ee7b7' : '#fca5a5'}`,
                                borderRadius: '10px',
                                padding: '12px 16px',
                                marginBottom: '16px',
                                color: message.type === 'success' ? '#065f46' : '#991b1b',
                                fontSize: '14px',
                            }}>
                                {message.text}
                            </div>
                        )}

                        <form onSubmit={handleUpload}>
                            {/* Image Upload */}
                            <div style={{ marginBottom: '18px' }}>
                                <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500', color: '#374151', fontSize: '14px' }}>
                                    Product Image
                                </label>
                                <div
                                    style={{
                                        border: '2px dashed #a7f3d0',
                                        borderRadius: '12px',
                                        padding: preview ? '0' : '36px',
                                        textAlign: 'center',
                                        cursor: 'pointer',
                                        background: '#ecfdf5',
                                        overflow: 'hidden',
                                        transition: 'all 0.25s ease',
                                    }}
                                    onClick={() => fileInputRef.current?.click()}
                                >
                                    {preview ? (
                                        <img src={preview} alt="Preview" style={{ width: '100%', height: '180px', objectFit: 'cover' }} />
                                    ) : (
                                        <>
                                            <div style={{
                                                width: '48px',
                                                height: '48px',
                                                background: 'linear-gradient(135deg, #10b981, #059669)',
                                                borderRadius: '12px',
                                                margin: '0 auto 12px',
                                                display: 'flex',
                                                alignItems: 'center',
                                                justifyContent: 'center',
                                            }}>
                                                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2">
                                                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                                                    <polyline points="17 8 12 3 7 8" />
                                                    <line x1="12" y1="3" x2="12" y2="15" />
                                                </svg>
                                            </div>
                                            <p style={{ color: '#065f46', fontWeight: '500', fontSize: '14px' }}>Click to select image</p>
                                            <p style={{ color: '#78716c', fontSize: '12px', marginTop: '4px' }}>JPG or PNG format</p>
                                        </>
                                    )}
                                </div>
                                <input ref={fileInputRef} type="file" accept="image/jpeg,image/png" onChange={handleFileSelect} style={{ display: 'none' }} />
                            </div>

                            <div style={{ marginBottom: '16px' }}>
                                <label style={{ display: 'block', marginBottom: '6px', fontWeight: '500', color: '#374151', fontSize: '14px' }}>
                                    Product Name
                                </label>
                                <input
                                    type="text"
                                    value={productName}
                                    onChange={(e) => setProductName(e.target.value)}
                                    placeholder="e.g., Premium Wireless Headphones"
                                    required
                                />
                            </div>

                            <div style={{ marginBottom: '22px' }}>
                                <label style={{ display: 'block', marginBottom: '6px', fontWeight: '500', color: '#374151', fontSize: '14px' }}>
                                    Product Code (SKU)
                                </label>
                                <input
                                    type="text"
                                    value={vendorCode}
                                    onChange={(e) => setVendorCode(e.target.value)}
                                    placeholder="e.g., HDPH-001"
                                    required
                                />
                            </div>

                            <button
                                type="submit"
                                disabled={uploading}
                                style={{
                                    width: '100%',
                                    padding: '14px',
                                    background: 'linear-gradient(135deg, #059669, #10b981)',
                                    color: 'white',
                                    border: 'none',
                                    borderRadius: '12px',
                                    fontSize: '15px',
                                    fontWeight: '600',
                                    cursor: uploading ? 'not-allowed' : 'pointer',
                                    opacity: uploading ? 0.7 : 1,
                                    boxShadow: '0 4px 14px rgba(5, 150, 105, 0.3)',
                                    transition: 'all 0.25s ease',
                                }}
                            >
                                {uploading ? 'Uploading...' : 'Submit for Review'}
                            </button>
                        </form>
                    </div>

                    {/* Submissions List */}
                    <div style={{
                        background: 'rgba(255, 255, 255, 0.85)',
                        backdropFilter: 'blur(20px)',
                        borderRadius: '20px',
                        padding: '28px',
                        border: '1px solid rgba(255, 255, 255, 0.9)',
                        boxShadow: '0 8px 32px rgba(6, 78, 59, 0.08)',
                        maxHeight: '540px',
                        overflow: 'auto',
                    }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                            <h2 style={{ fontSize: '16px', fontWeight: '600', color: '#065f46' }}>
                                Your Submissions
                            </h2>
                            <span style={{
                                background: 'linear-gradient(135deg, #10b981, #059669)',
                                color: 'white',
                                padding: '4px 12px',
                                borderRadius: '16px',
                                fontSize: '13px',
                                fontWeight: '600',
                            }}>
                                {submissions.length}
                            </span>
                        </div>

                        {submissions.length === 0 ? (
                            <div style={{ textAlign: 'center', padding: '48px 20px', color: '#78716c' }}>
                                <div style={{
                                    width: '64px',
                                    height: '64px',
                                    background: '#ecfdf5',
                                    borderRadius: '16px',
                                    margin: '0 auto 16px',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                }}>
                                    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#10b981" strokeWidth="2">
                                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                                        <polyline points="14 2 14 8 20 8" />
                                    </svg>
                                </div>
                                <p style={{ fontWeight: '500' }}>No submissions yet</p>
                                <p style={{ fontSize: '13px', marginTop: '4px' }}>Upload your first product image</p>
                            </div>
                        ) : (
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                                {submissions.map((sub) => {
                                    const statusStyle = getStatusStyle(sub.status);
                                    return (
                                        <div key={sub.id} style={{
                                            background: 'white',
                                            borderRadius: '12px',
                                            padding: '16px',
                                            border: '1px solid #e5e7eb',
                                            transition: 'all 0.25s ease',
                                        }}>
                                            <div style={{ display: 'flex', gap: '14px' }}>
                                                <img
                                                    src={`${API_BASE}${sub.image_url}`}
                                                    alt={sub.product_name}
                                                    style={{ width: '64px', height: '64px', borderRadius: '8px', objectFit: 'cover' }}
                                                    onError={(e) => { e.currentTarget.style.display = 'none'; }}
                                                />
                                                <div style={{ flex: 1 }}>
                                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '4px' }}>
                                                        <span style={{ fontWeight: '600', color: '#065f46', fontSize: '14px' }}>{sub.product_name}</span>
                                                        <span style={{
                                                            background: statusStyle.bg,
                                                            color: statusStyle.color,
                                                            padding: '3px 10px',
                                                            borderRadius: '6px',
                                                            fontSize: '12px',
                                                            fontWeight: '500',
                                                            display: 'flex',
                                                            alignItems: 'center',
                                                            gap: '5px',
                                                        }}>
                                                            <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: statusStyle.dot }}></span>
                                                            {sub.status.charAt(0).toUpperCase() + sub.status.slice(1)}
                                                        </span>
                                                    </div>
                                                    <p style={{ fontSize: '12px', color: '#78716c', fontFamily: 'monospace' }}>{sub.vendor_code}</p>

                                                    {sub.feedback && (
                                                        <div style={{
                                                            background: '#f9fafb',
                                                            borderRadius: '8px',
                                                            padding: '10px 12px',
                                                            marginTop: '10px',
                                                            border: '1px solid #e5e7eb',
                                                        }}>
                                                            <p style={{ fontSize: '11px', fontWeight: '500', color: '#78716c', marginBottom: '4px' }}>
                                                                Feedback from {sub.reviewed_by}:
                                                            </p>
                                                            <p style={{ fontSize: '13px', color: '#374151' }}>{sub.feedback}</p>
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
            </div>
        </div>
    );
};

export default VendorDashboard;
