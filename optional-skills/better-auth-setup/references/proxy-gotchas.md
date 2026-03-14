# Better Auth + Reverse Proxy — Gotchas & Troubleshooting

Common failures when running Better Auth behind a reverse proxy, with root causes and fixes. Each gotcha was discovered through real debugging — they are not obvious from the docs.

## Table of Contents

1. [redirect_uri_mismatch from Google](#1-redirect_uri_mismatch-from-google)
2. [state_mismatch after OAuth callback](#2-state_mismatch-after-oauth-callback)
3. [404 on all auth endpoints](#3-404-on-all-auth-endpoints)
4. [Session cookie not detected after login](#4-session-cookie-not-detected-after-login)
5. [trustedProxyHeaders not working](#5-trustedproxyheaders-not-working)
6. [baseURL caches wrong origin](#6-baseurl-caches-wrong-origin)
7. [BETTER_AUTH_URL env var overrides everything](#7-better_auth_url-env-var-overrides-everything)
8. [OAuth callback hits backend directly (skips proxy)](#8-oauth-callback-hits-backend-directly-skips-proxy)

---

## 1. redirect_uri_mismatch from Google

**Symptom**: Google OAuth returns `redirect_uri_mismatch` error page.

**Root cause**: The `redirect_uri` Better Auth sends to Google doesn't match what's configured in Google Console. This happens when Better Auth derives the wrong baseURL — typically the backend's domain instead of the frontend's.

**Debug**: Run the verification curl to see what `redirect_uri` is actually being sent:
```bash
curl -s -X POST "https://your-frontend.com/api/auth/sign-in/social" \
  -H "Content-Type: application/json" \
  -d '{"provider":"google","callbackURL":"/dashboard"}' | \
  python3 -c "import sys,json,urllib.parse; data=json.load(sys.stdin); url=data.get('url',''); params=urllib.parse.parse_qs(urllib.parse.urlparse(url).query); print('redirect_uri:', params.get('redirect_uri',['N/A'])[0])"
```

Compare the output to Google Console's "Authorized redirect URIs".

**Fix**:
- Ensure `allowedHosts` includes the frontend domain
- Ensure the proxy sets `X-Forwarded-Host` header (not just strips it)
- Ensure `trustedProxyHeaders: true` is in the `advanced` config
- Google Console redirect URI must be `https://{frontend}/auth/callback/{provider}` — note `/auth/`, NOT `/api/auth/`

**Google Console propagation**: Changes take up to 5 minutes. If you just updated, wait and retry.

---

## 2. state_mismatch after OAuth callback

**Symptom**: After Google redirects back, Better Auth returns a `state_mismatch` error, typically visible at the backend URL.

**Root cause**: The state cookie was set on the frontend domain during OAuth initiation, but the callback arrived directly at the backend domain. Different domain = no cookie = state mismatch.

**Fix**: The OAuth callback URL must route through the frontend proxy, not directly to the backend. This means:
1. A proxy route at `/auth/*` must exist on the frontend (in addition to `/api/auth/*`)
2. The `redirect_uri` sent to the OAuth provider must use the frontend domain
3. Both the initial request and callback must share the same domain for cookies to work

**How to verify**: Check the `redirect_uri` in the OAuth initiation response. If it points to the backend domain, the `allowedHosts` or forwarding headers are misconfigured.

---

## 3. 404 on all auth endpoints

**Symptom**: POST `/api/auth/sign-in/social` (or any auth endpoint) returns 404.

**Root causes** (multiple possible):

### 3a. baseURL includes a path component
Setting `baseURL` to something like `https://frontend.com/api` breaks Better Auth's internal routing. Better Auth uses `basePath` for path prefixing — `baseURL` should only be the origin (protocol + host).

### 3b. Host mismatch with static baseURL
If `baseURL` is `https://frontend.com` but requests arrive at the backend with `Host: backend.fly.dev`, Better Auth may reject the request because the host doesn't match. This is why dynamic `allowedHosts` is needed.

### 3c. allowedHosts array is empty or malformed
If the `allowedHosts` array doesn't match any incoming host AND no `fallback` is set, Better Auth has no baseURL to work with and may reject requests.

### 3d. Missing proxy route
If only `/api/auth/*` is proxied but the request arrives at `/auth/*` (OAuth callback), there's no route handler.

**Fix**: Use `allowedHosts` with all known domains, always set `fallback`, and ensure both proxy routes exist.

---

## 4. Session cookie not detected after login

**Symptom**: OAuth completes successfully (no Google errors, callback returns 302 to `/dashboard`), but the user is immediately redirected to `/sign-in?redirect=%2Fdashboard`.

**Root cause**: In production with HTTPS, Better Auth prefixes cookie names with `__Secure-`. The cookie is actually named `__Secure-better-auth.session_token`, not `better-auth.session_token`. If middleware only checks the unprefixed name, it never finds the cookie.

**Why it happens with allowedHosts**: When `baseURL` is a dynamic config object (not a string), Better Auth can't determine the protocol at initialization time. In production (`NODE_ENV=production`), it defaults to secure cookies with the `__Secure-` prefix.

**Fix**: Middleware must check both cookie names:
```typescript
const SESSION_COOKIES = [
  "__Secure-better-auth.session_token",
  "better-auth.session_token",
];
```

**This is the most insidious gotcha** because everything appears to work — OAuth succeeds, session is created, cookie is set — but the frontend doesn't recognize it. Without the skill, Claude diagnoses this as "Set-Cookie header stripping" (plausible but wrong) instead of the `__Secure-` prefix (correct).

---

## 5. trustedProxyHeaders not working

**Symptom**: Despite setting `trustedProxyHeaders: true`, Better Auth still uses the wrong origin for callback URLs.

**Root cause**: `trustedProxyHeaders` only takes effect when Better Auth actually reads forwarded headers. The `getBaseURL()` function has a priority order:
1. Static `baseURL` string (if set) — **always wins**
2. `BETTER_AUTH_URL` environment variable — **checked before headers**
3. `X-Forwarded-Host` / `X-Forwarded-Proto` headers — only reached if 1 and 2 are absent
4. Request URL — last resort

**Fix**: Use `allowedHosts` instead. It explicitly reads `X-Forwarded-Host` and constructs the baseURL per-request, bypassing the priority chain entirely.

---

## 6. baseURL caches wrong origin

**Symptom**: Auth works for the first request after deploy, then breaks. Or auth never works because the first request was a health check.

**Root cause**: When using a static `baseURL` string or `trustedProxyHeaders` without `allowedHosts`, Better Auth resolves the baseURL once from the first request and caches it. If the first request is a health check (which arrives with `Host: backend.internal`), all subsequent requests use that cached value.

**Fix**: Use `allowedHosts` — it derives baseURL per-request and never caches.

---

## 7. BETTER_AUTH_URL env var overrides everything

**Symptom**: You removed `baseURL` from the config to let `trustedProxyHeaders` work, but Better Auth still uses the wrong origin.

**Root cause**: Better Auth's `getBaseURL()` checks the `BETTER_AUTH_URL` environment variable before checking forwarded headers. If this env var is set (e.g., as a Fly.io secret), it takes precedence.

**Fix**: Either:
- Remove the `BETTER_AUTH_URL` env var entirely (risky — health checks need it)
- Use `allowedHosts` with `fallback: process.env.BETTER_AUTH_URL` — this bypasses the internal env var check while still having a fallback for non-proxied requests

---

## 8. OAuth callback hits backend directly (skips proxy)

**Symptom**: After Google OAuth, the browser lands on `https://backend.fly.dev/auth/callback/google` instead of going through the frontend proxy.

**Root cause**: Better Auth constructed the callback URL using the backend's origin instead of the frontend's. This means the forwarding headers weren't set correctly, or `allowedHosts` didn't match the frontend domain.

**Fix**:
1. Verify the proxy sets `X-Forwarded-Host: frontend.com` (not just strips headers)
2. Verify `allowedHosts` includes `frontend.com`
3. Use the curl verification command to check what `redirect_uri` is being generated

**Quick debug**: The most common cause is that the proxy strips forwarding headers but doesn't set new ones. The proxy must do both: strip (prevent spoofing) then set (tell backend the real origin).
