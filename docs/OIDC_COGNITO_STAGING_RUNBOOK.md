# OIDC Cognito Staging Runbook

**Issue:** [#819](https://github.com/nimeob/geo-ranking-ch/issues/819) — OIDC-0.wp3  
**Parent:** [#802](https://github.com/nimeob/geo-ranking-ch/issues/802) — OIDC-0  
**Stand:** 2026-03-02  
**Status:** Manuelles Runbook (MVP); IaC-Follow-up als separates Issue erfasst.

---

## Überblick

Dieses Runbook beschreibt, wie der Cognito User Pool + App Client für das **staging**-Environment
angelegt, die Hosted UI konfiguriert und die notwendigen Werte sicher (SSM/SecretsManager, kein
Klartext in TF State / Logs) gespeichert werden.

**Architekturentscheid:** API-Auth läuft über OIDC JWT Validation
(`src/api/oidc_jwt.py`). Der Browser-Login für das Portal wird via BFF implementiert
(#806). Das API selbst validiert nur Bearer-Tokens (JWKS/Issuer/Audience-Check).

---

## Voraussetzungen

```bash
export AWS_REGION="eu-central-1"
export AWS_ACCOUNT_ID="523234426229"
export PROJECT="swisstopo"
export ENV="staging"

# AWS CLI konfiguriert + Zugriff auf Cognito/SSM/IAM
aws sts get-caller-identity
```

---

## 1) Cognito User Pool anlegen

### 1.1 User Pool erstellen

```bash
USER_POOL_NAME="${PROJECT}-${ENV}"

aws cognito-idp create-user-pool \
  --pool-name "${USER_POOL_NAME}" \
  --region "${AWS_REGION}" \
  --auto-verified-attributes email \
  --username-attributes email \
  --admin-create-user-config AllowAdminCreateUserOnly=true \
  --mfa-configuration OFF \
  --policies 'PasswordPolicy={MinimumLength=12,RequireUppercase=true,RequireLowercase=true,RequireNumbers=true,RequireSymbols=false}' \
  --account-recovery-setting 'RecoveryMechanisms=[{Priority=1,Name=verified_email}]' \
  --query 'UserPool.Id' --output text
```

> ⚠️ `AllowAdminCreateUserOnly=true` deaktiviert Self-Signup (MVP). Nur admins können User anlegen.

**Ergebnis:** `USER_POOL_ID=eu-central-1_<suffix>` → sofort in SSM speichern (Schritt 5).

```bash
# Merke User Pool ID für folgende Schritte:
export USER_POOL_ID="eu-central-1_XXXXXXX"   # ← mit realem Wert ersetzen
```

### 1.2 User Pool Domain (für Hosted UI)

Die Domain-Prefix muss **global eindeutig** sein. Convention: `<project>-<env>-<account-suffix>`.

```bash
DOMAIN_PREFIX="${PROJECT}-${ENV}-523234"   # letzten 6 Ziffern der Account-ID

aws cognito-idp create-user-pool-domain \
  --domain "${DOMAIN_PREFIX}" \
  --user-pool-id "${USER_POOL_ID}" \
  --region "${AWS_REGION}"

export COGNITO_DOMAIN="https://${DOMAIN_PREFIX}.auth.${AWS_REGION}.amazoncognito.com"
echo "Hosted UI Base URL: ${COGNITO_DOMAIN}"
```

---

## 2) App Client (Auth Code + PKCE)

### 2.1 App Client erstellen

```bash
# Staging-Callback URLs — vor dem Anlegen staging ALB-URL eintragen:
# Placeholder: nach staging-Ingress-Setup durch reale ALB/Domain-URL ersetzen.
CALLBACK_URL="https://<staging-alb-dns>/auth/callback"
LOGOUT_URL="https://<staging-alb-dns>/auth/logout"

aws cognito-idp create-user-pool-client \
  --user-pool-id "${USER_POOL_ID}" \
  --client-name "${PROJECT}-${ENV}-bff" \
  --region "${AWS_REGION}" \
  --no-generate-secret \
  --allowed-o-auth-flows "code" \
  --allowed-o-auth-scopes "openid" "email" "profile" \
  --allowed-o-auth-flows-user-pool-client \
  --supported-identity-providers "COGNITO" \
  --callback-ur-ls "${CALLBACK_URL}" \
  --logout-ur-ls "${LOGOUT_URL}" \
  --enable-token-revocation \
  --prevent-user-existence-errors ENABLED \
  --auth-session-validity 3 \
  --access-token-validity 60 \
  --id-token-validity 60 \
  --refresh-token-validity 1 \
  --token-validity-units 'AccessToken=minutes,IdToken=minutes,RefreshToken=days' \
  --query 'UserPoolClient.ClientId' --output text
```

> **PKCE-Hinweis:** Auth Code Grant + PKCE wird standardmäßig unterstützt.
> Der BFF (#806) initiiert den Authorization Request mit `code_challenge_method=S256`.
> Da `--no-generate-secret` gesetzt ist (Public Client / BFF flow), wird kein Client Secret benötigt.

**Ergebnis:** `APP_CLIENT_ID=<26-char-id>` → sofort in SSM speichern (Schritt 5).

```bash
export APP_CLIENT_ID="<id>"   # ← mit realem Wert ersetzen
```

---

## 3) Token TTLs (dokumentiert)

| Token        | Gültigkeit (Staging) | Einheit |
|--------------|---------------------|---------|
| Access Token | 60                  | Minuten |
| ID Token     | 60                  | Minuten |
| Refresh Token | 1                  | Tage    |
| Auth Session  | 3                  | Minuten |

**Begründung:** Kurze Laufzeiten für Staging (wenig Risiko bei kompromittierten Tokens).
Für Prod kann Access/ID-Token auf 15–60 min und Refresh auf 7–30 Tage gesetzt werden.

**Automatisches Refresh:** Der BFF (#806) implementiert transparentes Token-Refresh
(bei 401 / `exp`-Check vor API-Call).

---

## 4) Hosted UI konfigurieren

Die Hosted UI wird beim App Client automatisch aktiviert, sobald Domain + OAuth Flows gesetzt sind.

**Login-URL (manueller Test):**

```
${COGNITO_DOMAIN}/oauth2/authorize
  ?response_type=code
  &client_id=${APP_CLIENT_ID}
  &redirect_uri=<URL-encoded CALLBACK_URL>
  &scope=openid+email+profile
  &code_challenge=<S256-challenge>
  &code_challenge_method=S256
```

**Token Exchange (manuell):**

```bash
# Nach erfolgreichem Login (code aus Redirect):
curl -X POST "${COGNITO_DOMAIN}/oauth2/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=authorization_code" \
  -d "client_id=${APP_CLIENT_ID}" \
  -d "code=<auth-code>" \
  -d "redirect_uri=<CALLBACK_URL>" \
  -d "code_verifier=<plain-verifier>"
```

**Logout:**

```
${COGNITO_DOMAIN}/logout
  ?client_id=${APP_CLIENT_ID}
  &logout_uri=<URL-encoded LOGOUT_URL>
```

---

## 5) Werte sicher in SSM speichern (kein Klartext in TF State/Logs)

> ⚠️ Alle Werte als `SecureString` anlegen. Niemals Werte direkt in Terraform-State, Logs oder
> Runbook-Commits.

```bash
# User Pool ID
aws ssm put-parameter \
  --region "${AWS_REGION}" \
  --name "/${PROJECT}/${ENV}/cognito/user-pool-id" \
  --type "String" \
  --value "${USER_POOL_ID}" \
  --description "Cognito User Pool ID (staging)" \
  --overwrite

# App Client ID (nicht sensitiv, aber konvention-konform via SSM)
aws ssm put-parameter \
  --region "${AWS_REGION}" \
  --name "/${PROJECT}/${ENV}/cognito/app-client-id" \
  --type "String" \
  --value "${APP_CLIENT_ID}" \
  --description "Cognito App Client ID (staging, no-secret)" \
  --overwrite

# Cognito Domain (Hosted UI Base URL)
aws ssm put-parameter \
  --region "${AWS_REGION}" \
  --name "/${PROJECT}/${ENV}/cognito/domain" \
  --type "String" \
  --value "${COGNITO_DOMAIN}" \
  --description "Cognito Hosted UI base URL (staging)" \
  --overwrite
```

---

## 6) API Environment Variables (für ECS Task Definition)

Der API-Service liest folgende Env Vars (siehe `src/api/web_service.py`):

| Variable                  | Wert (Staging)                                                                      | Pflicht |
|---------------------------|-------------------------------------------------------------------------------------|---------|
| `OIDC_JWKS_URL`           | `https://cognito-idp.eu-central-1.amazonaws.com/<USER_POOL_ID>/.well-known/jwks.json` | ✅ ja   |
| `OIDC_JWT_ISSUER`         | `https://cognito-idp.eu-central-1.amazonaws.com/<USER_POOL_ID>`                    | ✅ ja   |
| `OIDC_JWT_AUDIENCE`       | `<APP_CLIENT_ID>`                                                                   | ✅ ja   |
| `OIDC_JWKS_TTL_SECONDS`   | `300` (5 min Cache-TTL für JWKS)                                                    | optional |
| `OIDC_JWKS_TIMEOUT_SECONDS` | `5`                                                                               | optional |
| `OIDC_CLOCK_SKEW_SECONDS` | `60`                                                                                | optional |

**Konkrete Werte (nach User Pool Anlage):**

```bash
JWKS_URL="https://cognito-idp.${AWS_REGION}.amazonaws.com/${USER_POOL_ID}/.well-known/jwks.json"
JWT_ISSUER="https://cognito-idp.${AWS_REGION}.amazonaws.com/${USER_POOL_ID}"
JWT_AUDIENCE="${APP_CLIENT_ID}"

echo "OIDC_JWKS_URL=${JWKS_URL}"
echo "OIDC_JWT_ISSUER=${JWT_ISSUER}"
echo "OIDC_JWT_AUDIENCE=${JWT_AUDIENCE}"
```

Diese Werte als `SecureString` in SSM anlegen und im ECS Task Definition `environment`-Block
(nicht `secrets`) referenzieren — sie sind nicht sensitiv, aber konvention-konform via SSM (vgl.
#826 ECS wiring).

```bash
aws ssm put-parameter \
  --region "${AWS_REGION}" \
  --name "/${PROJECT}/${ENV}/api/OIDC_JWKS_URL" \
  --type "String" --value "${JWKS_URL}" --overwrite

aws ssm put-parameter \
  --region "${AWS_REGION}" \
  --name "/${PROJECT}/${ENV}/api/OIDC_JWT_ISSUER" \
  --type "String" --value "${JWT_ISSUER}" --overwrite

aws ssm put-parameter \
  --region "${AWS_REGION}" \
  --name "/${PROJECT}/${ENV}/api/OIDC_JWT_AUDIENCE" \
  --type "String" --value "${JWT_AUDIENCE}" --overwrite
```

---

## 7) Smoke Checks

### 7.1 User Pool erreichbar + JWKS abrufbar

```bash
# JWKS endpoint (öffentlich, kein Auth nötig)
curl -s "${JWKS_URL}" | python3 -c "import sys,json; d=json.load(sys.stdin); assert 'keys' in d and len(d['keys'])>0, 'no keys'; print(f'OK: {len(d[\"keys\"])} key(s)')"
# Expected: OK: 1 key(s)  (oder mehr)
```

### 7.2 API erkennt OIDC-Konfiguration

```bash
# Wenn API läuft und OIDC env vars gesetzt sind:
# Ohne Token → 401
curl -s -o /dev/null -w "%{http_code}" \
  -X POST "https://<staging-api>/analyze" \
  -H "Content-Type: application/json" -d '{}'
# Expected: 401

# Mit ungültigem Token → 401
curl -s -o /dev/null -w "%{http_code}" \
  -X POST "https://<staging-api>/analyze" \
  -H "Authorization: Bearer invalid.token.here" \
  -H "Content-Type: application/json" -d '{}'
# Expected: 401
```

### 7.3 Hosted UI erreichbar

```bash
# Hosted UI Login-Page → sollte 200 oder Redirect (302) zurückgeben
curl -s -o /dev/null -w "%{http_code}" \
  "${COGNITO_DOMAIN}/oauth2/authorize?response_type=code&client_id=${APP_CLIENT_ID}&redirect_uri=<URL-encoded-callback>&scope=openid"
# Expected: 302 (Redirect zur Login-Seite)
```

---

## 8) Callback/Logout URLs — Update nach Staging-Ingress

Sobald der Staging ALB/Domain live ist (#826/#827), müssen die Callback-URLs im App Client
aktualisiert werden:

```bash
NEW_CALLBACK="https://<real-staging-domain>/auth/callback"
NEW_LOGOUT="https://<real-staging-domain>/auth/logout"

aws cognito-idp update-user-pool-client \
  --user-pool-id "${USER_POOL_ID}" \
  --client-id "${APP_CLIENT_ID}" \
  --region "${AWS_REGION}" \
  --callback-ur-ls "${NEW_CALLBACK}" \
  --logout-ur-ls "${NEW_LOGOUT}" \
  --allowed-o-auth-flows "code" \
  --allowed-o-auth-scopes "openid" "email" "profile" \
  --allowed-o-auth-flows-user-pool-client \
  --supported-identity-providers "COGNITO"
```

> **Hinweis:** `update-user-pool-client` überschreibt alle OAuth-Felder vollständig.
> Immer alle `--allowed-o-auth-*` Parameter mitgeben, auch wenn sie sich nicht ändern.

---

## 9) Test-User anlegen (optional, für E2E Smoke)

```bash
TEST_USER_EMAIL="staging-test@<yourdomain>"

aws cognito-idp admin-create-user \
  --user-pool-id "${USER_POOL_ID}" \
  --username "${TEST_USER_EMAIL}" \
  --user-attributes Name=email,Value="${TEST_USER_EMAIL}" Name=email_verified,Value=true \
  --temporary-password "Staging!Test2026" \
  --message-action SUPPRESS \
  --region "${AWS_REGION}"

# Passwort auf permanenten Wert setzen (kein Force-Change-Password mehr):
aws cognito-idp admin-set-user-password \
  --user-pool-id "${USER_POOL_ID}" \
  --username "${TEST_USER_EMAIL}" \
  --password "Staging!Perm2026" \
  --permanent \
  --region "${AWS_REGION}"
```

> ⚠️ Test-Passwörter NICHT in Git/Commits. Nach E2E-Smoke User deaktivieren oder löschen.

---

## 10) IaC Follow-up

Dieses Runbook ist der MVP-Ansatz (manuell via CLI). Ein IaC-Follow-up (Terraform) ist als
eigenständiges Issue zu erfassen, sobald der manuelle Aufbau validiert ist.

Terraform-Ressourcen-Preview:
- `aws_cognito_user_pool`
- `aws_cognito_user_pool_domain`
- `aws_cognito_user_pool_client`

> ⚠️ `manage_flags` (wie bei staging_db.tf) einführen, damit kein versehentlicher Create/Destroy
> in dev/prod Workspaces.

---

## Referenzen

- [OIDC-0 Parent #802](https://github.com/nimeob/geo-ranking-ch/issues/802)
- [API JWT Validation (wp1) #817](https://github.com/nimeob/geo-ranking-ch/issues/817) — `src/api/oidc_jwt.py`
- [OIDC Guard (wp2) #818](https://github.com/nimeob/geo-ranking-ch/issues/818) — OIDC_JWKS_URL aktiviert Guard
- [ECS DB Secrets wiring #826](https://github.com/nimeob/geo-ranking-ch/issues/826) — SSM Pattern für ECS
- [BFF #806](https://github.com/nimeob/geo-ranking-ch/issues/806) — konsumiert Cognito Login-Flow
- [AWS Cognito Auth Code + PKCE Docs](https://docs.aws.amazon.com/cognito/latest/developerguide/authorization-endpoint.html)
