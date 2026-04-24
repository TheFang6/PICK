# 022 — Expand E2E Test Coverage

**Phase:** 6 (Improvements)
**Estimated Time:** 2-3 hours
**Dependencies:** 019 (existing E2E setup)

> **For agentic workers:** Use the `task-dev` skill to implement this plan task-by-task. English-only for all commits and PR text. Stop before opening a PR and wait for user review.

---

## Goal

Expand Playwright E2E coverage beyond the existing 4 spec files (pair, blacklist, history, nav). Add tests for the landing page, mobile responsiveness, error/edge-case handling, and session management.

---

## Context

Existing coverage:
- `pair.spec.ts` — 3 tests (pairing flow)
- `blacklist.spec.ts` — 10 tests (blacklist CRUD + bulk ops)
- `history.spec.ts` — 14 tests (calendar view)
- `nav.spec.ts` — 5 tests (navigation + logout)
- `fixtures.ts` — shared auth fixture

Gaps (web-testable with Playwright):
- Landing/home page not tested
- No mobile viewport tests
- No error state tests (API down, empty data)
- Session expiry redirect not tested
- Unauthenticated page access not tested

---

## Tech Stack

- Playwright 1.59.1, Next.js 16, TypeScript
- Existing `authPage` fixture from `e2e/fixtures.ts`

---

## Single PR

**Branch:** `test/022-expand-e2e` (off `main`)

---

## Task 1: Home page tests

**File:** `web/e2e/home.spec.ts`

### Step 1.1: Create home page spec

```typescript
import { test, expect } from "@playwright/test";

test.describe("Home page", () => {
  test("shows PICK branding and bot link", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByText("PICK")).toBeVisible();
    await expect(page.getByText("Lunch Bot")).toBeVisible();
    const botLink = page.getByRole("link", { name: /telegram/i });
    await expect(botLink).toBeVisible();
  });

  test("shows session expired message when redirected", async ({ page }) => {
    await page.goto("/?expired=1");
    await expect(page.getByText(/session expired/i)).toBeVisible();
  });

  test("does not show expired message on normal visit", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByText(/session expired/i)).not.toBeVisible();
  });
});
```

### Step 1.2: Run and verify

```bash
cd web && npx playwright test e2e/home.spec.ts
```

### Step 1.3: Commit

```bash
git add web/e2e/home.spec.ts
git commit -m "test: add E2E tests for home/landing page"
```

---

## Task 2: Auth guard / session tests

**File:** `web/e2e/auth.spec.ts`

### Step 2.1: Create auth guard spec

Test that protected pages redirect unauthenticated users.

```typescript
import { test, expect } from "@playwright/test";

test.describe("Auth guard", () => {
  test("blacklist page redirects to home when not authenticated", async ({ page }) => {
    await page.route("**/api/me", (route) =>
      route.fulfill({ status: 401, body: "Unauthorized" })
    );
    await page.goto("/blacklist");
    await expect(page).toHaveURL(/\/\?expired=1/);
  });

  test("history page redirects to home when not authenticated", async ({ page }) => {
    await page.route("**/api/me", (route) =>
      route.fulfill({ status: 401, body: "Unauthorized" })
    );
    await page.goto("/history");
    await expect(page).toHaveURL(/\/\?expired=1/);
  });
});
```

### Step 2.2: Run and verify

```bash
cd web && npx playwright test e2e/auth.spec.ts
```

### Step 2.3: Commit

```bash
git add web/e2e/auth.spec.ts
git commit -m "test: add E2E tests for auth guard redirects"
```

---

## Task 3: Error and empty state tests

**File:** `web/e2e/error-states.spec.ts`

### Step 3.1: Create error state spec

Test how pages handle API failures and empty data.

