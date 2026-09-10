import React from 'react';
import { Info } from 'lucide-react';

interface DisclaimerBannerProps {
  customText?: string;
}

export const DisclaimerBanner: React.FC<DisclaimerBannerProps> = ({ customText }) => {
  return (
    <div style={{
      background: 'rgba(233, 185, 73, 0.15)',
      border: '1px solid var(--accent-review)',
      borderRadius: '8px',
      padding: '12px 16px',
      margin: '16px 0',
      display: 'flex',
      alignItems: 'flex-start',
      gap: '12px'
    }}>
      <Info size={18} color="var(--accent-review)" style={{ flexShrink: 0, marginTop: '2px' }} />
      <p style={{ fontSize: '0.8rem', color: 'var(--text-primary)', lineHeight: '1.45', margin: 0 }}>
        <strong>💡 About LM-Screen: </strong> {customText || "This platform performs image-based Legal Metrology compliance screening for selected visible declarations. It does not replace inspection by an authorized officer, legal interpretation, laboratory testing, physical package measurement, or official enforcement procedures. Results depend on image quality, available declarations, product classification, rule version, and evidence confidence."}
      </p>
    </div>
  );
};
