import React, { useState, useEffect } from 'react';
import { getDashboardStats } from '../api';
import type { DashboardStats } from '../types';
import {
  PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend,
  BarChart, Bar, XAxis, YAxis, CartesianGrid, LineChart, Line
} from 'recharts';
import { BarChart3, Users, TrendingUp, AlertTriangle, CheckCircle, Clock, Zap } from 'lucide-react';

export const AnalyticsDashboard: React.FC = () => {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    getDashboardStats()
      .then(setStats)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading || !stats) {
    return (
      <div style={{ maxWidth: '1280px', margin: '0 auto', padding: '60px', textAlign: 'center', color: 'var(--text-secondary)' }}>
        <div style={{ width: '32px', height: '32px', border: '3px solid var(--border-color)', borderTopColor: 'var(--color-primary)', borderRadius: '50%', animation: 'spin 1s linear infinite', margin: '0 auto 16px' }} />
        Loading analytics...
      </div>
    );
  }

  const pieData = [
    { name: 'Pass Screening', value: stats.scans.pass_screening, color: '#7FB685' },
    { name: 'Potential Issue', value: stats.scans.potential_non_compliance, color: '#E9897E' },
    { name: 'Needs Review', value: stats.scans.needs_review, color: '#E9B949' }
  ].filter(d => d.value > 0);

  const issueData = (stats.citizen_intelligence.issue_distribution || []).slice(0, 6);
  const trendData = stats.scan_trend || [];
  const priorityProducts = stats.enforcement_prioritization.priority_products || [];

  const statCards = [
    { label: 'TOTAL SCANS', value: stats.scans.total, color: 'var(--text-primary)', sub: 'Live pipeline', icon: <BarChart3 size={18} /> },
    { label: 'PASS SCREENING', value: stats.scans.pass_screening, color: 'var(--accent-pass)', sub: 'No issues found', icon: <CheckCircle size={18} /> },
    { label: 'POTENTIAL ISSUE', value: stats.scans.potential_non_compliance, color: 'var(--accent-potential)', sub: 'Statutory flags', icon: <AlertTriangle size={18} /> },
    { label: 'NEEDS REVIEW', value: stats.scans.needs_review, color: 'var(--accent-review)', sub: 'Human review required', icon: <Clock size={18} /> },
    { label: 'CITIZEN SIGNALS', value: stats.citizen_intelligence.total_signals, color: 'var(--color-primary)', sub: 'Community reports', icon: <Users size={18} /> },
    { label: 'ACTIVE CLUSTERS', value: stats.enforcement_prioritization.active_clusters, color: '#6FA8DC', sub: 'Product-issue groups', icon: <Zap size={18} /> },
  ];

  return (
    <div style={{ maxWidth: '1280px', margin: '0 auto', padding: '24px' }}>
      {/* Disclaimer */}
      <div style={{ padding: '10px 16px', background: 'rgba(42,157,143,0.07)', border: '1px solid rgba(42,157,143,0.2)', borderRadius: '8px', marginBottom: '20px', fontSize: '0.76rem', color: 'var(--text-secondary)' }}>
        <strong style={{ color: 'var(--color-primary)' }}>Analytics Note:</strong> All statistics reflect real database records. Screening results are operational signals, not legal determinations. Final authority rests with authorized officers.
      </div>

      {/* Stat Cards */}
      <div className="flex-wrap-responsive" style={{ display: 'flex', gap: '12px', marginBottom: '24px', flexWrap: 'wrap' }}>
        {statCards.map((card, i) => (
          <div key={i} className="glass-panel" style={{ flex: '1', minWidth: '150px', padding: '18px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <span style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', fontWeight: 700, letterSpacing: '0.04em' }}>{card.label}</span>
              <span style={{ color: card.color, opacity: 0.7 }}>{card.icon}</span>
            </div>
            <div style={{ fontSize: '2rem', fontWeight: 800, color: card.color, margin: '6px 0 2px' }}>{card.value}</div>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>{card.sub}</div>
          </div>
        ))}
      </div>

      {/* Charts Row 1 */}
      <div className="grid-responsive" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '20px' }}>
        {/* Screening Distribution Pie */}
        <div className="glass-panel" style={{ padding: '24px' }}>
          <h3 style={{ fontSize: '1rem', fontWeight: 700, marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-primary)' }}>
            <BarChart3 size={16} color="var(--color-primary)" /> Three-State Screening Distribution
          </h3>
          <div style={{ width: '100%', height: 240 }}>
            <ResponsiveContainer>
              <PieChart>
                <Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} label={({ percent }) => `${((percent || 0) * 100).toFixed(0)}%`} labelLine={false}>
                  {pieData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ background: 'var(--bg-card)', border: '1px solid var(--border-color)', borderRadius: '8px', fontSize: '0.8rem' }} />
                <Legend iconType="circle" iconSize={10} wrapperStyle={{ fontSize: '0.78rem' }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Scan Trend Line Chart */}
        <div className="glass-panel" style={{ padding: '24px' }}>
          <h3 style={{ fontSize: '1rem', fontWeight: 700, marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-primary)' }}>
            <TrendingUp size={16} color="var(--color-primary)" /> Scan Volume — Last 7 Days
          </h3>
          {trendData.length > 0 ? (
            <div style={{ width: '100%', height: 220 }}>
              <ResponsiveContainer>
                <LineChart data={trendData} margin={{ top: 5, right: 20, left: -20, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" />
                  <XAxis dataKey="date" tick={{ fontSize: 11, fill: 'var(--text-secondary)' }} />
                  <YAxis tick={{ fontSize: 11, fill: 'var(--text-secondary)' }} allowDecimals={false} />
                  <Tooltip contentStyle={{ background: 'var(--bg-card)', border: '1px solid var(--border-color)', borderRadius: '8px', fontSize: '0.8rem' }} />
                  <Line type="monotone" dataKey="scans" stroke="var(--color-primary)" strokeWidth={2} dot={{ r: 4, fill: 'var(--color-primary)' }} activeDot={{ r: 6 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div style={{ height: 220, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', fontSize: '0.85rem' }}>No scan trend data available yet</div>
          )}
        </div>
      </div>

      {/* Charts Row 2 */}
      <div className="grid-responsive" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '20px' }}>
        {/* Issue Category Bar Chart */}
        <div className="glass-panel" style={{ padding: '24px' }}>
          <h3 style={{ fontSize: '1rem', fontWeight: 700, marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-primary)' }}>
            <AlertTriangle size={16} color="var(--color-primary)" /> Citizen Signal Categories
          </h3>
          {issueData.length > 0 ? (
            <div style={{ width: '100%', height: 220 }}>
              <ResponsiveContainer>
                <BarChart data={issueData} layout="vertical" margin={{ top: 0, right: 20, left: 10, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" horizontal={false} />
                  <XAxis type="number" tick={{ fontSize: 11, fill: 'var(--text-secondary)' }} allowDecimals={false} />
                  <YAxis type="category" dataKey="issue" tick={{ fontSize: 10, fill: 'var(--text-secondary)' }} width={110} />
                  <Tooltip contentStyle={{ background: 'var(--bg-card)', border: '1px solid var(--border-color)', borderRadius: '8px', fontSize: '0.8rem' }} />
                  <Bar dataKey="count" fill="var(--color-primary)" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div style={{ height: 220, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', fontSize: '0.85rem' }}>No citizen signals filed yet</div>
          )}
        </div>

        {/* Operational Metrics */}
        <div className="glass-panel" style={{ padding: '24px' }}>
          <h3 style={{ fontSize: '1rem', fontWeight: 700, marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-primary)' }}>
            <Users size={16} color="var(--color-primary)" /> Operational Metrics
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {[
              { label: 'Active Product-Issue Clusters', value: stats.enforcement_prioritization.active_clusters, color: '#6FA8DC' },
              { label: 'Completed Officer Adjudications', value: stats.enforcement_prioritization.completed_officer_reviews, color: 'var(--accent-pass)' },
              { label: 'Unverified Citizen Signals', value: stats.citizen_intelligence.unverified_signals, color: 'var(--accent-review)' },
              { label: 'Scans With Potential Issues', value: stats.scans.potential_non_compliance, color: 'var(--accent-potential)' },
            ].map((item, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 14px', background: 'var(--bg-main)', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>{item.label}</span>
                <span style={{ fontSize: '1.2rem', fontWeight: 800, color: item.color }}>{item.value}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Top Priority Products */}
      {priorityProducts.length > 0 && (
        <div className="glass-panel" style={{ padding: '24px' }}>
          <h3 style={{ fontSize: '1rem', fontWeight: 700, marginBottom: '4px', display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-primary)' }}>
            <Zap size={16} color="var(--color-primary)" /> Top Priority Products
          </h3>
          <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '16px' }}>
            Ranked by Operational Prioritization Score — not probability of legal violation
          </p>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.82rem' }}>
              <thead>
                <tr style={{ borderBottom: '2px solid var(--border-color)' }}>
                  {['Product', 'Issue', 'Priority', 'Score', 'Signals', 'AI Flags', 'Status'].map(h => (
                    <th key={h} style={{ padding: '8px 12px', textAlign: 'left', fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-secondary)', letterSpacing: '0.04em' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {priorityProducts.map((p, i) => (
                  <tr key={i} style={{ borderBottom: '1px solid var(--border-color)', transition: 'background 0.15s' }}
                    onMouseOver={e => (e.currentTarget.style.background = 'var(--bg-main)')}
                    onMouseOut={e => (e.currentTarget.style.background = 'transparent')}>
                    <td style={{ padding: '10px 12px', fontWeight: 600, color: 'var(--text-primary)' }}>
                      <div>{p.product_name}</div>
                      {p.gtin && <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>GTIN: {p.gtin}</div>}
                    </td>
                    <td style={{ padding: '10px 12px', color: 'var(--text-secondary)' }}>{p.issue_type}</td>
                    <td style={{ padding: '10px 12px' }}>
                      <span style={{
                        padding: '3px 8px', borderRadius: '12px', fontSize: '0.72rem', fontWeight: 700,
                        background: p.priority_label === 'HIGH' ? 'rgba(233,137,126,0.15)' : p.priority_label === 'MEDIUM' ? 'rgba(233,185,73,0.15)' : 'rgba(127,182,133,0.15)',
                        color: p.priority_label === 'HIGH' ? 'var(--accent-potential)' : p.priority_label === 'MEDIUM' ? 'var(--accent-review)' : 'var(--accent-pass)'
                      }}>{p.priority_label}</span>
                    </td>
                    <td style={{ padding: '10px 12px', fontWeight: 700, color: 'var(--text-primary)', fontFamily: 'var(--font-mono)', fontSize: '0.85rem' }}>{p.priority_score}</td>
                    <td style={{ padding: '10px 12px', color: 'var(--text-secondary)', textAlign: 'center' }}>{p.citizen_reports}</td>
                    <td style={{ padding: '10px 12px', color: 'var(--text-secondary)', textAlign: 'center' }}>{p.ai_flags}</td>
                    <td style={{ padding: '10px 12px' }}>
                      <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 600 }}>{p.status}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p style={{ marginTop: '12px', fontSize: '0.7rem', color: 'var(--text-muted)', fontStyle: 'italic' }}>
            ⚠ Operational Prioritization Score is for officer workflow prioritization only. It does not imply probability of legal violation.
          </p>
        </div>
      )}
    </div>
  );
};
