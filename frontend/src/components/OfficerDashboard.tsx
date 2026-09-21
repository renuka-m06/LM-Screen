import React, { useState, useEffect } from 'react';
import { getOfficerQueue, submitOfficerReview } from '../api';
import type { PriorityQueueItem } from '../types';
import { Shield } from 'lucide-react';

export const OfficerDashboard: React.FC<{ onInvestigate?: (productId?: string, scanId?: string, clusterId?: string) => void }> = ({ onInvestigate }) => {
  const [queue, setQueue] = useState<PriorityQueueItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [selectedCluster, setSelectedCluster] = useState<PriorityQueueItem | null>(null);
  const [decision, setDecision] = useState<string>('CONFIRM');
  const [rationale, setRationale] = useState<string>('');
  const [reviewSubmitting, setReviewSubmitting] = useState<boolean>(false);
  const [statusFilter, setStatusFilter] = useState<string>('ALL');

  const fetchQueue = async () => {
    setLoading(true);
    try {
      const data = await getOfficerQueue();
      setQueue(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchQueue();
  }, []);

  const handleReviewSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedCluster || !rationale) return;

    setReviewSubmitting(true);
    try {
      await submitOfficerReview(selectedCluster.cluster_id, decision, rationale);
      setSelectedCluster(null);
      setRationale('');
      fetchQueue();
    } catch (err) {
      console.error(err);
    } finally {
      setReviewSubmitting(false);
    }
  };

  const filteredQueue = queue.filter(item => {
    if (statusFilter === 'ALL') return true;
    return item.status === statusFilter;
  });

  return (
    <div style={{ maxWidth: '1280px', margin: '0 auto', padding: '24px' }}>
      <div className="glass-panel" style={{ padding: '24px', marginBottom: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <div>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 800, display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-primary)' }}>
              <Shield size={22} color="var(--accent-review)" /> Officer Intelligence Workbench
            </h2>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
              Evidence-driven investigation and verification queue.
            </p>
          </div>

          {/* Status Filter Tabs */}
          <div style={{ display: 'flex', gap: '8px', background: 'var(--color-subtle-bg)', padding: '4px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
            {['ALL', 'UNVERIFIED', 'REVIEW_REQUIRED', 'MARK_UNDER_INVESTIGATION', 'CONFIRM', 'REJECT'].map(st => (
              <button
                key={st}
                onClick={() => setStatusFilter(st)}
                style={{
                  background: statusFilter === st ? 'var(--color-primary)' : 'transparent',
                  color: statusFilter === st ? '#fff' : 'var(--text-secondary)',
                  border: 'none', padding: '6px 12px', borderRadius: '6px', fontSize: '0.78rem', fontWeight: 600, cursor: 'pointer'
                }}
              >
                {st}
              </button>
            ))}
          </div>
        </div>

        {/* Summary Cards */}
        {!loading && (
          <div className="grid-responsive" style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px', marginBottom: '24px' }}>
            <div className="glass-card" style={{ padding: '16px', borderLeft: '3px solid var(--color-primary)' }}>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', fontWeight: 700, textTransform: 'uppercase' }}>New Cases</span>
              <div style={{ fontSize: '1.5rem', fontWeight: 800, color: 'var(--text-primary)', marginTop: '4px' }}>{queue.filter(i => i.status === 'UNVERIFIED').length}</div>
            </div>
            <div className="glass-card" style={{ padding: '16px', borderLeft: '3px solid var(--accent-potential)' }}>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', fontWeight: 700, textTransform: 'uppercase' }}>Review Required</span>
              <div style={{ fontSize: '1.5rem', fontWeight: 800, color: 'var(--text-primary)', marginTop: '4px' }}>{queue.filter(i => i.status === 'REVIEW_REQUIRED').length}</div>
            </div>
            <div className="glass-card" style={{ padding: '16px', borderLeft: '3px solid var(--accent-review)' }}>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', fontWeight: 700, textTransform: 'uppercase' }}>Under Review</span>
              <div style={{ fontSize: '1.5rem', fontWeight: 800, color: 'var(--text-primary)', marginTop: '4px' }}>{queue.filter(i => i.status === 'MARK_UNDER_INVESTIGATION').length}</div>
            </div>
            <div className="glass-card" style={{ padding: '16px', borderLeft: '3px solid var(--accent-pass)' }}>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', fontWeight: 700, textTransform: 'uppercase' }}>Resolved</span>
              <div style={{ fontSize: '1.5rem', fontWeight: 800, color: 'var(--text-primary)', marginTop: '4px' }}>{queue.filter(i => i.status === 'CONFIRM' || i.status === 'REJECT').length}</div>
            </div>
          </div>
        )}

        {/* Priority Queue Table */}
        {loading ? (
          <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-secondary)' }}>Loading priority queue...</div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.88rem' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-color)', color: 'var(--text-secondary)', fontSize: '0.78rem', textTransform: 'uppercase' }}>
                  <th style={{ padding: '12px 16px' }}>Product Commodity</th>
                  <th style={{ padding: '12px 16px' }}>Issue Type</th>
                  <th style={{ padding: '12px 16px' }}>Operational Priority Score</th>
                  <th style={{ padding: '12px 16px' }}>Signals</th>
                  <th style={{ padding: '12px 16px' }}>Status</th>
                  <th style={{ padding: '12px 16px' }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {filteredQueue.map(item => (
                  <tr key={item.cluster_id} style={{ borderBottom: '1px solid var(--border-color)', transition: 'background 0.2s' }}>
                    <td style={{ padding: '14px 16px', fontWeight: 700, color: 'var(--text-primary)' }}>
                      {item.product_name}
                      <span style={{ display: 'block', fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 400 }}>GTIN: {item.gtin || 'N/A'}</span>
                    </td>
                    <td style={{ padding: '14px 16px', color: 'var(--accent-review)', fontWeight: 600 }}>{item.issue_type}</td>
                    <td style={{ padding: '14px 16px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <div style={{ width: '60px', height: '6px', background: 'var(--border-color)', borderRadius: '3px', overflow: 'hidden' }}>
                          <div style={{ width: `${item.priority_score * 100}%`, height: '100%', background: item.priority_score > 0.7 ? 'var(--accent-potential)' : item.priority_score > 0.4 ? 'var(--accent-review)' : 'var(--color-primary)' }} />
                        </div>
                        <span style={{ fontWeight: 800, color: 'var(--text-primary)', fontFamily: 'monospace' }}>{item.priority_score.toFixed(2)}</span>
                        <span style={{
                          padding: '2px 7px', borderRadius: '10px', fontSize: '0.68rem', fontWeight: 700,
                          background: (item as any).priority_label === 'HIGH' ? 'rgba(233,137,126,0.15)' : (item as any).priority_label === 'MEDIUM' ? 'rgba(233,185,73,0.15)' : 'rgba(127,182,133,0.15)',
                          color: (item as any).priority_label === 'HIGH' ? 'var(--accent-potential)' : (item as any).priority_label === 'MEDIUM' ? 'var(--accent-review)' : 'var(--accent-pass)'
                        }} title={(item as any).priority_breakdown ? `Signals: ${(item as any).priority_breakdown.citizen_signals} | AI: ${(item as any).priority_breakdown.ai_flags} | Quality: ${(item as any).priority_breakdown.evidence_quality} | Severity: ${(item as any).priority_breakdown.severity} | Recency: ${(item as any).priority_breakdown.recency}` : ''}>
                          {(item as any).priority_label || 'N/A'}
                        </span>
                      </div>
                      {(item as any).priority_breakdown && (
                        <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', marginTop: '4px', display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                          <span>Signals +{(item as any).priority_breakdown.citizen_signals}</span>
                          <span>AI +{(item as any).priority_breakdown.ai_flags}</span>
                          <span>Quality +{(item as any).priority_breakdown.evidence_quality}</span>
                        </div>
                      )}
                    </td>
                    <td style={{ padding: '14px 16px', color: 'var(--text-primary)' }}>
                      <span style={{ color: 'var(--color-primary)', fontWeight: 700 }}>{item.citizen_reports_count} Citizens</span> • <span style={{ color: 'var(--accent-potential)', fontWeight: 700 }}>{item.ai_flags_count} AI Flags</span>
                    </td>
                    <td style={{ padding: '14px 16px' }}>
                      <span style={{
                        padding: '4px 8px', borderRadius: '12px', fontSize: '0.72rem', fontWeight: 700,
                        background: item.status === 'CONFIRM' ? 'rgba(233, 137, 126, 0.2)' : item.status === 'UNVERIFIED' ? 'rgba(233, 185, 73, 0.2)' : 'rgba(111, 168, 220, 0.2)',
                        color: item.status === 'CONFIRM' ? 'var(--accent-potential)' : item.status === 'UNVERIFIED' ? 'var(--accent-review)' : 'var(--color-primary)'
                      }}>
                        {item.status}
                      </span>
                    </td>
                    <td style={{ padding: '14px 16px' }}>
                      <button
                        onClick={() => {
                          if (onInvestigate) {
                            onInvestigate(item.product_id, undefined, item.cluster_id);
                          } else {
                            setSelectedCluster(item);
                          }
                        }}
                        className="btn-secondary"
                        style={{ padding: '6px 12px', fontSize: '0.78rem' }}
                      >
                        Inspect & Review
                      </button>
                    </td>
                  </tr>
                ))}

                {filteredQueue.length === 0 && (
                  <tr>
                    <td colSpan={6} style={{ textAlign: 'center', padding: '48px 24px', color: 'var(--text-secondary)' }}>
                      <Shield size={32} style={{ margin: '0 auto 12px', opacity: 0.3 }} color="var(--text-secondary)" />
                      <p style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-primary)' }}>Everything looks quiet right now.</p>
                      <p style={{ fontSize: '0.85rem', marginTop: '4px' }}>No priority cases found matching your filter.</p>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Review Modal */}
      {selectedCluster && (
        <div style={{ position: 'fixed', top: 0, left: 0, width: '100vw', height: '100vh', background: 'rgba(0,0,0,0.4)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100 }}>
          <div className="glass-panel" style={{ width: '540px', padding: '24px', position: 'relative', background: 'var(--bg-card)' }}>
            <h3 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: '6px', color: 'var(--text-primary)' }}>
              Enforcement Officer Review: {selectedCluster.product_name}
            </h3>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '16px' }}>
              Priority Score: {selectedCluster.priority_score.toFixed(2)} • Issue: {selectedCluster.issue_type}
            </p>

            <form onSubmit={handleReviewSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div>
                <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', fontWeight: 600, display: 'block', marginBottom: '6px' }}>
                  Officer Adjudication Decision *
                </label>
                <select
                  value={decision}
                  onChange={(e) => setDecision(e.target.value)}
                  style={{ width: '100%', padding: '10px', borderRadius: '6px', border: '1px solid var(--border-color)', background: 'var(--bg-main)', color: 'var(--text-primary)', fontSize: '0.88rem' }}
                >
                  <option value="CONFIRM">CONFIRM — Issue Verified for Formal Investigation</option>
                  <option value="MARK_UNDER_INVESTIGATION">MARK_UNDER_INVESTIGATION — Pending Officer Site Verification</option>
                  <option value="REQUEST_MORE_EVIDENCE">REQUEST_MORE_EVIDENCE — Re-scan Required</option>
                  <option value="REJECT">REJECT — Invalid Signal / Retake False Flag</option>
                </select>
              </div>

              <div>
                <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', fontWeight: 600, display: 'block', marginBottom: '6px' }}>
                  Inspection Rationale & Audit Trail Note *
                </label>
                <textarea
                  rows={4}
                  required
                  placeholder="Record formal statutory officer rationale for decision log..."
                  value={rationale}
                  onChange={(e) => setRationale(e.target.value)}
                  style={{ width: '100%', padding: '10px', borderRadius: '6px', border: '1px solid var(--border-color)', background: 'var(--bg-main)', color: 'var(--text-primary)', fontSize: '0.88rem' }}
                />
              </div>

              <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end', marginTop: '10px' }}>
                <button type="button" onClick={() => setSelectedCluster(null)} className="btn-secondary">
                  Cancel
                </button>
                <button type="submit" disabled={reviewSubmitting} className="btn-primary">
                  {reviewSubmitting ? 'Recording Audit Trail...' : 'Commit Officer Decision'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
