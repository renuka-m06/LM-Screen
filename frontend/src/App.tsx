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
  } | null>(null);

  const handleInvestigate = (productId?: string, scanId?: string) => {
    setInvestigatingProductId(productId);
    setInvestigatingScanId(scanId);
  };

  const handleCloseInvestigation = () => {
    setInvestigatingProductId(undefined);
    setInvestigatingScanId(undefined);
  };

  const handleFileSignal = (scanResult: ScanResult) => {
    const derivedProduct = scanResult.extracted_fields?.product_name?.normalized_value;
    const userEntered = scanResult.identity_warnings?.[0]?.user_provided;
    const gtinVal = scanResult.extracted_fields?.gtin?.normalized_value;

    const mismatchWarning = scanResult.identity_warnings?.find(w => w.type === 'PRODUCT_IDENTITY_MISMATCH');

    let desc = `Observed label declaration details on retail scan #${scanResult.scan_id.slice(-8)}.`;
    if (mismatchWarning) {
      desc = `The submitted product name (${mismatchWarning.user_provided || userEntered || 'N/A'}) does not appear to match the product shown in the package image (${mismatchWarning.image_evidence || derivedProduct || 'N/A'}).`;
    }

    setPrefillSignalContext({
      related_scan_id: scanResult.scan_id,
      product_name: derivedProduct || userEntered || '',
      gtin: gtinVal || '',
      issue_category: mismatchWarning ? 'Information Mismatch' : 'Missing Information',
      description: desc
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
