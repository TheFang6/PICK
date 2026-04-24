import { test, expect } from "@playwright/test";

test.describe("Home page", () => {
  test("shows PICK branding and bot link", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "PICK" })).toBeVisible();
    await expect(page.getByText("Lunch Bot")).toBeVisible();
    const botLink = page.getByRole("link", { name: /telegram/i });
    await expect(botLink).toBeVisible();
    await expect(botLink).toHaveAttribute("href", "https://t.me/pick_food_bot");
  });

  test("shows session expired message when redirected", async ({ page }) => {
    await page.goto("/?expired=1");
    await expect(page.getByText("Session expired")).toBeVisible();
  });

  test("does not show expired message on normal visit", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByText("Session expired")).not.toBeVisible();
  });

  test("bot link opens in new tab", async ({ page }) => {
    await page.goto("/");
    const botLink = page.getByRole("link", { name: /telegram/i });
    await expect(botLink).toHaveAttribute("target", "_blank");
  });
});
