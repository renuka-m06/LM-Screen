import React, { useState, useEffect } from 'react';
import {
  getAnalyticsOverview, getAnalyticsTrends, getAnalyticsCategories,
  getAnalyticsRequirements, getAnalyticsQuality, getAnalyticsConsistency,
  getAnalyticsPrioritization, getSystemHealth
} from '../api';
import {
  BarChart3, Users, TrendingUp, AlertTriangle, Shield, CheckCircle, Package, Link, Database, LayoutDashboard
} from 'lucide-react';
import {
  PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend,
  BarChart, Bar, XAxis, YAxis, CartesianGrid, LineChart, Line
} from 'recharts';

export const AnalyticsDashboard: React.FC = () => {
  const [days, setDays] = useState<number>(30);
  const [activeLayer, setActiveLayer] = useState<'OVERVIEW' | 'PRODUCT' | 'EVIDENCE' | 'OFFICER'>('OVERVIEW');
  const [loading, setLoading] = useState<boolean>(true);
  
  const [overview, setOverview] = useState<any>(null);
  const [trends, setTrends] = useState<any[]>([]);
  const [categories, setCategories] = useState<any[]>([]);
  const [requirements, setRequirements] = useState<any[]>([]);
  const [quality, setQuality] = useState<any[]>([]);
  const [consistency, setConsistency] = useState<any[]>([]);
  const [prioritization, setPrioritization] = useState<any[]>([]);
  const [health, setHealth] = useState<any>(null);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      getAnalyticsOverview(days),
      getAnalyticsTrends(days),
      getAnalyticsCategories(days),
      getAnalyticsRequirements(days),
      getAnalyticsQuality(days),
      getAnalyticsConsistency(days),
      getAnalyticsPrioritization(days),
      getSystemHealth()
    ]).then(results => {
      setOverview(results[0]);
      setTrends(results[1]);
      setCategories(results[2]);
      setRequirements(results[3]);
      setQuality(results[4]);
      setConsistency(results[5]);
      setPrioritization(results[6]);
      setHealth(results[7]);
    }).catch(console.error).finally(() => setLoading(false));
  }, [days]);

  if (loading && !overview) {
    return (
      <div style={{ maxWidth: '1280px', margin: '0 auto', padding: '60px', textAlign: 'center', color: 'var(--text-secondary)' }}>
        <div style={{ width: '32px', height: '32px', border: '3px solid var(--border-color)', borderTopColor: 'var(--color-primary)', borderRadius: '50%', animation: 'spin 1s linear infinite', margin: '0 auto 16px' }} />
        Aggregating intelligence data...
      </div>
    );
  }
  
  if (!loading && overview && overview.total_scans === 0 && overview.total_observations === 0) {
    return (
      <div style={{ maxWidth: '1280px', margin: '0 auto', padding: '60px', textAlign: 'center', color: 'var(--text-secondary)' }}>
        <Database size={40} style={{ margin: '0 auto 16px', opacity: 0.5 }} />
        <h3 style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--text-primary)' }}>No screening data available.</h3>
        <p>The system has not recorded any observations in the selected time range.</p>
        <select value={days} onChange={e => setDays(Number(e.target.value))} style={{ marginTop: '16px', padding: '8px', borderRadius: '8px' }}>
          <option value={7}>Last 7 Days</option>
          <option value={30}>Last 30 Days</option>
          <option value={90}>Last 90 Days</option>
          <option value={9999}>All Time</option>
        </select>
      </div>
    );
  }

  const statCards = [
    { label: 'Total Scans', value: overview?.total_scans, color: 'var(--text-primary)', icon: <BarChart3 size={18} /> },
    { label: 'Observations', value: overview?.total_observations, color: 'var(--color-primary)', icon: <Users size={18} /> },
    { label: 'Unique Products', value: overview?.total_unique_product_clusters, color: '#6FA8DC', icon: <Package size={18} /> },
    { label: 'Review Required', value: overview?.cases_requiring_review, color: 'var(--accent-review)', icon: <AlertTriangle size={18} /> },
    { label: 'Evidence Conflicts', value: overview?.cases_with_evidence_conflicts, color: 'var(--accent-potential)', icon: <TrendingUp size={18} /> },
    { label: 'Officer Adjudicated', value: overview?.total_officer_reviewed_cases, color: 'var(--accent-pass)', icon: <CheckCircle size={18} /> }
  ];

  return (
    <div style={{ maxWidth: '1280px', margin: '0 auto', padding: '24px' }}>
      
      {/* Header and Filters */}
      <div className="glass-panel" style={{ padding: '20px 24px', marginBottom: '20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 800, display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-primary)' }}>
            <LayoutDashboard size={22} color="var(--color-primary)" /> Product Intelligence & Analytics
          </h2>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
            Evidence-driven decision support system based on real database records.
          </p>
        </div>
        
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          <label style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)' }}>Time Range:</label>
          <select value={days} onChange={e => setDays(Number(e.target.value))} style={{ padding: '8px 12px', borderRadius: '8px', border: '1px solid var(--border-color)', background: 'var(--bg-main)', color: 'var(--text-primary)', fontWeight: 600 }}>
            <option value={7}>Last 7 Days</option>
            <option value={30}>Last 30 Days</option>
            <option value={90}>Last 90 Days</option>
            <option value={9999}>All Time</option>
          </select>
        </div>
      </div>

      {/* Layer Navigation */}
      <div style={{ display: 'flex', gap: '8px', marginBottom: '20px', overflowX: 'auto', paddingBottom: '8px' }}>
        {[
          { id: 'OVERVIEW', label: 'System Overview' },
          { id: 'PRODUCT', label: 'Product Intelligence' },
          { id: 'EVIDENCE', label: 'Evidence Intelligence' },
          { id: 'OFFICER', label: 'Officer Review Intelligence' }
        ].map(layer => (
          <button
            key={layer.id}
            onClick={() => setActiveLayer(layer.id as any)}
            style={{
              padding: '10px 16px', borderRadius: '8px', border: 'none', fontWeight: 700, fontSize: '0.85rem', cursor: 'pointer',
              background: activeLayer === layer.id ? 'var(--color-primary)' : 'var(--color-subtle-bg)',
              color: activeLayer === layer.id ? '#fff' : 'var(--text-secondary)',
              whiteSpace: 'nowrap'
            }}
          >
            {layer.label}
          </button>
        ))}
      </div>

      {/* OVERVIEW LAYER */}
      {activeLayer === 'OVERVIEW' && (
        <>
          <div className="flex-wrap-responsive" style={{ display: 'flex', gap: '12px', marginBottom: '24px', flexWrap: 'wrap' }}>
            {statCards.map((card, i) => (
              <div key={i} className="glass-panel" style={{ flex: '1', minWidth: '150px', padding: '18px', borderLeft: `3px solid ${card.color}` }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <span style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', fontWeight: 700, textTransform: 'uppercase' }}>{card.label}</span>
                  <span style={{ color: card.color, opacity: 0.7 }}>{card.icon}</span>
                </div>
                <div style={{ fontSize: '1.8rem', fontWeight: 800, color: 'var(--text-primary)', margin: '6px 0 2px' }}>{card.value}</div>
              </div>
            ))}
          </div>

          {health && health.models && (
            <div className="glass-panel" style={{ padding: '24px', marginBottom: '24px' }}>
              <h3 style={{ fontSize: '1rem', fontWeight: 700, marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-primary)' }}>
                <CheckCircle size={16} color="var(--color-primary)" /> ML Model Health Overview
              </h3>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '16px' }}>
                {health.models.map((m: any) => (
                  <div key={m.model_name} style={{
                    padding: '16px', borderRadius: '8px', border: '1px solid var(--border-color)',
                    background: m.status === 'MODEL_READY' ? 'rgba(127,182,133,0.05)' : 'rgba(233,185,73,0.05)'
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                      <span style={{ fontWeight: 700, color: 'var(--text-primary)', fontSize: '0.9rem' }}>{m.model_name} {m.model_version}</span>
                      <span style={{ 
                        fontSize: '0.7rem', fontWeight: 800, padding: '2px 8px', borderRadius: '12px',
                        background: m.status === 'MODEL_READY' ? 'var(--accent-pass)' : 'var(--accent-review)', color: '#fff' 
                      }}>{m.status}</span>
                    </div>
                    {m.status !== 'MODEL_READY' && (
                      <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                        Model weights not found. System falling back to heuristic / OpenCV methods.
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="glass-panel" style={{ padding: '24px' }}>
            <h3 style={{ fontSize: '1rem', fontWeight: 700, marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-primary)' }}>
              <TrendingUp size={16} color="var(--color-primary)" /> Observation Trends
            </h3>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '16px' }}>Actual system scans and citizen reports over time.</p>
            <div style={{ width: '100%', height: 300 }}>
              <ResponsiveContainer>
                <LineChart data={trends} margin={{ top: 5, right: 20, left: -20, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" />
                  <XAxis dataKey="date" tick={{ fontSize: 11, fill: 'var(--text-secondary)' }} />
                  <YAxis tick={{ fontSize: 11, fill: 'var(--text-secondary)' }} allowDecimals={false} />
                  <Tooltip contentStyle={{ background: 'var(--bg-card)', border: '1px solid var(--border-color)', borderRadius: '8px', fontSize: '0.8rem' }} />
                  <Legend wrapperStyle={{ fontSize: '0.8rem' }} />
                  <Line type="monotone" name="Officer Scans" dataKey="scans" stroke="var(--color-primary)" strokeWidth={2} dot={{ r: 3 }} />
                  <Line type="monotone" name="Citizen Observations" dataKey="observations" stroke="var(--accent-review)" strokeWidth={2} dot={{ r: 3 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </>
      )}

      {/* PRODUCT LAYER */}
      {activeLayer === 'PRODUCT' && (
        <div className="grid-responsive" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
          <div className="glass-panel" style={{ padding: '24px' }}>
            <h3 style={{ fontSize: '1rem', fontWeight: 700, marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-primary)' }}>
              <Package size={16} color="var(--color-primary)" /> Products by Category
            </h3>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '16px' }}>Distribution of observed product clusters by classification context.</p>
            <div style={{ width: '100%', height: 300 }}>
              <ResponsiveContainer>
                <BarChart data={categories} layout="vertical" margin={{ top: 0, right: 20, left: 10, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" horizontal={false} />
                  <XAxis type="number" tick={{ fontSize: 11, fill: 'var(--text-secondary)' }} allowDecimals={false} />
                  <YAxis type="category" dataKey="category" tick={{ fontSize: 10, fill: 'var(--text-secondary)' }} width={120} />
                  <Tooltip contentStyle={{ background: 'var(--bg-card)', border: '1px solid var(--border-color)', borderRadius: '8px', fontSize: '0.8rem' }} />
                  <Bar name="Unique Products" dataKey="clusters" fill="#6FA8DC" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
          
          <div className="glass-panel" style={{ padding: '24px' }}>
             <h3 style={{ fontSize: '1rem', fontWeight: 700, marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-primary)' }}>
              <Link size={16} color="var(--color-primary)" /> Requirement Intelligence
            </h3>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '16px' }}>Frequency of requirements evaluated across all observations.</p>
            <div style={{ overflowY: 'auto', maxHeight: '300px' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border-color)', color: 'var(--text-secondary)', textAlign: 'left' }}>
                    <th style={{ padding: '8px' }}>Requirement</th>
                    <th style={{ padding: '8px', textAlign: 'center' }}>Supported</th>
                    <th style={{ padding: '8px', textAlign: 'center' }}>Uncertain</th>
                    <th style={{ padding: '8px', textAlign: 'center' }}>Missing</th>
                  </tr>
                </thead>
                <tbody>
                  {requirements.map((req, idx) => (
                    <tr key={idx} style={{ borderBottom: '1px solid var(--border-color)' }}>
                      <td style={{ padding: '10px 8px', fontWeight: 600, color: 'var(--text-primary)' }}>{req.requirement.toUpperCase()}</td>
                      <td style={{ padding: '10px 8px', textAlign: 'center', color: 'var(--accent-pass)' }}>{req.states['SUPPORTED'] || 0}</td>
                      <td style={{ padding: '10px 8px', textAlign: 'center', color: 'var(--accent-review)' }}>{req.states['UNCERTAIN'] || 0}</td>
                      <td style={{ padding: '10px 8px', textAlign: 'center', color: 'var(--accent-potential)' }}>{req.states['NOT_DETECTED'] || 0}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* EVIDENCE LAYER */}
      {activeLayer === 'EVIDENCE' && (
        <div className="grid-responsive" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
          <div className="glass-panel" style={{ padding: '24px' }}>
            <h3 style={{ fontSize: '1rem', fontWeight: 700, marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-primary)' }}>
              <Shield size={16} color="var(--color-primary)" /> Overall Evidence Quality
            </h3>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '16px' }}>
              Breakdown of raw extracted evidence validity.
            </p>
            <div style={{ width: '100%', height: 260 }}>
              <ResponsiveContainer>
                <PieChart>
                  <Pie data={quality} dataKey="count" nameKey="state" cx="50%" cy="50%" outerRadius={80} label={({ percent }) => `${((percent || 0) * 100).toFixed(0)}%`} labelLine={false}>
                    {quality.map((entry, index) => {
                       let color = 'var(--text-secondary)';
                       if (entry.state === 'SUPPORTED') color = 'var(--accent-pass)';
                       if (entry.state === 'UNCERTAIN') color = 'var(--accent-review)';
                       if (entry.state === 'NOT_DETECTED') color = 'var(--accent-potential)';
                       if (entry.state === 'CONFLICTING') color = '#E9897E';
                       return <Cell key={`cell-${index}`} fill={color} />;
                    })}
                  </Pie>
                  <Tooltip contentStyle={{ background: 'var(--bg-card)', border: '1px solid var(--border-color)', borderRadius: '8px', fontSize: '0.8rem' }} />
                  <Legend wrapperStyle={{ fontSize: '0.8rem' }} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="glass-panel" style={{ padding: '24px' }}>
             <h3 style={{ fontSize: '1rem', fontWeight: 700, marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-primary)' }}>
              <AlertTriangle size={16} color="var(--accent-potential)" /> Cross-Evidence Conflicts
            </h3>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '16px' }}>
              Number of cases where multiple evidence sources contain conflicting values. <br/>
              <em>This does not automatically establish legal non-compliance.</em>
            </p>
            <div style={{ overflowY: 'auto', maxHeight: '250px' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border-color)', color: 'var(--text-secondary)', textAlign: 'left' }}>
                    <th style={{ padding: '8px' }}>Conflict Type</th>
                    <th style={{ padding: '8px', textAlign: 'center' }}>Occurrences</th>
                  </tr>
                </thead>
                <tbody>
                  {consistency.filter(c => c.status !== 'CONSISTENT').map((c, idx) => (
                    <tr key={idx} style={{ borderBottom: '1px solid var(--border-color)' }}>
                      <td style={{ padding: '10px 8px', fontWeight: 600, color: 'var(--text-primary)' }}>{c.check_type.replace(/_/g, ' ')}</td>
                      <td style={{ padding: '10px 8px', textAlign: 'center', color: 'var(--accent-potential)', fontWeight: 800 }}>{c.count}</td>
                    </tr>
                  ))}
                  {consistency.filter(c => c.status !== 'CONSISTENT').length === 0 && (
                    <tr><td colSpan={2} style={{ padding: '20px', textAlign: 'center', color: 'var(--text-muted)' }}>No conflicts detected.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* OFFICER LAYER */}
      {activeLayer === 'OFFICER' && (
        <div className="grid-responsive" style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '20px' }}>
          <div className="glass-panel" style={{ padding: '24px' }}>
            <h3 style={{ fontSize: '1rem', fontWeight: 700, marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-primary)' }}>
              <Shield size={16} color="var(--color-primary)" /> Evidence-Based Prioritization
            </h3>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '16px' }}>
              Operational review queue prioritization driven by evidence actionability, conflicts, and recurrence.
            </p>
            
            <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
              {prioritization.map((p, idx) => {
                let color = 'var(--text-secondary)';
                if (p.priority_class === 'PRIORITY_REVIEW') color = 'var(--accent-potential)';
                if (p.priority_class === 'STANDARD_REVIEW') color = 'var(--accent-review)';
                if (p.priority_class === 'EVIDENCE_INSUFFICIENT') color = 'var(--text-muted)';
                return (
                  <div key={idx} style={{ flex: 1, minWidth: '200px', background: 'var(--color-subtle-bg)', padding: '20px', borderRadius: '10px', borderTop: `4px solid ${color}` }}>
                    <div style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '8px' }}>{p.priority_class.replace(/_/g, ' ')}</div>
                    <div style={{ fontSize: '2rem', fontWeight: 800, color: 'var(--text-primary)' }}>{p.count}</div>
                  </div>
                )
              })}
            </div>
            
            <div style={{ marginTop: '30px', padding: '16px', background: 'rgba(233,185,73,0.05)', border: '1px dashed var(--accent-review)', borderRadius: '8px' }}>
              <h4 style={{ fontSize: '0.9rem', color: 'var(--text-primary)', fontWeight: 700, marginBottom: '8px' }}>Important Intelligence Note</h4>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                Priority rankings are intended strictly for operational queue management. A product placed in "Priority Review" means there is strong, actionable evidence requiring human intervention (e.g., conflicts, repeat reports), not that the product is legally non-compliant. Statutory determination always requires formal officer verification.
              </p>
            </div>
          </div>
        </div>
      )}

    </div>
  );
};
