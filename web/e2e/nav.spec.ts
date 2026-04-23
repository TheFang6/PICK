import { test, expect, mockLogout } from "./fixtures";

test.describe("Nav", () => {
  test.beforeEach(async ({ authPage: page }) => {
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
    await page.goto("/blacklist");
  });

  test("PICK logo links to home", async ({ authPage: page }) => {
    const logo = page.getByRole("link", { name: /PICK/i }).first();
    await expect(logo).toHaveAttribute("href", "/");
  });

  test("active nav link has indigo background", async ({ authPage: page }) => {
    const blacklistLink = page.getByRole("link", { name: "Blacklist" });
    await expect(blacklistLink).toHaveClass(/bg-indigo-600/);
  });

  test("inactive nav link does not have indigo background", async ({ authPage: page }) => {
    const historyLink = page.getByRole("link", { name: "History" });
    await expect(historyLink).not.toHaveClass(/bg-indigo-600/);
  });

  test("shows user name in nav", async ({ authPage: page }) => {
    await expect(page.getByText("Test User")).toBeVisible();
  });

  test("sign out calls logout and redirects to /", async ({ authPage: page }) => {
    await mockLogout(page);
    await page.getByRole("button", { name: /sign out/i }).click();
    await expect(page).toHaveURL("/", { timeout: 3000 });
  });
});
