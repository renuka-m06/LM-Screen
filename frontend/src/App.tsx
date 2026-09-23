import { useState } from 'react';
import { Navbar } from './components/Navbar';
import { Scanner } from './components/Scanner';
import { CitizenPortal } from './components/CitizenPortal';
import { OfficerDashboard } from './components/OfficerDashboard';
import { AnalyticsDashboard } from './components/AnalyticsDashboard';
import { InvestigationView } from './components/InvestigationView';
import { CaseManagement } from './components/CaseManagement';
import { ErrorBoundary } from './components/ErrorBoundary';
import type { ScanResult } from './types';

export function App() {
  const [activeTab, setActiveTab] = useState<'scan' | 'citizen' | 'officer' | 'dashboard' | 'cases'>('scan');
  const [userRole, setUserRole] = useState<'CITIZEN' | 'OFFICER'>('CITIZEN');
  const [investigatingProductId, setInvestigatingProductId] = useState<string | undefined>(undefined);
  const [investigatingScanId, setInvestigatingScanId] = useState<string | undefined>(undefined);
  const [investigatingClusterId, setInvestigatingClusterId] = useState<string | undefined>(undefined);
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

  const handleInvestigate = (productId?: string, scanId?: string, clusterId?: string) => {
    setInvestigatingProductId(productId);
    setInvestigatingScanId(scanId);
    setInvestigatingClusterId(clusterId);
  };

  const handleCloseInvestigation = () => {
    setInvestigatingProductId(undefined);
    setInvestigatingScanId(undefined);
    setInvestigatingClusterId(undefined);
  };


  const handleFileSignal = (scanResult: ScanResult) => {
    // evidence is now an array — find product_name and gtin entries
    const evidenceArr: any[] = Array.isArray(scanResult.evidence) ? scanResult.evidence : [];
    const productEv = evidenceArr.find((e: any) => e.field === 'product_name' || e.field_name === 'product_name');
    const gtinEv    = evidenceArr.find((e: any) => e.field === 'gtin' || e.field_name === 'gtin');
    const userEntered  = (scanResult.identity_warnings as any)?.[0]?.user_provided;

    const mismatchWarning = (scanResult.identity_warnings as any)?.find((w: any) => w.type === 'PRODUCT_IDENTITY_MISMATCH');

    const productName = (productEv?.value ?? productEv?.normalized_value ?? userEntered) as string | undefined;
    const gtinVal     = (gtinEv?.value ?? gtinEv?.normalized_value) as string | undefined;

    const displayName = productName || mismatchWarning?.image_evidence || userEntered || 'N/A';
    const scanIdShort = (scanResult.screening_id ?? '').slice(-8);
    let desc = `Observed label declaration details on retail scan #${scanIdShort}.`;
    if (mismatchWarning) {
      desc = `The submitted product name (${mismatchWarning.user_provided || userEntered || 'N/A'}) does not appear to match the product shown in the package image (${displayName}).`;
    }

    setPrefillSignalContext({
      related_scan_id: scanResult.screening_id,
      product_name: productName,
      gtin: gtinVal,
      issue_category: mismatchWarning ? 'Information Mismatch' : 'Missing Information',
      description: desc,
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
        {investigatingProductId !== undefined || investigatingScanId !== undefined || investigatingClusterId !== undefined ? (
          <InvestigationView
            productId={investigatingProductId}
            scanId={investigatingScanId}
            clusterId={investigatingClusterId}
            userRole={userRole}
            onClose={handleCloseInvestigation}
          />
        ) : (
          <>
            {activeTab === 'scan' && (
              <ErrorBoundary
                fallbackMessage="Something went wrong while displaying the screening result."
                onReset={() => {}}
              >
                <Scanner
                  userRole={userRole}
                  onInvestigate={handleInvestigate}
                  onFileSignal={handleFileSignal}
                />
              </ErrorBoundary>
            )}
            {activeTab === 'citizen' && <CitizenPortal prefillContext={prefillSignalContext} />}
            {activeTab === 'officer' && (
              <OfficerDashboard
                onInvestigate={handleInvestigate}
                onOpenCases={() => setActiveTab('cases')}
              />
            )}
            {activeTab === 'dashboard' && <AnalyticsDashboard />}
            {activeTab === 'cases' && <CaseManagement userRole={userRole} />}
          </>
        )}
      </main>
    </div>
  );
}

export default App;
