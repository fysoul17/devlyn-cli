# Database Schema Reference

Complete Drizzle ORM schema for Better Auth with multi-tenant organization support, API keys, and usage tracking.

## Table of Contents
1. [Auth Tables](#auth-tables) — users, sessions, accounts, verifications
2. [Organization Tables](#organization-tables) — organizations, memberships, invitations
3. [Project & API Key Tables](#project--api-key-tables) — projects, api_keys
4. [Supporting Tables](#supporting-tables) — usage, billing, webhooks

## Auth Tables

These tables are managed by Better Auth. Define them in Drizzle with the exact columns Better Auth expects, using your preferred table names (you'll map them in the adapter config).

```typescript
import {
  boolean, index, pgTable, text, timestamp,
  uniqueIndex, uuid, varchar,
} from "drizzle-orm/pg-core";

// Users — core identity table
export const users = pgTable("users", {
  id: uuid("id").primaryKey().defaultRandom(),
  name: varchar("name", { length: 255 }),
  email: varchar("email", { length: 255 }).notNull().unique(),
  emailVerified: boolean("email_verified").notNull().default(false),
  image: text("image"),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).notNull().defaultNow(),
});

// Sessions — tracks active login sessions
export const sessions = pgTable(
  "sessions",
  {
    id: uuid("id").primaryKey().defaultRandom(),
    userId: uuid("user_id")
      .notNull()
      .references(() => users.id, { onDelete: "cascade" }),
    token: varchar("token", { length: 255 }).notNull().unique(),
    expiresAt: timestamp("expires_at", { withTimezone: true }).notNull(),
    ipAddress: varchar("ip_address", { length: 45 }),
    userAgent: text("user_agent"),
    createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
    updatedAt: timestamp("updated_at", { withTimezone: true }).notNull().defaultNow(),
  },
  (table) => [index("idx_sessions_user_id").on(table.userId)],
);

// Accounts — OAuth and credential accounts linked to users
export const accounts = pgTable(
  "accounts",
  {
    id: uuid("id").primaryKey().defaultRandom(),
    userId: uuid("user_id")
      .notNull()
      .references(() => users.id, { onDelete: "cascade" }),
    accountId: varchar("account_id", { length: 255 }).notNull(),
    providerId: varchar("provider_id", { length: 255 }).notNull(),
    accessToken: text("access_token"),
    refreshToken: text("refresh_token"),
    accessTokenExpiresAt: timestamp("access_token_expires_at", { withTimezone: true }),
    refreshTokenExpiresAt: timestamp("refresh_token_expires_at", { withTimezone: true }),
    scope: text("scope"),
    password: text("password"),
    idToken: text("id_token"),
    createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
    updatedAt: timestamp("updated_at", { withTimezone: true }).notNull().defaultNow(),
  },
  (table) => [
    index("idx_accounts_user_id").on(table.userId),
    uniqueIndex("idx_accounts_provider").on(table.providerId, table.accountId),
  ],
);

// Verifications — email verification and password reset tokens
export const verifications = pgTable(
  "verifications",
  {
    id: uuid("id").primaryKey().defaultRandom(),
    identifier: text("identifier").notNull(),
    value: text("value").notNull(),
    expiresAt: timestamp("expires_at", { withTimezone: true }).notNull(),
    createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
    updatedAt: timestamp("updated_at", { withTimezone: true }).notNull().defaultNow(),
  },
  (table) => [index("idx_verifications_identifier").on(table.identifier)],
);
```

### Key Design Decisions

- **UUIDs everywhere** — Better Auth supports UUID primary keys via `defaultRandom()`. This avoids sequential ID enumeration attacks.
- **Cascade deletes on sessions/accounts** — When a user is deleted, their sessions and OAuth accounts are automatically cleaned up.
- **Unique constraint on (providerId, accountId)** — Prevents duplicate OAuth account links.
- **Index on verifications.identifier** — Email lookups during verification need to be fast.
- **`withTimezone: true`** — All timestamps stored in UTC. Prevents timezone bugs in multi-region deployments.

## Organization Tables

Multi-tenant support with role-based membership.

```typescript
export const organizations = pgTable(
  "organizations",
  {
    id: uuid("id").primaryKey().defaultRandom(),
    name: varchar("name", { length: 255 }).notNull(),
    slug: varchar("slug", { length: 100 }).notNull().unique(),
    logo: text("logo"),
    metadata: text("metadata"),
    plan: varchar("plan", { length: 50 }).notNull().default("free"),
    // Billing provider fields (Stripe/Polar/etc.)
    billingCustomerId: varchar("billing_customer_id", { length: 255 }),
    billingSubscriptionId: varchar("billing_subscription_id", { length: 255 }),
    createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
    updatedAt: timestamp("updated_at", { withTimezone: true }).notNull().defaultNow(),
  },
  (table) => [index("idx_organizations_billing").on(table.billingCustomerId)],
);

export const orgMemberships = pgTable(
  "org_memberships",
  {
    id: uuid("id").primaryKey().defaultRandom(),
    organizationId: uuid("organization_id")
      .notNull()
      .references(() => organizations.id, { onDelete: "cascade" }),
    userId: uuid("user_id")
      .notNull()
      .references(() => users.id, { onDelete: "cascade" }),
    role: varchar("role", { length: 50 }).notNull().default("member"),
    createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
  },
  (table) => [
    uniqueIndex("idx_org_memberships_unique").on(table.organizationId, table.userId),
    index("idx_org_memberships_user").on(table.userId),
    index("idx_org_memberships_org").on(table.organizationId),
  ],
);

export const invitations = pgTable(
  "invitations",
  {
    id: uuid("id").primaryKey().defaultRandom(),
    email: varchar("email", { length: 255 }).notNull(),
    inviterId: uuid("inviter_id")
      .notNull()
      .references(() => users.id, { onDelete: "cascade" }),
    organizationId: uuid("organization_id")
      .notNull()
      .references(() => organizations.id, { onDelete: "cascade" }),
    role: varchar("role", { length: 50 }).notNull().default("member"),
    status: varchar("status", { length: 50 }).notNull().default("pending"),
    expiresAt: timestamp("expires_at", { withTimezone: true }).notNull(),
    createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
  },
  (table) => [
    index("idx_invitations_org").on(table.organizationId),
    index("idx_invitations_email").on(table.email),
  ],
);
```

### Key Design Decisions

- **Unique (org, user) membership** — A user can only have one role per org.
- **Plan on organization** — Billing is org-level, not user-level. This simplifies plan enforcement.
- **Slug is unique** — Used in URLs (`/orgs/my-org`). Auto-generated with UUID suffix to prevent collisions.

## Project & API Key Tables

Projects scope resources within an organization. API keys are scoped to projects.

```typescript
export const projects = pgTable(
  "projects",
  {
    id: uuid("id").primaryKey().defaultRandom(),
    organizationId: uuid("organization_id")
      .notNull()
      .references(() => organizations.id, { onDelete: "cascade" }),
    name: varchar("name", { length: 255 }).notNull(),
    slug: varchar("slug", { length: 100 }).notNull(),
    description: text("description"),
    createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
    updatedAt: timestamp("updated_at", { withTimezone: true }).notNull().defaultNow(),
  },
  (table) => [
    uniqueIndex("idx_projects_org_slug").on(table.organizationId, table.slug),
    index("idx_projects_org").on(table.organizationId),
  ],
);

export const apiKeys = pgTable(
  "api_keys",
  {
    id: uuid("id").primaryKey().defaultRandom(),
    projectId: uuid("project_id")
      .notNull()
      .references(() => projects.id, { onDelete: "cascade" }),
    name: varchar("name", { length: 255 }).notNull(),
    keyHash: varchar("key_hash", { length: 255 }).notNull(),
    keyPrefix: varchar("key_prefix", { length: 12 }).notNull(),
    lastUsedAt: timestamp("last_used_at", { withTimezone: true }),
    expiresAt: timestamp("expires_at", { withTimezone: true }),
    revokedAt: timestamp("revoked_at", { withTimezone: true }),
    createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
  },
  (table) => [
    index("idx_api_keys_project").on(table.projectId),
    uniqueIndex("idx_api_keys_hash").on(table.keyHash),
    index("idx_api_keys_prefix").on(table.keyPrefix),
  ],
);
```

### Key Design Decisions

- **Project slug unique per org** — Not globally unique, scoped to organization via composite unique index.
- **keyHash unique** — Enables O(1) lookup during API key validation.
- **Soft-delete via `revokedAt`** — Revoked keys remain in the database for audit trail. The auth middleware checks `revokedAt !== null` to reject them.
- **`lastUsedAt` nullable** — Updated fire-and-forget on each API key auth. Useful for usage analytics and stale key detection.
- **No plaintext key column** — The plaintext is generated, returned to the user once, and only the SHA-256 hash is stored. This is a security requirement, not an optimization.
