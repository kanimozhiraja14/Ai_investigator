# Runbook: Ingress SSL/TLS Certificate Expiration

**Service:** ingress-gateway  
**Severity:** P1  
**Category:** CERTIFICATE_EXPIRATION  

## Symptoms
- Alert: `SSLCertificateExpired` firing for edge domain.
- Users seeing browser security warning `NET::ERR_CERT_DATE_INVALID`.
- Ingress returning handshake failure `x509: certificate has expired`.

## Diagnostic Steps
1. Query `cert_manager_certificate_expiration_timestamp_seconds` metric.
2. Query logs from `cert-manager` controller for renewal error messages.
3. Check DNS provider API token credentials used for ACME DNS-01 verification.
4. Verify certificate status in ingress namespace.

## Root Cause Patterns
- Automated cert-manager renewal failed due to expired DNS provider API token.
- Webhook validation failure blocked updating the Kubernetes Secret containing the TLS keypair.

## Mitigation
1. Update DNS API token secret in `cert-manager` namespace.
2. Trigger manual certificate reissue: `cmctl renew <cert-name>`.
3. Reload ingress controller pods to pick up updated TLS secret.
