# API Key System Reference

Complete implementation for a custom API key system alongside Better Auth session cookies.

## Why Custom API Keys Instead of Better Auth's Plugin

Better Auth has an API key plugin, but building your own gives you:
- Full control over key format and prefix (e.g., `pyx_` for easy identification)
- Project-scoped keys (Better Auth's plugin scopes to users)
- Soft-delete with revocation timestamps (audit trail)
- Fire-and-forget usage tracking (`lastUsedAt`)
- Custom expiration logic

If your needs are simpler (user-scoped keys, no project hierarchy), Better Auth's built-in plugin works fine.

## Key Generation Utilities

```typescript
// src/lib/api-keys.ts

// Prefix makes keys instantly recognizable and enables fast auth middleware routing.
// Choose something unique to your product (e.g., "sk_", "pk_", "myapp_").
export const API_KEY_PREFIX = "pyx_";

// Base62: alphanumeric only, no special chars.
// Safe in URLs, headers, and JSON without encoding.
const BASE62_CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz";

export function base62Encode(bytes: Uint8Array): string {
  let result = "";
  for (const byte of bytes) {
    result += BASE62_CHARS[byte % 62];
  }
  return result;
}

// SHA-256 hash for storage.
// Web Crypto API is available in Bun, Deno, Cloudflare Workers, and browsers.
const encoder = new TextEncoder();

export async function hashKey(rawKey: string): Promise<string> {
  const data = encoder.encode(rawKey);
  const hashBuffer = await crypto.subtle.digest("SHA-256", data);
  return Buffer.from(hashBuffer).toString("hex");
}
```

## API Key Routes

Three endpoints: create, list, and revoke.

```typescript
// src/routes/api-keys.ts
import { and, count, eq } from "drizzle-orm";
import { Hono } from "hono";
import { z } from "zod";
import { db } from "../db";
import { apiKeys, projects } from "../db/schema";
import { API_KEY_PREFIX, base62Encode, hashKey } from "../lib/api-keys";
import { ForbiddenError, NotFoundError } from "../lib/errors";
import type { AppEnv } from "../types";

const apiKeyRoutes = new Hono<AppEnv>();

// How many chars of the key to show in listings (e.g., "pyx_AbCdEfGh...")
const API_KEY_PREFIX_LENGTH = 12;

const createKeySchema = z.object({
  name: z.string().min(1).max(255),
  projectId: z.string().uuid(),
  expiresAt: z
    .string()
    .datetime()
    .refine((date) => new Date(date) > new Date(), "Expiration date must be in the future")
    .nullable()
    .optional(),
});

// ─── CREATE ──────────────────────────────────────────────
// POST /v1/api-keys
// Returns the plaintext key ONLY in this response.
apiKeyRoutes.post("/", async (c) => {
  const tenant = c.get("tenant");
  const body = await c.req.json();
  const { name, projectId, expiresAt } = createKeySchema.parse(body);

  // Verify project belongs to the tenant's organization.
  // This prevents a user in Org A from creating a key for a project in Org B.
  const project = await db
    .select({ id: projects.id, organizationId: projects.organizationId })
    .from(projects)
    .where(eq(projects.id, projectId))
    .limit(1);

  if (project.length === 0) {
    throw new NotFoundError("Project not found");
  }

  if (project[0].organizationId !== tenant.organizationId) {
    throw new ForbiddenError();
  }

  // Generate cryptographically secure key
  const randomBytes = crypto.getRandomValues(new Uint8Array(32));
  const rawKey = API_KEY_PREFIX + base62Encode(randomBytes);

  // Hash for storage — plaintext NEVER persisted
  const keyHash = await hashKey(rawKey);
  const keyPrefix = rawKey.slice(0, API_KEY_PREFIX_LENGTH);

  const [inserted] = await db
    .insert(apiKeys)
    .values({
      projectId,
      name,
      keyHash,
      keyPrefix,
      expiresAt: expiresAt ? new Date(expiresAt) : null,
    })
    .returning({
      id: apiKeys.id,
      createdAt: apiKeys.createdAt,
    });

  return c.json(
    {
      id: inserted.id,
      key: rawKey, // Plaintext — shown once, never again
      name,
      projectId,
      keyPrefix,
      createdAt: inserted.createdAt,
      expiresAt: expiresAt ?? null,
    },
    201,
  );
});

// ─── LIST ────────────────────────────────────────────────
// GET /v1/api-keys?projectId=...&limit=20&offset=0
// Keys are masked — only prefix shown.
apiKeyRoutes.get("/", async (c) => {
  const tenant = c.get("tenant");
  const projectId = c.req.query("projectId");
  const limit = Math.min(Number(c.req.query("limit") || 20), 100);
  const offset = Math.max(Number(c.req.query("offset") || 0), 0);

  const conditions = [eq(projects.organizationId, tenant.organizationId)];
  if (projectId) {
    conditions.push(eq(apiKeys.projectId, projectId));
  }

  const whereClause = and(...conditions);

  const [items, [{ total }]] = await Promise.all([
    db
      .select({
        id: apiKeys.id,
        name: apiKeys.name,
        keyPrefix: apiKeys.keyPrefix,
        projectId: apiKeys.projectId,
        lastUsedAt: apiKeys.lastUsedAt,
        expiresAt: apiKeys.expiresAt,
        revokedAt: apiKeys.revokedAt,
        createdAt: apiKeys.createdAt,
      })
      .from(apiKeys)
      .innerJoin(projects, eq(apiKeys.projectId, projects.id))
      .where(whereClause)
      .limit(limit)
      .offset(offset),
    db
      .select({ total: count() })
      .from(apiKeys)
      .innerJoin(projects, eq(apiKeys.projectId, projects.id))
      .where(whereClause),
  ]);

  return c.json({
    keys: items.map((k) => ({
      id: k.id,
      name: k.name,
      hint: `${k.keyPrefix}...`,
      projectId: k.projectId,
      createdAt: k.createdAt,
      expiresAt: k.expiresAt,
      lastUsedAt: k.lastUsedAt,
      revoked: k.revokedAt !== null,
    })),
    total,
    hasMore: offset + items.length < total,
  });
});

// ─── REVOKE ──────────────────────────────────────────────
// DELETE /v1/api-keys/:id
// Soft delete via revokedAt timestamp.
apiKeyRoutes.delete("/:id", async (c) => {
  const tenant = c.get("tenant");
  const keyId = c.req.param("id");

  // Verify key exists AND belongs to tenant's org (single query).
  // This prevents ID enumeration — an attacker can't tell whether
  // a key exists in another org or doesn't exist at all.
  const key = await db
    .select({ id: apiKeys.id })
    .from(apiKeys)
    .innerJoin(projects, eq(apiKeys.projectId, projects.id))
    .where(and(eq(apiKeys.id, keyId), eq(projects.organizationId, tenant.organizationId)))
    .limit(1);

  if (key.length === 0) {
    throw new NotFoundError("API key not found");
  }

  await db.update(apiKeys).set({ revokedAt: new Date() }).where(eq(apiKeys.id, keyId));

  return c.body(null, 204);
});

export { apiKeyRoutes };
```

## Security Considerations

1. **Hash-only storage** — The plaintext key is never written to the database. If the DB is compromised, the hashes are useless without the original keys.

2. **Generic errors** — Auth failures for non-existent, revoked, and expired keys all return the same 401 error. This prevents an attacker from distinguishing between these states.

3. **Tenant isolation on revoke** — The DELETE query joins through projects to verify org ownership. Without this, a user could revoke keys in other organizations by guessing UUIDs.

4. **No plaintext in logs** — The key is returned in the HTTP response body but never logged. The `keyPrefix` (first 12 chars) is safe to log and display.

5. **Base62 encoding** — Produces URL-safe keys without special characters. No need for URL encoding in headers or query params.

6. **32 bytes of randomness** — Produces ~190 bits of entropy. Brute-forcing is computationally infeasible.
