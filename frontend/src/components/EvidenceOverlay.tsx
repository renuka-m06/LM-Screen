import React, { useState } from 'react';
import type { OCRToken } from '../types';
import { Eye } from 'lucide-react';
import { formatFieldValue } from '../utils';

interface EvidenceOverlayProps {
  imageSrc: string;
  ocrTokens: OCRToken[];
  extractedFields: any[]; // API returns array, not a keyed dict
  imageHash?: string;
}

export const EvidenceOverlay: React.FC<EvidenceOverlayProps> = ({ imageSrc, ocrTokens, extractedFields, imageHash }) => {
  const [selectedToken, setSelectedToken] = useState<OCRToken | null>(null);

  return (
    <div className="grid-responsive" style={{ display: 'grid', gridTemplateColumns: '1fr 360px', gap: '24px', alignItems: 'start' }}>
      {/* SVG Image Canvas */}
      <div className="glass-panel" style={{ padding: '16px', position: 'relative', overflow: 'hidden', textAlign: 'center' }}>
        <div style={{ position: 'relative', display: 'inline-block', maxWidth: '100%' }}>
          <img
            src={imageSrc}
            alt="Screening Evidence"
            style={{ maxWidth: '100%', height: 'auto', borderRadius: '8px', display: 'block' }}
          />

          {/* SVG Bounding Boxes Overlay */}
          <svg
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              width: '100%',
              height: '100%',
              pointerEvents: 'auto'
            }}
          >
            {ocrTokens.map((tok) => {
              if (!tok.polygon || tok.polygon.length < 4) return null;
              const pointsStr = tok.polygon.map((p) => `${p[0]},${p[1]}`).join(' ');
              const isSelected = selectedToken?.id === tok.id;

              return (
                <polygon
                  key={tok.id}
                  points={pointsStr}
                  fill={isSelected ? 'rgba(42, 157, 143, 0.35)' : 'rgba(42, 157, 143, 0.12)'}
                  stroke={isSelected ? 'var(--color-primary)' : 'rgba(42, 157, 143, 0.5)'}
                  strokeWidth={isSelected ? 3 : 1.5}
                  style={{ cursor: 'pointer', transition: 'all 0.2s ease' }}
                  onClick={() => setSelectedToken(tok)}
                >
                  <title>{`${tok.text} (Conf: ${(tok.confidence * 100).toFixed(0)}%)`}</title>
                </polygon>
              );
            })}
          </svg>
        </div>
      </div>

      {/* Evidence Side Panel */}
      <div className="glass-panel" style={{ padding: '16px' }}>
        <h3 style={{ fontSize: '1.05rem', fontWeight: 700, marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-primary)' }}>
          <Eye size={18} color="var(--color-primary)" /> Evidence Provenance
        </h3>

        {imageHash && (
          <div style={{ marginBottom: '16px', padding: '10px 12px', borderRadius: '8px', background: 'var(--color-subtle-bg)', border: '1px solid var(--border-color)', fontSize: '0.75rem' }}>
            <div style={{ fontWeight: 700, color: 'var(--text-primary)', marginBottom: '4px' }}>SHA-256 Digital Fingerprint</div>
            <div style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)', wordBreak: 'break-all' }}>
              {imageHash}
            </div>
          </div>
        )}

        {/* Tab Header */}
        <div style={{ display: 'flex', gap: '6px', marginBottom: '14px', borderBottom: '1px solid var(--border-color)', paddingBottom: '8px' }}>
          <span style={{ color: 'var(--color-primary)', fontWeight: 600, fontSize: '0.82rem', borderBottom: '2px solid var(--color-primary)', paddingBottom: '6px' }}>
            Extracted Statutory Fields
          </span>
        </div>

        {/* Fields List */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', maxHeight: '420px', overflowY: 'auto' }}>
          {(extractedFields ?? []).filter((f: any) => f?.type !== 'DETECTION' && (f?.field || f?.field_name)).map((field: any, idx: number) => {
            const rawVal = formatFieldValue(field.raw_text ?? field.raw_value);
            const methodVal = formatFieldValue(field.method ?? field.extraction_method);
            return (
              <div
                key={field.field ?? field.field_name ?? idx}
                className="glass-card"
                style={{ padding: '10px 12px', borderLeft: '3px solid var(--color-primary)' }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                  <span style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase' }}>
                    {String(field.field ?? field.field_name ?? 'unknown').replace(/_/g, ' ')}
                  </span>
                  <span style={{ fontSize: '0.72rem', color: 'var(--accent-pass)', fontWeight: 600 }}>
                    {typeof field.confidence === 'number' ? `${(field.confidence * 100).toFixed(0)}% Conf` : ''}
                  </span>
                </div>
                <div style={{ fontSize: '0.92rem', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '2px', wordBreak: 'break-word' }}>
                  {formatFieldValue(field.value ?? field.normalized_value)}
                </div>
                {rawVal !== '—' && rawVal !== '' && (
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontFamily: 'monospace', wordBreak: 'break-word' }}>
                    Raw: "{rawVal}"
                  </div>
                )}
                <div style={{ fontSize: '0.70rem', color: 'var(--color-primary)', marginTop: '4px', fontStyle: 'italic' }}>
                  Method: {methodVal === '—' ? 'OCR' : methodVal}
                </div>
              </div>
            );
          })}

          {(extractedFields ?? []).filter((f: any) => f?.type !== 'DETECTION' && (f?.field || f?.field_name)).length === 0 && (
            <div style={{ textAlign: 'center', color: 'var(--text-secondary)', padding: '32px 20px', fontSize: '0.9rem', background: 'var(--bg-main)', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
              <Eye size={24} style={{ margin: '0 auto 12px', opacity: 0.5 }} />
              We couldn't find enough reliable evidence in this image.
            </div>
          )}
        </div>

        {/* Selected Token Inspector */}
        {selectedToken && (
          <div style={{ marginTop: '16px', padding: '10px', background: 'var(--color-primary-soft)', border: '1px solid var(--color-primary)', borderRadius: '8px' }}>
            <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--color-primary)', marginBottom: '2px' }}>
              Selected OCR Token
            </div>
            <div style={{ fontSize: '0.9rem', color: 'var(--text-primary)', fontWeight: 600 }}>
              "{selectedToken.text}"
            </div>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
              Confidence: {(selectedToken.confidence * 100).toFixed(1)}% • Model: {selectedToken.model_version || 'PaddleOCR'}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
