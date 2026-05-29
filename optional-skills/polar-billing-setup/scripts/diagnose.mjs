#!/usr/bin/env node
// Polar usage-based billing diagnostic — walks the metering chain for one
// customer and reports, link by link, where billing breaks. Read-only.
//
// Usage:
//   POLAR_ACCESS_TOKEN=<token with meters:read + orders:read> \
//   POLAR_SERVER=production|sandbox \
//     node diagnose.mjs --customer <polar_customer_id> [--event-name <name>] [--meter <meter_id>]
//
// Why this exists: Polar metered billing fails silently. Events return
// `inserted:1`, subscriptions look active, orders get created — all at $0 —
// when a single link in the chain is misconfigured. This script checks each
// link and names the broken one instead of leaving you to guess.

const args = Object.fromEntries(
  process.argv.slice(2).reduce((acc, a, i, arr) => {
    if (a.startsWith("--")) acc.push([a.slice(2), arr[i + 1]?.startsWith("--") ? true : arr[i + 1]]);
    return acc;
  }, []),
);

const TOKEN = process.env.POLAR_ACCESS_TOKEN;
const SERVER = (process.env.POLAR_SERVER || "production").toLowerCase();
const BASE = SERVER === "sandbox" ? "https://sandbox-api.polar.sh" : "https://api.polar.sh";
const CUSTOMER = args.customer;
const EVENT_NAME = args["event-name"];
const METER_ARG = args.meter;

const C = { g: "\x1b[32m", r: "\x1b[31m", y: "\x1b[33m", d: "\x1b[2m", x: "\x1b[0m" };
const PASS = `${C.g}✓ PASS${C.x}`;
const FAIL = `${C.r}✗ FAIL${C.x}`;
const WARN = `${C.y}? UNKNOWN${C.x}`;

if (!TOKEN || !CUSTOMER) {
  console.error("Required: POLAR_ACCESS_TOKEN env + --customer <id>.");
  console.error("Optional: POLAR_SERVER=sandbox|production, --event-name <name>, --meter <id>.");
  process.exit(2);
}

const findings = [];
const note = (link, status, detail) => {
  findings.push({ link, status });
  const tag = status === "pass" ? PASS : status === "fail" ? FAIL : WARN;
  console.log(`${tag}  ${link}`);
  if (detail) console.log(`        ${C.d}${detail}${C.x}`);
};

async function get(path) {
  try {
    const res = await fetch(`${BASE}${path}`, { headers: { Authorization: `Bearer ${TOKEN}` } });
    let json = null;
    try { json = await res.json(); } catch { /* non-JSON */ }
    return { status: res.status, json };
  } catch (err) {
    return { status: 0, json: { error: String(err) } };
  }
}

console.log(`\nPolar billing diagnostic — ${SERVER} — customer ${CUSTOMER}\n`);

// ── Link 0: token scope ───────────────────────────────────────────────
const meterScopeProbe = await get(`/v1/meters/?limit=1`);
const canReadMeters = meterScopeProbe.status === 200;
if (canReadMeters) {
  note("token scope: meters:read", "pass");
} else if (meterScopeProbe.json?.error === "insufficient_scope") {
  note("token scope: meters:read", "fail",
    "Token lacks meters:read — meter/price checks below will be skipped. Create a read-scoped token (rule 8).");
} else {
  note("token scope: meters:read", "warn", `Unexpected status ${meterScopeProbe.status}.`);
}

// ── Link 1: customer state (consumed_units — the number that matters) ──
const state = await get(`/v1/customers/${CUSTOMER}/state`);
if (state.status !== 200) {
  note("customer state", "fail", `GET /v1/customers/${CUSTOMER}/state → ${state.status}. Wrong id, env, or customer:read scope.`);
  summarize();
  process.exit(0);
}
const activeMeters = state.json.active_meters || [];
const activeSubs = state.json.active_subscriptions || [];
const totalConsumed = activeMeters.reduce((s, m) => s + (m.consumed_units || 0), 0);
if (activeMeters.length === 0) {
  note("customer has an active meter", "fail", "No active_meters on the customer — no metered subscription, or meter not bound to the product price.");
} else if (totalConsumed > 0) {
  note("consumed_units > 0 (billing IS flowing)", "pass",
    activeMeters.map((m) => `meter ${m.meter_id}: consumed=${m.consumed_units}, balance=${m.balance}`).join("; "));
} else {
  note("consumed_units > 0", "fail",
    `consumed_units is 0 across ${activeMeters.length} meter(s) — usage is NOT being counted. Continue below to find why.`);
}

// ── Link 2: meter filter + aggregation ────────────────────────────────
const meterIds = METER_ARG ? [METER_ARG] : activeMeters.map((m) => m.meter_id).filter(Boolean);
let aggProperty = null;
let filterEventNames = [];
if (!canReadMeters) {
  note("meter filter + aggregation", "warn", "Skipped — no meters:read scope.");
} else if (meterIds.length === 0) {
  note("meter filter + aggregation", "warn", "No meter id resolved (pass --meter <id>).");
} else {
  for (const mid of meterIds) {
    const m = await get(`/v1/meters/${mid}`);
    if (m.status !== 200) { note(`meter ${mid}`, "warn", `→ ${m.status}`); continue; }
    aggProperty = m.json.aggregation?.property ?? null;
    const func = m.json.aggregation?.func;
    const clauses = JSON.stringify(m.json.filter);
    filterEventNames = [...clauses.matchAll(/"value"\s*:\s*"([^"]+)"/g)].map((x) => x[1]);
    note(`meter "${m.json.name}" config`, "pass",
      `aggregation: ${func}${aggProperty ? `(metadata.${aggProperty})` : "()"} · filter matches event name(s): ${filterEventNames.join(", ") || "?"}`);
  }
}

