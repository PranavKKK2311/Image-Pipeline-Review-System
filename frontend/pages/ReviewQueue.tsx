/**
 * ReviewQueue.tsx - Human-in-the-Loop Review UI
 * 
 * Allows reviewers to:
 * - View pending image review tasks
 * - See automated validation results
 * - Make accept/reject/edit decisions
 * - Upload corrected images
 * - Provide feedback for model improvement
 */

import React, { useState, useEffect } from 'react';

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
  image_url: string;
  validation_score: number;
  validation_checks: ValidationChecks;
  failure_reason: string;
  priority: number;
  created_at: string;
  due_by: string;
}

interface ReviewDecision {
  decision: 'accepted' | 'rejected' | 'requires_edit';
  reviewer_confidence: number;
  reviewer_notes: string;
  corrected_image_url?: string;
}

const ReviewQueue: React.FC = () => {
  const [tasks, setTasks] = useState<ReviewTask[]>([]);
  const [selectedTask, setSelectedTask] = useState<ReviewTask | null>(null);
  const [decision, setDecision] = useState<ReviewDecision>({
    decision: 'accepted',
    reviewer_confidence: 5,
    reviewer_notes: '',
  });
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [stats, setStats] = useState<any>(null);

  // Fetch pending review tasks on mount
  useEffect(() => {
    fetchPendingTasks();
    fetchStats();
    
    // Refresh every 30 seconds
    const interval = setInterval(() => {
      fetchPendingTasks();
      fetchStats();
    }, 30000);
    
    return () => clearInterval(interval);
  }, []);

  const fetchPendingTasks = async () => {
    try {
      const response = await fetch('/api/v1/review/pending?limit=50');
      const data = await response.json();
      setTasks(data.tasks || []);
    } catch (error) {
      console.error('Failed to fetch tasks:', error);
    }
  };

  const fetchStats = async () => {
    try {
      const response = await fetch('/api/v1/review/stats');
      const data = await response.json();
      setStats(data);
    } catch (error) {
      console.error('Failed to fetch stats:', error);
    }
  };

  const submitDecision = async () => {
    if (!selectedTask) return;
    
    setLoading(true);
    try {
      const response = await fetch('/api/v1/review/submit-decision', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          review_task_id: selectedTask.id,
          decision: decision.decision,
          reviewer_id: 42, // TODO: Get from auth
          reviewer_notes: decision.reviewer_notes,
          reviewer_confidence: decision.reviewer_confidence,
          corrected_image_url: decision.corrected_image_url,
        }),
      });

      if (response.ok) {
        setSubmitted(true);
        setTimeout(() => {
          setSubmitted(false);
          setSelectedTask(null);
          fetchPendingTasks();
        }, 2000);
      }
    } catch (error) {
      console.error('Failed to submit decision:', error);
    } finally {
      setLoading(false);
    }
  };

  // Score color coding
  const getScoreColor = (score: number): string => {
    if (score >= 0.85) return '#10b981'; // green
    if (score >= 0.70) return '#f59e0b'; // amber
    return '#ef4444'; // red
  };

  // Priority level
  const getPriorityLabel = (priority: number): string => {
    const labels = {
      1: 'Urgent',
      2: 'High',
      3: 'Normal',
      4: 'Low',
      5: 'Very Low',
    };
    return labels[priority as keyof typeof labels] || 'Unknown';
  };

  return (
    <div style={{ fontFamily: 'system-ui, -apple-system, sans-serif', padding: '20px' }}>
      <h1>📋 Image Review Queue</h1>

      {/* Queue Statistics */}
      {stats && (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
            gap: '16px',
            marginBottom: '32px',
          }}
        >
          <div style={{ border: '1px solid #e5e7eb', borderRadius: '8px', padding: '16px' }}>
            <div style={{ fontSize: '14px', color: '#6b7280' }}>Pending Tasks</div>
            <div style={{ fontSize: '32px', fontWeight: 'bold' }}>
              {stats.pending_count || 0}
            </div>
          </div>
          <div style={{ border: '1px solid #e5e7eb', borderRadius: '8px', padding: '16px' }}>
            <div style={{ fontSize: '14px', color: '#6b7280' }}>SLA Violations</div>
            <div style={{ fontSize: '32px', fontWeight: 'bold', color: '#ef4444' }}>
              {stats.sla_violations || 0}
            </div>
          </div>
          <div style={{ border: '1px solid #e5e7eb', borderRadius: '8px', padding: '16px' }}>
            <div style={{ fontSize: '14px', color: '#6b7280' }}>Avg Review Time</div>
            <div style={{ fontSize: '24px', fontWeight: 'bold' }}>
              {stats.avg_review_time_minutes?.toFixed(1) || 'N/A'} min
            </div>
          </div>
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '24px' }}>
        {/* Task List */}
        <div>
          <h2>Tasks ({tasks.length})</h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {tasks.length === 0 ? (
              <p style={{ color: '#6b7280' }}>No pending tasks</p>
            ) : (
              tasks.map((task) => (
                <div
                  key={task.id}
                  onClick={() => setSelectedTask(task)}
                  style={{
                    border:
                      selectedTask?.id === task.id
                        ? '2px solid #3b82f6'
                        : '1px solid #e5e7eb',
                    borderRadius: '8px',
                    padding: '12px',
                    cursor: 'pointer',
                    backgroundColor:
                      selectedTask?.id === task.id ? '#eff6ff' : '#ffffff',
                    transition: 'all 0.2s',
                  }}
                  onMouseEnter={(e) => {
                    if (selectedTask?.id !== task.id) {
                      e.currentTarget.style.borderColor = '#d1d5db';
                    }
                  }}
                >
                  <div style={{ fontWeight: 'bold', marginBottom: '4px' }}>
                    {task.product_name}
                  </div>
                  <div style={{ fontSize: '12px', color: '#6b7280', marginBottom: '8px' }}>
                    SKU: {task.canonical_sku}
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <div
                      style={{
                        fontSize: '12px',
                        fontWeight: 'bold',
                        color: getScoreColor(task.validation_score),
                      }}
                    >
                      Score: {task.validation_score.toFixed(2)}
                    </div>
                    <div style={{ fontSize: '12px', color: '#6b7280' }}>
                      Priority: {getPriorityLabel(task.priority)}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Task Detail & Review Form */}
        <div>
          {selectedTask ? (
            <>
              <h2>Review Details</h2>

              {/* Product Info */}
              <div
                style={{
                  border: '1px solid #e5e7eb',
                  borderRadius: '8px',
                  padding: '16px',
                  marginBottom: '20px',
                }}
              >
                <h3>{selectedTask.product_name}</h3>
                <p>
                  <strong>SKU:</strong> {selectedTask.canonical_sku}
                </p>
                <p>
                  <strong>Vendor Code:</strong> {selectedTask.vendor_code}
                </p>
                <p>
                  <strong>Reason for Review:</strong> {selectedTask.failure_reason}
                </p>
              </div>

              {/* Image Preview */}
              <div
                style={{
                  border: '1px solid #e5e7eb',
                  borderRadius: '8px',
                  padding: '16px',
                  marginBottom: '20px',
                }}
              >
                <h3>Product Image</h3>
                <img
                  src={selectedTask.image_url}
                  alt="Product"
                  style={{
                    maxWidth: '100%',
                    maxHeight: '300px',
                    borderRadius: '4px',
                    marginBottom: '12px',
                  }}
                />
                <div
                  style={{
                    display: 'grid',
                    gridTemplateColumns: '1fr 1fr',
                    gap: '12px',
                  }}
                >
                  <div>
                    <div style={{ fontSize: '12px', color: '#6b7280' }}>
                      Background White
                    </div>
                    <div
                      style={{
                        fontSize: '18px',
                        fontWeight: 'bold',
                        color: getScoreColor(selectedTask.validation_checks.background_white),
                      }}
                    >
                      {(selectedTask.validation_checks.background_white * 100).toFixed(0)}%
                    </div>
                  </div>
                  <div>
                    <div style={{ fontSize: '12px', color: '#6b7280' }}>Blur</div>
                    <div
                      style={{
                        fontSize: '18px',
                        fontWeight: 'bold',
                        color: getScoreColor(selectedTask.validation_checks.blur),
                      }}
                    >
                      {(selectedTask.validation_checks.blur * 100).toFixed(0)}%
                    </div>
                  </div>
                  <div>
                    <div style={{ fontSize: '12px', color: '#6b7280' }}>
                      Object Coverage
                    </div>
                    <div
                      style={{
                        fontSize: '18px',
                        fontWeight: 'bold',
                        color: getScoreColor(selectedTask.validation_checks.object_coverage),
                      }}
                    >
                      {(selectedTask.validation_checks.object_coverage * 100).toFixed(0)}%
                    </div>
                  </div>
                  <div>
                    <div style={{ fontSize: '12px', color: '#6b7280' }}>
                      Overall Score
                    </div>
                    <div
                      style={{
                        fontSize: '18px',
                        fontWeight: 'bold',
                        color: getScoreColor(selectedTask.validation_score),
                      }}
                    >
                      {(selectedTask.validation_score * 100).toFixed(0)}%
                    </div>
                  </div>
                </div>
              </div>

              {/* Decision Form */}
              <div
                style={{
                  border: '1px solid #e5e7eb',
                  borderRadius: '8px',
                  padding: '16px',
                  marginBottom: '20px',
                }}
              >
                <h3>Your Decision</h3>

                <div style={{ marginBottom: '16px' }}>
                  <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>
                    Decision
                  </label>
                  <select
                    value={decision.decision}
                    onChange={(e) =>
                      setDecision({
                        ...decision,
                        decision: e.target.value as any,
                      })
                    }
                    style={{
                      width: '100%',
                      padding: '8px',
                      borderRadius: '4px',
                      border: '1px solid #d1d5db',
                    }}
                  >
                    <option value="accepted">✓ Accept</option>
                    <option value="rejected">✗ Reject</option>
                    <option value="requires_edit">✎ Requires Edit</option>
                  </select>
                </div>

                <div style={{ marginBottom: '16px' }}>
                  <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>
                    Confidence (1-5)
                  </label>
                  <input
                    type="range"
                    min="1"
                    max="5"
                    value={decision.reviewer_confidence}
                    onChange={(e) =>
                      setDecision({
                        ...decision,
                        reviewer_confidence: parseInt(e.target.value),
                      })
                    }
                    style={{ width: '100%' }}
                  />
                  <div style={{ textAlign: 'center', marginTop: '8px', color: '#6b7280' }}>
                    {decision.reviewer_confidence}/5
                  </div>
                </div>

                <div style={{ marginBottom: '16px' }}>
                  <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>
                    Notes
                  </label>
                  <textarea
                    value={decision.reviewer_notes}
                    onChange={(e) =>
                      setDecision({
                        ...decision,
                        reviewer_notes: e.target.value,
                      })
                    }
                    placeholder="Add notes about your decision (for training purposes)"
                    style={{
                      width: '100%',
                      height: '80px',
                      padding: '8px',
                      borderRadius: '4px',
                      border: '1px solid #d1d5db',
                      fontFamily: 'system-ui',
                    }}
                  />
                </div>

                {decision.decision === 'requires_edit' && (
                  <div style={{ marginBottom: '16px' }}>
                    <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>
                      Upload Corrected Image
                    </label>
                    <input
                      type="file"
                      accept="image/*"
                      onChange={(e) => {
                        // TODO: Upload and get URL
                        if (e.target.files?.[0]) {
                          console.log('File selected:', e.target.files[0].name);
                        }
                      }}
                      style={{
                        display: 'block',
                        marginBottom: '8px',
                      }}
                    />
                  </div>
                )}

                <button
                  onClick={submitDecision}
                  disabled={loading || submitted}
                  style={{
                    width: '100%',
                    padding: '12px',
                    backgroundColor: submitted ? '#10b981' : '#3b82f6',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    fontWeight: 'bold',
                    cursor: loading || submitted ? 'not-allowed' : 'pointer',
                    opacity: loading || submitted ? 0.7 : 1,
                  }}
                >
                  {loading ? 'Submitting...' : submitted ? '✓ Submitted' : 'Submit Decision'}
                </button>
              </div>
            </>
          ) : (
            <div style={{ textAlign: 'center', color: '#6b7280', marginTop: '60px' }}>
              <p>Select a task to review</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ReviewQueue;
