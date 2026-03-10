# Test Infrastructure Reference

Test setup, seed factories, and integration test patterns for Better Auth with Bun.

## Table of Contents
1. [Test Preload](#test-preload)
2. [Seed Data Factory](#seed-data-factory)
3. [Integration Test App](#integration-test-app)
4. [Database Cleanup](#database-cleanup)
5. [Key Testing Patterns](#key-testing-patterns)

## Test Preload

Prevents the most common testing pitfall: real emails sent during test runs.

```typescript
// src/test-utils/setup.ts — preloaded via bunfig.toml
// Without this, test signups send real emails through Resend
// when RESEND_API_KEY is in your .env file.
process.env.NODE_ENV = "test";
process.env.RESEND_API_KEY = ""; // Force email to console-log fallback

// Bridge test database — use a separate DB for tests
if (process.env.TEST_DATABASE_URL) {
  process.env.DATABASE_URL = process.env.TEST_DATABASE_URL;
}
```

```toml
# bunfig.toml
[test]
preload = ["./src/test-utils/setup.ts"]
```

**Why preload?** Bun's preload runs before any test file imports. This guarantees that config validation (which runs at import time) sees the correct environment variables. Setting `RESEND_API_KEY = ""` before any module loads ensures the email module's lazy client never initializes.

## Seed Data Factory

Creates a complete tenant hierarchy for integration tests. Every call produces unique identifiers to prevent collisions in parallel test runs.

```typescript
// src/test-utils/db.ts
import { db } from "../db";
import {
  organizations, users, orgMemberships,
  projects, apiKeys, sessions, accounts,
  verifications, invitations,
} from "../db/schema";

export async function seedTestData() {
  const uniqueSuffix = `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;

  // Create org → user → membership → project → API key
  const [org] = await db.insert(organizations).values({
    name: `Test Org ${uniqueSuffix}`,
    slug: `test-org-${uniqueSuffix}`,
    plan: "free",
  }).returning();

  const [user] = await db.insert(users).values({
    email: `test-${uniqueSuffix}@example.com`,
    name: "Test User",
    emailVerified: true,
  }).returning();

  await db.insert(orgMemberships).values({
    organizationId: org.id,
    userId: user.id,
    role: "owner",
  });

  const [project] = await db.insert(projects).values({
    organizationId: org.id,
    name: `Test Project ${uniqueSuffix}`,
    slug: `test-project-${uniqueSuffix}`,
  }).returning();

  // Generate API key
  const { key, hash, prefix } = await generateTestApiKey();
  const [apiKey] = await db.insert(apiKeys).values({
    projectId: project.id,
    name: "Test Key",
    keyHash: hash,
    keyPrefix: prefix,
  }).returning();

  return { org, user, project, apiKey, plaintextKey: key };
}

// Helper: generate a test API key
async function generateTestApiKey() {
  const { API_KEY_PREFIX, base62Encode, hashKey } = await import("../lib/api-keys");
  const randomBytes = crypto.getRandomValues(new Uint8Array(32));
  const key = API_KEY_PREFIX + base62Encode(randomBytes);
  const hash = await hashKey(key);
  const prefix = key.slice(0, 12);
  return { key, hash, prefix };
}
```

**Key design decisions:**
- `uniqueSuffix` uses `Date.now()` + random chars for collision-free parallel tests
- `emailVerified: true` so tests don't need to go through email verification flow
- Returns `plaintextKey` so tests can immediately make authenticated requests

## Integration Test App

Builds the full middleware chain matching production. This catches middleware ordering bugs before they reach production.

```typescript
// src/test-utils/app.ts
import { Hono } from "hono";

// Lazy imports to avoid circular dependency issues during test setup
export function createIntegrationApp() {
  const { authMiddleware } = require("../middleware/auth");
  const { tenantContextMiddleware } = require("../middleware/tenant-context");
  const { rateLimitMiddleware } = require("../middleware/rate-limit");

  const app = new Hono();

  // Request ID
  app.use("*", async (c, next) => {
    c.set("requestId", crypto.randomUUID());
    await next();
  });

  // Auth → Tenant Context → Rate Limit (same order as production)
  app.use("*", authMiddleware);
  app.use("*", tenantContextMiddleware);
  app.use("*", rateLimitMiddleware);

  // Mount route handlers here...
  return app;
}
```

**Why lazy imports?** The auth module imports the database module, which reads `DATABASE_URL` from the environment. If imported eagerly at the top level, the test preload script might not have run yet, causing config validation to fail.

## Database Cleanup

Delete tables in FK dependency order to avoid constraint violations.

```typescript
// Clean tables in FK dependency order
export async function cleanupDatabase() {
  // Children first, parents last
  await db.delete(apiKeys);
  await db.delete(projects);
  await db.delete(orgMemberships);
  await db.delete(sessions);
  await db.delete(accounts);
  await db.delete(verifications);
  await db.delete(invitations);
  await db.delete(organizations);
  await db.delete(users);
}
```

**Order matters.** If you try to delete `organizations` before `projects`, the FK constraint on `projects.organization_id` will reject the delete. Start from leaf tables and work toward root tables.

## Key Testing Patterns

### Test Auth via API Key

```typescript
import { describe, test, expect, beforeAll, afterAll } from "bun:test";

describe("Protected endpoint", () => {
  let testData: Awaited<ReturnType<typeof seedTestData>>;

  beforeAll(async () => {
    testData = await seedTestData();
  });

  afterAll(async () => {
    await cleanupDatabase();
  });

  test("returns 200 with valid API key", async () => {
    const app = createIntegrationApp();
    const res = await app.request("/v1/endpoint", {
      headers: {
        Authorization: `Bearer ${testData.plaintextKey}`,
      },
    });
    expect(res.status).toBe(200);
  });

  test("returns 401 without auth", async () => {
    const app = createIntegrationApp();
    const res = await app.request("/v1/endpoint");
    expect(res.status).toBe(401);
  });
});
```

### Test Signup Flow

```typescript
test("signup creates user and personal org", async () => {
  const res = await app.request("/auth/sign-up/email", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      email: `signup-test-${Date.now()}@example.com`,
      password: "secure-password-123",
      name: "Test User",
    }),
  });

  expect(res.status).toBe(200);

  // Verify auto-org creation via databaseHooks
  const user = await db.select().from(users)
    .where(eq(users.email, email)).limit(1);

  const membership = await db.select().from(orgMemberships)
    .where(eq(orgMemberships.userId, user[0].id)).limit(1);

  expect(membership).toHaveLength(1);
  expect(membership[0].role).toBe("owner");
});
```

### Test Tenant Isolation

```typescript
test("cannot access resources from another org", async () => {
  const org1 = await seedTestData();
  const org2 = await seedTestData();

  // Use org1's API key to try accessing org2's project
  const res = await app.request(`/v1/projects/${org2.project.id}`, {
    headers: { Authorization: `Bearer ${org1.plaintextKey}` },
  });

  // Should be 404 (not 403, to prevent ID enumeration)
  expect(res.status).toBe(404);
});
```
