import React, { useState } from 'react';
import { uploadScanImage } from '../api';
import type { ScanResult } from '../types';
import { EvidenceOverlay } from './EvidenceOverlay';
import { DisclaimerBanner } from './DisclaimerBanner';
import { Upload, CheckCircle2, AlertTriangle, HelpCircle, RefreshCw, FileCode, Search, Microscope, MessageSquare } from 'lucide-react';

interface ScannerProps {
  userRole?: 'CITIZEN' | 'OFFICER';
  onInvestigate?: (productId?: string, scanId?: string) => void;
  onFileSignal?: (scanResult: ScanResult) => void;
}

export const Scanner: React.FC<ScannerProps> = ({ userRole = 'CITIZEN', onInvestigate, onFileSignal }) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [productName, setProductName] = useState<string>('');
  const [gtin, setGtin] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [scanResult, setScanResult] = useState<ScanResult | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // File Upload Handler
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setSelectedFile(file);
      setPreviewUrl(URL.createObjectURL(file));
      setScanResult(null);
      setErrorMsg(null);
    }
  };

  // Process Image Scan
  const handleRunScan = async () => {
    if (!selectedFile) return;
    setLoading(true);
    setErrorMsg(null);

    try {
      const result = await uploadScanImage(selectedFile, productName, gtin);
      setScanResult(result);
    } catch (err: any) {
      setErrorMsg(err.message || 'Scan processing failed.');
    } finally {
      setLoading(false);
    }
  };

  // Synthetic SIH Demo Preset Loaders
  const loadDemoPreset = (type: 'clean' | 'missing_mrp' | 'blurry' | 'mismatch') => {
    const canvas = document.createElement('canvas');
    canvas.width = 640;
    canvas.height = 640;
    const ctx = canvas.getContext('2d');
    if (ctx) {
      if (type === 'blurry') {
        ctx.fillStyle = '#f1f5f9';
        ctx.fillRect(0, 0, 640, 640);
        ctx.filter = 'blur(14px)';
        ctx.fillStyle = '#475569';
        ctx.font = '22px Arial, sans-serif';
        ctx.fillText('DailyFresh Washing Powder', 50, 100);
        ctx.fillText('Net Qty: 1.0 kg', 50, 180);
        ctx.fillText('MFD: 03/2026', 50, 240);
        ctx.fillText('MRP: Rs. 99.00', 50, 300);
      } else if (type === 'missing_mrp') {
        ctx.fillStyle = '#ffffff';
        ctx.fillRect(0, 0, 640, 640);
        ctx.strokeStyle = '#cbd5e1';
        ctx.lineWidth = 4;
        ctx.strokeRect(16, 16, 608, 608);

        ctx.fillStyle = '#0f172a';
        ctx.font = 'bold 26px Arial, sans-serif';
        ctx.fillText('ChocoDelight Dark Chocolate', 45, 80);

        ctx.font = 'bold 20px Arial, sans-serif';
        ctx.fillText('Net Qty: 100 g', 45, 150);
        ctx.fillText('MFD: 02/2026', 45, 210);
        ctx.fillText('Best Before: 12 Months', 45, 270);
        ctx.fillText('Mfg by: ChocoDelight Confectionery Mumbai', 45, 330);
        ctx.fillText('Consumer Care: 1800-22-9988', 45, 390);
        ctx.fillText('GSTIN: 27AAAAA1234A1Z5', 45, 450);

        // Barcode
        ctx.fillStyle = '#000000';
        for (let i = 0; i < 42; i++) {
          const w = (i % 4 === 0) ? 4 : 2;
          ctx.fillRect(45 + i * 8, 490, w, 55);
        }
        ctx.font = '16px monospace';
        ctx.fillText('8909876543210', 130, 575);
      } else if (type === 'mismatch') {
        // Identity mismatch demo: package shows completely different product
        ctx.fillStyle = '#fff8f0';
        ctx.fillRect(0, 0, 640, 640);
        ctx.strokeStyle = '#e8c8a0';
        ctx.lineWidth = 4;
        ctx.strokeRect(16, 16, 608, 608);

        ctx.fillStyle = '#1a1a2e';
        ctx.font = 'bold 26px Arial, sans-serif';
        ctx.fillText('Premium Choco-Chip Biscuits', 45, 80);

        ctx.font = 'bold 20px Arial, sans-serif';
        ctx.fillText('Net Quantity: 250 g', 45, 150);
        ctx.fillText('MRP: Rs. 150.00 (Incl. of all taxes)', 45, 210);
        ctx.fillText('Mfg. Date: 09/2026', 45, 270);
        ctx.fillText('Best Before: 6 Months from Mfg Date', 45, 330);
        ctx.fillText('Manufactured & Packed by:', 45, 390);
        ctx.fillText('ABC Foods Pvt Ltd.', 45, 415);
        ctx.fillText('123 Industrial Area, Andheri East', 45, 440);
        ctx.fillText('Mumbai, Maharashtra - 400093', 45, 465);
        ctx.fillText('Consumer Care: 1800-123-4567', 45, 500);
        ctx.fillText('GSTIN: 27AAABC5678D1Z4', 45, 530);

        // Barcode
        ctx.fillStyle = '#000000';
        for (let i = 0; i < 45; i++) {
          const w = (i % 3 === 0) ? 4 : 2;
          ctx.fillRect(45 + i * 8, 555, w, 50);
        }
        ctx.font = '14px monospace';
        ctx.fillText('8901234567890', 140, 620);
      } else {
        // Clean complete statutory package
        ctx.fillStyle = '#ffffff';
        ctx.fillRect(0, 0, 640, 640);
        ctx.strokeStyle = '#cbd5e1';
        ctx.lineWidth = 4;
        ctx.strokeRect(16, 16, 608, 608);

        ctx.fillStyle = '#0f172a';
        ctx.font = 'bold 26px Arial, sans-serif';
        ctx.fillText('PureHarvest Atta 5kg', 45, 80);

        ctx.font = 'bold 20px Arial, sans-serif';
        ctx.fillText('MRP: Rs. 260.00 (Incl. of all taxes)', 45, 140);
        ctx.fillText('Net Qty: 5.0 kg', 45, 195);
        ctx.fillText('MFD: 01/2026', 45, 250);
        ctx.fillText('Best Before: 6 Months from MFD', 45, 305);
        ctx.fillText('Consumer Care: 1800-11-2233', 45, 360);
        ctx.fillText('Mfg by: PureHarvest Agro Noida UP', 45, 415);
        ctx.fillText('GSTIN: 09AAAAA1234A1Z5', 45, 465);

        // Barcode
        ctx.fillStyle = '#000000';
        for (let i = 0; i < 45; i++) {
          const w = (i % 3 === 0) ? 4 : 2;
          ctx.fillRect(45 + i * 8, 500, w, 55);
        }
        ctx.font = '16px monospace';
        ctx.fillText('8901234567890', 140, 585);
      }
    }

    canvas.toBlob((blob) => {
      if (blob) {
        const file = new File([blob], `demo_${type}.png`, { type: 'image/png' });
        setSelectedFile(file);
        setPreviewUrl(URL.createObjectURL(file));
        setScanResult(null);
        setErrorMsg(null);
        if (type === 'clean') {
          setProductName('PureHarvest Atta 5kg');
          setGtin('8901234567890');
        } else if (type === 'missing_mrp') {
          setProductName('ChocoDelight Dark Chocolate');
          setGtin('8909876543210');
        } else if (type === 'mismatch') {
          // Identity mismatch: user says PureHarvest Atta, but image shows Premium Choco-Chip Biscuits
          setProductName('PureHarvest Atta 5kg');
          setGtin('8901234567890');
        } else {
          setProductName('DailyFresh Powder');
          setGtin('8905555444333');
        }
      }
    });
  };

  return (
    <div style={{ maxWidth: '1280px', margin: '0 auto', padding: '24px' }}>
      <DisclaimerBanner />

      {/* Main Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: scanResult ? '1fr 1fr' : '1fr', gap: '24px' }}>
        {/* Upload & Controls Panel */}
        <div className="glass-panel" style={{ padding: '24px' }}>
          <h2 style={{ fontSize: '1.2rem', fontWeight: 700, marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-primary)' }}>
            <Upload size={20} color="var(--color-primary)" /> Check a product package
          </h2>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '20px' }}>
            Upload a clear package image and we'll look for visible declarations and supporting evidence.
          </p>

          {/* Quick Preset Buttons for SIH Demo */}
          <div style={{ marginBottom: '20px' }}>
            <span style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', fontWeight: 600, display: 'block', marginBottom: '8px' }}>
              Try a demo scenario:
            </span>
            <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
              <button
                onClick={() => loadDemoPreset('clean')}
                style={{ padding: '6px 12px', borderRadius: '6px', border: '1px solid var(--border-color)', background: 'transparent', color: 'var(--text-secondary)', fontSize: '0.78rem', fontWeight: 500, cursor: 'pointer', transition: 'all 0.2s' }}
                onMouseOver={(e) => (e.currentTarget.style.background = 'var(--bg-main)')}
                onMouseOut={(e) => (e.currentTarget.style.background = 'transparent')}
              >
                [ Clean Declaration (PASS) ]
              </button>
              <button
                onClick={() => loadDemoPreset('missing_mrp')}
                style={{ padding: '6px 12px', borderRadius: '6px', border: '1px solid var(--border-color)', background: 'transparent', color: 'var(--text-secondary)', fontSize: '0.78rem', fontWeight: 500, cursor: 'pointer', transition: 'all 0.2s' }}
                onMouseOver={(e) => (e.currentTarget.style.background = 'var(--bg-main)')}
                onMouseOut={(e) => (e.currentTarget.style.background = 'transparent')}
              >
                [ Missing MRP (POTENTIAL) ]
              </button>
              <button
                onClick={() => loadDemoPreset('blurry')}
                style={{ padding: '6px 12px', borderRadius: '6px', border: '1px solid var(--border-color)', background: 'transparent', color: 'var(--text-secondary)', fontSize: '0.78rem', fontWeight: 500, cursor: 'pointer', transition: 'all 0.2s' }}
                onMouseOver={(e) => (e.currentTarget.style.background = 'var(--bg-main)')}
                onMouseOut={(e) => (e.currentTarget.style.background = 'transparent')}
              >
                [ Blurry Image (REVIEW) ]
              </button>
              <button
                onClick={() => loadDemoPreset('mismatch')}
                style={{ padding: '6px 12px', borderRadius: '6px', border: '1px solid var(--accent-review)', background: 'transparent', color: 'var(--accent-review)', fontSize: '0.78rem', fontWeight: 600, cursor: 'pointer', transition: 'all 0.2s' }}
                onMouseOver={(e) => (e.currentTarget.style.background = 'rgba(233,185,73,0.08)')}
                onMouseOut={(e) => (e.currentTarget.style.background = 'transparent')}
              >
                [ Identity Mismatch (REVIEW) ]
              </button>
            </div>
          </div>

          {/* File Drag-and-Drop Area */}
          <div
            style={{
              border: '2px dashed var(--border-color)', borderRadius: '12px', padding: '32px', textAlign: 'center',
              background: 'var(--bg-main)', cursor: 'pointer', transition: 'border-color 0.2s'
            }}
            onClick={() => document.getElementById('file-upload-input')?.click()}
            onMouseOver={(e) => (e.currentTarget.style.borderColor = 'var(--color-primary)')}
            onMouseOut={(e) => (e.currentTarget.style.borderColor = 'var(--border-color)')}
          >
            <input
              type="file"
              id="file-upload-input"
              accept="image/*"
              style={{ display: 'none' }}
              onChange={handleFileChange}
            />
            {previewUrl ? (
              <img src={previewUrl} alt="Preview" style={{ maxHeight: '240px', borderRadius: '8px', objectFit: 'contain' }} />
            ) : (
              <div>
                <Upload size={40} color="var(--color-primary)" style={{ marginBottom: '12px', opacity: 0.8 }} />
                <p style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-primary)' }}>Take a photo or choose an image</p>
                <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginTop: '6px' }}>Supports PNG, JPG, JPEG up to 10MB</p>
                
                <div style={{ marginTop: '20px', textAlign: 'left', display: 'inline-block', background: 'var(--bg-card)', padding: '12px 16px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                  <p style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '6px' }}>💡 Photo tips</p>
                  <ul style={{ listStyle: 'none', padding: 0, margin: 0, fontSize: '0.75rem', color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    <li><span style={{ color: 'var(--accent-pass)' }}>✓</span> Good lighting</li>
                    <li><span style={{ color: 'var(--accent-pass)' }}>✓</span> Package clearly visible</li>
                    <li><span style={{ color: 'var(--accent-pass)' }}>✓</span> Text readable</li>
                  </ul>
                </div>
              </div>
            )}
          </div>

          {/* Optional Commodity Metadata Inputs */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginTop: '16px' }}>
            <div>
              <label style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', fontWeight: 600, display: 'block', marginBottom: '4px' }}>Product Name (Optional)</label>
              <input
                type="text"
                placeholder="e.g. Organic Wheat Atta 5kg"
                value={productName}
                onChange={(e) => setProductName(e.target.value)}
                style={{ width: '100%', padding: '8px 12px', borderRadius: '6px', border: '1px solid var(--border-color)', background: 'var(--bg-card)', color: 'var(--text-primary)', fontSize: '0.85rem' }}
              />
            </div>
            <div>
              <label style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', fontWeight: 600, display: 'block', marginBottom: '4px' }}>GTIN / Barcode (Optional)</label>
              <input
                type="text"
                placeholder="e.g. 8901234567890"
                value={gtin}
                onChange={(e) => setGtin(e.target.value)}
                style={{ width: '100%', padding: '8px 12px', borderRadius: '6px', border: '1px solid var(--border-color)', background: 'var(--bg-card)', color: 'var(--text-primary)', fontSize: '0.85rem' }}
              />
            </div>
          </div>

          {/* Action Button */}
          <button
            onClick={handleRunScan}
            disabled={!selectedFile || loading}
            className="btn-primary"
            style={{ width: '100%', marginTop: '20px', padding: '14px', fontSize: '1rem', opacity: !selectedFile || loading ? 0.6 : 1 }}
          >
            <Search size={18} />
            Check this package
          </button>

          {loading && (
            <div style={{ marginTop: '16px', padding: '16px', background: 'var(--color-primary-soft)', borderRadius: '8px', border: '1px solid var(--border-color)', animation: 'pulse 2s infinite' }}>
              <p style={{ fontWeight: 600, color: 'var(--text-primary)', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <RefreshCw className="animate-spin" size={16} color="var(--color-primary)" /> Checking your package
              </p>
              <ul style={{ listStyle: 'none', padding: 0, margin: 0, fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: '1.8' }}>
                <li><span style={{ color: 'var(--accent-pass)', marginRight: '8px', fontWeight: 'bold' }}>✓</span> Image quality</li>
                <li><span style={{ color: 'var(--accent-pass)', marginRight: '8px', fontWeight: 'bold' }}>✓</span> Package detected</li>
                <li><span style={{ color: 'var(--text-muted)', marginRight: '8px', fontWeight: 'bold' }}>◌</span> Reading package information</li>
                <li><span style={{ color: 'var(--text-muted)', marginRight: '8px', fontWeight: 'bold' }}>◌</span> Reviewing available evidence</li>
              </ul>
            </div>
          )}

          {errorMsg && (
            <div style={{ marginTop: '16px', padding: '16px', background: 'rgba(233, 137, 126, 0.1)', border: '1px solid var(--accent-potential)', borderRadius: '8px', color: 'var(--text-primary)' }}>
              <p style={{ fontWeight: 700, color: 'var(--accent-potential)', marginBottom: '4px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <AlertTriangle size={16} /> Something went wrong
              </p>
              <p style={{ fontSize: '0.85rem' }}>{errorMsg === 'Scan processing failed.' ? 'Please try again.' : errorMsg}</p>
            </div>
          )}
        </div>

        {/* Screening Results Panel */}
        {scanResult && (
          <div className="glass-panel" style={{ padding: '24px' }}>
            <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '16px' }}>Screening Result Summary</h3>

            {/* Verdict Card */}
            {scanResult.status === 'PASS_SCREENING' && (
              <div style={{ padding: '16px', background: 'rgba(127, 182, 133, 0.1)', border: '1px solid var(--accent-pass)', borderRadius: '8px', marginBottom: '20px' }}>
                <h4 style={{ color: 'var(--accent-pass)', display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px', fontSize: '1.05rem' }}>
                  <CheckCircle2 size={20} /> Looks good so far
                </h4>
                <p style={{ fontSize: '0.88rem', color: 'var(--text-primary)', fontWeight: 600 }}>PASS_SCREENING</p>
                <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginTop: '2px' }}>No issue detected in the checks performed.</p>
              </div>
            )}
            
            {scanResult.status === 'POTENTIAL_NON_COMPLIANCE' && (
              <div style={{ padding: '16px', background: 'rgba(233, 137, 126, 0.1)', border: '1px solid var(--accent-potential)', borderRadius: '8px', marginBottom: '20px' }}>
                <h4 style={{ color: 'var(--accent-potential)', display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px', fontSize: '1.05rem' }}>
                  <AlertTriangle size={20} /> Something may need attention
                </h4>
                <p style={{ fontSize: '0.88rem', color: 'var(--text-primary)', fontWeight: 600 }}>POTENTIAL_NON_COMPLIANCE</p>
                <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginTop: '2px' }}>Potential non-compliance detected in the visible declarations.</p>
              </div>
            )}

            {scanResult.status === 'NEEDS_REVIEW' && (
              <div style={{ padding: '16px', background: 'rgba(233, 185, 73, 0.1)', border: '1px solid var(--accent-review)', borderRadius: '8px', marginBottom: '20px' }}>
                <h4 style={{ color: 'var(--accent-review)', display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px', fontSize: '1.05rem' }}>
                  <HelpCircle size={20} /> We need a little more information
                </h4>
                <p style={{ fontSize: '0.88rem', color: 'var(--text-primary)', fontWeight: 600 }}>NEEDS_REVIEW</p>
                <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginTop: '2px' }}>More evidence or human review required.</p>
              </div>
            )}

            {/* Scan Performance Metrics Bar */}
            <div style={{ display: 'flex', gap: '16px', padding: '10px 14px', background: 'var(--bg-main)', borderRadius: '8px', marginBottom: '16px', border: '1px solid var(--border-color)', flexWrap: 'wrap' }}>
              {scanResult.processing_time_ms && (
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>⏱ Processed in</span>
                  <span style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>{scanResult.processing_time_ms}ms</span>
                </div>
              )}
              {scanResult.ocr_token_count !== undefined && (
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>🔤 OCR tokens</span>
                  <span style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>{scanResult.ocr_token_count}</span>
                </div>
              )}
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>📋 Fields extracted</span>
                <span style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>{Object.keys(scanResult.extracted_fields || {}).length}</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>⚖️ Rules applied</span>
                <span style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>{scanResult.checks_performed.length}</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>📌 Rule version</span>
                <span style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--color-primary)', fontFamily: 'var(--font-mono)' }}>{scanResult.rule_version}</span>
              </div>
            </div>

            {/* Quality Gate Assessment Card */}
            <div className="glass-card" style={{ padding: '16px', marginBottom: '16px', background: 'var(--color-subtle-bg)', border: '1px solid var(--border-color)', borderRadius: '10px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                <span style={{ fontSize: '0.80rem', color: 'var(--text-secondary)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                  Image Quality Assessment
                </span>
                <span style={{
                  fontSize: '0.78rem',
                  fontWeight: 700,
                  padding: '3px 10px',
                  borderRadius: '20px',
                  background: scanResult.quality.status === 'ACCEPTABLE' ? 'rgba(127, 182, 133, 0.15)' : scanResult.quality.status === 'PARTIALLY_USABLE' ? 'rgba(233, 185, 73, 0.15)' : 'rgba(233, 137, 126, 0.15)',
                  color: scanResult.quality.status === 'ACCEPTABLE' ? 'var(--accent-pass)' : scanResult.quality.status === 'PARTIALLY_USABLE' ? 'var(--accent-review)' : 'var(--accent-potential)',
                  border: `1px solid ${scanResult.quality.status === 'ACCEPTABLE' ? 'var(--accent-pass)' : scanResult.quality.status === 'PARTIALLY_USABLE' ? 'var(--accent-review)' : 'var(--accent-potential)'}`
                }}>
                  {(scanResult.quality as any).quality_label || (scanResult.quality.status === 'ACCEPTABLE' ? 'Good (Clear & Legible)' : scanResult.quality.status === 'PARTIALLY_USABLE' ? 'Fair (Partially Clear)' : 'Poor (Retake Needed)')}
                </span>
              </div>

              {/* User-friendly indicators */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px', textAlign: 'center', padding: '10px 0', borderTop: '1px solid var(--border-color)', borderBottom: '1px solid var(--border-color)' }}>
                <div>
                  <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', display: 'block', marginBottom: '3px' }}>Clarity</span>
                  <span style={{ fontSize: '0.82rem', fontWeight: 600, color: (scanResult.quality?.blur_score ?? 0) >= 80 ? 'var(--accent-pass)' : 'var(--accent-potential)' }}>
                    {(scanResult.quality?.blur_score ?? 0) >= 80 ? '✓ Sharp' : '⚠ Blurry'}
                  </span>
                </div>
                <div>
                  <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', display: 'block', marginBottom: '3px' }}>Lighting</span>
                  <span style={{ fontSize: '0.82rem', fontWeight: 600, color: ((scanResult.quality?.brightness_score ?? 0) >= 0.10 && (scanResult.quality?.brightness_score ?? 0) <= 0.90) ? 'var(--accent-pass)' : 'var(--accent-review)' }}>
                    {((scanResult.quality?.brightness_score ?? 0) >= 0.10 && (scanResult.quality?.brightness_score ?? 0) <= 0.90) ? '✓ Balanced' : 'Check Lighting'}
                  </span>
                </div>
                <div>
                  <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', display: 'block', marginBottom: '3px' }}>Reflections</span>
                  <span style={{ fontSize: '0.82rem', fontWeight: 600, color: (scanResult.quality?.glare_ratio ?? 0) <= 0.15 ? 'var(--accent-pass)' : 'var(--accent-potential)' }}>
                    {(scanResult.quality?.glare_ratio ?? 0) <= 0.15 ? '✓ Low glare' : '⚠ Glare detected'}
                  </span>
                </div>
              </div>

              {/* Technical Diagnostics Collapsible */}
              <details style={{ marginTop: '10px', fontSize: '0.75rem', color: 'var(--text-secondary)', cursor: 'pointer' }}>
                <summary style={{ fontWeight: 600, outline: 'none' }}>View technical diagnostic metrics</summary>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '8px', marginTop: '8px', padding: '8px', background: 'var(--bg-main)', borderRadius: '6px', textAlign: 'center' }}>
                  <div>
                    <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)', display: 'block' }}>Blur Score</span>
                    <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{scanResult.quality.blur_score}</span>
                  </div>
                  <div>
                    <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)', display: 'block' }}>Brightness</span>
                    <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{scanResult.quality.brightness_score}</span>
                  </div>
                  <div>
                    <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)', display: 'block' }}>Glare Ratio</span>
                    <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{scanResult.quality.glare_ratio}</span>
                  </div>
                  <div>
                    <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)', display: 'block' }}>Resolution</span>
                    <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{scanResult.quality.width && scanResult.quality.height ? `${scanResult.quality.width}x${scanResult.quality.height}` : '600x600'}</span>
                  </div>
                </div>
              </details>
            </div>

            {/* Checks Performed List */}
            <h4 style={{ fontSize: '0.88rem', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '10px', textTransform: 'uppercase' }}>
              Statutory Declarations Checklist ({scanResult.rule_version})
            </h4>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginBottom: '20px' }}>
              {scanResult.checks_performed.map((chk: any, idx: number) => (
                <div key={idx} style={{ padding: '10px 12px', borderRadius: '6px', background: 'var(--color-subtle-bg)', border: '1px solid var(--border-color)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <div style={{ flex: 1 }}>
                      <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-primary)' }}>{chk.rule_name || chk.rule_id}</span>
                      {chk.rule_id && <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)', marginLeft: '8px', fontFamily: 'var(--font-mono)' }}>{chk.rule_id}</span>}
                      <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '2px' }}>{chk.reason}</p>
                      {(chk as any).legal_reference && (
                        <p style={{ fontSize: '0.68rem', color: 'var(--accent-cyan)', marginTop: '3px', fontStyle: 'italic' }}>§ {(chk as any).legal_reference}</p>
                      )}
                    </div>
                    <span style={{
                      fontSize: '0.72rem', fontWeight: 700, whiteSpace: 'nowrap', marginLeft: '12px',
                      padding: '3px 8px', borderRadius: '12px',
                      background: chk.status === 'PASS' ? 'rgba(127,182,133,0.15)' : chk.status === 'POTENTIAL_NON_COMPLIANCE' ? 'rgba(233,137,126,0.15)' : 'rgba(233,185,73,0.15)',
                      color: chk.status === 'PASS' ? 'var(--accent-pass)' : chk.status === 'POTENTIAL_NON_COMPLIANCE' ? 'var(--accent-potential)' : 'var(--accent-review)'
                    }}>
                      {chk.status === 'PASS' ? '✓ PASS' : chk.status === 'POTENTIAL_NON_COMPLIANCE' ? '⚠ FLAG' : '? REVIEW'}
                    </span>
                  </div>
                </div>
              ))}
            </div>

            {/* Identity Warnings — shown prominently above review reasons */}
            {scanResult.identity_warnings && scanResult.identity_warnings.length > 0 && (
              <div style={{ padding: '14px', background: 'rgba(233, 185, 73, 0.12)', border: '2px solid var(--accent-review)', borderRadius: '10px', marginBottom: '16px' }}>
                {scanResult.identity_warnings.map((w: any, i: number) => (
                  <div key={i} style={{ marginBottom: i < scanResult.identity_warnings.length - 1 ? '12px' : 0 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                      <AlertTriangle size={16} color="var(--accent-review)" />
                      <span style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--accent-review)' }}>
                        {w.type === 'PRODUCT_IDENTITY_MISMATCH' ? '⚠ Product Identity Mismatch' : '⚠ GTIN Consistency Warning'}
                      </span>
                    </div>
                    {w.type === 'PRODUCT_IDENTITY_MISMATCH' && (
                      <div style={{ fontSize: '0.8rem', color: 'var(--text-primary)', paddingLeft: '24px' }}>
                        <div><span style={{ color: 'var(--text-secondary)' }}>You entered:</span> <strong>{w.user_provided}</strong></div>
                        <div><span style={{ color: 'var(--text-secondary)' }}>Image evidence:</span> <strong>{w.image_evidence}</strong></div>
                        <div style={{ marginTop: '6px', fontSize: '0.76rem', color: 'var(--text-secondary)' }}>{w.explanation}</div>
                      </div>
                    )}
                    {w.type === 'GTIN_CONSISTENCY_WARNING' && (
                      <div style={{ fontSize: '0.8rem', color: 'var(--text-primary)', paddingLeft: '24px' }}>
                        {w.user_provided && <div><span style={{ color: 'var(--text-secondary)' }}>User GTIN:</span> <strong>{w.user_provided}</strong></div>}
                        {w.ocr_value && <div><span style={{ color: 'var(--text-secondary)' }}>OCR barcode:</span> <strong>{w.ocr_value}</strong></div>}
                        {w.barcode_decoded && <div><span style={{ color: 'var(--text-secondary)' }}>Decoded barcode:</span> <strong>{w.barcode_decoded}</strong></div>}
                        <div style={{ marginTop: '6px', fontSize: '0.76rem', color: 'var(--text-secondary)' }}>{w.explanation}</div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}

            {/* Review Reasons if applicable */}
            {scanResult.review_reasons.length > 0 && (
              <div style={{ padding: '12px', background: 'rgba(233, 185, 73, 0.1)', border: '1px solid rgba(233, 185, 73, 0.25)', borderRadius: '8px', marginBottom: '16px' }}>
                <span style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--accent-review)', display: 'block', marginBottom: '4px' }}>Review Factors Identified:</span>
                <ul style={{ paddingLeft: '16px', fontSize: '0.78rem', color: 'var(--text-primary)' }}>
                  {scanResult.review_reasons.map((r: any, i: number) => <li key={i}>{r}</li>)}
                </ul>
              </div>
            )}

            {/* Decision Trace — collapsible */}
            {scanResult.decision_trace && scanResult.decision_trace.length > 0 && (
              <details style={{ marginBottom: '16px', fontSize: '0.78rem' }}>
                <summary style={{ cursor: 'pointer', fontWeight: 700, color: 'var(--text-secondary)', padding: '8px 0', outline: 'none', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <Search size={14} /> View Decision Trace
                </summary>
                <div style={{ marginTop: '8px', border: '1px solid var(--border-color)', borderRadius: '8px', overflow: 'hidden' }}>
                  {scanResult.decision_trace.map((step, idx) => (
                    <div key={idx} style={{
                      display: 'flex', alignItems: 'flex-start', gap: '10px', padding: '8px 12px',
                      background: idx % 2 === 0 ? 'var(--bg-main)' : 'var(--bg-card)',
                      borderBottom: idx < scanResult.decision_trace.length - 1 ? '1px solid var(--border-color)' : 'none'
                    }}>
                      <span style={{
                        fontSize: '0.7rem', fontWeight: 700, padding: '2px 6px', borderRadius: '4px', whiteSpace: 'nowrap',
                        background: step.status === 'OK' || step.status === 'CONSISTENT' || step.status === 'PASS_SCREENING' ? 'rgba(127,182,133,0.15)' :
                          step.status?.includes('MISMATCH') || step.status === 'POTENTIAL_NON_COMPLIANCE' ? 'rgba(233,137,126,0.15)' : 'rgba(233,185,73,0.15)',
                        color: step.status === 'OK' || step.status === 'CONSISTENT' || step.status === 'PASS_SCREENING' ? 'var(--accent-pass)' :
                          step.status?.includes('MISMATCH') || step.status === 'POTENTIAL_NON_COMPLIANCE' ? 'var(--accent-potential)' : 'var(--accent-review)'
                      }}>{step.status}</span>
                      <div>
                        <span style={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: '0.78rem' }}>{step.stage}</span>
                        {step.detail && <span style={{ color: 'var(--text-secondary)', marginLeft: '6px' }}>{step.detail}</span>}
                      </div>
                    </div>
                  ))}
                </div>
              </details>
            )}

            {/* Officer Action — Investigate Product Workspace */}
            {userRole === 'OFFICER' && onInvestigate && (
              <button
                onClick={() => onInvestigate(scanResult.product_id, scanResult.scan_id)}
                style={{
                  width: '100%', padding: '10px 16px', marginTop: '12px',
                  display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px',
                  background: 'var(--color-primary)', border: 'none',
                  borderRadius: '8px', color: '#ffffff',
                  fontWeight: 700, fontSize: '0.88rem', cursor: 'pointer',
                  transition: 'all 0.2s ease'
                }}
                onMouseOver={e => { (e.currentTarget as HTMLElement).style.opacity = '0.9'; }}
                onMouseOut={e => { (e.currentTarget as HTMLElement).style.opacity = '1'; }}
              >
                <Microscope size={16} />
                Investigate This Product
              </button>
            )}

            {/* Citizen Action — Request / Report an Issue */}
            {userRole === 'CITIZEN' && onFileSignal && scanResult.status !== 'PASS_SCREENING' && (
              <button
                onClick={() => onFileSignal(scanResult)}
                style={{
                  width: '100%', padding: '10px 16px', marginTop: '12px',
                  display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px',
                  background: 'var(--color-primary)', border: 'none',
                  borderRadius: '8px', color: '#ffffff',
                  fontWeight: 700, fontSize: '0.88rem', cursor: 'pointer',
                  transition: 'all 0.2s ease'
                }}
              >
                <MessageSquare size={16} />
                Request / Report an Issue (File Citizen Signal)
              </button>
            )}

            {/* Report a Concern link — active navigation to Citizen tab */}
            {scanResult.status !== 'PASS_SCREENING' && (
              <div style={{ marginTop: '12px', padding: '12px 14px', background: 'rgba(42,157,143,0.06)', border: '1px dashed var(--color-primary)', borderRadius: '8px' }}>
                <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginBottom: '6px' }}>
                  <strong style={{ color: 'var(--text-primary)' }}>Did you notice something concerning?</strong> Citizen signals are unverified observations, not legal complaints.
                </div>
                <button
                  type="button"
                  onClick={() => {
                    if (onFileSignal) {
                      onFileSignal(scanResult);
                    }
                  }}
                  style={{
                    background: 'transparent', border: 'none',
                    fontSize: '0.78rem', fontWeight: 700, color: 'var(--color-primary)',
                    cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: '4px',
                    padding: 0, marginTop: '2px', textDecoration: 'underline'
                  }}
                >
                  → File a Citizen Signal in the Citizen tab
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Interactive Evidence Canvas Section */}
      {scanResult && previewUrl && (
        <div style={{ marginTop: '24px' }}>
          <h3 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-primary)' }}>
            <FileCode size={20} color="var(--color-primary)" /> What we found on the package
          </h3>
          <EvidenceOverlay
            imageSrc={previewUrl}
            ocrTokens={scanResult.ocr_tokens}
            extractedFields={scanResult.extracted_fields}
            imageHash={scanResult.image_hash}
          />
        </div>
      )}
    </div>
  );
};
