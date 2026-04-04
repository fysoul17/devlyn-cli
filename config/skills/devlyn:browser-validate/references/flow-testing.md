# Flow Testing: Done-Criteria to Browser Steps

How to read `.claude/done-criteria.md` and convert testable criteria into browser action sequences. This is the bridge between "what should work" and "prove it works in the browser."

Read this file only during PHASE 4 (FLOW) when done-criteria exists.

---

## Step 1: Classify Each Criterion

Read `.claude/done-criteria.md` and classify each criterion:

**Browser-testable** — the criterion describes something a user can see or do in the UI:
- "User can create a new project from the dashboard"
- "Error message appears when form is submitted with empty fields"
- "Navigation shows active state on current page"
- "Data table loads and displays 10 rows"

**Not browser-testable** — the criterion is about backend logic, data integrity, or code quality:
- "API returns 401 for unauthenticated requests"
- "Database migration runs without errors"
- "Test coverage exceeds 80%"
- "No TypeScript errors"

Skip non-browser-testable criteria. Note them as "Skipped — not browser-testable" in the report.

## Step 2: Convert to Action Sequences

For each browser-testable criterion, generate a sequence of steps:

### Pattern: Navigation + Verification
```
Criterion: "Dashboard shows project count"
Steps:
  1. Navigate to /dashboard
  2. Find element containing project count (look for text matching a number pattern)
  3. Verify: element exists and contains a numeric value
  4. Screenshot
```

### Pattern: Form Interaction
```
Criterion: "User can create a new project"
Steps:
  1. Navigate to /dashboard (or wherever the create action lives)
  2. Find "Create" or "New Project" button
  3. Click it
  4. Find form fields (name, description, etc.)
  5. Fill with test data: name="Test Project", description="Browser validation test"
  6. Find and click submit button
  7. Verify: success indicator appears (toast, redirect, new item in list)
  8. Screenshot at steps 3, 6, and 7
```

### Pattern: Error State
```
Criterion: "Error message shows when form submitted empty"
Steps:
  1. Navigate to the form page
  2. Find submit button
  3. Click submit without filling any fields
  4. Verify: error message(s) visible
  5. Screenshot showing error state
```

### Pattern: Conditional UI
```
Criterion: "Empty state shows when no data exists"
Steps:
  1. Navigate to the list/table page
  2. Check if data exists — if so, this test needs a clean state
  3. If clean state achievable: verify empty state message/illustration
  4. If not: skip with note "Cannot verify empty state — data already exists"
  5. Screenshot
```

## Step 3: Handle Data Dependencies

Some flow tests need specific data to exist (or not exist). Approach:

1. **Read-only tests preferred** — test flows that verify existing state rather than create/modify
2. **Create test data if safe** — if the flow creates something (like a project), use obvious test names ("Browser Validation Test — safe to delete")
3. **Skip if destructive** — don't test delete flows, don't modify existing data, don't test flows that send emails or notifications
4. **Note dependencies** — if a test can't run because of missing data, note it as "Skipped — requires [specific data state]"

## Step 4: Handle Auth-Protected Pages

If a route requires authentication:
1. Check if the app redirects to a login page
2. If login is a simple form (email + password): note "Auth required — skipping unless test credentials available"
3. If login uses OAuth/SSO: skip entirely, note "Skipped — requires OAuth flow"
4. Do not attempt to log in with guessed credentials

## Test Data Guidelines

When filling forms during flow tests, use obviously fake but valid data:
- Name: "Test User" or "Browser Validate Test"
- Email: "test@browser-validate.local"
- Description: "Created by browser-validate skill — safe to delete"
- Numbers: use small, obvious values (1, 10, 100)

This makes test data easy to identify and clean up later.

## Output Format

For each flow test, report:

```
Criterion: [original text from done-criteria]
Classification: browser-testable | skipped
Steps executed: [N of total]
Result: PASS | FAIL | SKIPPED
Evidence:
  - Screenshot: [path]
  - Console errors during flow: [count] — [details]
  - Network failures during flow: [count] — [details]
  - Failure point: [which step failed and why]
```
