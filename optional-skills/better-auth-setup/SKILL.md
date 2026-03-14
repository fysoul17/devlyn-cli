---
name: better-auth-setup
description: >
  Production-ready Better Auth integration for fullstack projects. Covers both the backend
  (Bun + Hono + Drizzle + PostgreSQL) and the frontend reverse proxy architecture (Next.js,
  Cloudflare Workers, or any framework proxying auth requests to a separate backend). Sets up
  email/password auth, session cookies, OAuth providers (Google, GitHub), API key auth,
  organization/multi-tenant support, email verification, CORS, security headers, auth middleware,
  tenant context, proxy forwarding headers, dynamic baseURL with allowedHosts, cookie prefix
  handling, and test infrastructure — all in one pass with zero gotchas. Use this skill whenever
  setting up Better Auth, adding OAuth/social login, configuring a reverse proxy for auth,
  debugging redirect_uri_mismatch errors, fixing state_mismatch cookie issues, session cookies
  not persisting after OAuth callback, or when the user mentions Better Auth, OAuth proxy,
  auth setup, login, signup, session management, API keys, multi-tenant auth, or
  "session cookie not working".
allowed-tools: Read, Grep, Glob, Edit, Write, Bash
argument-hint: "[new-project-path | 'debug' | 'proxy']"
---

# Better Auth Production Setup

Set up a complete, production-hardened authentication system using Better Auth. This skill covers two deployment architectures:

1. **Backend-only** — Better Auth running directly in a Hono + Bun + Drizzle + PostgreSQL API server
2. **Fullstack with proxy** — A separate frontend (e.g., Next.js on Cloudflare Workers) that proxies auth requests to the backend

The setup produces a dual-auth system: session cookies for browser users and API keys for programmatic access, with multi-tenant organization support and plan-based access control. Every configuration choice addresses a real production gotcha that caused hours of debugging.

## Reference Files

Read these when each step directs you to them:

- `${CLAUDE_SKILL_DIR}/references/schema.md` — Complete Drizzle schema (auth, org, API key tables)
- `${CLAUDE_SKILL_DIR}/references/middleware.md` — Auth middleware, tenant context, types, error handler
- `${CLAUDE_SKILL_DIR}/references/api-keys.md` — Key generation, CRUD routes, security patterns
- `${CLAUDE_SKILL_DIR}/references/config-and-entry.md` — Env config, error types, entry point wiring
- `${CLAUDE_SKILL_DIR}/references/testing.md` — Test preload, seed factory, integration patterns
- `${CLAUDE_SKILL_DIR}/references/proxy-setup.md` — Reverse proxy architecture, forwarding headers, OAuth callback routing
- `${CLAUDE_SKILL_DIR}/references/proxy-gotchas.md` — Proxy-specific troubleshooting (redirect_uri_mismatch, state_mismatch, cookie prefix issues)

## Handling Input

Parse `$ARGUMENTS` to determine the mode:

- **Empty or project path**: Detect architecture, then run the full setup workflow
- **`debug`**: Skip to the verification checklist (Step 11) to diagnose an existing setup
- **`proxy`**: Skip to proxy-specific steps (Steps 12-14) for an existing backend
- **Specific step number** (e.g., `step 3`): Jump to that step for targeted work

If `$ARGUMENTS` is empty, ask the user for the project path or confirm the current directory.

## Step 0: Detect Architecture

Before starting, determine the deployment architecture:

1. Check if the project has a **separate frontend** that proxies to the backend (look for Next.js, proxy routes, `API_URL` env vars)
2. Check if the **current project IS the backend** (Hono, Express, or similar server framework with Better Auth)

| Architecture | Signals | Steps |
|---|---|---|
| Backend-only | Hono/Express project, no frontend proxy | Steps 1-11 |
| Frontend proxy (setting up frontend) | Next.js/Remix project with `API_URL` pointing to a backend | Steps 12-14 |
| Fullstack (both) | Both projects accessible | Steps 1-14 |

