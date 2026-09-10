import React from 'react';
import { Shield, ScanLine, FileText, LayoutDashboard, UserCheck } from 'lucide-react';

interface NavbarProps {
  activeTab: 'scan' | 'citizen' | 'officer' | 'dashboard';
  setActiveTab: (tab: 'scan' | 'citizen' | 'officer' | 'dashboard') => void;
  userRole: 'CITIZEN' | 'OFFICER';
  setUserRole: (role: 'CITIZEN' | 'OFFICER') => void;
}

export const Navbar: React.FC<NavbarProps> = ({ activeTab, setActiveTab, userRole, setUserRole }) => {
  return (
    <header style={{ background: 'var(--bg-card)', borderBottom: '1px solid var(--border-color)', padding: '12px 20px', position: 'sticky', top: 0, zIndex: 50 }}>
      <div className="flex-wrap-responsive" style={{ maxWidth: '1280px', margin: '0 auto', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '16px' }}>
        {/* Brand & Emblem */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', cursor: 'pointer' }} onClick={() => setActiveTab('scan')}>
          <div style={{ background: 'var(--color-primary)', padding: '10px', borderRadius: '10px', display: 'flex' }}>
            <Shield size={24} color="#ffffff" />
          </div>
          <div>
            <h1 style={{ fontSize: '1.2rem', fontWeight: 800, letterSpacing: '-0.02em', color: 'var(--text-primary)' }}>
              LM-SCREEN
            </h1>
            <p className="hide-on-mobile" style={{ fontSize: '0.65rem', color: 'var(--text-secondary)', fontWeight: 500, letterSpacing: '0.02em' }}>
              DEPARTMENT OF CONSUMER AFFAIRS • LEGAL METROLOGY SCREENING
            </p>
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '4px', background: 'var(--bg-main)', padding: '4px', borderRadius: '10px', border: '1px solid var(--border-color)' }}>
          <button
            onClick={() => setActiveTab('scan')}
            style={{
              display: 'flex', alignItems: 'center', gap: '6px', padding: '8px 14px', borderRadius: '6px', border: 'none',
              background: activeTab === 'scan' ? 'var(--color-primary-soft)' : 'transparent', color: activeTab === 'scan' ? 'var(--color-primary)' : 'var(--text-secondary)',
              fontWeight: 600, fontSize: '0.82rem', cursor: 'pointer', transition: 'all 0.2s'
            }}
          >
            <ScanLine size={16} /> AI Screening
          </button>
          <button
            onClick={() => setActiveTab('citizen')}
            style={{
              display: 'flex', alignItems: 'center', gap: '6px', padding: '8px 14px', borderRadius: '6px', border: 'none',
              background: activeTab === 'citizen' ? 'var(--color-primary-soft)' : 'transparent', color: activeTab === 'citizen' ? 'var(--color-primary)' : 'var(--text-secondary)',
              fontWeight: 600, fontSize: '0.82rem', cursor: 'pointer', transition: 'all 0.2s'
            }}
          >
            <FileText size={16} /> Citizen Signals
          </button>
          <button
            onClick={() => setActiveTab('officer')}
            style={{
              display: 'flex', alignItems: 'center', gap: '6px', padding: '8px 14px', borderRadius: '6px', border: 'none',
              background: activeTab === 'officer' ? 'var(--color-primary-soft)' : 'transparent', color: activeTab === 'officer' ? 'var(--color-primary)' : 'var(--text-secondary)',
              fontWeight: 600, fontSize: '0.82rem', cursor: 'pointer', transition: 'all 0.2s'
            }}
          >
            <Shield size={16} /> Priority Queue
          </button>
          <button
            onClick={() => setActiveTab('dashboard')}
            style={{
              display: 'flex', alignItems: 'center', gap: '6px', padding: '8px 14px', borderRadius: '6px', border: 'none',
              background: activeTab === 'dashboard' ? 'var(--color-primary-soft)' : 'transparent', color: activeTab === 'dashboard' ? 'var(--color-primary)' : 'var(--text-secondary)',
              fontWeight: 600, fontSize: '0.82rem', cursor: 'pointer', transition: 'all 0.2s'
            }}
          >
            <LayoutDashboard size={16} /> Analytics
          </button>
        </nav>

        {/* Role Toggle Selector */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <button
            onClick={() => setUserRole(userRole === 'CITIZEN' ? 'OFFICER' : 'CITIZEN')}
            style={{
              display: 'flex', alignItems: 'center', gap: '6px', padding: '6px 12px', borderRadius: '20px',
              border: '1px solid var(--border-color)', background: 'var(--color-primary-soft)', color: 'var(--text-primary)',
              fontSize: '0.8rem', fontWeight: 600, cursor: 'pointer'
            }}
          >
            <UserCheck size={14} color="#2A9D8F" />
            Mode: <span style={{ color: userRole === 'OFFICER' ? 'var(--accent-review)' : 'var(--color-primary)' }}>{userRole}</span>
          </button>
        </div>
      </div>
    </header>
  );
};
