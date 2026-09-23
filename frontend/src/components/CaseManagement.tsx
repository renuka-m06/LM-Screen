import React, { useState, useEffect, useCallback } from 'react';
import {
  listCases, getCaseDetail, createCase, addCaseNote,
  recordCaseFinding, createCaseInspection, closeCase, reopenCase
} from '../api';
import type { CaseSummary, CaseDetail, PriorityQueueItem } from '../types';
import { formatFieldValue } from '../utils';
import {
  Shield, AlertTriangle, CheckCircle2, Clock, Search,
  ChevronRight, ChevronDown, FileText, Activity, Eye, Package,
  MessageSquare, ClipboardList, BarChart2, MapPin, Calendar,
  X, Check, RefreshCw, ArrowLeft, Plus, Info
} from 'lucide-react';

// ─── Status helpers ───────────────────────────────────────────────────────────

const STATUS_CONFIG: Record<string, { bg: string; color: string; border: string; label: string; icon?: React.ReactNode }> = {
  REVIEW_REQUIRED:      { bg: 'rgba(233,185,73,0.12)',  color: '#e8b94a', border: '#e8b94a', label: 'Review Required' },
  UNDER_REVIEW:         { bg: 'rgba(111,168,220,0.12)', color: '#6fa8dc', border: '#6fa8dc', label: 'Under Review' },
  EVIDENCE_VERIFIED:    { bg: 'rgba(127,182,133,0.12)', color: '#7fb685', border: '#7fb685', label: 'Evidence Verified' },
  ACTION_REQUIRED:      { bg: 'rgba(233,137,126,0.15)', color: '#e9897e', border: '#e9897e', label: 'Action Required' },
  INSPECTION_ASSIGNED:  { bg: 'rgba(180,130,230,0.12)', color: '#b482e6', border: '#b482e6', label: 'Inspection Assigned' },
  RESOLVED:             { bg: 'rgba(127,182,133,0.18)', color: '#5fad66', border: '#5fad66', label: 'Resolved' },
  CLOSED:               { bg: 'rgba(100,100,100,0.12)', color: '#888',    border: '#888',    label: 'Closed' },
  DISMISSED:            { bg: 'rgba(100,100,100,0.12)', color: '#aaa',    border: '#aaa',    label: 'Dismissed' },
  EVIDENCE_INSUFFICIENT:{ bg: 'rgba(233,137,126,0.08)', color: '#c97',    border: '#c97',    label: 'Evidence Insufficient' },
  DUPLICATE:            { bg: 'rgba(100,100,100,0.08)', color: '#777',    border: '#777',    label: 'Duplicate' },
};

const PRIORITY_CONFIG: Record<string, { color: string; bg: string; label: string }> = {
  HIGH:           { color: '#e9897e', bg: 'rgba(233,137,126,0.12)', label: 'High' },
  PRIORITY_REVIEW:{ color: '#e9897e', bg: 'rgba(233,137,126,0.12)', label: 'Priority Review' },
  MEDIUM:         { color: '#e8b94a', bg: 'rgba(233,185,73,0.10)',  label: 'Medium' },
  LOW:            { color: '#7fb685', bg: 'rgba(127,182,133,0.10)', label: 'Low' },
};

const TRIGGER_LABELS: Record<string, string> = {
  CROSS_EVIDENCE_CONFLICT: 'Cross-Evidence Conflict',
  POTENTIAL_NON_COMPLIANCE: 'Potential Non-Compliance',
  REPEATED_OBSERVATION: 'Repeated Observation',
  OFFICER_CREATED: 'Officer Initiated',
  CITIZEN_OBSERVATION: 'Citizen Observation',
  EVIDENCE_PATTERN: 'Evidence Pattern',
  PRIORITIZATION_SIGNAL: 'Prioritization Signal',
};

const EVIDENCE_STATE_CONFIG: Record<string, { color: string; label: string }> = {
  VERIFIED:           { color: '#7fb685', label: 'Verified' },
  SUPPORTED:          { color: '#6fa8dc', label: 'Supported' },
  MANUALLY_VERIFIED:  { color: '#5fad66', label: 'Manually Verified' },
  UNCERTAIN:          { color: '#e8b94a', label: 'Uncertain' },
  CONFLICTING:        { color: '#e9897e', label: 'Conflicting' },
  UNREADABLE:         { color: '#c97',    label: 'Unreadable' },
  NOT_DETECTED:       { color: '#888',    label: 'Not Detected' },
  NOT_APPLICABLE:     { color: '#777',    label: 'N/A' },
  ABSENT_FROM_EVIDENCE:{ color: '#888',  label: 'Absent' },
};

const VALID_FINDINGS = [
  'EVIDENCE_VERIFIED','ISSUE_NOT_CONFIRMED','MORE_EVIDENCE_REQUIRED',
  'INSPECTION_REQUIRED','DUPLICATE_CASE','RESOLVED'
];
const VALID_CLOSURE_OUTCOMES = [
  'EVIDENCE_INSUFFICIENT','ISSUE_NOT_CONFIRMED','DUPLICATE',
  'RESOLVED_AFTER_VERIFICATION','INSPECTION_COMPLETED'
];

// ─── Sub-components ───────────────────────────────────────────────────────────

const StatusBadge: React.FC<{ status: string; small?: boolean }> = ({ status, small }) => {
  const cfg = STATUS_CONFIG[status] || { bg: 'rgba(100,100,100,0.1)', color: '#888', border: '#888', label: status };
  return (
    <span style={{
      display: 'inline-block',
      padding: small ? '2px 8px' : '4px 12px',
      borderRadius: '20px',
      fontSize: small ? '0.68rem' : '0.75rem',
      fontWeight: 700,
      background: cfg.bg,
      color: cfg.color,
      border: `1px solid ${cfg.border}`,
      whiteSpace: 'nowrap',
    }}>
      {cfg.label}
    </span>
  );
};

const PriorityBadge: React.FC<{ priority: string }> = ({ priority }) => {
  const cfg = PRIORITY_CONFIG[priority] || { color: '#888', bg: 'rgba(100,100,100,0.1)', label: priority };
  return (
    <span style={{
      display: 'inline-block', padding: '3px 10px', borderRadius: '12px',
      fontSize: '0.72rem', fontWeight: 700, background: cfg.bg, color: cfg.color,
    }}>
      {cfg.label}
    </span>
  );
};

const Section: React.FC<{ title: string; icon?: React.ReactNode; children: React.ReactNode; collapsible?: boolean }> = ({
  title, icon, children, collapsible = false
}) => {
  const [open, setOpen] = useState(true);
  return (
    <div style={{
      background: 'var(--bg-card)', border: '1px solid var(--border-color)',
      borderRadius: '12px', marginBottom: '16px', overflow: 'hidden'
    }}>
      <div
        onClick={collapsible ? () => setOpen(o => !o) : undefined}
        style={{
          display: 'flex', alignItems: 'center', gap: '10px',
          padding: '14px 20px',
          borderBottom: open ? '1px solid var(--border-color)' : 'none',
          cursor: collapsible ? 'pointer' : 'default',
          background: 'rgba(255,255,255,0.02)',
        }}
      >
        {icon}
        <span style={{ fontWeight: 700, fontSize: '0.9rem', color: 'var(--text-primary)', flex: 1 }}>{title}</span>
        {collapsible && (open ? <ChevronDown size={16} color="var(--text-muted)" /> : <ChevronRight size={16} color="var(--text-muted)" />)}
      </div>
      {open && <div style={{ padding: '16px 20px' }}>{children}</div>}
    </div>
  );
};