```typescript
import { test, expect } from "@playwright/test";
import { authPage } from "./fixtures";

authPage.describe("Error states", () => {
  authPage("blacklist page shows empty state when no restaurants", async ({ page }) => {
    await page.route("**/api/restaurants*", (route) =>
      route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([]) })
    );
    await page.route("**/api/blacklist", (route) =>
      route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([]) })
    );
    await page.goto("/blacklist");
    // Should render page without crashing
    await expect(page.getByText(/blacklist/i)).toBeVisible();
  });

  authPage("history page shows empty state for month with no data", async ({ page }) => {
    await page.route("**/api/history*", (route) =>
      route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([]) })
    );
    await page.goto("/history");
    await expect(page.getByText(/no lunches/i)).toBeVisible();
  });

  authPage("blacklist page handles API error gracefully", async ({ page }) => {
    await page.route("**/api/restaurants*", (route) =>
      route.fulfill({ status: 500, body: "Internal Server Error" })
    );
    await page.route("**/api/blacklist", (route) =>
      route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([]) })
    );
    await page.goto("/blacklist");
    // Page should still render without crashing
    await expect(page).toHaveURL("/blacklist");
  });
});
```

### Step 3.2: Run and verify

```bash
cd web && npx playwright test e2e/error-states.spec.ts
```

### Step 3.3: Commit

```bash
git add web/e2e/error-states.spec.ts
git commit -m "test: add E2E tests for error and empty states"
```

---

## Task 4: Mobile responsive tests

**File:** `web/e2e/responsive.spec.ts`

### Step 4.1: Create responsive spec

Use Playwright's viewport to test mobile rendering.

```typescript
import { devices } from "@playwright/test";
import { authPage, expect } from "./fixtures";

const iPhone = devices["iPhone 13"];

authPage.describe("Mobile responsive", () => {
  authPage.use({ ...iPhone });

  authPage("blacklist page renders on mobile", async ({ page }) => {
    await page.route("**/api/restaurants*", (route) =>
      route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([
        { id: "r1", name: "Test Restaurant", rating: 4.0, source: "google_maps" },
      ]) })
    );
    await page.route("**/api/blacklist", (route) =>
      route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([]) })
    );
    await page.goto("/blacklist");
    await expect(page.getByText("Test Restaurant")).toBeVisible();
  });

  authPage("history page renders on mobile", async ({ page }) => {
    await page.route("**/api/history*", (route) =>
      route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([]) })
    );
    await page.goto("/history");
    await expect(page.getByText(/history/i)).toBeVisible();
  });

  authPage("nav is accessible on mobile", async ({ page }) => {
    await page.route("**/api/restaurants*", (route) =>
      route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([]) })
    );
    await page.route("**/api/blacklist", (route) =>
      route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([]) })
    );
    await page.goto("/blacklist");
    await expect(page.getByText("PICK")).toBeVisible();
  });
});
```

### Step 4.2: Run and verify

```bash
cd web && npx playwright test e2e/responsive.spec.ts
```

### Step 4.3: Commit

```bash
git add web/e2e/responsive.spec.ts
git commit -m "test: add E2E tests for mobile responsive layouts"
```

---

## Task 5: Run full E2E suite + update docs

### Step 5.1: Run all E2E tests

```bash
cd web && npx playwright test
```

All tests must pass.

### Step 5.2: Update STRUCTURE.md and INDEX.md

Add new test files to STRUCTURE.md. Add task 022 to INDEX.md.

### Step 5.3: Commit

```bash
git add backend/STRUCTURE.md tasks/INDEX.md tasks/022-expand-e2e-tests.md
git commit -m "docs: add task 022 and update structure for expanded E2E tests"
```

### Step 5.4: STOP — wait for user review before opening PR.

---

## Acceptance Criteria

- [ ] Home page tests pass (branding, expired message)
- [ ] Auth guard tests pass (redirect on 401)
- [ ] Error/empty state tests pass (API errors, no data)
- [ ] Mobile responsive tests pass (iPhone viewport)
- [ ] Full E2E suite passes (old + new tests)
- [ ] STRUCTURE.md and INDEX.md updated

---

## Risk / Rollback

- Tests only — no production code changes. Zero risk to production behavior.
- If a test flakes, fix the test or mark it with `test.fixme()` and file an issue.
