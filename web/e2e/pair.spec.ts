import { test, expect } from "@playwright/test";

test.describe("Pairing flow", () => {
  test("valid token: shows success then redirects to /blacklist", async ({ page }) => {
    await page.route("**/api/pair", (route) =>
      route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({}) })
    );
    await page.route("**/api/me", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ user_id: "u1", name: "Fang" }),
      })
    );
    await page.route("**/api/blacklist**", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ entries: [] }),
      })
    );
    await page.route("**/api/restaurants**", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ restaurants: [] }),
      })
    );

    await page.goto("/pair?token=valid-token-abc");
    await expect(page.getByText("Paired successfully!")).toBeVisible();
    await expect(page).toHaveURL("/blacklist", { timeout: 5000 });
  });

  test("invalid token: shows error message", async ({ page }) => {
    await page.route("**/api/pair", (route) =>
      route.fulfill({
        status: 400,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Invalid or expired token" }),
      })
    );

    await page.goto("/pair?token=bad-token");
    await expect(page.getByText("Invalid or expired token")).toBeVisible();
    await expect(page.getByRole("link", { name: /back to telegram/i })).toBeVisible();
  });

  test("missing token: shows error without API call", async ({ page }) => {
    await page.goto("/pair");
    await expect(page.getByText("No pairing token provided")).toBeVisible();
  });
});