If uncertain, ask the user which architecture they're using.

---

## Workflow

Follow this exact sequence. Each step builds on the previous one, and skipping ahead causes cascading issues.

### Step 1: Configure Environment

**Entry:** Project has `package.json` with Hono and Drizzle installed.
**Exit:** `src/config.ts` exists with Zod validation, `.env` has `BETTER_AUTH_SECRET`.

Install dependencies:
```bash
bun add better-auth @better-auth/cli drizzle-orm pino resend zod
bun add -d drizzle-kit
```

Generate the auth secret immediately (do not use a placeholder):
```bash
bunx @better-auth/cli@latest secret
```

Read `${CLAUDE_SKILL_DIR}/references/config-and-entry.md` for the complete Zod config implementation. Key env vars:

| Variable | Required | Purpose |
|----------|----------|---------|
| `BETTER_AUTH_SECRET` | Yes | Token signing (min 32 chars) |
| `BETTER_AUTH_URL` | Yes | Base URL for auth service |
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `TRUSTED_ORIGINS` | Production | Comma-separated frontend origins |
| `CORS_ORIGIN` | No | CORS allowed origins (default: `*`) |
| `RESEND_API_KEY` | No | Email delivery (console fallback if absent) |

---

### Step 2: Define Database Schema

**Entry:** Config validated at startup.
**Exit:** Migration applied, tables created in PostgreSQL.

Read `${CLAUDE_SKILL_DIR}/references/schema.md` for the complete schema. Key decisions:

- Use **plural table names** (`users`, `sessions`) — mapped to Better Auth's singular models in Step 3
- Use **UUIDs** for all primary keys
- Add **indexes** on foreign keys and frequently-queried columns
- `api_keys` stores only the **hash**, never the plaintext
- `organizations` needs a `plan` column for tiered access control

After defining the schema, generate and apply migrations:
```bash
bunx drizzle-kit generate
bunx drizzle-kit migrate
```

---

### Step 3: Create Better Auth Instance

**Entry:** Schema migrated, config module ready.
**Exit:** `src/lib/auth.ts` with all plugins and hooks configured.

This is the most critical file. It addresses every known production gotcha:

