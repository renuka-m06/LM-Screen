import React, { useState, useEffect } from 'react';
import { submitCitizenReport } from '../api';
import { MessageSquare, Send, CheckCircle2, AlertCircle, Link as LinkIcon } from 'lucide-react';

interface CitizenPortalProps {
  prefillContext?: {
    related_scan_id?: string;
    product_name?: string;
    gtin?: string;
    issue_category?: string;
    description?: string;
  } | null;
}

export const CitizenPortal: React.FC<CitizenPortalProps> = ({ prefillContext }) => {
  const [productName, setProductName] = useState('');
  const [gtin, setGtin] = useState('');
  const [issueCategory, setIssueCategory] = useState('Information Mismatch');
  const [description, setDescription] = useState('');
  const [locationCity, setLocationCity] = useState('Delhi');
  const [submitting, setSubmitting] = useState(false);
  const [submittedResponse, setSubmittedResponse] = useState<{ report_id: string; message: string } | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    if (prefillContext) {
      if (prefillContext.product_name) setProductName(prefillContext.product_name);
      if (prefillContext.gtin) setGtin(prefillContext.gtin);
      if (prefillContext.issue_category) setIssueCategory(prefillContext.issue_category);
      if (prefillContext.description) setDescription(prefillContext.description);
    }
  }, [prefillContext]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setErrorMsg(null);
    setSubmittedResponse(null);

    try {
      const res = await submitCitizenReport({
        gtin: gtin || undefined,
        product_name: productName || undefined,
        issue_category: issueCategory,
        description,
        location_city: locationCity,
        scan_id: prefillContext?.related_scan_id
      });
      setSubmittedResponse(res);
      // Reset description
      setDescription('');
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to submit report.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={{ maxWidth: '800px', margin: '0 auto', padding: '24px' }}>
      <div className="glass-panel" style={{ padding: '24px' }}>
        <h2 style={{ fontSize: '1.2rem', fontWeight: 700, marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-primary)' }}>
          <MessageSquare size={20} color="var(--color-primary)" /> Report something you noticed
        </h2>
        <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '20px' }}>
          Tell us what you noticed on a product package. Your report can help officers identify products that may need a closer look.
        </p>

        {/* Related Scan Context Indicator */}
        {prefillContext?.related_scan_id && (
          <div style={{ marginTop: '12px', padding: '10px 14px', borderRadius: '8px', background: 'rgba(42,157,143,0.08)', border: '1px solid var(--color-primary)', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.82rem', color: 'var(--color-primary)', fontWeight: 600 }}>
            <LinkIcon size={16} /> Related Scan Evidence Attached: <span style={{ fontFamily: 'var(--font-mono)' }}>#{prefillContext.related_scan_id.slice(-8)}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ marginTop: '24px', display: 'flex', flexDirection: 'column', gap: '24px' }}>
          <div>
            <label style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', fontWeight: 600, display: 'block', marginBottom: '6px' }}>
              Issue Category *
            </label>
            <select
              value={issueCategory}
              onChange={(e) => setIssueCategory(e.target.value)}
              style={{ width: '100%', padding: '10px 14px', borderRadius: '8px', border: '1px solid var(--border-color)', background: 'var(--bg-card)', color: 'var(--text-primary)', fontSize: '0.9rem' }}
            >
              <option value="Suspicious MRP">Suspicious MRP (Overpricing / Sticker Overwrite)</option>
              <option value="Label Tampering">Label Tampering / Altered Expiry</option>
              <option value="Missing Information">Missing Information (Missing MRP / Net Qty / MFD)</option>
              <option value="Quantity Concern">Quantity Concern (Perceived Short Weight/Volume)</option>
              <option value="Information Mismatch">Information Mismatch (GTIN vs Package Label)</option>
              <option value="Other">Other Packaged Commodity Concern</option>
            </select>
          </div>

          <div className="grid-responsive" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
            <div>
              <label style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', fontWeight: 600, display: 'block', marginBottom: '6px' }}>Product Brand / Name</label>
              <input
                type="text"
                placeholder="e.g. ChocoDelight Dark Chocolate"
                value={productName}
                onChange={(e) => setProductName(e.target.value)}
                style={{ width: '100%', padding: '10px 14px', borderRadius: '8px', border: '1px solid var(--border-color)', background: 'var(--bg-card)', color: 'var(--text-primary)', fontSize: '0.9rem' }}
              />
            </div>
            <div>
              <label style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', fontWeight: 600, display: 'block', marginBottom: '6px' }}>Barcode / GTIN (Optional)</label>
              <input
                type="text"
                placeholder="e.g. 8909876543210"
                value={gtin}
                onChange={(e) => setGtin(e.target.value)}
                style={{ width: '100%', padding: '10px 14px', borderRadius: '8px', border: '1px solid var(--border-color)', background: 'var(--bg-card)', color: 'var(--text-primary)', fontSize: '0.9rem' }}
              />
            </div>
          </div>

          <div>
            <label style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', fontWeight: 600, display: 'block', marginBottom: '6px' }}>City / Location</label>
            <input
              type="text"
              placeholder="e.g. Mumbai, Maharashtra"
              value={locationCity}
              onChange={(e) => setLocationCity(e.target.value)}
              style={{ width: '100%', padding: '10px 14px', borderRadius: '8px', border: '1px solid var(--border-color)', background: 'var(--bg-card)', color: 'var(--text-primary)', fontSize: '0.9rem' }}
            />
          </div>

          <div>
            <label style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', fontWeight: 600, display: 'block', marginBottom: '6px' }}>Observed Details / Description</label>
            <textarea
              rows={4}
              placeholder="Describe the visible declaration concern observed on the retail package..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              style={{ width: '100%', padding: '10px 14px', borderRadius: '8px', border: '1px solid var(--border-color)', background: 'var(--bg-card)', color: 'var(--text-primary)', fontSize: '0.9rem', resize: 'vertical' }}
            />
          </div>

          <button
            type="submit"
            disabled={submitting}
            className="btn-primary"
            style={{ padding: '14px', fontSize: '1rem', marginTop: '8px' }}
          >
            <Send size={18} /> {submitting ? 'Submitting report...' : 'Submit report for officer review'}
          </button>
        </form>

        {submittedResponse && (
          <div style={{ marginTop: '20px', padding: '16px', background: 'rgba(127, 182, 133, 0.15)', border: '1px solid rgba(127, 182, 133, 0.3)', borderRadius: '8px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--accent-pass)', fontWeight: 700, marginBottom: '6px' }}>
              <CheckCircle2 size={18} /> Signal Registered Successfully (ID: {submittedResponse.report_id.slice(0, 8)})
            </div>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-primary)' }}>{submittedResponse.message}</p>
          </div>
        )}

        {errorMsg && (
          <div style={{ marginTop: '20px', padding: '16px', background: 'rgba(233, 137, 126, 0.15)', border: '1px solid rgba(233, 137, 126, 0.3)', borderRadius: '8px', color: 'var(--accent-potential)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 700 }}>
              <AlertCircle size={18} /> {errorMsg}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
