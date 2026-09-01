# Security Policy

## Blocked Files (NEVER read, display, or process)
.env, .env.*, .envrc, ~/.aws/*, ~/.ssh/*, ~/.gnupg/*, ~/.kube/*,
*token*, *secret*, *credential*, *key.pem, *.keystore, *.jks

## Blocked Environment Variables (NEVER expose)
*TOKEN*, *API_KEY*, *SECRET*, *PASSWORD*, *AUTH*, *ACCESS_KEY*,
*SESSION*, DB_*, *KEY*

## Blocked Commands (NEVER execute)
source .env, export secrets, curl with auth headers, rm -rf,
truncate, DROP TABLE without WHERE

## Secret Patterns (REDACT in output)
ghp_*, sk-*, xox[baprs]-*, AKIA*, -----BEGIN.*KEY-----, JWT tokens
Authorization: Bearer <token> → redact credential portion

## Destructive Operations
NEVER create destructive tests/scripts. NEVER delete files without approval.
Tests must use isolated environments with reversible side effects.
Any destructive command requires explicit user approval.

## Principles
1. Least privilege: never read a file unless absolutely necessary
2. Refuse by default: when in doubt, refuse and explain
3. No exfiltration: never pipe sensitive content to network commands
4. Redact over expose: if secrets appear in output, redact them
5. No injection: never write sensitive content to logs or stdout
