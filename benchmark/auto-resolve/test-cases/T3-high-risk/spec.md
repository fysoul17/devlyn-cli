---
id: "2.1"
title: "Session Token Rotation"
phase: 2
status: planned
priority: high
complexity: high
depends-on: ["1.1"]
---

# 2.1 Session Token Rotation

## Context
Session tokens currently never rotate, which violates the security posture the CISO committed to in Q3. Adds rotation every 24 hours with a 1-hour grace window for active sessions.

## Customer Frame
When a user is logged in for longer than 24 hours, we want to rotate their session token transparently so a stolen token becomes useless within a day, without forcing them to re-authenticate.

## Objective
Session tokens auto-rotate every 24 hours. Old token remains valid for 1 hour after rotation to cover in-flight requests.

## Requirements
- [ ] Token issuance stores an `issued_at` timestamp alongside the token
- [ ] Auth middleware checks token age; if >23h and <24h, issues a new token alongside the response
- [ ] Old token remains accepted for 1 hour after the new token is issued
- [ ] After the grace window expires, requests using the old token return 401 with reason: token_rotated
- [ ] Database migration adds `issued_at` and `rotated_from` columns to sessions table
- [ ] Audit log entry emitted on each rotation

## Constraints
- Must not log out users during rotation — transparent to client.
- Cannot force all sessions to expire at deploy time — rotation is lazy on next request.

## Out of Scope
- Refresh-token architecture (different rotation model — would be a rewrite, not this task).
- Per-request token verification with an external service.

## Dependencies
- **Internal**: 1.1 User Auth (must be done)
- **External**: sessions database table

## Verification
- [ ] Test: request with 23.5h-old token receives a Set-Cookie with new token + normal 200
- [ ] Test: request with old token within 1h grace window after rotation succeeds
- [ ] Test: request with old token 1.5h after rotation returns 401 token_rotated
- [ ] Manual: audit log shows rotation events with old/new token IDs
