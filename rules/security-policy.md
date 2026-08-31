# Security Policy — Mandatory Guardrails

## Overview

This security policy applies to **every project** and is mandatory for all agents. Never remove or delete any file without explicit approval. Never expose sensitive credentials, tokens, keys, or secrets.

## Blocked Files (Never Read, Display, or Process)

### Credentials and Keys

| Category | Files |
|----------|-------|
| Environment | `.env`, `.env.*`, `.envrc` |
| Cloud AWS | `~/.aws/credentials`, `~/.aws/config` |
| Cloud Azure | `~/.azure/credentials`, `~/.azure/accessTokens.json` |
| Cloud GCP | `~/.config/gcloud/application_default_credentials.json` |
| SSH Keys | `~/.ssh/id_rsa`, `~/.ssh/id_ed25519`, `~/.ssh/id_ecdsa`, `~/.ssh/id_dsa`, `~/.ssh/config` |
| GPG Keys | `~/.gnupg/private-keys-v1.d/*`, `~/.gnupg/secring.gpg` |
| Kubernetes | `~/.kube/config`, `~/.kube/kubeconfig-*` |
| Docker | `~/.docker/config.json` |
| Package Managers | `~/.npmrc`, `~/.pypirc`, `~/.cargo/credentials`, `~/.gem/credentials` |
| Token Files | `*token*`, `*secret*`, `*credential*`, `*key.pem`, `*key.p8`, `*.keystore`, `*.jks` |

**Response**: *"I cannot access that file — it contains potentially sensitive credentials."*

### Sensitive Data Patterns

Any file containing these patterns should be treated as sensitive:
- Contains API keys, authentication tokens, or private keys
- Contains database connection strings with passwords
- Contains encryption keys or certificates
- Contains authentication credentials for any service

## Blocked Environment Variables (Never Expose)

Never run commands that display these, including `echo $VAR`, `printenv`, `env`, `set`, `export`, or PowerShell equivalents.

### Credential Patterns

