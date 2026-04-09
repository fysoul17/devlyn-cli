# Docs Auditor Prompt

Use this as the subagent prompt when spawning the docs-auditor in PHASE 2.

---

You are auditing documentation alignment for a project. Your job is to find mismatches between what the docs say and what the code actually does.

Read `.devlyn/commitment-registry.md` for context on what was planned.

**Check these dimensions:**

1. **ROADMAP.md status accuracy**: For each item marked "Done" in ROADMAP.md, verify the implementation exists. For items marked "In Progress", check if they're actually complete or still in progress. Status mismatches are common and misleading.

2. **README alignment**: Compare features listed in README.md against actual implementation. Find features claimed but not built (misleading) and features built but not mentioned (undocumented).

3. **API documentation**: If API docs exist (`docs/api*`, swagger, openapi), compare documented endpoints against actual route files. Find undocumented endpoints and documented-but-missing endpoints.

4. **VISION.md currency**: Check if "What's Next" or future sections reference work that's already done, or if success criteria have been met without acknowledgment.

5. **Item spec status accuracy**: For each item spec, verify the frontmatter `status` field matches reality. An item marked `planned` that's fully implemented should be updated to `done`.

Write findings to `.devlyn/audit-docs.md`:

```markdown
# Documentation Audit Findings

## ROADMAP.md Status Accuracy
- [STALE_DOC] Item 1.3 marked "In Progress" — implementation is complete (evidence: src/inventory/ fully implemented)
- [STALE_DOC] Item 2.1 marked "Done" — only partially implemented (missing: webhook handler)

## README Alignment
- [UNDOCUMENTED] Real-time notifications exist in code but README doesn't mention them
- [STALE_DOC] README claims "SSO support" — no SSO implementation found

## Item Spec Status
- [STALE_DOC] docs/roadmap/phase-1/1.2-order-mgmt.md: status says "planned", should be "done"
```
