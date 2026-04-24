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

  test("pair page does NOT redirect on 401", async ({ page }) => {
    await page.route("**/api/me", (route) =>
      route.fulfill({ status: 401, body: "Unauthorized" })
    );
    await page.goto("/pair");
    await expect(page).toHaveURL(/\/pair/);
  });
});
