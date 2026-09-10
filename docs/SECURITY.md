# LM-Screen Security & Privacy Guidelines

## Security Controls
1. **File Input Validation**:
   - Strict MIME-type checking (`image/jpeg`, `image/png`, `image/webp`, `image/bmp`, `image/tiff`).
   - File size limits (Max 10 MB per upload).
   - Safe OpenCV image decoding buffer validation.

2. **Secret Management**:
   - Secrets and environment variables loaded via `.env`.
   - No hardcoded API keys or JWT secrets in source code or frontend bundles.

3. **Role-Based Access Control**:
   - Roles: `CITIZEN`, `OFFICER`, `ADMIN`.
   - Backend endpoint protection for officer and admin routes.

4. **Immutable Audit Trails**:
   - Officer review overrides logged with timestamp, reviewer ID, badge number, and rationale.