const InfoGrid: React.FC<{ items: Array<{ label: string; value: React.ReactNode; wide?: boolean }> }> = ({ items }) => (
  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px' }}>
    {items.map((item, i) => item.value ? (
      <div key={i} style={{
        padding: '10px 14px', background: 'rgba(255,255,255,0.02)',
        borderRadius: '8px', border: '1px solid var(--border-color)',
        gridColumn: item.wide ? 'span 3' : undefined
      }}>
        <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 700, textTransform: 'uppercase', marginBottom: '4px' }}>{item.label}</div>
        <div style={{ fontSize: '0.88rem', color: 'var(--text-primary)', fontWeight: 600 }}>{item.value}</div>
      </div>
    ) : null)}
  </div>
);

// ─── Modal ────────────────────────────────────────────────────────────────────

const Modal: React.FC<{
  title: string; onClose: () => void; children: React.ReactNode; danger?: boolean
}> = ({ title, onClose, children, danger }) => (
  <div style={{
    position: 'fixed', inset: 0, zIndex: 200,
    background: 'rgba(0,0,0,0.65)', display: 'flex', alignItems: 'center', justifyContent: 'center'
  }}>
    <div style={{
      background: 'var(--bg-card)', borderRadius: '14px', width: '520px', maxWidth: '95vw',
      border: `1px solid ${danger ? 'rgba(233,137,126,0.4)' : 'var(--border-color)'}`,
      boxShadow: '0 24px 60px rgba(0,0,0,0.5)',
      maxHeight: '90vh', overflowY: 'auto',
    }}>
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '18px 22px', borderBottom: '1px solid var(--border-color)'
      }}>
        <h3 style={{ fontSize: '1rem', fontWeight: 800, color: danger ? 'var(--accent-potential)' : 'var(--text-primary)', margin: 0 }}>{title}</h3>
        <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)' }}>
          <X size={18} />
        </button>
      </div>
      <div style={{ padding: '22px' }}>{children}</div>
    </div>
  </div>
);

// ─── Case Detail View ─────────────────────────────────────────────────────────

