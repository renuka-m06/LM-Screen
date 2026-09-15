import React, { useState, useEffect } from 'react';
import { submitCitizenReport } from '../api';
import {
  MessageSquare, Send, CheckCircle2, AlertCircle,
  Link as LinkIcon, AlertTriangle,
} from 'lucide-react';

// â”€â”€ Types â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

interface CitizenPortalProps {
  prefillContext?: {
    related_scan_id?: string;
    product_name?: string;
    gtin?: string;
    issue_category?: string;
    description?: string;
    /** Per-field skip reasons emitted by the confidence guard in App.tsx */
    skipped_fields?: Record<string, string>;
  } | null;
}

// â”€â”€ Helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

/**
 * Renders an amber inline note beneath a form field that was intentionally
 * left blank because the scan's OCR confidence was too low to trust the value.
 */
const FieldNote: React.FC<{ reason: string }> = ({ reason }) => (
  <div
    id="field-skip-note"
    style={{
      marginTop: '5px',
      display: 'flex',
      alignItems: 'flex-start',
      gap: '6px',
      padding: '7px 10px',
      borderRadius: '6px',
      background: 'rgba(255, 190, 60, 0.10)',
      border: '1px solid rgba(255, 190, 60, 0.30)',
      fontSize: '0.78rem',
      color: 'var(--text-secondary)',
      lineHeight: 1.4,
    }}
    role="note"
    aria-live="polite"
  >
    <AlertTriangle
      size={13}
      style={{ marginTop: '1px', flexShrink: 0, color: '#f5a623' }}
    />
    <span>
      <strong style={{ color: '#f5a623', fontWeight: 700 }}>
        Couldn&apos;t confidently read this
      </strong>{' '}
      â€” {reason}. Please fill in manually.
    </span>
  </div>
);

// â”€â”€ Component â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