// ── Link 3: do real events carry the aggregated property? (the typo trap) ──
const evName = EVENT_NAME || filterEventNames[0];
const evResp = await get(`/v1/events/?customer_id=${CUSTOMER}&limit=25`);
if (evResp.status !== 200) {
  note("events carry the aggregated property", "warn", `Cannot read events → ${evResp.status} (needs events:read).`);
} else {
  const items = (evResp.json.items || []).filter((e) => !evName || e.name === evName);
  if (items.length === 0) {
    note("recent events exist for this customer", "fail",
      `No events${evName ? ` named "${evName}"` : ""} found. The app isn't emitting (or wrong name).`);
  } else {
    const keys = new Set();
    items.forEach((e) => Object.keys(e.metadata || {}).forEach((k) => keys.add(k)));
    const userEvents = items.filter((e) => e.source !== "system");
    console.log(`        ${C.d}recent "${evName}" event metadata keys: ${[...keys].join(", ")}${C.x}`);
    if (aggProperty) {
      const withProp = userEvents.filter((e) => e.metadata && aggProperty in e.metadata).length;
      if (userEvents.length > 0 && withProp === 0) {
        note("emitted metadata key matches meter aggregation property", "fail",
          `Meter sums metadata.${aggProperty} but NONE of the recent events carry that key. THIS is the silent $0 bug (rule 1). Emit "${aggProperty}", or note the locked-in spelling and match it.`);
      } else if (withProp < userEvents.length) {
        note("emitted metadata key matches meter aggregation property", "warn",
          `Only ${withProp}/${userEvents.length} events carry metadata.${aggProperty}. Mixed keys — likely mid-migration.`);
      } else {
        note("emitted metadata key matches meter aggregation property", "pass",
          `All ${userEvents.length} recent events carry metadata.${aggProperty}.`);
      }
    } else {
      note("recent events exist", "pass", `${items.length} event(s); aggregation property unknown (no meters:read) — verify key by hand.`);
    }
  }
}

// ── Link 4: product has a metered price bound to the meter ─────────────
const productId = activeSubs[0]?.product_id;
if (!canReadMeters) {
  note("metered price attached to meter", "warn", "Skipped — no scope to read product.");
} else if (!productId) {
  note("metered price attached to meter", "warn", "No active subscription product_id in customer state.");
} else {
  const p = await get(`/v1/products/${productId}`);
  if (p.status !== 200) {
    note("metered price attached to meter", "warn", `GET product → ${p.status}.`);
  } else {
    const prices = p.json.prices || [];
    const metered = prices.find((pr) => pr.amount_type === "metered_unit");
    if (!metered) {
      note("metered price attached to meter", "fail",
        `Product has prices [${prices.map((pr) => pr.amount_type).join(", ")}] but NO metered_unit price — usage can't bill.`);
    } else if (meterIds.length && !meterIds.includes(metered.meter_id)) {
      note("metered price attached to meter", "fail",
        `Metered price points at meter ${metered.meter_id}, not the customer's active meter(s) ${meterIds.join(",")}.`);
    } else {
      note("metered price attached to meter", "pass",
        `metered_unit price, unit_amount=${metered.unit_amount}, meter_id=${metered.meter_id}.`);
    }
  }
}

// ── Link 5: orders (are invoices actually non-zero?) ──────────────────
const orders = await get(`/v1/orders/?customer_id=${CUSTOMER}&limit=5`);
if (orders.status !== 200) {
  note("orders show non-zero billing", "warn", `Cannot read orders → ${orders.status} (needs orders:read).`);
} else {
  const items = orders.json.items || [];
  const nonZero = items.filter((o) => (o.total_amount ?? 0) > 0).length;
  if (items.length === 0) {
    note("orders exist", "warn", "No orders yet (new subscription or pre-first-cycle).");
  } else if (nonZero > 0) {
    note("orders show non-zero billing", "pass", `${nonZero}/${items.length} recent orders are non-zero.`);
  } else if (totalConsumed > 0) {
    // Usage is accruing now, but these orders are $0 — they predate the fix or
    // the current cycle hasn't closed. Not a broken link; the next invoice bills.
    note("orders show non-zero billing", "warn",
      `All ${items.length} recent orders total $0, but consumed_units=${totalConsumed} now — these orders predate the fix / current cycle hasn't closed. The next invoice will bill the accrued usage.`);
  } else {
    note("orders show non-zero billing", "fail",
      `All ${items.length} recent orders total $0 and consumed_units is 0 — corroborates broken metering above.`);
  }
}

summarize();

function summarize() {
  const fails = findings.filter((f) => f.status === "fail");
  console.log("");
  if (fails.length === 0) {
    console.log(`${C.g}Billing chain looks intact.${C.x} If invoices are still $0, check sandbox-vs-production (rule 7) and that you're inspecting the right environment.`);
  } else {
    console.log(`${C.r}Broken link(s):${C.x} ${fails.map((f) => f.link).join("  |  ")}`);
    console.log(`${C.d}Fix the first broken link, re-emit one event, and re-run this to confirm consumed_units increments (no backfill — rule 4).${C.x}`);
  }
}
