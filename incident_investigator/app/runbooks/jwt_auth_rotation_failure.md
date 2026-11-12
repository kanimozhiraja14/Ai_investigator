# Runbook: JWT Secret Rotation Failure & Inter-Service RPC 401

**Service:** user-profile-service  
**Severity:** P1  
**Category:** AUTH_SECRET_ROTATION  

## Symptoms
- Alert: `ServiceAuth401Spike` (inter-service authorization failure rate > 25%).
- Web frontend and checkout services failing to fetch user profile details.
- Logs full of `SignatureVerificationException: Key ID (kid) not found in JWKS cache`.

## Diagnostic Steps
1. Query `http_requests_total{status="401"}` on `user-profile-service`.
2. Inspect application logs for JWT header validation errors (`kid mismatch` or `unknown key ID`).
3. Check HashiCorp Vault / KMS secret rotation audit logs for key rotation timestamp.
4. Verify JWKS caching TTL setting in `user-profile-service` configuration.

## Root Cause Patterns
- Vault rotated signing key without supporting dual-key verification window.
- Consuming service cached old public key set for 24 hours with no cache-busting on validation failure.

## Mitigation
1. Trigger immediate cache invalidation on `user-profile-service` JWKS client.
2. Configure 48-hour overlap window during secret rotation in Vault.
3. Update JWKS client to automatically refetch key set when encountering an unknown `kid`.