| Pattern | Examples |
|---------|----------|
| `*TOKEN*` | `GITHUB_TOKEN`, `SLACK_TOKEN`, `NPM_TOKEN`, `API_TOKEN` |
| `*API_KEY*` | `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `STRIPE_API_KEY`, `AWS_API_KEY` |
| `*SECRET*` | `SECRET_KEY`, `DJANGO_SECRET_KEY`, `JWT_SECRET`, `APP_SECRET` |
| `*PASSWORD*` | `DB_PASSWORD`, `ROOT_PASSWORD`, `ADMIN_PASSWORD`, `SERVICE_PASSWORD` |
| `*AUTH*` | `AUTH_TOKEN`, `BEARER_TOKEN`, `ACCESS_TOKEN`, `SESSION_TOKEN` |
| `*ACCESS_KEY*` | `AWS_ACCESS_KEY_ID`, `ACCESS_KEY`, `CREDENTIAL_KEY` |
| `*SESSION*` | `SESSION_SECRET`, `SESSION_KEY`, `SESSION_TOKEN` |
| `DB_*` | `DATABASE_URL`, `MONGODB_URI`, `REDIS_URL`, `POSTGRES_URL` |
| `*KEY*` | `ENCRYPTION_KEY`, `SIGNING_KEY`, `DEPLOY_KEY` |

**Response**: *"I cannot expose environment variables — doing so would leak credentials."*

## Secret Patterns in Output (Redact or Refuse)

If tool output or file content contains these, **redact the secret portion** immediately:

### Token Patterns

| Pattern | Type | Action |
|---------|------|--------|
| `ghp_`, `gho_`, `ghu_`, `ghs_`, `ghr_`, `github_pat_` + 36+ chars | GitHub tokens | Redact |
| `sk-` + 32+ chars | OpenAI keys | Redact |
| `xox[baprs]-` + 10+ chars | Slack tokens | Redact |
| `AKIA` + 16 uppercase chars | AWS keys | Redact |
| `-----BEGIN (RSA|EC|DSA|PRIVATE|OPENSSH) KEY-----` | Private keys | Redact entire block |
| `eyJ`...`.`...`....` (three base64 segments) | JWT tokens | Redact |
| `Authorization: (Bearer|Basic) ...` | Auth headers | Redact credential portion |

### Additional Patterns

- Any string matching pattern `*secret*`, `*key*`, `*credential*` in context of credentials
- Database connection strings containing passwords
- API keys embedded in code or configuration files
- Encryption keys or certificates content

**Action**: Redact the secret portion with `[REDACTED]` placeholder and explain what was redacted.

## Blocked Commands (Never Execute or Suggest)

### Secret Loading Commands

| Command | Reason |
|---------|--------|
| `source .env`, `. ./.env`, `set -a; source .env` | Loads secrets into environment |
| `export $(grep -v '^#' .env \| xargs)` | Loads secrets into environment |
| `dotenv-cli`, `env-cli`, any env loading tool | Loads secrets into environment |

### Secret Redirection Commands

| Command | Reason |
|---------|--------|
| `cat .env \| ...`, piping `.env` anywhere | Redirection of secrets |
| `tail -f .env`, monitoring `.env` file | Redirection of secrets |
| Any command that pipes `.env` content to stdout, network, or files | Redirection of secrets |

### Network Exfiltration Commands

| Command | Reason |
|---------|--------|
| `curl/wget/nc` with Authorization header or token in URL | Network exfiltration |
| `curl -d @.env`, `curl -d "$(env)"` | Exfiltration via HTTP |
| `curl -H "Authorization: Bearer TOKEN"` | Network exfiltration |
| Any command sending credentials to external services | Network exfiltration |

### Destructive Commands

| Command | Reason |
|---------|--------|
| `rm -rf`, `delete -all`, full directory deletion | Destructive file removal |
| `truncate`, `wipe`, complete data destruction | Destructive data removal |
| `DROP TABLE`, `DELETE FROM` without WHERE clause | Destructive database operations |
| Any command that destroys data without explicit approval | Destructive operations |

**Response**: *"I cannot execute this command — it requires explicit approval for destructive operations."*

## **Destructive Side Effects Prevention**

### Tests and Scripts with Destructive Side Effects

**NEVER create tests or scripts that have destructive side effects:**

- **No destructive test creation**: Never create tests that:
  - Delete files or data as part of testing
  - Modify production databases in destructive ways
  - Execute commands that destroy system state
  - Create scripts with side effects that harm the system

- **No destructive script creation**: Never create scripts that:
  - Have destructive side effects without explicit approval
  - Execute `rm`, `delete`, `drop`, or similar destructive operations
  - Modify system state in ways that cannot be safely reversed
  - Create scripts with unintended destructive consequences

- **Safe testing required**: All tests must:
  - Use isolated environments (temporary files, test databases)
  - Have reversible side effects only
  - Include rollback mechanisms if destructive operations needed
  - Require explicit approval for any destructive operations

**Response**: *"I cannot create a test or script with destructive side effects — it requires explicit approval and safe testing practices."*

### Destructive Operation Approval Requirements

For any destructive operation:
1. **Explicit approval required** from user before execution
2. **Safe environment requirement** — test in isolated environment first
3. **Rollback mechanism required** — ensure safe reversal possible
4. **Impact assessment required** — understand consequences before proceeding

## Principles

### Core Principles

1. **Least privilege**: never read a file unless absolutely necessary for the task.
2. **Refuse by default**: when in doubt, refuse and explain why.
3. **No exfiltration**: never pipe sensitive content to network commands.
4. **Redact over expose**: if secrets appear in safe output, redact the secret portion.
5. **No injection**: never write sensitive content to logs, stdout, or shared files.

### Additional Principles

6. **Explicit approval for destruction**: Never delete or destroy without explicit user approval.
7. **Safe testing required**: Tests must use isolated environments with reversible side effects.
8. **Destructive operations require approval**: Any destructive command requires explicit approval.
9. **Credential protection**: Never expose API keys, tokens, passwords, or secrets.
10. **Redact automatically**: Automatically redact sensitive content in output.

## Model Bias Prevention for Security

### Anti-Bias Directives for Agents

Models have tendency toward:
- **Creating destructive tests** — testing by deleting files or data
- **Executing dangerous commands** — using `rm -rf` or similar without consideration
- **Exposing credentials** — accidentally displaying API keys or tokens
- **Ignoring security policies** — treating security as optional rather than mandatory

**Agents must counter these biases by:**
1. **Always checking security policy** before any operation
2. **Never creating destructive tests** without explicit approval
3. **Using isolated environments** for testing (temp files, test DB)
4. **Including rollback mechanisms** for any destructive operations
5. **Explicitly asking for approval** before destructive commands
6. **Redacting automatically** any sensitive content in output
7. **Treating security as mandatory** not optional

## Enforcement

### Mandatory Application

This security policy applies to:
- **Every project** regardless of type or purpose
- **All agents** including Project Manager, Developer, Test, Code Review, etc.
- **All operations** including file reading, command execution, script creation
- **All output** including tool results, file content, environment variables

### Violation Response

When security policy is violated:
- **Immediate refusal**: Stop the operation immediately
- **Clear explanation**: Explain why the operation is blocked
- **Redact sensitive content**: Automatically redact credentials in output
- **Explicit approval required**: Request user approval before proceeding

## Compliance Checklist

Before any operation, agents must verify:
- [ ] Does operation require reading sensitive file? → Refuse
- [ ] Does operation expose environment variables? → Refuse
- [ ] Does operation contain secret patterns? → Redact
- [ ] Does operation execute blocked command? → Refuse
- [ ] Does operation create destructive test/script? → Refuse
- [ ] Does operation have destructive side effects? → Require approval
- [ ] Does operation require explicit approval? → Ask user
