# Config, Error Types, and Entry Point Reference

Environment configuration, error hierarchy, and Hono entry point wiring for Better Auth.

## Table of Contents
1. [Environment Config](#environment-config)
2. [Error Types](#error-types)
3. [Error Handler Middleware](#error-handler-middleware)
4. [Entry Point](#entry-point)
5. [Middleware Order](#middleware-order)

## Environment Config

Validate all auth-related environment variables at startup using Zod. Fail fast on missing or invalid values — never let the app start with bad config.

```typescript
// src/config.ts
import { z } from "zod";

// Treat empty strings as undefined so optional fields work with .env files
const optionalString = z.preprocess(
  (val) => (val === "" ? undefined : val),
  z.string().optional()
);

const configSchema = z.object({
  // Auth (required)
  BETTER_AUTH_SECRET: z.string().min(32, "Auth secret must be at least 32 characters"),
  BETTER_AUTH_URL: z.string().url().default("http://localhost:3000"),

  // OAuth (optional — enables Google login when both present)
  GOOGLE_CLIENT_ID: optionalString,
  GOOGLE_CLIENT_SECRET: optionalString,

  // Email
  RESEND_API_KEY: optionalString,
  EMAIL_FROM: z.string().default("noreply@example.com"),

  // CORS
  CORS_ORIGIN: z.string().default("*"),
  TRUSTED_ORIGINS: optionalString,

  // Database
  DATABASE_URL: z.string().url(),

  // Node env
  NODE_ENV: z.enum(["development", "test", "production"]).default("development"),
});

export type Config = z.infer<typeof configSchema>;
export const config = configSchema.parse(process.env);

// Reject dev-like secrets in production
if (config.NODE_ENV === "production") {
  const devSecrets = ["super-secret-dev-key", "development-secret", "change-me"];
  if (devSecrets.some((s) => config.BETTER_AUTH_SECRET.includes(s))) {
    console.error("FATAL: Development auth secret detected in production");
    process.exit(1);
  }
}
```

**Why this matters:** A missing `BETTER_AUTH_SECRET` causes silent auth failures. A too-short secret weakens token signing. Catching these at startup prevents debugging phantom 401s in production.

## Error Types

A consistent error hierarchy where every auth/tenant error has a distinct code. This lets the frontend differentiate between "wrong password", "no organization", and "rate limited."

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

**Response envelope** (consistent across all endpoints):
```json
{
  "error": {
    "code": "auth_required",
    "message": "Authentication required"
  },
  "requestId": "uuid"
}
```

## Error Handler Middleware

Catches all errors and returns the consistent envelope. Masks unhandled errors in production.

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

  // Unhandled error — mask in production to prevent information leakage
  const message = config.NODE_ENV === "production"
    ? "Internal server error"
    : err.message;

  console.error("Unhandled error:", err);

  return c.json({
    error: { code: "internal_error", message },
    requestId,
  }, 500);
};
```

## Entry Point

The order middleware is registered determines whether auth works. Get this wrong and you get silent CORS failures or missing request IDs in error responses.

```typescript
// src/index.ts
import { Hono } from "hono";
import { cors } from "hono/cors";
import { config } from "./config";
import { authRoutes } from "./routes/auth";
import { authMiddleware } from "./middleware/auth";
import { tenantContextMiddleware } from "./middleware/tenant-context";
import { errorHandler } from "./middleware/error-handler";

const app = new Hono();

// === GLOBAL MIDDLEWARE (order is critical) ===

// 1. Request ID — must be first so error handler can include it
app.use("*", async (c, next) => {
  c.set("requestId", crypto.randomUUID());
  await next();
});

// 2. Security headers
app.use("*", async (c, next) => {
  if (config.NODE_ENV === "production") {
    c.header("Strict-Transport-Security", "max-age=31536000; includeSubDomains");
  }
  c.header("X-Frame-Options", "DENY");
  await next();
});

// 3. CORS — comes before auth routes because if CORS is registered after,
//    preflight OPTIONS requests fail and cross-origin auth breaks completely.
const origins = config.CORS_ORIGIN.split(",").map((o) => o.trim()).filter(Boolean);
app.use("*", cors({
  origin: origins.length === 1 && origins[0] === "*" ? "*" : origins,
  allowMethods: ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
  allowHeaders: ["Content-Type", "Authorization"],
  exposeHeaders: ["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset", "Retry-After"],
  credentials: origins[0] !== "*", // credentials: true only with specific origins
}));

// 4. Request logging (add pino or your preferred logger here)
// 5. Error handler (catches AppError and returns envelope)
app.onError(errorHandler);

// === PUBLIC ROUTES ===
app.route("/auth", authRoutes);

// === PROTECTED ROUTES ===
// Auth → Tenant Context → Rate Limit → Route handlers
const protectedRoutes = new Hono();
protectedRoutes.use("*", authMiddleware);
protectedRoutes.use("*", tenantContextMiddleware);
// protectedRoutes.use("*", rateLimitMiddleware); // Add when ready
app.route("/v1", protectedRoutes);

// Mount your protected route handlers on protectedRoutes:
// protectedRoutes.route("/projects", projectRoutes);
// protectedRoutes.route("/api-keys", apiKeyRoutes);

export default app;
```

## Middleware Order

| Order | Middleware | Why This Position |
|-------|-----------|-------------------|
| 1 | Request ID | Error handler needs it for the response envelope |
| 2 | Security Headers | Applied to all responses including errors |
| 3 | CORS | Handles OPTIONS preflight before auth rejects them |
| 4 | Logging | Tracks all requests including auth failures |
| 5 | Error Handler | Catch-all for consistent error envelope |
| 6 | Auth (protected only) | Validates credentials |
| 7 | Tenant Context (protected only) | Resolves org from auth |
| 8 | Rate Limit (protected only) | Plan-aware throttling |
