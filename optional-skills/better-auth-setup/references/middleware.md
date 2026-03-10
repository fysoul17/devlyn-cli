# Auth & Tenant Context Middleware Reference

Complete implementations for the dual-path auth middleware and tenant context middleware.

## Table of Contents
1. [Types](#types)
2. [Auth Middleware](#auth-middleware)
3. [Tenant Context Middleware](#tenant-context-middleware)
4. [API Key Utilities](#api-key-utilities)
5. [Error Types](#error-types)

## Types

Define these types in a shared `types.ts` file. They're used across middleware, routes, and tests.

```typescript
// src/types.ts

// API key auth — resolved from Authorization: Bearer pyx_...
export type ApiKeyAuthContext = {
  type: "api_key";
  apiKeyId: string;
  projectId: string;
  organizationId: string;
};

// Session auth — resolved from Better Auth session cookie
export type SessionAuthContext = {
  type: "session";
  userId: string;
  sessionId: string;
};

// Union type — the auth middleware sets one of these
export type AuthContext = ApiKeyAuthContext | SessionAuthContext;

// Tenant context — resolved after auth
export type TenantContext = {
  organizationId: string;
  projectId: string | null;  // null for session auth (no project scope)
  userId: string | null;     // null for API key auth (no user scope)
  plan: string;              // e.g., "free", "pro", "team", "enterprise"
};

// Hono app environment — tells Hono what variables are available
export type AppEnv = {
  Variables: {
    requestId: string;
    auth: AuthContext;
    tenant: TenantContext;
  };
};
```

## Auth Middleware

The auth middleware supports two authentication paths in a single middleware function. This avoids route-level conditional logic and keeps auth centralized.

```typescript
// src/middleware/auth.ts
import { eq } from "drizzle-orm";
import { createMiddleware } from "hono/factory";
import { db } from "../db";
import { apiKeys, projects } from "../db/schema";
import { API_KEY_PREFIX, hashKey } from "../lib/api-keys";
import { auth } from "../lib/auth";
import { AuthError } from "../lib/errors";
import { logger } from "../lib/logger";
import type { AuthContext } from "../types";

export const authMiddleware = createMiddleware<{
  Variables: { auth: AuthContext };
}>(async (c, next) => {
  const authHeader = c.req.header("Authorization");

  // Path 1: API key authentication (Bearer pyx_...)
  if (authHeader?.startsWith(`Bearer ${API_KEY_PREFIX}`)) {
    const rawKey = authHeader.slice("Bearer ".length);
    const authContext = await validateApiKey(rawKey);
    c.set("auth", authContext);
    return next();
  }

  // Path 2: Non-pyx Bearer token — reject with clear guidance
  // Without this check, random Bearer tokens would fall through to session
  // auth and silently fail, confusing the developer.
  if (authHeader?.startsWith("Bearer ")) {
    throw new AuthError("Invalid API key format. Keys must start with 'pyx_'.");
  }

  // Path 3: Session cookie (Better Auth)
  // IMPORTANT: Pass c.req.raw.headers (the raw Request headers),
  // NOT c.req.header() — Better Auth needs the full Headers object.
  const session = await auth.api.getSession({ headers: c.req.raw.headers });

  // GOTCHA: Better Auth returns null (not { session: null }) for invalid sessions.
  // Always check session?.user, not session.user.
  if (session?.user) {
    c.set("auth", {
      type: "session",
      userId: session.user.id,
      sessionId: session.session.id,
    });
    return next();
  }

  // No valid auth found
  throw new AuthError();
});

async function validateApiKey(rawKey: string): Promise<AuthContext> {
  const keyHash = await hashKey(rawKey);

  // Single query: look up key + join project for org info
  const result = await db
    .select({
      keyId: apiKeys.id,
      projectId: apiKeys.projectId,
      revokedAt: apiKeys.revokedAt,
      expiresAt: apiKeys.expiresAt,
      orgId: projects.organizationId,
    })
    .from(apiKeys)
    .innerJoin(projects, eq(apiKeys.projectId, projects.id))
    .where(eq(apiKeys.keyHash, keyHash))
    .limit(1);

  if (result.length === 0) {
    // SECURITY: Generic error — don't reveal whether key exists.
    // An attacker probing keys should see the same error for
    // "key not found" and "key is revoked."
    throw new AuthError();
  }

  const key = result[0];

  // Check revocation
  if (key.revokedAt) {
    throw new AuthError();
  }

  // Check expiration
  if (key.expiresAt && key.expiresAt < new Date()) {
    throw new AuthError();
  }

  // Fire-and-forget: update lastUsedAt without blocking the request.
  // If this fails, the request still succeeds — usage tracking is
  // nice-to-have, not critical path.
  db.update(apiKeys)
    .set({ lastUsedAt: new Date() })
    .where(eq(apiKeys.id, key.keyId))
    .execute()
    .catch((err) => {
      logger.warn({ error: err, apiKeyId: key.keyId }, "Failed to update API key lastUsedAt");
    });

  return {
    type: "api_key",
    apiKeyId: key.keyId,
    projectId: key.projectId,
    organizationId: key.orgId,
  };
}
```

### Design Decisions

1. **Single middleware, two paths** — Keeps auth logic centralized. Routes don't need to know which auth method was used.

2. **Explicit non-pyx Bearer rejection** — Without this, a developer using a random JWT would get a generic "auth required" error after session validation fails. The explicit rejection saves debugging time.

3. **Generic AuthError for all key failures** — Whether the key doesn't exist, is revoked, or is expired, the error is the same. This prevents key enumeration attacks.

4. **Fire-and-forget `lastUsedAt`** — The `.catch()` prevents unhandled promise rejections. The request isn't delayed by a non-critical DB write.

5. **Inner join for org resolution** — A single query fetches the key and its project's org. No second DB round-trip needed.

## Tenant Context Middleware

Runs after auth middleware. Resolves the organization, project (if applicable), and plan for the authenticated entity.

```typescript
// src/middleware/tenant-context.ts
import { desc, eq } from "drizzle-orm";
import { createMiddleware } from "hono/factory";
import { db } from "../db";
import { orgMemberships, organizations } from "../db/schema";
import { AppError, AuthError, ForbiddenError } from "../lib/errors";
import type { AuthContext, TenantContext } from "../types";

export const tenantContextMiddleware = createMiddleware<{
  Variables: { auth: AuthContext; tenant: TenantContext };
}>(async (c, next) => {
  const authCtx = c.get("auth");

  if (!authCtx) {
    throw new AuthError();
  }

  let tenant: TenantContext;

  if (authCtx.type === "api_key") {
    // API key auth: org already resolved in auth middleware, just fetch plan
    const org = await db
      .select({ plan: organizations.plan })
      .from(organizations)
      .where(eq(organizations.id, authCtx.organizationId))
      .limit(1);

    if (org.length === 0) {
      throw new ForbiddenError();
    }

    tenant = {
      organizationId: authCtx.organizationId,
      projectId: authCtx.projectId,
      userId: null,
      plan: org[0].plan,
    };
  } else {
    // Session auth: look up user's org membership
    // For multi-org users, picks most recent membership.
    // TODO: Support explicit org selection via X-Organization-Id header.
    const membership = await db
      .select({
        orgId: orgMemberships.organizationId,
        plan: organizations.plan,
      })
      .from(orgMemberships)
      .innerJoin(organizations, eq(orgMemberships.organizationId, organizations.id))
      .where(eq(orgMemberships.userId, authCtx.userId))
      .orderBy(desc(orgMemberships.createdAt))
      .limit(1);

    if (membership.length === 0) {
      // LESSON: Use a distinct error code, not a generic ForbiddenError.
      // The frontend needs to differentiate "you don't have permission" from
      // "you need to create/join an organization." With a generic 403, the
      // frontend can't show helpful UX like "Create your first organization."
      throw new AppError("no_organization", "No organization membership found", 403);
    }

    tenant = {
      organizationId: membership[0].orgId,
      projectId: null,
      userId: authCtx.userId,
      plan: membership[0].plan,
    };
  }

  c.set("tenant", tenant);
  return next();
});
```

### Design Decisions

1. **Separate from auth middleware** — Auth validates identity. Tenant context resolves authorization scope. Keeping them separate makes each testable independently.

2. **API key already has org** — The auth middleware resolves projectId and organizationId during key validation (via the projects join). No extra DB query needed for the org ID — only one query to fetch the plan.

3. **Most-recent membership for multi-org** — A temporary strategy until `X-Organization-Id` header support is added. Ordered by `createdAt DESC` so the auto-created personal org (from signup) is the default.

4. **Distinct `no_organization` error code** — Enables the frontend to show contextual UX. A generic `forbidden` error gives no indication of what's wrong.

## API Key Utilities

Shared constants and functions for key generation and validation.

```typescript
// src/lib/api-keys.ts

// All API keys start with this prefix. Used for:
// 1. Quick identification in auth middleware
// 2. User-visible hint in the dashboard
// 3. Preventing confusion with other Bearer tokens
export const API_KEY_PREFIX = "pyx_";

// Base62 encoding (alphanumeric only, no special chars)
const BASE62_CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz";

export function base62Encode(bytes: Uint8Array): string {
  let result = "";
  for (const byte of bytes) {
    result += BASE62_CHARS[byte % 62];
  }
  return result;
}

// SHA-256 hash for storage — uses Web Crypto API (available in Bun and browsers)
const encoder = new TextEncoder();

export async function hashKey(rawKey: string): Promise<string> {
  const data = encoder.encode(rawKey);
  const hashBuffer = await crypto.subtle.digest("SHA-256", data);
  return Buffer.from(hashBuffer).toString("hex");
}
```

### Key Generation (in route handler)

```typescript
// Generate cryptographically secure key
const randomBytes = crypto.getRandomValues(new Uint8Array(32));
const rawKey = API_KEY_PREFIX + base62Encode(randomBytes);

// Hash for storage — plaintext NEVER stored
const keyHash = await hashKey(rawKey);
const keyPrefix = rawKey.slice(0, 12); // Visible hint: "pyx_AbCdEfGh"

// Store hash + prefix in database
await db.insert(apiKeys).values({
  projectId,
  name,
  keyHash,
  keyPrefix,
  expiresAt: expiresAt ? new Date(expiresAt) : null,
});

// Return plaintext to user — they'll never see it again
return c.json({ key: rawKey, hint: `${keyPrefix}...` }, 201);
```

## Error Types

```typescript
// src/lib/errors.ts

export class AppError extends Error {
  constructor(
    public code: string,
    message: string,
    public statusCode: number = 500,
    public details?: Record<string, unknown>
  ) {
    super(message);
  }
}

export class AuthError extends AppError {
  constructor(message = "Authentication required") {
    super("auth_required", message, 401);
  }
}

export class ForbiddenError extends AppError {
  constructor(message = "Insufficient permissions") {
    super("forbidden", message, 403);
  }
}

export class NotFoundError extends AppError {
  constructor(message = "Resource not found") {
    super("not_found", message, 404);
  }
}

export class ValidationError extends AppError {
  constructor(message: string, details?: Record<string, unknown>) {
    super("validation_error", message, 422, details);
  }
}

export class RateLimitError extends AppError {
  constructor(retryAfter: number) {
    super("rate_limited", "Too many requests", 429, { retryAfter });
  }
}
```

### Error Handler Middleware

```typescript
// src/middleware/error-handler.ts
import type { ErrorHandler } from "hono";
import { AppError } from "../lib/errors";
import { config } from "../config";

export const errorHandler: ErrorHandler = (err, c) => {
  const requestId = c.get("requestId") ?? "unknown";

  if (err instanceof AppError) {
    return c.json({
      error: {
        code: err.code,
        message: err.message,
        ...(err.details && { details: err.details }),
      },
      requestId,
    }, err.statusCode as any);
  }

  // Unhandled error — mask in production
  const message = config.NODE_ENV === "production"
    ? "Internal server error"
    : err.message;

  console.error("Unhandled error:", err);

  return c.json({
    error: {
      code: "internal_error",
      message,
    },
    requestId,
  }, 500);
};
```
