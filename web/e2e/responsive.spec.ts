import { devices } from "@playwright/test";
import { test, expect } from "./fixtures";

const iPhone = devices["iPhone 13"];

test.use({ viewport: iPhone.viewport, userAgent: iPhone.userAgent });

test.describe("Mobile responsive", () => {
  test("home page renders on mobile", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "PICK" })).toBeVisible();
    await expect(page.getByText("Lunch Bot")).toBeVisible();
  });

  test("blacklist page renders on mobile", async ({ authPage: page }) => {
    await page.route("**/api/restaurants**", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          restaurants: [
            { id: "r1", name: "Test Restaurant", rating: 4.0, source: "google_maps", vicinity: null },
          ],
        }),
      })
    );
    await page.route("**/api/blacklist**", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ entries: [] }),
      })
    );
    await page.goto("/blacklist");
    await expect(page.getByText("Test Restaurant")).toBeVisible();
    await expect(page.getByText("PICK")).toBeVisible();
  });

  test("history page renders on mobile", async ({ authPage: page }) => {
    await page.route("**/api/history**", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ entries: [] }),
      })
    );
    await page.goto("/history");
    await expect(page.getByText("History")).toBeVisible();
    await expect(page.getByText("Click a day to see details")).toBeVisible();
  });

  test("nav links are accessible on mobile", async ({ authPage: page }) => {
    await page.route("**/api/restaurants**", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ restaurants: [] }),
      })
    );
    await page.route("**/api/blacklist**", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ entries: [] }),
      })
    );
    await page.goto("/blacklist");
    const blacklistLink = page.getByRole("link", { name: /blacklist/i });
    await expect(blacklistLink).toBeVisible();
    const historyLink = page.getByRole("link", { name: /history/i });
    await expect(historyLink).toBeVisible();
  });
});
