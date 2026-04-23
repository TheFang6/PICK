import { test, expect } from "./fixtures";

const RESTAURANTS = [
  { id: "r1", name: "Suki Hot Plate", rating: 4.2, source: "google_maps", vicinity: null },
  { id: "r2", name: "Ramen House", rating: 4.5, source: "google_maps", vicinity: null },
  { id: "r3", name: "Pad Thai Corner", rating: 4.0, source: "manual", vicinity: null },
];

const BLACKLIST_ENTRIES = [
  {
    id: "bl1",
    user_id: "user-123",
    restaurant_id: "r99",
    restaurant_name: "Banned Place",
    mode: "permanent",
    expires_at: null,
    created_at: "2026-04-01T00:00:00Z",
  },
  {
    id: "bl2",
    user_id: "user-123",
    restaurant_id: "r98",
    restaurant_name: "Skip Today",
    mode: "today",
    expires_at: null,
    created_at: "2026-04-23T00:00:00Z",
  },
];

test.describe("Blacklist page", () => {
  test.beforeEach(async ({ authPage: page }) => {
    await page.route("**/api/restaurants**", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ restaurants: RESTAURANTS }),
      })
    );
    await page.route("**/api/blacklist**", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ entries: BLACKLIST_ENTRIES }),
      })
    );
    await page.goto("/blacklist");
  });

  test("shows available restaurants and existing blacklist sections", async ({ authPage: page }) => {
    await expect(page.getByText("Suki Hot Plate")).toBeVisible();
    await expect(page.getByText("Ramen House")).toBeVisible();
    await expect(page.getByText("Permanent (1)")).toBeVisible();
    await expect(page.getByText("Today only (1)")).toBeVisible();
  });

  test("filter by search narrows restaurant list", async ({ authPage: page }) => {
    await page.getByPlaceholder("Filter restaurants...").fill("ramen");
    await expect(page.getByText("Ramen House")).toBeVisible();
    await expect(page.getByText("Suki Hot Plate")).not.toBeVisible();
  });

  test("clear search X button restores full list", async ({ authPage: page }) => {
    const input = page.getByPlaceholder("Filter restaurants...");
    await input.fill("ramen");
    await expect(page.getByText("Suki Hot Plate")).not.toBeVisible();
    // The X button is inside the same relative container as the input
    await input.locator("..").locator("button").click();
    await expect(page.getByText("Suki Hot Plate")).toBeVisible();
  });

  test("select all selects every visible restaurant", async ({ authPage: page }) => {
    await page.getByText("Select all").first().click();
    await expect(page.getByText("3 selected")).toBeVisible();
  });

  test("bulk add permanent sends POST to /api/blacklist", async ({ authPage: page }) => {
    let postCount = 0;
    // Override: intercept POST before the beforeEach wildcard route
    await page.route("**/api/blacklist**", (route) => {
      if (route.request().method() === "POST") {
        postCount++;
        route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({}) });
      } else {
        // Pass GET requests through as original mock
        route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ entries: BLACKLIST_ENTRIES }),
        });
      }
    });

    await page.getByText("Suki Hot Plate").click();
    // "Ban permanently (1)" button appears in the sticky action bar
    await page.getByRole("button", { name: /ban permanently/i }).click();
    expect(postCount).toBe(1);
  });

  test("bulk remove shows confirm dialog", async ({ authPage: page }) => {
    await page.getByText("Banned Place").click();
    await page.getByRole("button", { name: /remove from blacklist/i }).click();
    await expect(page.getByRole("dialog")).toBeVisible();
    await expect(page.getByText(/remove 1 restaurant from blacklist/i)).toBeVisible();
  });

  test("confirm removal calls DELETE and closes dialog", async ({ authPage: page }) => {
    let deleteCalled = false;
    await page.route("**/api/blacklist/**", (route) => {
      if (route.request().method() === "DELETE") {
        deleteCalled = true;
        route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({}) });
      } else {
        route.continue();
      }
    });

    await page.getByText("Banned Place").click();
    await page.getByRole("button", { name: /remove from blacklist/i }).click();
    await expect(page.getByRole("dialog")).toBeVisible();
    // Click the "Remove" confirm button inside the dialog
    await page.getByRole("dialog").getByRole("button", { name: /^remove$/i }).click();
    expect(deleteCalled).toBe(true);
    await expect(page.getByRole("dialog")).not.toBeVisible();
  });

  test("cancel confirm dialog keeps entries intact", async ({ authPage: page }) => {
    await page.getByText("Banned Place").click();
    await page.getByRole("button", { name: /remove from blacklist/i }).click();
    await expect(page.getByRole("dialog")).toBeVisible();
    await page.getByRole("button", { name: /cancel/i }).click();
    await expect(page.getByRole("dialog")).not.toBeVisible();
    await expect(page.getByText("Banned Place")).toBeVisible();
  });
});