```typescript
// src/lib/auth.ts
import { betterAuth } from "better-auth";
import { drizzleAdapter } from "better-auth/adapters/drizzle";
import { organization } from "better-auth/plugins";

export const auth = betterAuth({
  // Always set basePath explicitly — missing this causes route mismatches
  // between where Hono mounts auth routes and where Better Auth handles them.
  basePath: "/auth",

  // For backend-only: use a static baseURL.
  // For proxy architecture: use allowedHosts (see Step 12).
  baseURL: config.BETTER_AUTH_URL,
  secret: config.BETTER_AUTH_SECRET,

  // Required for cross-origin cookie auth. Without this, a separate frontend
  // app cannot authenticate because Better Auth rejects the origin.
  trustedOrigins: config.TRUSTED_ORIGINS
    ? config.TRUSTED_ORIGINS.split(",").map((o) => o.trim()).filter(Boolean)
    : [],

  // Map plural Drizzle table names to Better Auth's singular model names.
  // Better Auth expects "user", "session", etc. If your Drizzle schema uses
  // "users", "sessions", you need this mapping or queries fail silently.
  database: drizzleAdapter(db, {
    provider: "pg",
    schema: {
      ...schema,
      user: schema.users,
      session: schema.sessions,
      account: schema.accounts,
      verification: schema.verifications,
      organization: schema.organizations,
      member: schema.orgMemberships,
      invitation: schema.invitations,
    },
  }),

  emailAndPassword: {
    enabled: true,
    minPasswordLength: 8,
    requireEmailVerification: true,
    sendResetPassword: async ({ user, url }) => {
      await sendEmail({ to: user.email, subject: "Reset your password",
        html: `<p>Click <a href="${url}">here</a> to reset your password.</p>` });
    },
  },

  emailVerification: {
    sendOnSignUp: true,
    sendVerificationEmail: async ({ user, url }) => {
      await sendEmail({ to: user.email, subject: "Verify your email",
        html: `<p>Click <a href="${url}">here</a> to verify your email.</p>` });
    },
  },

  session: { cookieCache: { enabled: true, maxAge: 5 * 60 } },

  plugins: [organization()],

  // Better Auth's organization plugin does NOT auto-create an org on signup.
  // If your API requires tenant context (org membership), users will get 403
  // on every request after signup. This hook creates a personal org automatically.
  databaseHooks: {
    user: {
      create: {
        after: async (user) => {
          try {
            const name = user.name || user.email.split("@")[0];
            const orgSlug = `${slugify(name)}-${user.id.slice(-8)}`;
            const [org] = await db.insert(schema.organizations)
              .values({ name: `${name}'s Org`, slug: orgSlug, plan: "free" })
              .returning();
            await db.insert(schema.orgMemberships)
              .values({ organizationId: org.id, userId: user.id, role: "owner" });
          } catch (error) {
            // Log but don't crash signup — a missing org is recoverable,
            // a failed signup is not.
            console.error("Failed to create personal org:", user.id, error);
          }
        },
      },
    },
  },
});
```

### Gotchas This Config Addresses

| Setting | What happens if missing |
|---------|----------------------|
| `basePath: "/auth"` | Auth routes 404 because Better Auth handles at `/` while Hono mounts at `/auth` |
| `trustedOrigins` | Cross-origin cookie auth fails silently |
| Table name mapping | Drizzle queries fail silently (plural vs singular mismatch) |
| `databaseHooks` auto-org | New users 403 on all protected endpoints |
| `try/catch` in hook | Slug collision crashes signup instead of just skipping org creation |

---

### Step 4: Set Up Email Delivery

**Entry:** Auth instance configured with email callbacks.
**Exit:** `src/lib/email.ts` with Resend integration and dev fallback.

```typescript
// src/lib/email.ts
import { Resend } from "resend";
import { config } from "../config";

let resend: Resend | null = null;
function getResendClient(): Resend | null {
  if (!config.RESEND_API_KEY) return null;
  if (!resend) resend = new Resend(config.RESEND_API_KEY);
  return resend;
}

