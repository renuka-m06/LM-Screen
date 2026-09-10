# LM-Screen — SIH Demonstration Script

## DEMO SEQUENCE FOR SIH JUDGES

### Demo 1: Clean Packaged Commodity Scan
1. Open `http://localhost:5173`.
2. Click **"1. Clean Declaration (PASS)"** test preset.
3. Click **"Execute Compliance Screening"**.
4. Result: `PASS_SCREENING` (*"No issue detected in the checks performed"*).
5. Inspect SVG evidence overlay showing green token bounding boxes for MRP, Net Qty, MFD, and Consumer Care details.

### Demo 2: Missing Statutory Declaration Scan
1. Click **"2. Missing MRP (POTENTIAL)"** test preset.
2. Click **"Execute Compliance Screening"**.
3. Result: `POTENTIAL_NON_COMPLIANCE` (*"Potential non-compliance detected"*).
4. View Rule Trace `LM001` identifying missing Maximum Retail Price declaration on visible package panel.

### Demo 3: Image Quality Retake Gate
1. Click **"3. Blurry Image (REVIEW)"** test preset.
2. Click **"Execute Compliance Screening"**.
3. Result: `NEEDS_REVIEW` (*"More evidence or human review required"*).
4. Observe Quality Gate displaying low blur score (< 80.0) forcing a retake request rather than making a false screening decision.

### Demo 4: Citizen Intelligence Signal Submission
1. Click **"Citizen Signals"** tab.
2. Fill out commodity name and select **"Suspicious MRP"**.
3. Click **"Submit Citizen Signal for Officer Review"**.
4. Confirm signal registered with status **`UNVERIFIED`** and disclaimer warning.

### Demo 5: Enforcement Officer Adjudication Queue
1. Switch role to **"Mode: OFFICER"** or click **"Priority Queue"** tab.
2. View products ranked by Operational Prioritization Score.
3. Click **"Inspect & Review"** on high-priority commodity.
4. Select **`CONFIRM`** decision, type inspector rationale, and click **"Commit Officer Decision"**.
5. Observe cluster status update and audit trail entry creation.
