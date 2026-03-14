# Reverse Proxy Architecture — Complete Setup Guide

When the frontend (e.g., Next.js on Cloudflare Workers) is a separate application that proxies auth requests to the backend (e.g., Hono on Fly.io), several non-obvious configurations are required for OAuth, cookies, and redirects to work correctly.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Proxy Route Configuration](#proxy-route-configuration)
3. [Forwarding Headers](#forwarding-headers)
4. [Location Header Rewriting](#location-header-rewriting)
5. [Dynamic baseURL with allowedHosts](#dynamic-baseurl-with-allowedhosts)
6. [Frontend Middleware Cookie Detection](#frontend-middleware-cookie-detection)
7. [OAuth Provider Configuration](#oauth-provider-configuration)
8. [CSP Configuration](#csp-configuration)
9. [Edge Runtime (Cloudflare Workers)](#edge-runtime-cloudflare-workers)

---

## Architecture Overview

```
Browser (your-frontend.com)
  |
  |-- POST /api/auth/sign-in/social  -->  Proxy  -->  Backend /auth/sign-in/social
  |                                                     |
  |                                                     v
  |                                              Sets state cookie
  |                                              Returns redirect to Google
  |
  |-- Browser redirects to Google OAuth
  |
  |-- Google redirects to callback URL
  |       (MUST go through proxy, not directly to backend)
  |
  |-- GET /auth/callback/google  -->  Proxy  -->  Backend /auth/callback/google
  |                                                     |
  |                                                     v
  |                                              Reads state cookie (same domain!)
  |                                              Creates session
  |                                              Sets session cookie
  |                                              Redirects to /dashboard
```

The critical insight: **OAuth callbacks MUST go through the same proxy as the initial request**, so cookies (state and session) are on the same domain.

---

## Proxy Route Configuration

Two proxy routes are needed — one for API calls, one for OAuth callbacks:

| Frontend Route | Backend Route | Purpose |
|---|---|---|
| `/api/auth/*` | `/auth/*` | Auth-client API calls (browser SDK) |
| `/auth/*` | `/auth/*` | OAuth callbacks (provider redirects here) |

The auth-client (browser) sends requests to `/api/auth/*`. OAuth callbacks arrive at `/auth/*` because Better Auth constructs callback URLs from `{baseURL}{basePath}/callback/{provider}`, and the derived baseURL from `allowedHosts` is the frontend origin.

### Next.js API Route Example

```typescript
// src/app/api/auth/[...path]/route.ts
import { NextRequest, NextResponse } from "next/server";

const API_URL = process.env.API_URL; // e.g., "https://backend.fly.dev"

async function proxyRequest(request: NextRequest) {
  const url = new URL(request.url);
  const authPath = url.pathname.replace("/api/auth", "/auth");
  const targetUrl = `${API_URL}${authPath}${url.search}`;

  const headers = new Headers(request.headers);

  // Strip then set forwarding headers (see next section)
  headers.delete("x-forwarded-for");
  headers.delete("x-forwarded-host");
  headers.delete("x-forwarded-proto");
  headers.delete("x-real-ip");
  headers.delete("cf-connecting-ip");
  headers.set("x-forwarded-host", url.host);
  headers.set("x-forwarded-proto", url.protocol.replace(":", ""));

  const response = await fetch(targetUrl, {
    method: request.method,
    headers,
    body: request.method !== "GET" && request.method !== "HEAD"
      ? await request.text()
      : undefined,
    redirect: "manual",
  });

  const responseHeaders = new Headers(response.headers);

  // Rewrite Location headers (see section below)
  const location = responseHeaders.get("location");
  if (location && API_URL && location.startsWith(API_URL)) {
    const frontendOrigin = url.origin;
    responseHeaders.set("location", location.replace(API_URL, frontendOrigin));
  }

  return new NextResponse(response.body, {
    status: response.status,
    headers: responseHeaders,
  });
}

export const GET = proxyRequest;
export const POST = proxyRequest;
```

```typescript
// src/app/auth/[...path]/route.ts
// Same handler — reuse for OAuth callbacks
export { GET, POST } from "../api/auth/[...path]/route";
```

---

## Forwarding Headers

The proxy MUST set `X-Forwarded-Host` and `X-Forwarded-Proto` so Better Auth knows the real origin. This is how Better Auth constructs the correct OAuth callback URL.

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

**Why both strip AND set?** Stripping prevents clients from spoofing these headers. Setting them tells the backend the true origin of the request. The proxy is the trusted boundary — it's the only thing that knows the real origin.

---

## Location Header Rewriting

When the backend returns a redirect (302), the `Location` header points to the backend's origin. The proxy must rewrite it to the frontend:

```typescript
const location = responseHeaders.get("location");
if (location && API_URL && location.startsWith(API_URL)) {
  const frontendOrigin = new URL(request.url).origin;
  responseHeaders.set("location", location.replace(API_URL, frontendOrigin));
}
```

Without this, redirects after OAuth callback would send the user to the backend domain instead of the frontend.

---

## Dynamic baseURL with allowedHosts

**DO NOT** use a static `baseURL` string in the backend's Better Auth config. It breaks the proxy architecture because:

- A static baseURL caches on first request (often a health check with `Host: backend.internal`), permanently setting the wrong origin
- `trustedProxyHeaders: true` alone does NOT work when `baseURL` is set — the static value takes precedence
- The `BETTER_AUTH_URL` env var also overrides forwarded headers (it's checked before headers in the priority chain)

**The correct approach** — use `allowedHosts` with a `fallback`:

```typescript
export const auth = betterAuth({
  baseURL: {
    allowedHosts: [
      "your-frontend.com",      // Frontend domain (via proxy)
      "your-backend.fly.dev",   // Backend domain (direct access)
      "localhost",              // Local development
      "*.fly.dev",              // Platform internal routing
    ],
    fallback: process.env.BETTER_AUTH_URL, // For health checks / unmatched hosts
  },
  basePath: "/auth",

  advanced: {
    // Required for allowedHosts to read X-Forwarded-Host from the proxy
    trustedProxyHeaders: true,
  },
  // ...
});
```

**How allowedHosts works internally:**
1. Reads `X-Forwarded-Host` header (set by proxy), falls back to `Host` header
2. Validates against the allowedHosts list (supports wildcards like `*.fly.dev`)
3. Constructs baseURL per-request (not cached!)
4. If no match, uses `fallback`
5. OAuth callback URL = `{derived-baseURL}{basePath}/callback/{provider}`

**The `getBaseURL()` priority chain** (why `trustedProxyHeaders` alone isn't enough):
1. Static `baseURL` string (if set) — **always wins**
2. `BETTER_AUTH_URL` environment variable — **checked before headers**
3. `X-Forwarded-Host` / `X-Forwarded-Proto` headers — only reached if 1 and 2 are absent
4. Request URL — last resort

`allowedHosts` bypasses this entire priority chain by explicitly reading the forwarded headers and constructing the URL per-request.

---

## Frontend Middleware Cookie Detection

In production with HTTPS, Better Auth adds a `__Secure-` prefix to cookie names. Your frontend middleware MUST check for both:

```typescript
const SESSION_COOKIES = [
  "__Secure-better-auth.session_token",  // Production (HTTPS)
  "better-auth.session_token",            // Development (HTTP)
];

const hasSession = SESSION_COOKIES.some(
  (name) => !!request.cookies.get(name)?.value,
);
```

**Why this happens:** When `baseURL` is a dynamic config object (allowedHosts), Better Auth can't determine the protocol at initialization time. In production (`NODE_ENV=production`), it defaults to secure cookies with the `__Secure-` prefix. If your middleware only checks for `better-auth.session_token`, it will never find the cookie and will redirect authenticated users to sign-in.

This is the most insidious gotcha in the proxy architecture — OAuth completes successfully, session is created, cookie is set, but the frontend doesn't recognize it.

---

## OAuth Provider Configuration

### Google Console Settings

- **Authorized JavaScript origins**: `https://your-frontend.com`
- **Authorized redirect URIs**: `https://your-frontend.com/auth/callback/google`

The redirect URI uses `/auth/callback/google` (NOT `/api/auth/callback/google`) because Better Auth constructs it from `{baseURL}{basePath}/callback/google`, and the derived baseURL from `allowedHosts` is the frontend origin.

### Google Console Propagation

Changes take up to 5 minutes to propagate. If you get `redirect_uri_mismatch` immediately after updating, wait and retry before changing configuration.

### Backend Social Provider Config

```typescript
socialProviders: {
  google: {
    clientId: process.env.GOOGLE_CLIENT_ID!,
    clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
  },
  // Add more as needed:
  // github: { clientId: ..., clientSecret: ... },
},
```

---

## CSP Configuration

If using Content Security Policy headers on the frontend, add required domains:

```typescript
const cspDirectives = [
  "default-src 'self'",
  `script-src 'self' 'unsafe-inline' https://static.cloudflareinsights.com`,
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data: https://lh3.googleusercontent.com", // Google avatars
  "connect-src 'self'",
  "font-src 'self'",
  "frame-ancestors 'none'",
];
```

---

## Edge Runtime (Cloudflare Workers)

If deploying the frontend to Cloudflare Workers, the middleware must use the correct runtime:

```typescript
// Next.js 16
export const runtime = "experimental-edge";
// NOT "edge" — Next.js 16 requires "experimental-edge"
```

For earlier Next.js versions:
```typescript
export const runtime = "edge";
```
