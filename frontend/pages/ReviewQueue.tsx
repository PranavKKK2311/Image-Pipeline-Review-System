/**
 * ReviewQueue.tsx - Official Review UI (Dark Matcha, No Emojis)
 */

import React, { useState, useEffect } from 'react';

// Get API base URL from environment variable
const API_BASE = import.meta.env.VITE_API_URL || '';

interface ValidationChecks {
  background_white: number;
  blur: number;
  object_coverage: number;
  perceptual_similarity: number;
}

interface ReviewTask {
  id: number;
  product_name: string;
  canonical_sku: string;
  vendor_code: string;
  vendor_name?: string;
  vendor_email?: string;
  image_url: string;
  validation_score: number;
  validation_checks: ValidationChecks;
  failure_reason: string;
  priority: number;
  created_at: string;
  due_by: string;
}

const ReviewQueue: React.FC = () => {
  const [tasks, setTasks] = useState<ReviewTask[]>([]);
  const [selectedTask, setSelectedTask] = useState<ReviewTask | null>(null);
  const [decision, setDecision] = useState<'accepted' | 'rejected'>('accepted');
  const [feedback, setFeedback] = useState('');
  const [confidence, setConfidence] = useState(5);
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [stats, setStats] = useState<any>(null);
  const [imageError, setImageError] = useState(false);

  const token = localStorage.getItem('token');
  const user = JSON.parse(localStorage.getItem('user') || '{}');

  useEffect(() => {
    fetchPendingTasks();
    fetchStats();
    const interval = setInterval(() => {
      fetchPendingTasks();
      fetchStats();
    }, 10000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    setImageError(false);
  }, [selectedTask]);

  const fetchPendingTasks = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/v1/review/pending?limit=50`, {
        headers: { 'Authorization': `Bearer ${token}` },
      });
      if (response.ok) {
        const data = await response.json();
        setTasks(data.tasks || []);
      }
    } catch (error) {
      console.error('Failed to fetch tasks:', error);
    }
  };

  const fetchStats = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/v1/review/stats`, {
        headers: { 'Authorization': `Bearer ${token}` },
      });
      if (response.ok) {
        const data = await response.json();
        setStats(data);
      }
    } catch (error) {
      console.error('Failed to fetch stats:', error);
    }
  };

  const submitDecision = async () => {
    if (!selectedTask) return;

    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/v1/review/submit-decision`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          review_task_id: selectedTask.id,
          decision: decision,
          reviewer_id: 1,
          reviewer_notes: feedback,
          reviewer_confidence: confidence,
          feedback_message: feedback,
        }),
      });

      if (response.ok) {
        setSubmitted(true);
        setTimeout(() => {
          setSubmitted(false);
          setSelectedTask(null);
          setFeedback('');
          setConfidence(5);
          fetchPendingTasks();
          fetchStats();
        }, 1500);
      }
    } catch (error) {
      console.error('Failed to submit decision:', error);
    } finally {
      setLoading(false);
    }
  };

  const logout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    window.location.href = '/login';
  };

  const getScoreColor = (score: number): string => {
    if (score >= 0.85) return '#059669';
    if (score >= 0.70) return '#d97706';
    return '#dc2626';
  };

  const getImageUrl = (url: string): string => {
    if (!url) return '';
    if (url.startsWith('http://') || url.startsWith('https://')) return url;
    if (url.startsWith('/uploads/')) return `${API_BASE}${url}`;
    return url;
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
            Review Queue
          </h1>
          <p style={{ fontSize: '13px', color: '#78716c' }}>Review and approve vendor submissions</p>
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

      <div style={{ maxWidth: '1300px', margin: '0 auto', padding: '24px 32px' }}>
        {/* Stats */}
        {stats && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px', marginBottom: '24px' }}>
            {[
              { label: 'Pending', value: stats.pending_count || 0, bg: '#ecfdf5', border: '#a7f3d0', color: '#059669' },
              { label: 'Accepted', value: stats.accepted_count || 0, bg: '#d1fae5', border: '#6ee7b7', color: '#047857' },
              { label: 'Rejected', value: stats.rejected_count || 0, bg: '#fee2e2', border: '#fecaca', color: '#dc2626' },
              { label: 'SLA Violations', value: stats.sla_violations || 0, bg: '#fef3c7', border: '#fde68a', color: '#d97706' },
            ].map((stat) => (
              <div key={stat.label} style={{
                background: stat.bg,
                border: `1px solid ${stat.border}`,
                borderRadius: '14px',
                padding: '20px',
              }}>
                <p style={{ fontSize: '13px', color: '#64748b', marginBottom: '4px', fontWeight: '500' }}>{stat.label}</p>
                <p style={{ fontSize: '2rem', fontWeight: '700', color: stat.color }}>{stat.value}</p>
              </div>
            ))}
          </div>
        )}

        <div style={{ display: 'grid', gridTemplateColumns: '360px 1fr', gap: '24px' }}>
          {/* Task List */}
          <div style={{
            background: 'rgba(255, 255, 255, 0.85)',
            backdropFilter: 'blur(20px)',
            border: '1px solid rgba(255, 255, 255, 0.9)',
            borderRadius: '20px',
            boxShadow: '0 8px 32px rgba(6, 78, 59, 0.08)',
            maxHeight: 'calc(100vh - 240px)',
            overflow: 'auto',
          }}>
            <div style={{ padding: '18px 20px', borderBottom: '1px solid #e5e7eb' }}>
              <h2 style={{ fontSize: '15px', fontWeight: '600', color: '#065f46' }}>
                Pending Reviews ({tasks.length})
              </h2>
            </div>

            {tasks.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '48px 20px', color: '#78716c' }}>
                <div style={{
                  width: '56px',
                  height: '56px',
                  background: '#ecfdf5',
                  borderRadius: '14px',
                  margin: '0 auto 14px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}>
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#10b981" strokeWidth="2">
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                </div>
                <p style={{ fontWeight: '500' }}>All caught up!</p>
              </div>
            ) : (
              <div>
                {tasks.map((task) => (
                  <div
                    key={task.id}
                    onClick={() => setSelectedTask(task)}
                    style={{
                      padding: '16px 20px',
                      borderBottom: '1px solid #f1f5f9',
                      cursor: 'pointer',
                      background: selectedTask?.id === task.id
                        ? 'linear-gradient(135deg, #ecfdf5, white)'
                        : 'white',
                      borderLeft: selectedTask?.id === task.id ? '3px solid #10b981' : '3px solid transparent',
                      transition: 'all 0.2s ease',
                    }}
                  >
                    <div style={{ fontWeight: '600', color: '#065f46', marginBottom: '4px', fontSize: '14px' }}>
                      {task.product_name}
                    </div>
                    {task.vendor_name && (
                      <div style={{ fontSize: '12px', color: '#78716c', marginBottom: '8px' }}>
                        by {task.vendor_name}
                      </div>
                    )}
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{
                        padding: '3px 10px',
                        borderRadius: '6px',
                        fontSize: '12px',
                        fontWeight: '600',
                        background: task.validation_score >= 0.70
                          ? 'linear-gradient(135deg, #fef3c7, #fde68a)'
                          : 'linear-gradient(135deg, #fee2e2, #fecaca)',
                        color: getScoreColor(task.validation_score),
                      }}>
                        {(task.validation_score * 100).toFixed(0)}% Score
                      </span>
                      <span style={{ fontSize: '11px', color: '#94a3b8', fontFamily: 'monospace' }}>
                        {task.canonical_sku}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Review Panel */}
          {selectedTask ? (
            <div style={{
              background: 'rgba(255, 255, 255, 0.85)',
              backdropFilter: 'blur(20px)',
              border: '1px solid rgba(255, 255, 255, 0.9)',
              borderRadius: '20px',
              padding: '28px',
              boxShadow: '0 8px 32px rgba(6, 78, 59, 0.08)',
            }}>
              {/* Header */}
              <div style={{ marginBottom: '24px', paddingBottom: '18px', borderBottom: '1px solid #e5e7eb' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
                  <div>
                    <h2 style={{ fontSize: '1.25rem', fontWeight: '700', color: '#065f46', marginBottom: '8px' }}>
                      {selectedTask.product_name}
                    </h2>
                    <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                      <span style={{ background: '#f1f5f9', padding: '4px 10px', borderRadius: '6px', fontSize: '12px', color: '#475569' }}>
                        SKU: {selectedTask.canonical_sku}
                      </span>
                      {selectedTask.vendor_name && (
                        <span style={{ background: '#ecfdf5', padding: '4px 10px', borderRadius: '6px', fontSize: '12px', color: '#047857' }}>
                          Vendor: {selectedTask.vendor_name}
                        </span>
                      )}
                    </div>
                  </div>
                  <div style={{
                    background: selectedTask.validation_score >= 0.70
                      ? 'linear-gradient(135deg, #fef3c7, #fde68a)'
                      : 'linear-gradient(135deg, #fee2e2, #fecaca)',
                    padding: '14px 18px',
                    borderRadius: '12px',
                    textAlign: 'center',
                  }}>
                    <p style={{ fontSize: '11px', color: '#64748b', marginBottom: '2px', fontWeight: '500' }}>Overall Score</p>
                    <p style={{ fontSize: '1.5rem', fontWeight: '700', color: getScoreColor(selectedTask.validation_score) }}>
                      {(selectedTask.validation_score * 100).toFixed(0)}%
                    </p>
                  </div>
                </div>
              </div>

              {/* Content */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '24px' }}>
                {/* Image */}
                <div style={{ borderRadius: '14px', overflow: 'hidden', background: '#ecfdf5', padding: '3px' }}>
                  {!imageError ? (
                    <img
                      src={getImageUrl(selectedTask.image_url)}
                      alt={selectedTask.product_name}
                      onError={() => setImageError(true)}
                      style={{ width: '100%', height: '260px', objectFit: 'cover', borderRadius: '11px' }}
                    />
                  ) : (
                    <div style={{
                      width: '100%',
                      height: '260px',
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                      justifyContent: 'center',
                      background: '#f9fafb',
                      borderRadius: '11px',
                      color: '#78716c',
                    }}>
                      <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#a3a3a3" strokeWidth="1.5">
                        <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                        <circle cx="8.5" cy="8.5" r="1.5" />
                        <polyline points="21 15 16 10 5 21" />
                      </svg>
                      <p style={{ marginTop: '12px', fontSize: '14px' }}>Image not available</p>
                    </div>
                  )}
                </div>

                {/* Metrics */}
                <div>
                  <h3 style={{ fontSize: '14px', fontWeight: '600', color: '#065f46', marginBottom: '14px' }}>
                    Quality Metrics
                  </h3>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                    {[
                      { label: 'Background', value: selectedTask.validation_checks.background_white },
                      { label: 'Sharpness', value: selectedTask.validation_checks.blur },
                      { label: 'Coverage', value: selectedTask.validation_checks.object_coverage },
                      { label: 'Similarity', value: selectedTask.validation_checks.perceptual_similarity },
                    ].map((m) => (
                      <div key={m.label} style={{
                        background: 'white',
                        border: '1px solid #e5e7eb',
                        borderRadius: '10px',
                        padding: '14px',
                        textAlign: 'center',
                      }}>
                        <p style={{ fontSize: '1.5rem', fontWeight: '700', color: getScoreColor(m.value), marginBottom: '2px' }}>
                          {(m.value * 100).toFixed(0)}%
                        </p>
                        <p style={{ fontSize: '11px', color: '#78716c', fontWeight: '500' }}>{m.label}</p>
                      </div>
                    ))}
                  </div>

                  <div style={{
                    background: 'linear-gradient(135deg, #fef3c7, #fef9c3)',
                    border: '1px solid #fde68a',
                    borderRadius: '10px',
                    padding: '14px',
                    marginTop: '12px',
                  }}>
                    <p style={{ fontSize: '11px', fontWeight: '600', color: '#92400e', marginBottom: '4px' }}>
                      Review Reason
                    </p>
                    <p style={{ fontSize: '13px', color: '#78350f' }}>{selectedTask.failure_reason}</p>
                  </div>
                </div>
              </div>

              {/* Decision Form */}
              <div style={{
                background: 'linear-gradient(135deg, #ecfdf5, #fefce8)',
                border: '1px solid #a7f3d0',
                borderRadius: '16px',
                padding: '24px',
              }}>
                <h3 style={{ fontSize: '15px', fontWeight: '600', color: '#065f46', marginBottom: '18px' }}>
                  Your Decision
                </h3>

                {/* Buttons */}
                <div style={{ display: 'flex', gap: '12px', marginBottom: '20px' }}>
                  <button
                    onClick={() => setDecision('accepted')}
                    style={{
                      flex: 1,
                      padding: '14px',
                      borderRadius: '10px',
                      border: decision === 'accepted' ? '2px solid #059669' : '2px solid #e5e7eb',
                      background: decision === 'accepted' ? 'linear-gradient(135deg, #059669, #10b981)' : 'white',
                      color: decision === 'accepted' ? 'white' : '#374151',
                      fontWeight: '600',
                      fontSize: '14px',
                      cursor: 'pointer',
                      boxShadow: decision === 'accepted' ? '0 4px 14px rgba(5, 150, 105, 0.3)' : 'none',
                      transition: 'all 0.25s ease',
                    }}
                  >
                    Approve
                  </button>
                  <button
                    onClick={() => setDecision('rejected')}
                    style={{
                      flex: 1,
                      padding: '14px',
                      borderRadius: '10px',
                      border: decision === 'rejected' ? '2px solid #dc2626' : '2px solid #e5e7eb',
                      background: decision === 'rejected' ? 'linear-gradient(135deg, #dc2626, #ef4444)' : 'white',
                      color: decision === 'rejected' ? 'white' : '#374151',
                      fontWeight: '600',
                      fontSize: '14px',
                      cursor: 'pointer',
                      boxShadow: decision === 'rejected' ? '0 4px 14px rgba(220, 38, 38, 0.3)' : 'none',
                      transition: 'all 0.25s ease',
                    }}
                  >
                    Reject
                  </button>
                </div>

                {/* Confidence */}
                <div style={{ marginBottom: '18px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px' }}>
                    <label style={{ fontSize: '13px', fontWeight: '500', color: '#374151' }}>Confidence Level</label>
                    <span style={{
                      background: 'linear-gradient(135deg, #059669, #10b981)',
                      color: 'white',
                      padding: '2px 10px',
                      borderRadius: '12px',
                      fontSize: '12px',
                      fontWeight: '600',
                    }}>
                      {confidence}/5
                    </span>
                  </div>
                  <input
                    type="range"
                    min="1"
                    max="5"
                    value={confidence}
                    onChange={(e) => setConfidence(parseInt(e.target.value))}
                    style={{ width: '100%' }}
                  />
                </div>

                {/* Feedback */}
                <div style={{ marginBottom: '18px' }}>
                  <label style={{ display: 'block', marginBottom: '8px', fontSize: '13px', fontWeight: '500', color: '#374151' }}>
                    Feedback for Vendor
                  </label>
                  <textarea
                    value={feedback}
                    onChange={(e) => setFeedback(e.target.value)}
                    placeholder={decision === 'accepted' ? "Great image quality. Approved for catalog." : "Please re-upload with..."}
                    style={{
                      width: '100%',
                      height: '90px',
                      padding: '12px 14px',
                      borderRadius: '10px',
                      border: '2px solid #a7f3d0',
                      fontSize: '14px',
                      resize: 'vertical',
                      fontFamily: 'inherit',
                      background: 'white',
                    }}
                  />
                </div>

                {/* Submit */}
                <button
                  onClick={submitDecision}
                  disabled={loading || submitted}
                  style={{
                    width: '100%',
                    padding: '14px',
                    background: submitted
                      ? 'linear-gradient(135deg, #059669, #10b981)'
                      : 'linear-gradient(135deg, #047857, #059669)',
                    color: 'white',
                    border: 'none',
                    borderRadius: '12px',
                    fontSize: '15px',
                    fontWeight: '600',
                    cursor: loading || submitted ? 'not-allowed' : 'pointer',
                    boxShadow: '0 4px 14px rgba(4, 120, 87, 0.3)',
                    transition: 'all 0.25s ease',
                  }}
                >
                  {loading ? 'Submitting...' : submitted ? 'Submitted Successfully!' : 'Submit Decision'}
                </button>
              </div>
            </div>
          ) : (
            <div style={{
              background: 'rgba(255, 255, 255, 0.6)',
              border: '2px dashed #a7f3d0',
              borderRadius: '20px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              minHeight: '400px',
            }}>
              <div style={{ textAlign: 'center', color: '#78716c' }}>
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
                    <line x1="16" y1="13" x2="8" y2="13" />
                    <line x1="16" y1="17" x2="8" y2="17" />
                  </svg>
                </div>
                <p style={{ fontSize: '15px', fontWeight: '500', color: '#065f46' }}>Select a submission to review</p>
                <p style={{ fontSize: '13px', marginTop: '4px' }}>Choose from the queue on the left</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ReviewQueue;
