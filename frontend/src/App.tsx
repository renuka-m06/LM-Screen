import { useState } from 'react';
import { Navbar } from './components/Navbar';
import { Scanner } from './components/Scanner';
import { CitizenPortal } from './components/CitizenPortal';
import { OfficerDashboard } from './components/OfficerDashboard';
import { AnalyticsDashboard } from './components/AnalyticsDashboard';
import { InvestigationView } from './components/InvestigationView';
import type { ScanResult } from './types';

export function App() {
  const [activeTab, setActiveTab] = useState<'scan' | 'citizen' | 'officer' | 'dashboard'>('scan');
  const [userRole, setUserRole] = useState<'CITIZEN' | 'OFFICER'>('CITIZEN');
  const [investigatingProductId, setInvestigatingProductId] = useState<string | undefined>(undefined);
  const [investigatingScanId, setInvestigatingScanId] = useState<string | undefined>(undefined);
  const [prefillSignalContext, setPrefillSignalContext] = useState<{
    related_scan_id?: string;
    product_name?: string;
    gtin?: string;
    issue_category?: string;
    description?: string;
    // Per-field skip reasons: present when a field was intentionally left
    // blank because OCR confidence was too low or evidence_state was UNCERTAIN.
    skipped_fields?: Record<string, string>;
  } | null>(null);

  const handleInvestigate = (productId?: string, scanId?: string) => {
    setInvestigatingProductId(productId);
    setInvestigatingScanId(scanId);
  };

  const handleCloseInvestigation = () => {
    setInvestigatingProductId(undefined);
    setInvestigatingScanId(undefined);
  };

  /**
   * Guard for prefill values derived from OCR extraction.
   * A field is only used to prefill the form when ALL of:
   *   • confidence > PREFILL_CONFIDENCE_THRESHOLD (0.70)
   *   • evidence_state is not 'UNCERTAIN'
   * If either check fails the field is left undefined (blank in the form)
   * and a human-readable skip reason is recorded so CitizenPortal can show
   * an explanatory note instead of a silent empty box.
   */
  const PREFILL_CONFIDENCE_THRESHOLD = 0.70;

  const guardedField = (
    field: ScanResult['extracted_fields'][string] | undefined,
    fallback?: string
  ): { value: string | undefined; skipReason: string | undefined } => {
    // If no OCR field at all, prefer the fallback (e.g. user-entered name)
    if (!field) {
      return { value: fallback || undefined, skipReason: undefined };
    }
    const conf = field.confidence ?? 0;
    const state = field.evidence_state ?? '';
    if (conf <= PREFILL_CONFIDENCE_THRESHOLD || state === 'UNCERTAIN') {
      const why = state === 'UNCERTAIN'
        ? `Scan couldn't read this reliably (OCR quality issue — confidence ${Math.round(conf * 100)}%)`
        : `Low scan confidence (${Math.round(conf * 100)}%) — please verify manually`;
      return { value: undefined, skipReason: why };
    }
    return { value: field.normalized_value || fallback || undefined, skipReason: undefined };
  };

  const handleFileSignal = (scanResult: ScanResult) => {
    const productField = scanResult.extracted_fields?.product_name;
    const gtinField    = scanResult.extracted_fields?.gtin;
    const userEntered  = scanResult.identity_warnings?.[0]?.user_provided;

    const mismatchWarning = scanResult.identity_warnings?.find(w => w.type === 'PRODUCT_IDENTITY_MISMATCH');

    // Apply confidence + state guards to every OCR-derived prefill value.
    const { value: productName, skipReason: productSkip } = guardedField(productField, userEntered);
    const { value: gtinVal,    skipReason: gtinSkip }     = guardedField(gtinField);

    const skipped_fields: Record<string, string> = {};
    if (productSkip) skipped_fields['product_name'] = productSkip;
    if (gtinSkip)    skipped_fields['gtin']         = gtinSkip;

    // Build description — use the guarded product name in the message,
    // falling back to user-entered name or the image evidence from the warning.
    const displayName = productName
      || mismatchWarning?.image_evidence
      || userEntered
      || 'N/A';
    let desc = `Observed label declaration details on retail scan #${scanResult.scan_id.slice(-8)}.`;
    if (mismatchWarning) {
      desc = `The submitted product name (${mismatchWarning.user_provided || userEntered || 'N/A'}) does not appear to match the product shown in the package image (${displayName}).`;
    }

    setPrefillSignalContext({
      related_scan_id: scanResult.scan_id,
      product_name: productName,
      gtin: gtinVal,
      issue_category: mismatchWarning ? 'Information Mismatch' : 'Missing Information',
      description: desc,
      ...(Object.keys(skipped_fields).length > 0 && { skipped_fields }),
    });

    setInvestigatingProductId(undefined);
    setInvestigatingScanId(undefined);
    setActiveTab('citizen');
  };

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg-main)', color: 'var(--text-primary)' }}>
      <Navbar
        activeTab={activeTab}
        setActiveTab={(tab) => {
          setActiveTab(tab);
          setInvestigatingProductId(undefined);
          setInvestigatingScanId(undefined);
        }}
        userRole={userRole}
        setUserRole={setUserRole}
      />

      <main>
        {/* Investigation view takes priority when active */}
        {investigatingProductId !== undefined || investigatingScanId !== undefined ? (
          <InvestigationView
            productId={investigatingProductId}
            scanId={investigatingScanId}
            userRole={userRole}
            onClose={handleCloseInvestigation}
          />
        ) : (
          <>
            {activeTab === 'scan' && (
              <Scanner
                userRole={userRole}
                onInvestigate={handleInvestigate}
                onFileSignal={handleFileSignal}
              />
            )}
            {activeTab === 'citizen' && <CitizenPortal prefillContext={prefillSignalContext} />}
            {activeTab === 'officer' && <OfficerDashboard />}
            {activeTab === 'dashboard' && <AnalyticsDashboard />}
          </>
        )}
      </main>
    </div>
  );
}

export default App;
