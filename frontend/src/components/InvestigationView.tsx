import React, { useState, useEffect } from 'react';
import { getProductIntelligence, listProducts, getScanResult, submitOfficerReview, getScanFindings, correctEvidence } from '../api';
import type { ScanResult, Finding } from '../types';
import {
  ArrowLeft, Shield, AlertTriangle, CheckCircle2, HelpCircle,
  Users, Search, ClipboardList, TrendingUp, FileText, ChevronDown,
  ChevronRight, Activity, Eye, Calendar, Package, Send, Lock
} from 'lucide-react';

interface InvestigationViewProps {
  productId?: string;
  scanId?: string;
  userRole?: string;
  onClose: () => void;
}

const RiskBadge: React.FC<{ level: string }> = ({ level }) => {
  const config: Record<string, { bg: string; color: string; border: string; label: string }> = {
    HIGH: { bg: 'rgba(233, 137, 126, 0.12)', color: 'var(--accent-potential)', border: 'var(--accent-potential)', label: '⚠ HIGH RISK' },
    ELEVATED: { bg: 'rgba(233, 185, 73, 0.12)', color: 'var(--accent-review)', border: 'var(--accent-review)', label: '◉ ELEVATED' },
    LOW: { bg: 'rgba(127, 182, 133, 0.12)', color: 'var(--accent-pass)', border: 'var(--accent-pass)', label: '✓ LOW RISK' },
  };
  const c = config[level] || config['LOW'];
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: '6px',
      padding: '5px 14px', borderRadius: '20px', fontWeight: 700, fontSize: '0.82rem',
      background: c.bg, color: c.color, border: `1.5px solid ${c.border}`
    }}>
      {c.label}
    </span>
  );
};

const StatusIcon: React.FC<{ status: string }> = ({ status }) => {
  if (status === 'PASS_SCREENING') return <CheckCircle2 size={14} color="var(--accent-pass)" />;
  if (status === 'POTENTIAL_NON_COMPLIANCE') return <AlertTriangle size={14} color="var(--accent-potential)" />;
  return <HelpCircle size={14} color="var(--accent-review)" />;
};

const EvidenceWeightBadge: React.FC<{ weight: string }> = ({ weight }) => {
  const map: Record<string, { color: string; bg: string }> = {
    HIGH: { color: 'var(--accent-potential)', bg: 'rgba(233,137,126,0.1)' },
    MEDIUM: { color: 'var(--accent-review)', bg: 'rgba(233,185,73,0.1)' },
    NONE: { color: 'var(--text-muted)', bg: 'var(--color-subtle-bg)' },
  };
  const s = map[weight] || map['NONE'];
  return (
    <span style={{ fontSize: '0.7rem', fontWeight: 700, padding: '2px 8px', borderRadius: '10px', background: s.bg, color: s.color }}>
      {weight}
    </span>
  );
};