const CaseDetailView: React.FC<{ caseId: string; onBack: () => void }> = ({ caseId, onBack }) => {
  const [detail, setDetail] = useState<CaseDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeModal, setActiveModal] = useState<string | null>(null);

  // Form state
  const [noteText, setNoteText] = useState('');
  const [finding, setFinding] = useState(VALID_FINDINGS[0]);
  const [findingNotes, setFindingNotes] = useState('');
  const [closureOutcome, setClosureOutcome] = useState(VALID_CLOSURE_OUTCOMES[0]);
  const [closureReason, setClosureReason] = useState('');
  const [reopenReason, setReopenReason] = useState('');
  const [inspectionLocation, setInspectionLocation] = useState('');
  const [inspectionNotes, setInspectionNotes] = useState('');
  const [actionLoading, setActionLoading] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getCaseDetail(caseId);
      setDetail(data);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [caseId]);

  useEffect(() => { load(); }, [load]);

  const handleAction = async (action: () => Promise<any>) => {
    setActionLoading(true);
    setActionError(null);
    try {
      await action();
      setActiveModal(null);
      await load();
    } catch (e: any) {
      setActionError(e.message);
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) return (
    <div style={{ textAlign: 'center', padding: '80px', color: 'var(--text-secondary)' }}>
      <Activity size={32} style={{ marginBottom: '16px', opacity: 0.4 }} />
      <p>Loading case data...</p>
    </div>
  );
  if (error) return (
    <div style={{ textAlign: 'center', padding: '60px', color: 'var(--accent-potential)' }}>
      <AlertTriangle size={32} style={{ marginBottom: '12px' }} />
      <p>{error}</p>
      <button onClick={load} className="btn-secondary" style={{ marginTop: '12px' }}>Retry</button>
    </div>
  );
  if (!detail) return null;

  const isActive = !['CLOSED', 'DUPLICATE', 'DISMISSED', 'RESOLVED'].includes(detail.status);
  const canInspect = ['ACTION_REQUIRED', 'UNDER_REVIEW', 'EVIDENCE_VERIFIED'].includes(detail.status);
  const canClose   = !['CLOSED', 'DUPLICATE'].includes(detail.status);
  const canReopen  = ['RESOLVED', 'CLOSED', 'DISMISSED', 'EVIDENCE_INSUFFICIENT'].includes(detail.status);

  return (
    <div style={{ maxWidth: '1100px', margin: '0 auto', padding: '24px' }}>

      {/* BACK BUTTON */}
      <button onClick={onBack} className="btn-secondary"
        style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '20px', fontSize: '0.85rem' }}>
        <ArrowLeft size={14} /> Back to Cases
      </button>

      {/* ── CASE HEADER ── */}
      <div className="glass-panel" style={{ padding: '22px 28px', marginBottom: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '16px', flexWrap: 'wrap' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' }}>
              <Shield size={22} color="var(--color-primary)" />
              <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)', fontWeight: 700, letterSpacing: '0.05em' }}>
                {detail.case_number}
              </span>
              <StatusBadge status={detail.status} />
              <PriorityBadge priority={detail.priority} />
            </div>
            <h1 style={{ fontSize: '1.4rem', fontWeight: 800, color: 'var(--text-primary)', margin: '0 0 4px' }}>
              {detail.product.name}
            </h1>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', margin: 0 }}>
              {TRIGGER_LABELS[detail.trigger_type] || detail.trigger_type} &nbsp;·&nbsp;
              {detail.assigned_officer ? `Officer: ${detail.assigned_officer.name}` : 'Unassigned'}
              &nbsp;·&nbsp; Created {new Date(detail.created_at).toLocaleDateString('en-IN')}
            </p>
          </div>
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            {isActive && (
              <>
                <button onClick={() => setActiveModal('note')} className="btn-secondary" style={{ fontSize: '0.8rem', padding: '8px 14px' }}>
                  <MessageSquare size={13} style={{ marginRight: '5px' }} /> Add Note
                </button>
                <button onClick={() => setActiveModal('finding')} className="btn-secondary" style={{ fontSize: '0.8rem', padding: '8px 14px' }}>
                  <ClipboardList size={13} style={{ marginRight: '5px' }} /> Record Finding
                </button>
                {canInspect && (
                  <button onClick={() => setActiveModal('inspection')} className="btn-secondary" style={{ fontSize: '0.8rem', padding: '8px 14px' }}>
                    <MapPin size={13} style={{ marginRight: '5px' }} /> Assign Inspection
                  </button>
                )}
              </>
            )}
            {canClose && (
              <button onClick={() => setActiveModal('close')} className="btn-secondary"
                style={{ fontSize: '0.8rem', padding: '8px 14px', borderColor: 'rgba(233,137,126,0.4)', color: 'var(--accent-potential)' }}>
                Close Case
              </button>
            )}
            {canReopen && (
              <button onClick={() => setActiveModal('reopen')} className="btn-secondary" style={{ fontSize: '0.8rem', padding: '8px 14px' }}>
                <RefreshCw size={13} style={{ marginRight: '5px' }} /> Reopen
              </button>
            )}
          </div>
        </div>
      </div>

      {/* ── PRODUCT IDENTITY ── */}
      <Section title="Product Identity" icon={<Package size={16} color="var(--color-primary)" />}>
        <InfoGrid items={[
          { label: 'Product Name',  value: detail.product.name },
          { label: 'Brand',         value: detail.product.brand },
          { label: 'GTIN / Barcode',value: detail.product.gtin },
          { label: 'Category',      value: detail.product.category },
          { label: 'Net Quantity',  value: detail.product.net_quantity },
        ]} />
      </Section>

      {/* ── WHY THIS CASE EXISTS ── */}
      <Section title="Why This Case Exists" icon={<Info size={16} color="var(--accent-review)" />}>
        <div style={{
          background: 'rgba(233,185,73,0.06)', border: '1px solid rgba(233,185,73,0.2)',
          borderRadius: '8px', padding: '16px', marginBottom: '12px'
        }}>
          <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', fontWeight: 700, marginBottom: '6px' }}>TRIGGER</div>
          <div style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--accent-review)', marginBottom: '6px' }}>
            {TRIGGER_LABELS[detail.trigger_type] || detail.trigger_type}
          </div>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.88rem', margin: 0 }}>
            {detail.trigger_description}
          </p>
        </div>
        <div style={{
          background: 'rgba(100,130,180,0.05)', border: '1px solid var(--border-color)',
          borderRadius: '8px', padding: '14px', fontSize: '0.83rem', color: 'var(--text-secondary)'
        }}>
          <strong style={{ color: 'var(--text-primary)' }}>Important:</strong>{' '}
          LM-Screen does not independently make legal determinations. This case was opened because
          the screening pipeline identified signals that require officer verification. The officer
          must review the evidence and determine the appropriate action through departmental procedures.
        </div>
        {detail.reason && (
          <p style={{ marginTop: '12px', color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
            <strong>Creation reason:</strong> {detail.reason}
          </p>
        )}
      </Section>

      {/* ── EVIDENCE CHAIN ── */}
      <Section title={`Evidence (${detail.evidence.length} items)`} icon={<Eye size={16} color="var(--color-primary)" />} collapsible>
        {detail.evidence.length === 0 ? (
          <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>No evidence items linked to this case yet.</p>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {detail.evidence.map(ev => {
              const stCfg = EVIDENCE_STATE_CONFIG[ev.evidence_state || ''] || { color: '#888', label: ev.evidence_state || 'Unknown' };
              return (
                <div key={ev.evidence_id} style={{
                  background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border-color)',
                  borderRadius: '8px', padding: '14px', display: 'grid',
                  gridTemplateColumns: '1fr 1fr 1fr 120px', gap: '12px', alignItems: 'start'
                }}>
                  <div>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 700, marginBottom: '4px' }}>FIELD</div>
                    <div style={{ fontWeight: 700, fontSize: '0.9rem', color: 'var(--text-primary)' }}>{ev.field_name}</div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '2px' }}>via {ev.extraction_method}</div>
                  </div>
                  <div>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 700, marginBottom: '4px' }}>RAW → NORMALIZED</div>
                    <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', wordBreak: 'break-word' }}>{formatFieldValue(ev.raw_value)}</div>
                    <div style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-primary)', wordBreak: 'break-word' }}>{formatFieldValue(ev.normalized_value)}</div>
                  </div>
                  <div>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 700, marginBottom: '4px' }}>SOURCE</div>
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>{ev.source_type || 'OCR'}</div>
                    {ev.confidence !== undefined && (
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                        Confidence: {Math.round((ev.confidence || 0) * 100)}%
                      </div>
                    )}
                    {ev.corrections.length > 0 && (
                      <div style={{ fontSize: '0.72rem', color: '#7fb685', marginTop: '4px' }}>
                        ✓ {ev.corrections.length} officer correction(s)
                      </div>
                    )}
                  </div>
                  <div>
                    <span style={{
                      display: 'inline-block', padding: '3px 8px', borderRadius: '10px',
                      fontSize: '0.68rem', fontWeight: 700,
                      background: `${stCfg.color}18`, color: stCfg.color,
                      border: `1px solid ${stCfg.color}40`
                    }}>
                      {stCfg.label}
                    </span>
                    {ev.quality_reasons.length > 0 && (
                      <div style={{ marginTop: '6px' }}>
                        {ev.quality_reasons.slice(0, 2).map((r, i) => (
                          <div key={i} style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>• {r}</div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </Section>

      {/* ── APPLICABLE REQUIREMENTS ── */}
      <Section title={`Applicable Requirements (${detail.rule_results.length})`} icon={<FileText size={16} color="var(--color-primary)" />} collapsible>
        {detail.rule_results.length === 0 ? (
          <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>No rule results linked to this case.</p>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {detail.rule_results.map((r, i) => {
              const isIssue = ['POTENTIAL_NON_COMPLIANCE','NEEDS_REVIEW'].includes(r.status);
              return (
                <div key={i} style={{
                  display: 'flex', gap: '14px', alignItems: 'flex-start',
                  padding: '12px 14px', borderRadius: '8px',
                  background: isIssue ? 'rgba(233,137,126,0.06)' : 'rgba(127,182,133,0.06)',
                  border: `1px solid ${isIssue ? 'rgba(233,137,126,0.2)' : 'rgba(127,182,133,0.2)'}`,
                }}>
                  <div style={{ paddingTop: '2px' }}>
                    {isIssue
                      ? <AlertTriangle size={14} color="var(--accent-potential)" />
                      : <CheckCircle2 size={14} color="var(--accent-pass)" />}
                  </div>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 700, fontSize: '0.88rem', color: 'var(--text-primary)', marginBottom: '2px' }}>
                      {r.rule_name}
                    </div>
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>{r.reason}</div>
                    <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                      Applicability: {r.applicability} · Status: {r.status}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </Section>

      {/* ── CONSISTENCY CHECKS ── */}
      <Section title={`Consistency Checks (${detail.consistency_checks.length})`} icon={<BarChart2 size={16} color="var(--accent-review)" />} collapsible>
        {detail.consistency_checks.length === 0 ? (
          <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>No consistency checks for this case.</p>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {detail.consistency_checks.map((c, i) => {
              const isConflict = c.status === 'REVIEW_REQUIRED';
              return (
                <div key={i} style={{
                  padding: '12px 14px', borderRadius: '8px',
                  background: isConflict ? 'rgba(233,137,126,0.07)' : 'rgba(127,182,133,0.05)',
                  border: `1px solid ${isConflict ? 'rgba(233,137,126,0.25)' : 'rgba(127,182,133,0.2)'}`,
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                    <span style={{ fontWeight: 700, fontSize: '0.88rem', color: 'var(--text-primary)' }}>{c.check_type}</span>
                    <StatusBadge status={c.status} small />
                  </div>
                  <p style={{ color: 'var(--text-secondary)', fontSize: '0.83rem', margin: '0 0 6px' }}>{c.explanation}</p>
                  {c.observed_values && Object.keys(c.observed_values).length > 0 && (
                    <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                      {Object.entries(c.observed_values).map(([k, v]) => (
                        <span key={k} style={{
                          fontSize: '0.72rem', padding: '2px 8px', borderRadius: '8px',
                          background: 'rgba(255,255,255,0.05)', border: '1px solid var(--border-color)',
                          color: 'var(--text-secondary)'
                        }}>
                          {k}: <strong>{String(v)}</strong>
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </Section>

      {/* ── RELATED OBSERVATIONS ── */}
      {detail.cluster && (
        <Section title="Related Product Observations" icon={<Activity size={16} color="var(--color-primary)" />} collapsible>
          <InfoGrid items={[
            { label: 'Observation Count', value: String(detail.cluster.observation_count) },
            { label: 'AI Flags',          value: String(detail.cluster.ai_flag_count) },
            { label: 'Related Scans',     value: String(detail.cluster.related_scan_count) },
            { label: 'Match Method',      value: detail.cluster.match_method },
            { label: 'Match Strength',    value: detail.cluster.match_strength },
            { label: 'Evidence Strength', value: detail.cluster.evidence_strength },
          ]} />
          {detail.cluster.priority_reasons && detail.cluster.priority_reasons.length > 0 && (
            <div style={{ marginTop: '12px' }}>
              <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', fontWeight: 700, marginBottom: '8px' }}>PRIORITIZATION SIGNALS</div>
              {detail.cluster.priority_reasons.map((r, i) => (
                <div key={i} style={{
                  display: 'flex', gap: '8px', marginBottom: '6px',
                  padding: '8px 12px', borderRadius: '6px',
                  background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border-color)'
                }}>
                  <Check size={13} color="var(--accent-pass)" style={{ marginTop: '2px', flexShrink: 0 }} />
                  <div>
                    <div style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-primary)' }}>{r.code}</div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>{r.description}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
          <div style={{
            marginTop: '12px', padding: '10px 14px', borderRadius: '6px',
            background: 'rgba(100,130,180,0.06)', border: '1px solid var(--border-color)',
            fontSize: '0.8rem', color: 'var(--text-muted)', fontStyle: 'italic'
          }}>
            Note: &ldquo;Same product&rdquo; is not the same as &ldquo;same case&rdquo;. Multiple observations may belong to the same product cluster but represent independent review instances.
          </div>
        </Section>
      )}

      {/* ── OFFICER NOTES ── */}
      <Section title={`Officer Notes (${detail.notes.length})`} icon={<MessageSquare size={16} color="var(--color-primary)" />}>
        {detail.notes.length === 0 && (
          <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginBottom: '12px' }}>No notes yet.</p>
        )}
        {detail.notes.map(n => (
          <div key={n.note_id} style={{
            padding: '14px 16px', borderRadius: '8px', marginBottom: '10px',
            background: 'rgba(111,168,220,0.06)', border: '1px solid rgba(111,168,220,0.2)'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
              <span style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--color-primary)' }}>{n.author}</span>
              <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                {new Date(n.created_at).toLocaleString('en-IN')}
              </span>
            </div>
            <p style={{ fontSize: '0.88rem', color: 'var(--text-primary)', margin: 0, lineHeight: 1.6 }}>&ldquo;{n.note}&rdquo;</p>
          </div>
        ))}
        {isActive && (
          <button onClick={() => setActiveModal('note')} className="btn-secondary" style={{ fontSize: '0.8rem' }}>
            <Plus size={13} style={{ marginRight: '5px' }} /> Add Note
          </button>
        )}
      </Section>

      {/* ── INSPECTIONS ── */}
      {detail.inspections.length > 0 && (
        <Section title={`Inspections (${detail.inspections.length})`} icon={<MapPin size={16} color="var(--accent-review)" />}>
          {detail.inspections.map(ins => (
            <div key={ins.inspection_id} style={{
              padding: '14px 16px', borderRadius: '8px', marginBottom: '10px',
              background: 'rgba(180,130,230,0.06)', border: '1px solid rgba(180,130,230,0.2)'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px', flexWrap: 'wrap', gap: '8px' }}>
                <div>
                  <StatusBadge status={ins.status} small />
                  {ins.assigned_to && <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginLeft: '10px' }}>Assigned to: {ins.assigned_to}</span>}
                </div>
                {ins.scheduled_at && (
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    <Calendar size={11} style={{ marginRight: '4px' }} />
                    Scheduled: {new Date(ins.scheduled_at).toLocaleDateString('en-IN')}
                  </span>
                )}
              </div>
              {ins.location_hint && (
                <p style={{ fontSize: '0.83rem', color: 'var(--text-secondary)', margin: '0 0 4px' }}>
                  <MapPin size={11} style={{ marginRight: '4px' }} /> {ins.location_hint}
                </p>
              )}
              {ins.notes && <p style={{ fontSize: '0.83rem', color: 'var(--text-secondary)', margin: '6px 0 0' }}>{ins.notes}</p>}
              <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '6px' }}>
                ⓘ Inspection assignment recorded in LM-Screen. Ready for integration with departmental workflow.
              </p>
            </div>
          ))}
        </Section>
      )}

      {/* ── CASE ACTIONS ── */}
      <Section title="Case Actions" icon={<Shield size={16} color="var(--color-primary)" />}>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px' }}>
          {isActive && <>
            <button onClick={() => setActiveModal('note')} className="btn-secondary">
              <MessageSquare size={13} /> Add Note
            </button>
            <button onClick={() => setActiveModal('finding')} className="btn-secondary">
              <ClipboardList size={13} /> Record Finding
            </button>
            {canInspect && (
              <button onClick={() => setActiveModal('inspection')} className="btn-secondary">
                <MapPin size={13} /> Assign Inspection
              </button>
            )}
          </>}
          {canClose && (
            <button onClick={() => setActiveModal('close')} className="btn-secondary"
              style={{ borderColor: 'rgba(233,137,126,0.4)', color: 'var(--accent-potential)' }}>
              Close Case
            </button>
          )}
          {canReopen && (
            <button onClick={() => setActiveModal('reopen')} className="btn-secondary">
              <RefreshCw size={13} /> Reopen Case
            </button>
          )}
        </div>

        {detail.finding && (
          <div style={{
            marginTop: '16px', padding: '14px 16px', borderRadius: '8px',
            background: 'rgba(127,182,133,0.06)', border: '1px solid rgba(127,182,133,0.2)'
          }}>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 700, marginBottom: '4px' }}>OFFICER FINDING</div>
            <div style={{ fontWeight: 700, color: 'var(--text-primary)' }}>{detail.finding}</div>
            {detail.finding_notes && <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', margin: '6px 0 0' }}>{detail.finding_notes}</p>}
            {detail.finding_recorded_at && (
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                Recorded: {new Date(detail.finding_recorded_at).toLocaleString('en-IN')}
              </div>
            )}
          </div>
        )}

        {detail.closure_outcome && (
          <div style={{
            marginTop: '12px', padding: '14px 16px', borderRadius: '8px',
            background: 'rgba(100,100,100,0.06)', border: '1px solid var(--border-color)'
          }}>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 700, marginBottom: '4px' }}>CLOSURE</div>
            <div style={{ fontWeight: 700, color: 'var(--text-primary)' }}>{detail.closure_outcome}</div>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', margin: '4px 0 0' }}>{detail.closure_reason}</p>
          </div>
        )}
      </Section>

      {/* ── AUDIT TRAIL ── */}
      <Section title={`Audit Trail (${detail.audit_trail.length} events)`} icon={<Clock size={16} color="var(--text-muted)" />} collapsible>
        {detail.audit_trail.length === 0 ? (
          <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>No audit events yet.</p>
        ) : (
          <div style={{ position: 'relative', paddingLeft: '24px' }}>
            <div style={{
              position: 'absolute', left: '8px', top: '8px', bottom: '8px',
              width: '2px', background: 'var(--border-color)', borderRadius: '1px'
            }} />
            {detail.audit_trail.map((ev) => (
              <div key={ev.event_id} style={{
                position: 'relative', paddingBottom: '16px', marginBottom: '0'
              }}>
                <div style={{
                  position: 'absolute', left: '-20px', top: '4px', width: '10px', height: '10px',
                  borderRadius: '50%', background: 'var(--color-primary)', border: '2px solid var(--bg-card)'
                }} />
                <div style={{
                  padding: '10px 14px', borderRadius: '8px',
                  background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border-color)',
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '8px' }}>
                    <div>
                      <span style={{ fontWeight: 700, fontSize: '0.82rem', color: 'var(--text-primary)' }}>{ev.action}</span>
                      <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginLeft: '8px' }}>by {ev.actor}</span>
                    </div>
                    <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
                      {new Date(ev.timestamp).toLocaleString('en-IN')}
                    </span>
                  </div>
                  {ev.old_status && ev.new_status && (
                    <div style={{ marginTop: '4px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <StatusBadge status={ev.old_status} small />
                      <ChevronRight size={12} color="var(--text-muted)" />
                      <StatusBadge status={ev.new_status} small />
                    </div>
                  )}
                  {ev.reason && <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', margin: '4px 0 0' }}>{ev.reason}</p>}
                </div>
              </div>
            ))}
          </div>
        )}
      </Section>

      {/* ── DISCLAIMER ── */}
      <div style={{
        padding: '12px 16px', borderRadius: '8px', marginTop: '4px',
        background: 'rgba(100,100,100,0.04)', border: '1px solid var(--border-color)',
        fontSize: '0.78rem', color: 'var(--text-muted)', fontStyle: 'italic', lineHeight: 1.6
      }}>
        ⓘ {detail.disclaimer}
      </div>

      {/* ━━━ MODALS ━━━ */}

      {activeModal === 'note' && (
        <Modal title="Add Officer Note" onClose={() => setActiveModal(null)}>
          <p style={{ fontSize: '0.83rem', color: 'var(--text-secondary)', marginBottom: '14px' }}>
            Notes are visible to all authorized officers. Citizens cannot access officer notes.
          </p>
          <textarea
            value={noteText}
            onChange={e => setNoteText(e.target.value)}
            rows={5}
            placeholder="Record your observation, finding, or action taken..."
            style={{
              width: '100%', padding: '10px', borderRadius: '6px',
              border: '1px solid var(--border-color)', background: 'var(--bg-main)',
              color: 'var(--text-primary)', fontSize: '0.88rem', resize: 'vertical', boxSizing: 'border-box'
            }}
          />
          {actionError && <p style={{ color: 'var(--accent-potential)', fontSize: '0.83rem', marginTop: '8px' }}>{actionError}</p>}
          <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end', marginTop: '14px' }}>
            <button onClick={() => setActiveModal(null)} className="btn-secondary">Cancel</button>
            <button disabled={actionLoading || !noteText.trim()} className="btn-primary"
              onClick={() => handleAction(() => addCaseNote(caseId, noteText))}>
              {actionLoading ? 'Saving...' : 'Save Note'}
            </button>
          </div>
        </Modal>
      )}

      {activeModal === 'finding' && (
        <Modal title="Record Officer Finding" onClose={() => setActiveModal(null)}>
          <p style={{ fontSize: '0.83rem', color: 'var(--text-secondary)', marginBottom: '14px' }}>
            Select the finding that best reflects your verification of the evidence.
          </p>
          <div style={{ marginBottom: '14px' }}>
            <label style={{ fontSize: '0.78rem', color: 'var(--text-muted)', fontWeight: 700, display: 'block', marginBottom: '6px' }}>FINDING</label>
            <select value={finding} onChange={e => setFinding(e.target.value)} style={{
              width: '100%', padding: '10px', borderRadius: '6px',
              border: '1px solid var(--border-color)', background: 'var(--bg-main)', color: 'var(--text-primary)'
            }}>
              {VALID_FINDINGS.map(f => <option key={f} value={f}>{f}</option>)}
            </select>
          </div>
          <div>
            <label style={{ fontSize: '0.78rem', color: 'var(--text-muted)', fontWeight: 700, display: 'block', marginBottom: '6px' }}>NOTES</label>
            <textarea value={findingNotes} onChange={e => setFindingNotes(e.target.value)} rows={4}
              placeholder="Describe what you observed..."
              style={{
                width: '100%', padding: '10px', borderRadius: '6px',
                border: '1px solid var(--border-color)', background: 'var(--bg-main)',
                color: 'var(--text-primary)', fontSize: '0.88rem', resize: 'vertical', boxSizing: 'border-box'
              }}
            />
          </div>
          {actionError && <p style={{ color: 'var(--accent-potential)', fontSize: '0.83rem', marginTop: '8px' }}>{actionError}</p>}
          <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end', marginTop: '14px' }}>
            <button onClick={() => setActiveModal(null)} className="btn-secondary">Cancel</button>
            <button disabled={actionLoading} className="btn-primary"
              onClick={() => handleAction(() => recordCaseFinding(caseId, finding, findingNotes))}>
              {actionLoading ? 'Saving...' : 'Record Finding'}
            </button>
          </div>
        </Modal>
      )}

      {activeModal === 'inspection' && (
        <Modal title="Assign Field Inspection" onClose={() => setActiveModal(null)}>
          <div style={{
            padding: '10px 14px', borderRadius: '6px', marginBottom: '16px',
            background: 'rgba(180,130,230,0.06)', border: '1px solid rgba(180,130,230,0.2)',
            fontSize: '0.82rem', color: 'var(--text-secondary)'
          }}>
            ⓘ This records the inspection assignment within LM-Screen. The actual field inspection
            follows departmental procedures. Ready for future integration with departmental workflow.
          </div>
          <div style={{ marginBottom: '12px' }}>
            <label style={{ fontSize: '0.78rem', color: 'var(--text-muted)', fontWeight: 700, display: 'block', marginBottom: '6px' }}>LOCATION HINT</label>
            <input value={inspectionLocation} onChange={e => setInspectionLocation(e.target.value)}
              placeholder="Market / area / retailer location..."
              style={{
                width: '100%', padding: '10px', borderRadius: '6px',
                border: '1px solid var(--border-color)', background: 'var(--bg-main)',
                color: 'var(--text-primary)', boxSizing: 'border-box'
              }}
            />
          </div>
          <div>
            <label style={{ fontSize: '0.78rem', color: 'var(--text-muted)', fontWeight: 700, display: 'block', marginBottom: '6px' }}>INSPECTION NOTES</label>
            <textarea value={inspectionNotes} onChange={e => setInspectionNotes(e.target.value)} rows={3}
              placeholder="Instructions or context for the inspection..."
              style={{
                width: '100%', padding: '10px', borderRadius: '6px',
                border: '1px solid var(--border-color)', background: 'var(--bg-main)',
                color: 'var(--text-primary)', fontSize: '0.88rem', resize: 'vertical', boxSizing: 'border-box'
              }}
            />
          </div>
          {actionError && <p style={{ color: 'var(--accent-potential)', fontSize: '0.83rem', marginTop: '8px' }}>{actionError}</p>}
          <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end', marginTop: '14px' }}>
            <button onClick={() => setActiveModal(null)} className="btn-secondary">Cancel</button>
            <button disabled={actionLoading} className="btn-primary"
              onClick={() => handleAction(() => createCaseInspection(caseId, {
                location_hint: inspectionLocation, notes: inspectionNotes
              }))}>
              {actionLoading ? 'Assigning...' : 'Assign Inspection'}
            </button>
          </div>
        </Modal>
      )}

      {activeModal === 'close' && (
        <Modal title="Close Case" onClose={() => setActiveModal(null)} danger>
          <p style={{ fontSize: '0.83rem', color: 'var(--text-secondary)', marginBottom: '14px' }}>
            Closing a case requires a structured outcome and reason. This action is audited.
            The case can be reopened if new evidence emerges.
          </p>
          <div style={{ marginBottom: '12px' }}>
            <label style={{ fontSize: '0.78rem', color: 'var(--text-muted)', fontWeight: 700, display: 'block', marginBottom: '6px' }}>CLOSURE OUTCOME *</label>
            <select value={closureOutcome} onChange={e => setClosureOutcome(e.target.value)} style={{
              width: '100%', padding: '10px', borderRadius: '6px',
              border: '1px solid var(--border-color)', background: 'var(--bg-main)', color: 'var(--text-primary)'
            }}>
              {VALID_CLOSURE_OUTCOMES.map(o => <option key={o} value={o}>{o.replace(/_/g,' ')}</option>)}
            </select>
          </div>
          <div>
            <label style={{ fontSize: '0.78rem', color: 'var(--text-muted)', fontWeight: 700, display: 'block', marginBottom: '6px' }}>REASON *</label>
            <textarea value={closureReason} onChange={e => setClosureReason(e.target.value)} rows={4} required
              placeholder="Explain the reason for closing this case..."
              style={{
                width: '100%', padding: '10px', borderRadius: '6px',
                border: '1px solid var(--border-color)', background: 'var(--bg-main)',
                color: 'var(--text-primary)', resize: 'vertical', boxSizing: 'border-box'
              }}
            />
          </div>
          {actionError && <p style={{ color: 'var(--accent-potential)', fontSize: '0.83rem', marginTop: '8px' }}>{actionError}</p>}
          <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end', marginTop: '14px' }}>
            <button onClick={() => setActiveModal(null)} className="btn-secondary">Cancel</button>
            <button disabled={actionLoading || !closureReason.trim()}
              style={{ background: 'var(--accent-potential)', color: '#fff', border: 'none', padding: '10px 18px', borderRadius: '8px', fontWeight: 700, cursor: 'pointer' }}
              onClick={() => handleAction(() => closeCase(caseId, closureOutcome, closureReason))}>
              {actionLoading ? 'Closing...' : 'Close Case'}
            </button>
          </div>
        </Modal>
      )}

      {activeModal === 'reopen' && (
        <Modal title="Reopen Case" onClose={() => setActiveModal(null)}>
          <p style={{ fontSize: '0.83rem', color: 'var(--text-secondary)', marginBottom: '14px' }}>
            The original closure events will be preserved in the audit trail.
          </p>
          <textarea value={reopenReason} onChange={e => setReopenReason(e.target.value)} rows={3} required
            placeholder="Why is this case being reopened?"
            style={{
              width: '100%', padding: '10px', borderRadius: '6px',
              border: '1px solid var(--border-color)', background: 'var(--bg-main)',
              color: 'var(--text-primary)', fontSize: '0.88rem', resize: 'vertical', boxSizing: 'border-box'
            }}
          />
          {actionError && <p style={{ color: 'var(--accent-potential)', fontSize: '0.83rem', marginTop: '8px' }}>{actionError}</p>}
          <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end', marginTop: '14px' }}>
            <button onClick={() => setActiveModal(null)} className="btn-secondary">Cancel</button>
            <button disabled={actionLoading || !reopenReason.trim()} className="btn-primary"
              onClick={() => handleAction(() => reopenCase(caseId, reopenReason))}>
              {actionLoading ? 'Reopening...' : 'Reopen Case'}
            </button>
          </div>
        </Modal>
      )}
    </div>
  );
};

// ─── Case Creation Dialog ────────────────────────────────────────────────────

const CreateCaseDialog: React.FC<{
  queueItem?: PriorityQueueItem;
  onClose: () => void;
  onCreated: (caseId: string) => void;
}> = ({ queueItem, onClose, onCreated }) => {
  const [triggerType, setTriggerType] = useState(
    queueItem?.priority_class === 'PRIORITY_REVIEW' ? 'CROSS_EVIDENCE_CONFLICT' : 'OFFICER_CREATED'
  );
  const [reason, setReason] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleCreate = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await createCase({
        trigger_type: triggerType,
        cluster_id: queueItem?.cluster_id,
        product_id: queueItem?.product_id,
        reason: reason || `Case initiated from Officer Workbench for ${queueItem?.product_name || 'product'}.`,
      });
      onCreated(result.case_id);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal title="Create Investigation Case" onClose={onClose}>
      {queueItem && (
        <div style={{
          padding: '12px 14px', borderRadius: '8px', marginBottom: '16px',
          background: 'rgba(111,168,220,0.08)', border: '1px solid rgba(111,168,220,0.2)'
        }}>
          <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 700, marginBottom: '4px' }}>PRODUCT</div>
          <div style={{ fontWeight: 700, color: 'var(--text-primary)' }}>{queueItem.product_name}</div>
          {queueItem.gtin && <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>GTIN: {queueItem.gtin}</div>}
          <div style={{ marginTop: '6px', display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            <PriorityBadge priority={queueItem.priority_class} />
            <StatusBadge status={queueItem.status} small />
          </div>
        </div>
      )}

      <div style={{ marginBottom: '14px' }}>
        <label style={{ fontSize: '0.78rem', color: 'var(--text-muted)', fontWeight: 700, display: 'block', marginBottom: '6px' }}>
          TRIGGER TYPE *
        </label>
        <select value={triggerType} onChange={e => setTriggerType(e.target.value)} style={{
          width: '100%', padding: '10px', borderRadius: '6px',
          border: '1px solid var(--border-color)', background: 'var(--bg-main)', color: 'var(--text-primary)'
        }}>
          <option value="OFFICER_CREATED">Officer Initiated</option>
          <option value="CROSS_EVIDENCE_CONFLICT">Cross-Evidence Conflict</option>
          <option value="POTENTIAL_NON_COMPLIANCE">Potential Non-Compliance</option>
          <option value="REPEATED_OBSERVATION">Repeated Observation</option>
          <option value="CITIZEN_OBSERVATION">Citizen Observation</option>
          <option value="PRIORITIZATION_SIGNAL">Prioritization Signal</option>
        </select>
      </div>

      <div>
        <label style={{ fontSize: '0.78rem', color: 'var(--text-muted)', fontWeight: 700, display: 'block', marginBottom: '6px' }}>
          CREATION REASON
        </label>
        <textarea value={reason} onChange={e => setReason(e.target.value)} rows={3}
          placeholder="Describe why this case is being opened..."
          style={{
            width: '100%', padding: '10px', borderRadius: '6px',
            border: '1px solid var(--border-color)', background: 'var(--bg-main)',
            color: 'var(--text-primary)', fontSize: '0.88rem', resize: 'vertical', boxSizing: 'border-box'
          }}
        />
      </div>

      <div style={{
        marginTop: '12px', padding: '10px 14px', borderRadius: '6px',
        background: 'rgba(100,100,100,0.04)', border: '1px solid var(--border-color)',
        fontSize: '0.78rem', color: 'var(--text-muted)', lineHeight: 1.5
      }}>
        ⓘ LM-Screen will verify that the trigger is supported by actual screening evidence before creating the case.
        Raw OCR extraction alone is insufficient — a conflict, rule issue, or repeated observation is required.
      </div>

      {error && (
        <div style={{
          marginTop: '10px', padding: '10px 14px', borderRadius: '6px',
          background: 'rgba(233,137,126,0.1)', border: '1px solid rgba(233,137,126,0.3)',
          fontSize: '0.83rem', color: 'var(--accent-potential)'
        }}>
          {error}
        </div>
      )}

      <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end', marginTop: '16px' }}>
        <button onClick={onClose} className="btn-secondary">Cancel</button>
        <button disabled={loading} className="btn-primary" onClick={handleCreate}>
          {loading ? 'Creating...' : 'Create Case'}
        </button>
      </div>
    </Modal>
  );
};

// ─── Case List ────────────────────────────────────────────────────────────────

interface CaseManagementProps {
  userRole?: string;
  initialClusterId?: string;
}

export const CaseManagement: React.FC<CaseManagementProps> = () => {
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [statusCounts, setStatusCounts] = useState<Record<string, number>>({});
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const PAGE_SIZE = 20;

  // Navigation
  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(null);
  const [showCreateDialog, setShowCreateDialog] = useState(false);

  const [selectedQueueItem, setSelectedQueueItem] = useState<PriorityQueueItem | undefined>(undefined);

  const loadCases = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await listCases({
        status: statusFilter === 'ALL' ? undefined : statusFilter,
        search: search || undefined,
        page,
        page_size: PAGE_SIZE,
      });
      setCases(res.cases);
      setStatusCounts(res.status_counts || {});
      setTotal(res.total);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [statusFilter, search, page]);

  useEffect(() => { loadCases(); }, [loadCases]);



  if (selectedCaseId) {
    return <CaseDetailView caseId={selectedCaseId} onBack={() => { setSelectedCaseId(null); loadCases(); }} />;
  }



  return (
    <div style={{ maxWidth: '1280px', margin: '0 auto', padding: '24px' }}>

      {/* Header */}
      <div className="glass-panel" style={{ padding: '22px 28px', marginBottom: '20px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '6px' }}>
              <Shield size={22} color="var(--color-primary)" />
              <h2 style={{ fontSize: '1.2rem', fontWeight: 800, color: 'var(--text-primary)', margin: 0 }}>
                Case Management
              </h2>
            </div>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', margin: 0 }}>
              Evidence-backed investigation cases for authorized officer review and action.
            </p>
          </div>
          <button
            onClick={() => { setSelectedQueueItem(undefined); setShowCreateDialog(true); }}
            className="btn-primary"
            style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
          >
            <Plus size={15} /> New Case
          </button>
        </div>

        {/* Status summary cards */}
        {!loading && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '12px', marginTop: '20px' }}>
            {[
              ['Review Required', 'REVIEW_REQUIRED', '#e8b94a'],
              ['Under Review',    'UNDER_REVIEW',    '#6fa8dc'],
              ['Action Required', 'ACTION_REQUIRED', '#e9897e'],
              ['Inspection',      'INSPECTION_ASSIGNED','#b482e6'],
              ['Resolved',        'RESOLVED',        '#7fb685'],
            ].map(([label, key, color]) => (
              <div key={key} className="glass-card" style={{
                padding: '14px 16px', borderLeft: `3px solid ${color}`,
                cursor: 'pointer', transition: 'background 0.2s',
                background: statusFilter === key ? `${color}12` : undefined
              }} onClick={() => setStatusFilter(statusFilter === key ? 'ALL' : key as string)}>
                <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', fontWeight: 700, textTransform: 'uppercase', marginBottom: '4px' }}>
                  {label}
                </div>
                <div style={{ fontSize: '1.5rem', fontWeight: 800, color: color as string }}>
                  {statusCounts[key as string] || 0}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Filters & Search */}
      <div style={{ display: 'flex', gap: '12px', marginBottom: '16px', flexWrap: 'wrap', alignItems: 'center' }}>
        <div style={{ position: 'relative', flex: 1, minWidth: '220px' }}>
          <Search size={14} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
          <input
            value={search}
            onChange={e => { setSearch(e.target.value); setPage(1); }}
            placeholder="Search case number or product name..."
            style={{
              width: '100%', paddingLeft: '36px', paddingRight: '12px', paddingTop: '9px', paddingBottom: '9px',
              borderRadius: '8px', border: '1px solid var(--border-color)',
              background: 'var(--bg-card)', color: 'var(--text-primary)', fontSize: '0.85rem', boxSizing: 'border-box'
            }}
          />
        </div>

        <div style={{ display: 'flex', gap: '6px', background: 'var(--color-subtle-bg)', padding: '4px', borderRadius: '8px', border: '1px solid var(--border-color)', overflowX: 'auto' }}>
          {['ALL','REVIEW_REQUIRED','UNDER_REVIEW','ACTION_REQUIRED','RESOLVED','CLOSED'].map(st => (
            <button key={st} onClick={() => { setStatusFilter(st); setPage(1); }} style={{
              background: statusFilter === st ? 'var(--color-primary)' : 'transparent',
              color: statusFilter === st ? '#fff' : 'var(--text-secondary)',
              border: 'none', padding: '6px 10px', borderRadius: '6px',
              fontSize: '0.72rem', fontWeight: 600, cursor: 'pointer', whiteSpace: 'nowrap'
            }}>
              {st === 'ALL' ? 'All' : STATUS_CONFIG[st]?.label || st}
            </button>
          ))}
        </div>

        <button onClick={loadCases} className="btn-secondary" style={{ padding: '9px 14px' }}>
          <RefreshCw size={14} />
        </button>
      </div>

      {/* Table */}
      {loading ? (
        <div style={{ textAlign: 'center', padding: '60px', color: 'var(--text-secondary)' }}>
          <Activity size={28} style={{ marginBottom: '12px', opacity: 0.4 }} />
          <p>Loading cases...</p>
        </div>
      ) : error ? (
        <div style={{ textAlign: 'center', padding: '60px', color: 'var(--accent-potential)' }}>
          <AlertTriangle size={28} style={{ marginBottom: '12px' }} />
          <p>{error}</p>
          <button onClick={loadCases} className="btn-secondary" style={{ marginTop: '12px' }}>Retry</button>
        </div>
      ) : cases.length === 0 ? (
        <div className="glass-panel" style={{ textAlign: 'center', padding: '60px' }}>
          <Shield size={36} style={{ marginBottom: '16px', opacity: 0.2 }} color="var(--text-secondary)" />
          <p style={{ fontWeight: 700, color: 'var(--text-primary)', fontSize: '1rem' }}>No cases found</p>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.88rem', marginTop: '6px' }}>
            {statusFilter !== 'ALL' ? `No cases with status "${STATUS_CONFIG[statusFilter]?.label || statusFilter}".` : 'No cases exist yet. Create one from the Officer Workbench when a meaningful screening signal is detected.'}
          </p>
          {statusFilter !== 'ALL' && (
            <button onClick={() => setStatusFilter('ALL')} className="btn-secondary" style={{ marginTop: '16px' }}>
              Show All Cases
            </button>
          )}
        </div>
      ) : (
        <div className="glass-panel" style={{ overflowX: 'auto', padding: 0 }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border-color)', background: 'rgba(255,255,255,0.02)' }}>
                {['Case ID','Product','Trigger','Priority','Evidence','Status','Officer','Updated','Action'].map(h => (
                  <th key={h} style={{ padding: '12px 14px', color: 'var(--text-muted)', fontWeight: 700, fontSize: '0.72rem', textTransform: 'uppercase', textAlign: 'left', whiteSpace: 'nowrap' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {cases.map(c => (
                <tr key={c.case_id} style={{ borderBottom: '1px solid var(--border-color)', transition: 'background 0.15s' }}
                  onMouseEnter={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.02)')}
                  onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}>
                  <td style={{ padding: '13px 14px' }}>
                    <span style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--color-primary)', fontFamily: 'monospace' }}>
                      {c.case_number || c.case_id.slice(0, 8).toUpperCase()}
                    </span>
                  </td>
                  <td style={{ padding: '13px 14px', maxWidth: '200px' }}>
                    <div style={{ fontWeight: 700, color: 'var(--text-primary)', fontSize: '0.88rem', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {c.product.name}
                    </div>
                    {c.product.gtin && <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>GTIN: {c.product.gtin}</div>}
                  </td>
                  <td style={{ padding: '13px 14px' }}>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', whiteSpace: 'nowrap' }}>
                      {TRIGGER_LABELS[c.trigger_type] || c.trigger_type}
                    </span>
                  </td>
                  <td style={{ padding: '13px 14px' }}>
                    <PriorityBadge priority={c.priority} />
                  </td>
                  <td style={{ padding: '13px 14px' }}>
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-primary)' }}>{c.evidence_count} items</div>
                    {c.conflict_count > 0 && (
                      <div style={{ fontSize: '0.72rem', color: 'var(--accent-potential)' }}>⚠ {c.conflict_count} conflict(s)</div>
                    )}
                  </td>
                  <td style={{ padding: '13px 14px' }}>
                    <StatusBadge status={c.status} small />
                    {c.finding && <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', marginTop: '3px' }}>{c.finding}</div>}
                  </td>
                  <td style={{ padding: '13px 14px' }}>
                    <span style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                      {c.assigned_officer?.name || <span style={{ color: 'var(--text-muted)' }}>Unassigned</span>}
                    </span>
                  </td>
                  <td style={{ padding: '13px 14px' }}>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
                      {new Date(c.updated_at).toLocaleDateString('en-IN')}
                    </span>
                  </td>
                  <td style={{ padding: '13px 14px' }}>
                    <button
                      onClick={() => setSelectedCaseId(c.case_id)}
                      className="btn-secondary"
                      style={{ padding: '6px 12px', fontSize: '0.75rem', whiteSpace: 'nowrap' }}
                    >
                      <Eye size={12} style={{ marginRight: '4px' }} /> Open
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {/* Pagination */}
          {total > PAGE_SIZE && (
            <div style={{ padding: '14px 20px', borderTop: '1px solid var(--border-color)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                Showing {(page - 1) * PAGE_SIZE + 1}–{Math.min(page * PAGE_SIZE, total)} of {total}
              </span>
              <div style={{ display: 'flex', gap: '8px' }}>
                <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1} className="btn-secondary" style={{ padding: '6px 12px', fontSize: '0.8rem' }}>
                  Previous
                </button>
                <button onClick={() => setPage(p => p + 1)} disabled={page * PAGE_SIZE >= total} className="btn-secondary" style={{ padding: '6px 12px', fontSize: '0.8rem' }}>
                  Next
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Create Case Dialog */}
      {showCreateDialog && (
        <CreateCaseDialog
          queueItem={selectedQueueItem}
          onClose={() => setShowCreateDialog(false)}
          onCreated={(id) => {
            setShowCreateDialog(false);
            setSelectedCaseId(id);
          }}
        />
      )}
    </div>
  );
};

export default CaseManagement;