export async function sendEmail({ to, subject, html }: { to: string; subject: string; html: string }) {
  const client = getResendClient();
  if (!client) {
    console.log(`[EMAIL] To: ${to} | Subject: ${subject}`);
    return;
  }
  const { error } = await client.emails.send({ from: config.EMAIL_FROM, to, subject, html });
  if (error) throw new Error(`Email delivery failed: ${error.message}`);
}
```

Test email leaks are a real risk — when `RESEND_API_KEY` is in your `.env`, test signups send real emails. Step 10 addresses this by clearing the key in the test preload.

---

### Step 5: Mount Auth Routes

**Entry:** Auth instance and email module ready.
**Exit:** `/auth/*` endpoints responding to signup, login, session, signout.

```typescript
// src/routes/auth.ts
import { Hono } from "hono";
import { auth } from "../lib/auth";

export const authRoutes = new Hono();

// Pass c.req.raw (the standard Request object), NOT c or c.req.
// Better Auth expects a standard Request. Passing the Hono wrapper causes
// type errors or silent failures.
authRoutes.on(["POST", "GET"], "/*", (c) => auth.handler(c.req.raw));
```

---

### Step 6: Build Auth Middleware

**Entry:** Auth routes mounted.
**Exit:** `src/middleware/auth.ts` validates API keys and session cookies.

Read `${CLAUDE_SKILL_DIR}/references/middleware.md` for the complete implementation. The middleware:
- Detects API keys via `Authorization: Bearer pyx_...` prefix
- Validates via SHA-256 hash lookup + revocation + expiration checks
- Falls back to Better Auth session cookie validation
- Explicitly rejects non-`pyx_` Bearer tokens (prevents confusing silent failures)
- Updates `lastUsedAt` fire-and-forget (no request blocking)
- Returns generic 401 for all key failures (prevents key enumeration)

---

### Step 7: Build Tenant Context Middleware

**Entry:** Auth middleware populates `AuthContext` on the request.
**Exit:** `src/middleware/tenant-context.ts` resolves org and plan.

Read `${CLAUDE_SKILL_DIR}/references/middleware.md` for the implementation. Key behaviors:
- API key auth: org already resolved from the key's project, just fetches plan
- Session auth: looks up user's most recent org membership
- Uses distinct error code `no_organization` (not generic `forbidden`) so the frontend can show "Create your first organization" instead of "Access denied"

---

### Step 8: Define Error Types

**Entry:** Middleware needs error classes to throw.
**Exit:** `src/lib/errors.ts` with `AppError` hierarchy, `src/middleware/error-handler.ts`.

Read `${CLAUDE_SKILL_DIR}/references/config-and-entry.md` for the complete error hierarchy and handler. Every error has a distinct `code` field for frontend differentiation:

| Error Class | Code | Status |
|-------------|------|--------|
| `AuthError` | `auth_required` | 401 |
| `ForbiddenError` | `forbidden` | 403 |
| `NotFoundError` | `not_found` | 404 |
| `ValidationError` | `validation_error` | 422 |
| `RateLimitError` | `rate_limited` | 429 |

---

### Step 9: Wire Entry Point

**Entry:** All middleware and routes implemented.
**Exit:** `src/index.ts` with correct middleware ordering.

Read `${CLAUDE_SKILL_DIR}/references/config-and-entry.md` for the complete entry point. The middleware order is:

1. **Request ID** — first, so error handler can include it in responses
2. **Security Headers** — HSTS (production), X-Frame-Options
3. **CORS** — before auth routes, otherwise OPTIONS preflight fails
4. **Logging** — tracks all requests including auth failures
5. **Error Handler** — catches `AppError` and returns consistent envelope
6. **Auth** (protected `/v1/*` only) — validates credentials
7. **Tenant Context** (protected only) — resolves org from auth
8. **Rate Limit** (protected only) — plan-aware throttling

CORS before auth routes is non-negotiable. If registered after, preflight OPTIONS requests fail and browsers block all cross-origin requests.

---

### Step 10: Set Up Test Infrastructure

**Entry:** Application fully functional.
**Exit:** Test preload, seed factory, integration app, cleanup utilities.

Read `${CLAUDE_SKILL_DIR}/references/testing.md` for the complete test setup. Essential components:

1. **Test preload** (`bunfig.toml` + `setup.ts`) — clears `RESEND_API_KEY`, bridges `TEST_DATABASE_URL`
2. **Seed factory** (`seedTestData()`) — creates full tenant hierarchy with unique slugs
3. **Integration app** (`createIntegrationApp()`) — full middleware chain matching production
4. **Database cleanup** (`cleanupDatabase()`) — deletes in FK dependency order

---

### Step 11: Verify Setup

**Entry:** All code implemented.
**Exit:** Every checklist item passes.

Run through each item. Every one represents a real production bug that was discovered the hard way.

<rules>
Do not skip any checklist item. Each one catches a specific class of bug.
If any item fails, fix the root cause before proceeding.
</rules>

**Auth Flow**
- [ ] Signup creates user + auto-creates personal org with `plan: "free"`
- [ ] Signup sends verification email (check console in dev)
- [ ] Login with verified email returns session cookie
- [ ] `GET /auth/session` returns session data
- [ ] `GET /auth/session` with invalid cookie returns `null` body (not `{ session: null }`)
- [ ] Signout destroys session

**API Key Auth**
- [ ] Creating API key returns plaintext once, stores only hash
- [ ] `Authorization: Bearer pyx_...` resolves to correct project and org
- [ ] Revoked keys return 401
- [ ] Expired keys return 401
- [ ] Non-`pyx_` Bearer tokens explicitly rejected

**Cross-Origin**
- [ ] OPTIONS preflight returns correct CORS headers
- [ ] Frontend on different origin can complete signup + login flow
- [ ] `credentials: true` set when using specific origins (not `*`)
- [ ] `TRUSTED_ORIGINS` includes frontend URL

**Tenant Context**
- [ ] API key auth resolves org from key's project
- [ ] Session auth resolves org from user's membership
- [ ] User with no org gets `no_organization` error code (not generic 403)
- [ ] No cross-tenant data access possible

**Security**
- [ ] `BETTER_AUTH_SECRET` is 32+ chars (generated, not placeholder)
- [ ] Dev secret rejected in production
- [ ] HSTS header present in production responses
- [ ] Error messages masked in production
- [ ] No key enumeration possible through auth error responses

**Testing**
- [ ] `RESEND_API_KEY` cleared in test setup (no real emails sent)
- [ ] Test database uses separate connection (`TEST_DATABASE_URL`)
- [ ] Seed data uses unique slugs (parallel test safety)
- [ ] Database cleanup respects FK dependency order

---

## API Key System

For the complete custom API key implementation (generation, validation, CRUD routes), read `${CLAUDE_SKILL_DIR}/references/api-keys.md`.

Summary:
- **Format**: `pyx_` prefix + 32 random bytes base62-encoded (~50 chars)
- **Storage**: SHA-256 hash only — plaintext never persisted
- **Validation**: Hash lookup → revocation check → expiration check → resolve project/org
- **CRUD**: Create (returns plaintext once), List (shows prefix only), Revoke (soft delete)

---

## Slugify Utility

Shared across project creation and auto-org creation to prevent duplicate implementations:

```typescript
// src/lib/slug.ts
export function slugify(text: string): string {
  return text
    .toLowerCase().trim()
    .replace(/[^\w\s-]/g, "")
    .replace(/[\s_]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 50);
}
```

Always append a unique suffix (UUID slice or timestamp) to prevent collisions.

---

---

## Proxy Architecture (Steps 12-14)

These steps apply when the frontend is a separate application that proxies auth requests to the backend. Read `${CLAUDE_SKILL_DIR}/references/proxy-setup.md` for the complete guide with code examples.

### Step 12: Configure Dynamic baseURL on Backend

**Entry:** Backend auth works directly (Steps 1-11 complete or existing backend).
**Exit:** Backend derives baseURL per-request from forwarded headers.

Replace the static `baseURL` in `src/lib/auth.ts` with `allowedHosts`:

```typescript
export const auth = betterAuth({
  baseURL: {
    allowedHosts: [
      "your-frontend.com",      // Frontend domain (via proxy)
      "your-backend.fly.dev",   // Backend domain (direct access)
      "localhost",              // Local development
      "*.fly.dev",              // Platform internal routing
    ],
    fallback: process.env.BETTER_AUTH_URL,
  },
  basePath: "/auth",
  advanced: {
    trustedProxyHeaders: true,  // Read X-Forwarded-Host from the proxy
  },
  // ... rest of config unchanged
});
```

**Why `allowedHosts` instead of a static baseURL:**
- A static `baseURL` caches on first request (often a health check with internal hostname)
- `trustedProxyHeaders: true` alone does NOT work when `baseURL` is set — the static value takes precedence
- The `BETTER_AUTH_URL` env var also overrides forwarded headers
- `allowedHosts` derives baseURL per-request and never caches

Add Google OAuth (or other social providers):

```typescript
socialProviders: {
  google: {
    clientId: process.env.GOOGLE_CLIENT_ID!,
    clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
  },
},
```

---

### Step 13: Configure Frontend Proxy

**Entry:** Backend uses `allowedHosts` with `trustedProxyHeaders`.
**Exit:** Frontend proxies auth requests and OAuth callbacks correctly.

The frontend proxy must do three things. Read `${CLAUDE_SKILL_DIR}/references/proxy-setup.md` for complete code.

#### 13a. Create two proxy routes

| Frontend Route | Backend Route | Purpose |
|---|---|---|
| `/api/auth/*` | `/auth/*` | Auth-client API calls (browser) |
| `/auth/*` | `/auth/*` | OAuth callbacks (Google redirects here) |

The second route is critical — Better Auth constructs OAuth callback URLs from `{baseURL}{basePath}/callback/{provider}`. When it derives baseURL from the frontend origin, the callback becomes `https://your-frontend.com/auth/callback/google`.

#### 13b. Set forwarding headers (not just strip them)

```typescript
// Strip user-provided headers to prevent spoofing
headers.delete("x-forwarded-for");
headers.delete("x-forwarded-host");
headers.delete("x-forwarded-proto");
headers.delete("x-real-ip");
headers.delete("cf-connecting-ip");

// Then set correct values from the actual request
headers.set("x-forwarded-host", url.host);
headers.set("x-forwarded-proto", url.protocol.replace(":", ""));
```

#### 13c. Rewrite Location headers

When the backend returns a redirect, rewrite the `Location` header to point to the frontend origin.

---

### Step 14: Configure Frontend Middleware

**Entry:** Proxy routes working.
**Exit:** Middleware detects session cookies correctly, including `__Secure-` prefix.

In production with HTTPS, Better Auth adds a `__Secure-` prefix to cookie names. Your middleware MUST check for both:

```typescript
const SESSION_COOKIES = [
  "__Secure-better-auth.session_token",  // Production (HTTPS)
  "better-auth.session_token",            // Development (HTTP)
];

const hasSession = SESSION_COOKIES.some(
  (name) => !!request.cookies.get(name)?.value,
);
```

This is the most insidious gotcha in the proxy architecture — OAuth completes successfully, session is created, cookie is set, but the frontend middleware doesn't recognize it because it only checks the unprefixed name.

Configure the OAuth provider (Google Console example):
- **Authorized JavaScript origins**: `https://your-frontend.com`
- **Authorized redirect URIs**: `https://your-frontend.com/auth/callback/google`

The redirect URI uses `/auth/callback/google`, NOT `/api/auth/callback/google`.

---

### Step 15: Verify Proxy Setup

In addition to the Step 11 checklist, verify:

**Proxy**
- [ ] Proxy route exists at `/api/auth/*` (for auth-client API calls)
- [ ] Proxy route exists at `/auth/*` (for OAuth callbacks)
- [ ] Proxy strips THEN sets `X-Forwarded-Host` and `X-Forwarded-Proto`
- [ ] Proxy rewrites `Location` headers from backend origin to frontend origin

**Dynamic baseURL**
- [ ] Backend uses `allowedHosts` (not a static `baseURL` string)
- [ ] `allowedHosts` includes frontend domain, backend domain, and `localhost`
- [ ] `fallback` is set for health checks
- [ ] `trustedProxyHeaders: true` is in `advanced` config

**OAuth**
- [ ] Google Console redirect URI is `https://{frontend}/auth/callback/google`
- [ ] Verification curl returns `redirect_uri` with frontend domain (not backend)

**Cookies**
- [ ] Middleware checks both `__Secure-better-auth.session_token` and `better-auth.session_token`

Test with:
```bash
curl -s -X POST "https://your-frontend.com/api/auth/sign-in/social" \
  -H "Content-Type: application/json" \
  -d '{"provider":"google","callbackURL":"/dashboard"}' | \
  python3 -c "import sys,json,urllib.parse; data=json.load(sys.stdin); url=data.get('url',''); params=urllib.parse.parse_qs(urllib.parse.urlparse(url).query); print('redirect_uri:', params.get('redirect_uri',['N/A'])[0])"
```

Expected: `redirect_uri: https://your-frontend.com/auth/callback/google`

For detailed troubleshooting of proxy-specific failures, read `${CLAUDE_SKILL_DIR}/references/proxy-gotchas.md`.

---

## Quick Reference: Common Mistakes

### Backend Mistakes

| Mistake | Consequence | Prevention |
|---------|-------------|------------|
| Missing `basePath` | Auth routes 404 | Set `basePath: "/auth"` explicitly |
| Missing `trustedOrigins` | Cross-origin auth silent failure | Configure from `TRUSTED_ORIGINS` env |
| No table name mapping | Queries fail silently | Map plural to singular in adapter |
| No auto-org on signup | Users 403 everywhere | `databaseHooks.user.create.after` |
| CORS after auth routes | Preflight fails | CORS before all route handlers |
| `c.req` not `c.req.raw` | Type errors or silent failure | Always `auth.handler(c.req.raw)` |
| `RESEND_API_KEY` in tests | Real emails to test addresses | Clear in test preload |
| Generic 403 for no org | Frontend can't show helpful UX | Distinct `no_organization` code |
| `credentials: true` + `*` | Browser rejects response | Specific origins with credentials |

### Proxy Mistakes

| Mistake | Consequence | Prevention |
|---------|-------------|------------|
| Static `baseURL` with proxy | OAuth callback uses wrong domain | Use `allowedHosts` + `fallback` |
| `trustedProxyHeaders` without `allowedHosts` | Static baseURL or env var overrides | `allowedHosts` bypasses priority chain |
| Only `/api/auth/*` proxy route | OAuth callback 404 (Google redirects to `/auth/callback/*`) | Add `/auth/*` proxy route |
| Proxy only strips headers | Backend doesn't know frontend origin | Strip THEN set `X-Forwarded-Host` |
| Middleware checks only `better-auth.session_token` | Authenticated users redirected to sign-in | Check both `__Secure-` prefixed and plain |
| Google Console redirect URI with `/api/auth/` | `redirect_uri_mismatch` from Google | Use `/auth/callback/google` (not `/api/auth/`) |
| `BETTER_AUTH_URL` env var set | Overrides forwarded headers | Use `allowedHosts` with `fallback` instead |

<example>
**User**: "Set up Better Auth in my new Hono project at ./my-api"

**Steps taken**:
1. Read project's package.json to confirm Hono + Drizzle
2. Install dependencies (better-auth, resend, zod, etc.)
3. Generate auth secret, create .env
4. Create src/config.ts with Zod validation
5. Create src/db/schema.ts with all auth + org + API key tables
6. Run drizzle-kit generate + migrate
7. Create src/lib/auth.ts with basePath, trustedOrigins, table mapping, databaseHooks
8. Create src/lib/email.ts with Resend + console fallback
9. Create src/routes/auth.ts with c.req.raw handler
10. Create src/middleware/auth.ts (dual-path: API key + session)
11. Create src/middleware/tenant-context.ts
12. Create src/lib/errors.ts + src/middleware/error-handler.ts
13. Create src/index.ts with correct middleware order
14. Create test utilities (setup.ts, db.ts, app.ts)
15. Run verification checklist
</example>

<example>
**User**: "I have a Next.js frontend and Hono backend. I need Google OAuth working through the proxy."

**Steps taken**:
1. Detect proxy architecture (Step 0)
2. Update backend auth.ts: replace static baseURL with allowedHosts + trustedProxyHeaders (Step 12)
3. Add Google social provider to auth config (Step 12)
4. Create /api/auth/* and /auth/* proxy routes on frontend (Step 13)
5. Set forwarding headers in proxy (Step 13)
6. Add Location header rewriting (Step 13)
7. Update frontend middleware to check both cookie names (Step 14)
8. Configure Google Console redirect URI (Step 14)
9. Run proxy verification checklist (Step 15)
</example>