export const InvestigationView: React.FC<InvestigationViewProps> = ({ productId, scanId, userRole = 'OFFICER', onClose }) => {
  const [intel, setIntel] = useState<any>(null);
  const [scanDetail, setScanDetail] = useState<ScanResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'scans' | 'signals' | 'audit'>('overview');
  const [expandedScan, setExpandedScan] = useState<string | null>(null);
  const [expandedFindings, setExpandedFindings] = useState<Finding[]>([]);
  const [loadingFindings, setLoadingFindings] = useState(false);
  const [products, setProducts] = useState<any[]>([]);
  const [selectedProductId, setSelectedProductId] = useState<string | undefined>(productId);

  // Officer review form state
  const [selectedAction, setSelectedAction] = useState<string>('MARK_UNDER_INVESTIGATION');
  const [rationale, setRationale] = useState<string>('Product identity conflicts with submitted product name. Flagged for detailed officer investigation.');
  const [submittingReview, setSubmittingReview] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitSuccess, setSubmitSuccess] = useState(false);

  // Load product list for dropdown selector
  useEffect(() => {
    listProducts().then(setProducts).catch(() => {});
  }, []);

  // Load scan detail if scanId provided
  useEffect(() => {
    if (!scanId) return;
    getScanResult(scanId)
      .then(data => {
        setScanDetail(data);
        if (data.product_id && !selectedProductId) {
          setSelectedProductId(data.product_id);
        }
      })
      .catch(() => {});
  }, [scanId]);

  // Load intelligence when selectedProductId changes
  useEffect(() => {
    if (!selectedProductId) return;
    setLoading(true);
    setError(null);
    setIntel(null);
    getProductIntelligence(selectedProductId)
      .then(data => { setIntel(data); setLoading(false); })
      .catch(err => { setError(err.message); setLoading(false); });
  }, [selectedProductId]);

  const handleReviewSubmit = async () => {
    if (!rationale.trim()) {
      setSubmitError('Officer rationale is required.');
      return;
    }
    setSubmittingReview(true);
    setSubmitError(null);
    setSubmitSuccess(false);

    try {
      await submitOfficerReview({
        scan_id: scanId,
        product_id: selectedProductId,
        cluster_id: intel?.issue_clusters?.[0]?.cluster_id,
        decision: selectedAction,
        rationale: rationale
      }, userRole);

      setSubmitSuccess(true);
      // Refresh intelligence
      if (selectedProductId) {
        const updated = await getProductIntelligence(selectedProductId);
        setIntel(updated);
      }
    } catch (err: any) {
      setSubmitError(err.message || 'Unable to save this review. Please try again.');
    } finally {
      setSubmittingReview(false);
    }
  };

  const handleScanExpand = async (clickedScanId: string) => {
    if (expandedScan === clickedScanId) {
      setExpandedScan(null);
      return;
    }
    setExpandedScan(clickedScanId);
    setLoadingFindings(true);
    try {
      const data = await getScanFindings(clickedScanId);
      setExpandedFindings(data.findings || []);
    } catch (err) {
      console.error('Failed to load findings:', err);
      setExpandedFindings([]);
    } finally {
      setLoadingFindings(false);
    }
  };

  const TABS = [
    { id: 'overview', label: 'Evidence Chain', icon: <Eye size={15} /> },
    { id: 'scans', label: `Scan History${intel ? ` (${intel.scan_history.length})` : ''}`, icon: <Activity size={15} /> },
    { id: 'signals', label: `Citizen Signals${intel ? ` (${intel.citizen_signals?.length || 0})` : ''}`, icon: <Users size={15} /> },
    { id: 'audit', label: 'Audit Trail', icon: <ClipboardList size={15} /> },
  ];

  return (
    <div style={{ maxWidth: '1280px', margin: '0 auto', padding: '24px' }}>
      {/* Header Bar */}
      <div className="glass-panel" style={{ padding: '20px 24px', marginBottom: '20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', justifyContent: 'space-between', flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <button
              onClick={onClose}
              style={{
                display: 'flex', alignItems: 'center', gap: '6px', background: 'transparent',
                border: '1px solid var(--border-color)', color: 'var(--text-secondary)',
                padding: '6px 12px', borderRadius: '8px', fontSize: '0.82rem', fontWeight: 600, cursor: 'pointer'
              }}
            >
              <ArrowLeft size={14} /> Back
            </button>
            <div>
              <h2 style={{ fontSize: '1.15rem', fontWeight: 800, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Shield size={20} color="var(--color-primary)" />
                Officer Investigation Workspace
              </h2>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
                Consolidated evidence, history, citizen signals &amp; officer review actions
              </p>
            </div>
          </div>

          {/* Product Selector */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Package size={15} color="var(--text-muted)" />
            <select
              value={selectedProductId || ''}
              onChange={e => setSelectedProductId(e.target.value || undefined)}
              style={{
                padding: '8px 12px', borderRadius: '8px', border: '1px solid var(--border-color)',
                background: 'var(--bg-card)', color: 'var(--text-primary)', fontSize: '0.85rem',
                fontFamily: 'var(--font-main)', cursor: 'pointer', minWidth: '220px'
              }}
            >
              <option value="">Select a product...</option>
              {products.map(p => (
                <option key={p.product_id} value={p.product_id}>{p.product_name} {p.gtin ? `(${p.gtin})` : ''}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Identity Warning Banner from Scan */}
      {scanDetail?.identity_warnings && scanDetail.identity_warnings.length > 0 && (
        <div style={{ padding: '16px', background: 'rgba(233, 185, 73, 0.12)', border: '2px solid var(--accent-review)', borderRadius: '10px', marginBottom: '20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
            <AlertTriangle size={18} color="var(--accent-review)" />
            <h4 style={{ fontSize: '0.95rem', fontWeight: 800, color: 'var(--accent-review)' }}>
              Product Identity Conflict Detected
            </h4>
          </div>
          {scanDetail.identity_warnings.map((w, idx) => (
            <div key={idx} style={{ fontSize: '0.85rem', color: 'var(--text-primary)', paddingLeft: '26px' }}>
              <div><span style={{ color: 'var(--text-secondary)' }}>You entered:</span> <strong>{w.user_provided}</strong></div>
              <div><span style={{ color: 'var(--text-secondary)' }}>Image-derived product:</span> <strong>{w.image_evidence}</strong></div>
              <div style={{ marginTop: '4px', fontSize: '0.78rem', color: 'var(--text-secondary)' }}>{w.explanation}</div>
            </div>
          ))}
        </div>
      )}

      {/* Officer Action Panel */}
      <div className="glass-panel" style={{ padding: '20px', marginBottom: '20px', border: '1.5px solid var(--color-primary)' }}>
        <h4 style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Shield size={18} color="var(--color-primary)" />
          Officer Review &amp; Enforcement Action
        </h4>

        {userRole !== 'OFFICER' ? (
          <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', padding: '12px', background: 'var(--color-subtle-bg)', borderRadius: '8px' }}>
            <Lock size={14} style={{ display: 'inline', marginRight: '6px' }} />
            You are currently viewing in <strong>CITIZEN</strong> mode. Officer authorization is required to perform review actions.
          </div>
        ) : (
          <div>
            <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', marginBottom: '12px' }}>
              {[
                { id: 'MARK_UNDER_INVESTIGATION', label: 'MARK UNDER INVESTIGATION', color: 'var(--accent-review)' },
                { id: 'REQUEST_MORE_EVIDENCE', label: 'REQUEST MORE EVIDENCE', color: 'var(--color-primary)' },
                { id: 'CONFIRM', label: 'CONFIRM NON-COMPLIANCE', color: 'var(--accent-potential)' },
                { id: 'REJECT', label: 'REJECT / DISMISS', color: 'var(--accent-pass)' },
              ].map(act => (
                <button
                  key={act.id}
                  onClick={() => {
                    setSelectedAction(act.id);
                    if (act.id === 'REQUEST_MORE_EVIDENCE') {
                      setRationale('Please upload a clearer image showing the complete product identity and declaration panel.');
                    } else if (act.id === 'MARK_UNDER_INVESTIGATION') {
                      setRationale('Product identity conflicts with submitted product name. Flagged for detailed officer investigation.');
                    } else if (act.id === 'CONFIRM') {
                      setRationale('Label declaration non-compliance confirmed based on official inspection.');
                    } else if (act.id === 'REJECT') {
                      setRationale('Screening flag reviewed and dismissed after inspection.');
                    }
                  }}
                  style={{
                    padding: '8px 14px', borderRadius: '8px', fontSize: '0.8rem', fontWeight: 700, cursor: 'pointer',
                    background: selectedAction === act.id ? act.color : 'transparent',
                    color: selectedAction === act.id ? '#ffffff' : 'var(--text-primary)',
                    border: `1.5px solid ${act.color}`
                  }}
                >
                  {act.label}
                </button>
              ))}
            </div>

            <div style={{ marginBottom: '12px' }}>
              <label style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: '4px' }}>
                Officer Rationale / Reason *
              </label>
              <textarea
                rows={3}
                value={rationale}
                onChange={e => setRationale(e.target.value)}
                placeholder="Enter officer rationale or instructions..."
                style={{ width: '100%', padding: '10px', borderRadius: '8px', border: '1px solid var(--border-color)', background: 'var(--bg-card)', color: 'var(--text-primary)', fontSize: '0.85rem' }}
              />
            </div>

            {submitError && (
              <div style={{ marginBottom: '12px', padding: '10px 14px', borderRadius: '8px', background: 'rgba(233,137,126,0.15)', color: 'var(--accent-potential)', fontSize: '0.82rem', fontWeight: 600 }}>
                {submitError}
              </div>
            )}

            {submitSuccess && (
              <div style={{ marginBottom: '12px', padding: '10px 14px', borderRadius: '8px', background: 'rgba(127,182,133,0.15)', color: 'var(--accent-pass)', fontSize: '0.82rem', fontWeight: 600 }}>
                ✓ Officer review action saved to audit trail successfully.
              </div>
            )}

            <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
              <button
                onClick={handleReviewSubmit}
                disabled={submittingReview}
                className="btn-primary"
                style={{ padding: '10px 20px', fontSize: '0.88rem' }}
              >
                <Send size={15} /> {submittingReview ? 'Persisting Action...' : 'Persist Officer Action'}
              </button>

              {scanId && (
                <button
                  onClick={() => {
                    import('../api').then(({ generateNoticeUrl }) => {
                      window.open(generateNoticeUrl(scanId), '_blank');
                    });
                  }}
                  className="btn-secondary"
                  style={{ padding: '10px 20px', fontSize: '0.88rem', display: 'flex', alignItems: 'center', gap: '6px' }}
                >
                  <FileText size={15} /> Generate Sec 15 Notice
                </button>
              )}
            </div>
          </div>
        )}
      </div>

      {/* No product selected */}
      {!selectedProductId && !scanDetail && (
        <div className="glass-panel" style={{ padding: '60px 24px', textAlign: 'center' }}>
          <Search size={40} color="var(--color-primary)" style={{ margin: '0 auto 16px', opacity: 0.6 }} />
          <p style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '8px' }}>Select a product to investigate</p>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
            Choose a product from the dropdown above, or scan a product first to register it.
          </p>
        </div>
      )}

      {/* Loading */}
      {selectedProductId && loading && (
        <div className="glass-panel" style={{ padding: '60px 24px', textAlign: 'center' }}>
          <div style={{ width: '40px', height: '40px', border: '3px solid var(--border-color)', borderTopColor: 'var(--color-primary)', borderRadius: '50%', animation: 'spin 1s linear infinite', margin: '0 auto 16px' }} />
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>Building product intelligence view...</p>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="glass-panel" style={{ padding: '24px', background: 'rgba(233,137,126,0.05)', border: '1px solid var(--accent-potential)' }}>
          <p style={{ color: 'var(--accent-potential)', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '8px' }}>
            <AlertTriangle size={16} /> {error}
          </p>
        </div>
      )}

      {/* Main Intelligence View */}
      {intel && !loading && (
        <>
          {/* Product + Risk Summary Banner */}
          <div className="glass-panel" style={{ padding: '20px 24px', marginBottom: '20px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px' }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '4px' }}>
                  <h3 style={{ fontSize: '1.1rem', fontWeight: 800, color: 'var(--text-primary)' }}>{intel.product.product_name}</h3>
                  <RiskBadge level={intel.risk_summary.risk_level} />
                </div>
                <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
                  {intel.product.gtin && (
                    <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                      GTIN: {intel.product.gtin}
                    </span>
                  )}
                  <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)', textTransform: 'capitalize' }}>
                    Category: {intel.product.category}
                  </span>
                  {intel.product.manufacturer && (
                    <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                      Mfg: {intel.product.manufacturer}
                    </span>
                  )}
                </div>
              </div>

              {/* Stats Row */}
              <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
                {[
                  { label: 'Scans', value: intel.risk_summary.total_scans, color: 'var(--text-primary)' },
                  { label: 'Passes', value: intel.risk_summary.pass_count, color: 'var(--accent-pass)' },
                  { label: 'Flagged', value: intel.risk_summary.potential_count, color: 'var(--accent-potential)' },
                  { label: 'Citizen Signals', value: intel.risk_summary.citizen_signal_count, color: 'var(--accent-review)' },
                  { label: 'Active Issues', value: intel.risk_summary.active_clusters, color: 'var(--color-primary)' },
                ].map(stat => (
                  <div key={stat.label} style={{
                    textAlign: 'center', padding: '8px 14px', borderRadius: '10px',
                    background: 'var(--color-subtle-bg)', border: '1px solid var(--border-color)'
                  }}>
                    <div style={{ fontSize: '1.3rem', fontWeight: 800, color: stat.color }}>{stat.value}</div>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 600 }}>{stat.label}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Tab Navigation */}
          <div style={{ display: 'flex', gap: '4px', marginBottom: '20px', background: 'var(--bg-card)', border: '1px solid var(--border-color)', borderRadius: '12px', padding: '4px', width: 'fit-content' }}>
            {TABS.map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                style={{
                  display: 'flex', alignItems: 'center', gap: '6px',
                  padding: '8px 16px', borderRadius: '8px', border: 'none',
                  background: activeTab === tab.id ? 'var(--color-primary)' : 'transparent',
                  color: activeTab === tab.id ? '#fff' : 'var(--text-secondary)',
                  fontWeight: 600, fontSize: '0.82rem', cursor: 'pointer',
                  transition: 'all 0.2s ease'
                }}
              >
                {tab.icon}
                {tab.label}
              </button>
            ))}
          </div>

          {/* OVERVIEW TAB — Evidence Chain */}
          {activeTab === 'overview' && (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 320px', gap: '20px' }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                {scanDetail?.product_context && (
                  <div className="glass-panel" style={{ padding: '20px' }}>
                    <h4 style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <Package size={16} color="var(--color-primary)" />
                      Product Context (Applicability Drivers)
                    </h4>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px' }}>
                      <div style={{ background: 'var(--color-subtle-bg)', padding: '10px 14px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                        <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', display: 'block' }}>Category</span>
                        <span style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-primary)', textTransform: 'capitalize' }}>
                          {scanDetail.product_context.product_category === 'CONTEXT_REVIEW_REQUIRED' ? (
                            <span style={{ color: 'var(--accent-review)' }}>⚠ REVIEW REQUIRED</span>
                          ) : (
                            scanDetail.product_context.product_category || 'General'
                          )}
                        </span>
                      </div>
                      <div style={{ background: 'var(--color-subtle-bg)', padding: '10px 14px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                        <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', display: 'block' }}>Market Context</span>
                        <span style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-primary)', textTransform: 'capitalize' }}>{scanDetail.product_context.market_context || 'Retail'}</span>
                      </div>
                      <div style={{ background: 'var(--color-subtle-bg)', padding: '10px 14px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                        <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', display: 'block' }}>Origin</span>
                        <span style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-primary)', textTransform: 'capitalize' }}>{scanDetail.product_context.origin || 'Domestic'}</span>
                      </div>
                      <div style={{ background: 'var(--color-subtle-bg)', padding: '10px 14px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                        <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', display: 'block' }}>Classifier Confidence</span>
                        <span style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                          {((scanDetail.product_context.context_confidence || 1) * 100).toFixed(0)}%
                        </span>
                      </div>
                    </div>
                  </div>
                )}
                {/* Evidence Chain */}
                <div className="glass-panel" style={{ padding: '20px' }}>
                  <h4 style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <TrendingUp size={16} color="var(--color-primary)" />
                  WHY this risk level? — Evidence Chain
                </h4>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  {intel.evidence_chain.map((ev: any, idx: number) => (
                    <div key={idx} style={{
                      padding: '14px 16px', borderRadius: '10px',
                      background: ev.weight === 'HIGH' ? 'rgba(233,137,126,0.06)' : ev.weight === 'MEDIUM' ? 'rgba(233,185,73,0.06)' : 'var(--color-subtle-bg)',
                      border: `1px solid ${ev.weight === 'HIGH' ? 'rgba(233,137,126,0.25)' : ev.weight === 'MEDIUM' ? 'rgba(233,185,73,0.25)' : 'var(--border-color)'}`,
                    }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                        <span style={{ fontSize: '0.82rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                          {ev.signal}
                        </span>
                        <EvidenceWeightBadge weight={ev.weight} />
                      </div>
                      <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: '1.5' }}>
                        {ev.observation}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            </div>

                {/* Top Issues */}
                {intel.risk_summary.top_issues.length > 0 && (
                  <div style={{ marginTop: '20px', paddingTop: '16px', borderTop: '1px solid var(--border-color)' }}>
                    <h5 style={{ fontSize: '0.82rem', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '10px', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                      Most Reported Issues
                    </h5>
                    <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                      {intel.risk_summary.top_issues.map((issue: any) => (
                        <span key={issue.issue} style={{
                          padding: '4px 12px', borderRadius: '20px', fontSize: '0.78rem', fontWeight: 600,
                          background: 'rgba(233,185,73,0.1)', color: 'var(--accent-review)',
                          border: '1px solid rgba(233,185,73,0.25)'
                        }}>
                          {issue.issue} ({issue.count})
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Quick Stats Sidebar */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                <div className="glass-panel" style={{ padding: '16px' }}>
                  <h5 style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '12px', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                    Screening Outcomes
                  </h5>
                  {[
                    { label: 'PASS_SCREENING', count: intel.risk_summary.pass_count, color: 'var(--accent-pass)' },
                    { label: 'POTENTIAL_NON_COMPLIANCE', count: intel.risk_summary.potential_count, color: 'var(--accent-potential)' },
                    { label: 'NEEDS_REVIEW', count: intel.risk_summary.review_count, color: 'var(--accent-review)' },
                  ].map(item => (
                    <div key={item.label} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '6px 0', borderBottom: '1px solid var(--border-color)' }}>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>{item.label}</span>
                      <span style={{ fontSize: '0.88rem', fontWeight: 700, color: item.color }}>{item.count}</span>
                    </div>
                  ))}
                </div>

                <div className="glass-panel" style={{ padding: '16px' }}>
                  <h5 style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                    Product Record
                  </h5>
                  <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span>Category</span>
                      <span style={{ color: 'var(--text-primary)', fontWeight: 600, textTransform: 'capitalize' }}>{intel.product.category}</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span>Registered</span>
                      <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{new Date(intel.product.registered_at).toLocaleDateString()}</span>
                    </div>
                    {intel.product.gtin && (
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <span>GTIN</span>
                        <span style={{ color: 'var(--text-primary)', fontWeight: 600, fontFamily: 'var(--font-mono)', fontSize: '0.72rem' }}>{intel.product.gtin}</span>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* SCAN HISTORY TAB */}
          {activeTab === 'scans' && (
            <div className="glass-panel" style={{ padding: '20px' }}>
              <h4 style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Activity size={16} color="var(--color-primary)" />
                All Screening Scans ({intel.scan_history.length})
              </h4>

              {intel.scan_history.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
                  <Activity size={32} style={{ margin: '0 auto 12px', opacity: 0.4 }} />
                  <p>No scans on record for this product.</p>
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {intel.scan_history.map((scan: any) => (
                    <div key={scan.scan_id}>
                      <div
                        className="glass-card"
                        style={{ padding: '12px 16px', cursor: 'pointer' }}
                        onClick={() => handleScanExpand(scan.scan_id)}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                            <StatusIcon status={scan.status} />
                            <div>
                              <div style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-primary)' }}>{scan.status}</div>
                              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', display: 'flex', gap: '10px', marginTop: '2px' }}>
                                <span><Calendar size={10} style={{ display: 'inline', marginRight: '3px' }} />{new Date(scan.timestamp).toLocaleString()}</span>
                                <span>Confidence: {(scan.screening_confidence * 100).toFixed(0)}%</span>
                                <span>Quality: {scan.quality_status}</span>
                              </div>
                            </div>
                          </div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>#{scan.scan_id.slice(-8)}</span>
                            {expandedScan === scan.scan_id ? <ChevronDown size={14} color="var(--text-muted)" /> : <ChevronRight size={14} color="var(--text-muted)" />}
                          </div>
                        </div>
                      </div>

                      {/* Expanded Scan Detail: Evidence Graph Layer */}
                      {expandedScan === scan.scan_id && (
                        <div style={{
                          marginTop: '4px', padding: '16px', borderRadius: '10px',
                          background: 'var(--color-subtle-bg)', border: '1px solid var(--border-color)'
                        }}>
                          <p style={{ fontSize: '0.8rem', fontWeight: 800, color: 'var(--text-primary)', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                            <TrendingUp size={14} color="var(--color-primary)" /> Evidence Chain
                          </p>
                          
                          {loadingFindings ? (
                            <div style={{ padding: '20px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                              Loading evidence graph...
                            </div>
                          ) : expandedFindings.length === 0 ? (
                            <div style={{ padding: '20px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                              No traceable evidence found for this scan.
                            </div>
                          ) : (
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                              {expandedFindings.map((finding: Finding) => (
                                <div key={finding.finding_id} style={{ padding: '12px', borderRadius: '8px', background: 'var(--bg-card)', border: '1px solid var(--border-color)' }}>
                                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
                                    <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                                      <span style={{ fontSize: '0.75rem', fontWeight: 700, padding: '2px 8px', borderRadius: '12px', background: 'var(--color-subtle-bg)', color: 'var(--text-primary)', textTransform: 'uppercase' }}>
                                        {finding.field.replace(/_/g, ' ')}
                                      </span>
                                      <span style={{ fontSize: '0.7rem', fontWeight: 800, padding: '2px 8px', borderRadius: '12px', background: finding.applicability === 'REQUIRED' ? 'var(--color-primary)' : 'var(--color-subtle-bg)', color: finding.applicability === 'REQUIRED' ? '#fff' : 'var(--text-secondary)' }}>
                                        {finding.applicability}
                                      </span>
                                      <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
                                        {finding.rule_reference}
                                      </span>
                                    </div>
                                    <span style={{ fontSize: '0.75rem', fontWeight: 800, color: finding.status === 'PASS' ? 'var(--accent-pass)' : finding.status === 'POTENTIAL_NON_COMPLIANCE' ? 'var(--accent-potential)' : 'var(--accent-review)' }}>
                                      {finding.status}
                                    </span>
                                  </div>

                                  <div style={{ background: 'var(--color-subtle-bg)', padding: '10px', borderRadius: '6px', fontSize: '0.8rem', color: 'var(--text-primary)', whiteSpace: 'pre-wrap', fontFamily: 'var(--font-mono)' }}>
                                    {finding.explanation}
                                  </div>

                                  {/* Officer Correction UI */}
                                  {finding.evidence_ids && finding.evidence_ids.length > 0 && userRole === 'OFFICER' && (
                                    <div style={{ marginTop: '12px', paddingTop: '12px', borderTop: '1px dashed var(--border-color)' }}>
                                      <form onSubmit={async (e) => {
                                        e.preventDefault();
                                        const form = e.target as HTMLFormElement;
                                        const val = (form.elements.namedItem('correct_val') as HTMLInputElement).value;
                                        if (val) {
                                          try {
                                            await correctEvidence(scan.scan_id, finding.evidence_ids[0], val, 'Manual Officer Correction', userRole);
                                            alert('Evidence corrected successfully.');
                                            handleScanExpand(scan.scan_id); // Refresh
                                          } catch (err: any) {
                                            alert(err.message || 'Correction failed');
                                          }
                                        }
                                      }} style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                                        <Shield size={14} color="var(--accent-review)" />
                                        <input name="correct_val" type="text" placeholder={`Correct ${finding.field}...`} defaultValue={finding.observed_value || ''} style={{ flex: 1, padding: '6px 10px', borderRadius: '6px', border: '1px solid var(--border-color)', background: 'var(--bg-card)', color: 'var(--text-primary)', fontSize: '0.8rem' }} />
                                        <button type="submit" style={{ padding: '6px 12px', borderRadius: '6px', background: 'var(--accent-review)', color: '#fff', border: 'none', fontSize: '0.75rem', fontWeight: 700, cursor: 'pointer' }}>Override</button>
                                      </form>
                                    </div>
                                  )}
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* CITIZEN SIGNALS TAB */}
          {activeTab === 'signals' && (
            <div className="glass-panel" style={{ padding: '20px' }}>
              <h4 style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Users size={16} color="var(--color-primary)" />
                Citizen Intelligence Signals ({intel.citizen_signals.length})
              </h4>

              {intel.citizen_signals.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
                  <Users size={32} style={{ margin: '0 auto 12px', opacity: 0.4 }} />
                  <p>No citizen signals for this product yet.</p>
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  {intel.citizen_signals.map((sig: any) => (
                    <div key={sig.report_id} className="glass-card" style={{ padding: '14px 16px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '12px' }}>
                        <div style={{ flex: 1 }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                            <span style={{
                              fontSize: '0.75rem', fontWeight: 700, padding: '2px 10px', borderRadius: '20px',
                              background: 'rgba(233,185,73,0.1)', color: 'var(--accent-review)',
                              border: '1px solid rgba(233,185,73,0.25)'
                            }}>
                              {sig.issue_category}
                            </span>
                            <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                              📍 {sig.location_city}
                            </span>
                          </div>
                          {sig.description && (
                            <p style={{ fontSize: '0.85rem', color: 'var(--text-primary)', lineHeight: '1.5', marginBottom: '6px' }}>
                              "{sig.description}"
                            </p>
                          )}
                          <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                            Filed: {new Date(sig.created_at).toLocaleDateString()}
                          </span>
                        </div>
                        <span style={{
                          fontSize: '0.7rem', fontWeight: 700, padding: '3px 10px', borderRadius: '20px',
                          background: sig.status === 'CONFIRMED' ? 'rgba(127,182,133,0.1)' : 'var(--color-subtle-bg)',
                          color: sig.status === 'CONFIRMED' ? 'var(--accent-pass)' : 'var(--text-muted)',
                          border: `1px solid ${sig.status === 'CONFIRMED' ? 'rgba(127,182,133,0.3)' : 'var(--border-color)'}`
                        }}>
                          {sig.status}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* AUDIT TRAIL TAB */}
          {activeTab === 'audit' && (
            <div className="glass-panel" style={{ padding: '20px' }}>
              <h4 style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <ClipboardList size={16} color="var(--color-primary)" />
                Officer Action Audit Trail
              </h4>

              {intel.issue_clusters.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
                  <ClipboardList size={32} style={{ margin: '0 auto 12px', opacity: 0.4 }} />
                  <p>No issue clusters or officer actions on record.</p>
                </div>
              ) : (
                intel.issue_clusters.map((cluster: any) => (
                  <div key={cluster.cluster_id} style={{ marginBottom: '20px' }}>
                    <div style={{
                      padding: '12px 16px', borderRadius: '10px 10px 0 0',
                      background: 'var(--color-subtle-bg)', border: '1px solid var(--border-color)',
                      display: 'flex', justifyContent: 'space-between', alignItems: 'center'
                    }}>
                      <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
                        <span style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                          Issue Cluster: {cluster.issue_type}
                        </span>
                        <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>#{cluster.cluster_id.slice(-8)}</span>
                      </div>
                      <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                        <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Priority: <b style={{ color: 'var(--text-primary)' }}>{cluster.priority_score}</b></span>
                        <span style={{
                          fontSize: '0.7rem', fontWeight: 700, padding: '2px 10px', borderRadius: '20px',
                          background: cluster.status === 'CONFIRM' ? 'rgba(127,182,133,0.1)' : 'rgba(233,185,73,0.1)',
                          color: cluster.status === 'CONFIRM' ? 'var(--accent-pass)' : 'var(--accent-review)',
                          border: `1px solid ${cluster.status === 'CONFIRM' ? 'rgba(127,182,133,0.3)' : 'rgba(233,185,73,0.25)'}`
                        }}>
                          {cluster.status}
                        </span>
                      </div>
                    </div>

                    <div style={{ border: '1px solid var(--border-color)', borderTop: 'none', borderRadius: '0 0 10px 10px', overflow: 'hidden' }}>
                      {cluster.audit_trail.length === 0 ? (
                        <div style={{ padding: '16px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.82rem' }}>
                          No officer reviews on this cluster yet.
                        </div>
                      ) : (
                        cluster.audit_trail.map((entry: any, idx: number) => (
                          <div key={entry.review_id} style={{
                            padding: '14px 16px',
                            background: idx % 2 === 0 ? 'var(--bg-card)' : 'var(--color-subtle-bg)',
                            borderTop: idx > 0 ? '1px solid var(--border-color)' : 'none'
                          }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '12px' }}>
                              <div style={{ flex: 1 }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                                  <span style={{
                                    fontSize: '0.75rem', fontWeight: 700, padding: '2px 10px', borderRadius: '20px',
                                    background: entry.decision === 'CONFIRM' ? 'rgba(127,182,133,0.1)' : entry.decision === 'REJECT' ? 'rgba(233,137,126,0.1)' : 'rgba(233,185,73,0.1)',
                                    color: entry.decision === 'CONFIRM' ? 'var(--accent-pass)' : entry.decision === 'REJECT' ? 'var(--accent-potential)' : 'var(--accent-review)',
                                    border: `1px solid ${entry.decision === 'CONFIRM' ? 'rgba(127,182,133,0.3)' : entry.decision === 'REJECT' ? 'rgba(233,137,126,0.3)' : 'rgba(233,185,73,0.25)'}`
                                  }}>
                                    {entry.decision}
                                  </span>
                                  <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                                    by Officer · {new Date(entry.timestamp).toLocaleString()}
                                  </span>
                                </div>
                                <p style={{ fontSize: '0.85rem', color: 'var(--text-primary)', lineHeight: '1.5', fontStyle: 'italic' }}>
                                  "{entry.rationale}"
                                </p>
                              </div>
                              <FileText size={14} color="var(--text-muted)" style={{ flexShrink: 0, marginTop: '2px' }} />
                            </div>
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>
          )}
        </>
      )}

      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
};