export const CitizenPortal: React.FC<CitizenPortalProps> = ({ prefillContext }) => {
  const [productName, setProductName]     = useState('');
  const [gtin, setGtin]                   = useState('');
  const [issueCategory, setIssueCategory] = useState('Information Mismatch');
  const [description, setDescription]     = useState('');
  const [locationCity, setLocationCity]   = useState('Delhi');
  const [submitting, setSubmitting]       = useState(false);
  const [submittedResponse, setSubmittedResponse] = useState<{
    report_id: string;
    message: string;
  } | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Track which fields were intentionally left blank and why.
  const [skippedFields, setSkippedFields] = useState<Record<string, string>>({});

  useEffect(() => {
    if (prefillContext) {
      // Only set state values that passed the confidence guard in App.tsx.
      // Fields absent from prefillContext (undefined) stay blank.
      setProductName(prefillContext.product_name ?? '');
      setGtin(prefillContext.gtin ?? '');
      if (prefillContext.issue_category) setIssueCategory(prefillContext.issue_category);
      if (prefillContext.description) setDescription(prefillContext.description);
      setSkippedFields(prefillContext.skipped_fields ?? {});
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
        scan_id: prefillContext?.related_scan_id,
      });
      setSubmittedResponse(res);
      setDescription('');
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : 'Failed to submit report.';
      setErrorMsg(msg);
    } finally {
      setSubmitting(false);
    }
  };

  // Derived: are any fields currently blank due to a skip?
  const hasSkips = Object.keys(skippedFields).length > 0;

  return (
    <div style={{ maxWidth: '800px', margin: '0 auto', padding: '24px' }}>
      <div className="glass-panel" style={{ padding: '24px' }}>
        <h2
          style={{
            fontSize: '1.2rem',
            fontWeight: 700,
            marginBottom: '8px',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            color: 'var(--text-primary)',
          }}
        >
          <MessageSquare size={20} color="var(--color-primary)" />
          Report something you noticed
        </h2>
        <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '20px' }}>
          Tell us what you noticed on a product package. Your report can help officers
          identify products that may need a closer look.
        </p>

        {/* Related Scan Context Indicator */}
        {prefillContext?.related_scan_id && (
          <div
            style={{
              marginTop: '12px',
              padding: '10px 14px',
              borderRadius: '8px',
              background: 'rgba(42,157,143,0.08)',
              border: '1px solid var(--color-primary)',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              fontSize: '0.82rem',
              color: 'var(--color-primary)',
              fontWeight: 600,
            }}
          >
            <LinkIcon size={16} />
            Related Scan Evidence Attached:{' '}
            <span style={{ fontFamily: 'var(--font-mono)' }}>
              #{prefillContext.related_scan_id.slice(-8)}
            </span>
          </div>
        )}

        {/* Scan-quality advisory banner â€” shown when â‰¥1 field was skipped */}
        {hasSkips && (
          <div
            id="prefill-quality-advisory"
            style={{
              marginTop: '14px',
              padding: '11px 14px',
              borderRadius: '8px',
              background: 'rgba(255, 190, 60, 0.08)',
              border: '1px solid rgba(255, 190, 60, 0.35)',
              display: 'flex',
              alignItems: 'flex-start',
              gap: '10px',
              fontSize: '0.82rem',
              color: 'var(--text-secondary)',
              lineHeight: 1.5,
            }}
            role="status"
            aria-live="polite"
          >
            <AlertTriangle size={16} style={{ marginTop: '1px', flexShrink: 0, color: '#f5a623' }} />
            <span>
              <strong style={{ color: '#f5a623' }}>
                Some fields couldn&apos;t be pre-filled from the scan
              </strong>{' '}
              â€” the OCR confidence was too low for those values to be reliable. Fields
              marked below are left blank for you to fill in manually. All other fields
              have been prefilled from high-confidence scan data.
            </span>
          </div>
        )}

        <form
          onSubmit={handleSubmit}
          style={{ marginTop: '24px', display: 'flex', flexDirection: 'column', gap: '24px' }}
        >
          {/* Issue Category */}
          <div>
            <label
              htmlFor="issue-category-select"
              style={{
                fontSize: '0.82rem',
                color: 'var(--text-secondary)',
                fontWeight: 600,
                display: 'block',
                marginBottom: '6px',
              }}
            >
              Issue Category *
            </label>
            <select
              id="issue-category-select"
              value={issueCategory}
              onChange={(e) => setIssueCategory(e.target.value)}
              style={{
                width: '100%',
                padding: '10px 14px',
                borderRadius: '8px',
                border: '1px solid var(--border-color)',
                background: 'var(--bg-card)',
                color: 'var(--text-primary)',
                fontSize: '0.9rem',
              }}
            >
              <option value="Suspicious MRP">Suspicious MRP (Overpricing / Sticker Overwrite)</option>
              <option value="Label Tampering">Label Tampering / Altered Expiry</option>
              <option value="Missing Information">Missing Information (Missing MRP / Net Qty / MFD)</option>
              <option value="Quantity Concern">Quantity Concern (Perceived Short Weight/Volume)</option>
              <option value="Information Mismatch">Information Mismatch (GTIN vs Package Label)</option>
              <option value="Other">Other Packaged Commodity Concern</option>
            </select>
          </div>

          {/* Product Brand / Name + Barcode row */}
          <div
            className="grid-responsive"
            style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}
          >
            {/* Product Name */}
            <div>
              <label
                htmlFor="product-name-input"
                style={{
                  fontSize: '0.82rem',
                  color: 'var(--text-secondary)',
                  fontWeight: 600,
                  display: 'block',
                  marginBottom: '6px',
                }}
              >
                Product Brand / Name
              </label>
              <input
                id="product-name-input"
                type="text"
                placeholder={
                  skippedFields['product_name']
                    ? 'Enter product name manuallyâ€¦'
                    : 'e.g. ChocoDelight Dark Chocolate'
                }
                value={productName}
                onChange={(e) => {
                  setProductName(e.target.value);
                  // Dismiss skip note as soon as the citizen starts typing
                  if (skippedFields['product_name']) {
                    setSkippedFields((prev) => {
                      const next = { ...prev };
                      delete next['product_name'];
                      return next;
                    });
                  }
                }}
                style={{
                  width: '100%',
                  padding: '10px 14px',
                  borderRadius: '8px',
                  border: skippedFields['product_name']
                    ? '1px solid rgba(255, 190, 60, 0.55)'
                    : '1px solid var(--border-color)',
                  background: 'var(--bg-card)',
                  color: 'var(--text-primary)',
                  fontSize: '0.9rem',
                }}
              />
              {skippedFields['product_name'] && (
                <FieldNote reason={skippedFields['product_name']} />
              )}
            </div>

            {/* Barcode / GTIN */}
            <div>
              <label
                htmlFor="gtin-input"
                style={{
                  fontSize: '0.82rem',
                  color: 'var(--text-secondary)',
                  fontWeight: 600,
                  display: 'block',
                  marginBottom: '6px',
                }}
              >
                Barcode / GTIN (Optional)
              </label>
              <input
                id="gtin-input"
                type="text"
                placeholder={
                  skippedFields['gtin']
                    ? 'Enter barcode manuallyâ€¦'
                    : 'e.g. 8909876543210'
                }
                value={gtin}
                onChange={(e) => {
                  setGtin(e.target.value);
                  if (skippedFields['gtin']) {
                    setSkippedFields((prev) => {
                      const next = { ...prev };
                      delete next['gtin'];
                      return next;
                    });
                  }
                }}
                style={{
                  width: '100%',
                  padding: '10px 14px',
                  borderRadius: '8px',
                  border: skippedFields['gtin']
                    ? '1px solid rgba(255, 190, 60, 0.55)'
                    : '1px solid var(--border-color)',
                  background: 'var(--bg-card)',
                  color: 'var(--text-primary)',
                  fontSize: '0.9rem',
                }}
              />
              {skippedFields['gtin'] && (
                <FieldNote reason={skippedFields['gtin']} />
              )}
            </div>
          </div>

          {/* City / Location */}
          <div>
            <label
              htmlFor="location-city-input"
              style={{
                fontSize: '0.82rem',
                color: 'var(--text-secondary)',
                fontWeight: 600,
                display: 'block',
                marginBottom: '6px',
              }}
            >
              City / Location
            </label>
            <input
              id="location-city-input"
              type="text"
              placeholder="e.g. Mumbai, Maharashtra"
              value={locationCity}
              onChange={(e) => setLocationCity(e.target.value)}
              style={{
                width: '100%',
                padding: '10px 14px',
                borderRadius: '8px',
                border: '1px solid var(--border-color)',
                background: 'var(--bg-card)',
                color: 'var(--text-primary)',
                fontSize: '0.9rem',
              }}
            />
          </div>

          {/* Description */}
          <div>
            <label
              htmlFor="description-textarea"
              style={{
                fontSize: '0.82rem',
                color: 'var(--text-secondary)',
                fontWeight: 600,
                display: 'block',
                marginBottom: '6px',
              }}
            >
              Observed Details / Description
            </label>
            <textarea
              id="description-textarea"
              rows={4}
              placeholder="Describe the visible declaration concern observed on the retail package..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              style={{
                width: '100%',
                padding: '10px 14px',
                borderRadius: '8px',
                border: '1px solid var(--border-color)',
                background: 'var(--bg-card)',
                color: 'var(--text-primary)',
                fontSize: '0.9rem',
                resize: 'vertical',
              }}
            />
          </div>

          <button
            type="submit"
            id="citizen-report-submit-btn"
            disabled={submitting}
            className="btn-primary"
            style={{ padding: '14px', fontSize: '1rem', marginTop: '8px' }}
          >
            <Send size={18} />{' '}
            {submitting ? 'Submitting report...' : 'Submit report for officer review'}
          </button>
        </form>

        {/* Success */}
        {submittedResponse && (
          <div
            style={{
              marginTop: '20px',
              padding: '16px',
              background: 'rgba(127, 182, 133, 0.15)',
              border: '1px solid rgba(127, 182, 133, 0.3)',
              borderRadius: '8px',
            }}
          >
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                color: 'var(--accent-pass)',
                fontWeight: 700,
                marginBottom: '6px',
              }}
            >
              <CheckCircle2 size={18} />
              Signal Registered Successfully (ID: {submittedResponse.report_id.slice(0, 8)})
            </div>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-primary)' }}>
              {submittedResponse.message}
            </p>
          </div>
        )}

        {/* Error */}
        {errorMsg && (
          <div
            style={{
              marginTop: '20px',
              padding: '16px',
              background: 'rgba(233, 137, 126, 0.15)',
              border: '1px solid rgba(233, 137, 126, 0.3)',
              borderRadius: '8px',
              color: 'var(--accent-potential)',
            }}
          >
            <div
              style={{ display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 700 }}
            >
              <AlertCircle size={18} /> {errorMsg}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
