import { test, expect } from "./fixtures";

const now = new Date();
const MONTH = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
const DAY10_DATE = `${MONTH}-10`;

const HISTORY_ENTRIES = [
  {
    id: "h1",
    restaurant_id: "r1",
    restaurant_name: "Suki Hot Plate",
    date: DAY10_DATE,
    attendees: ["user-123"],
    attendee_names: ["Fang"],
  },
  {
    id: "h2",
    restaurant_id: "r2",
    restaurant_name: "Ramen House",
    date: DAY10_DATE,
    attendees: ["user-123", "user-456"],
    attendee_names: ["Fang", "Boon"],
  },
];

test.describe("History page", () => {
  test.beforeEach(async ({ authPage: page }) => {
    await page.route("**/api/history**", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ entries: HISTORY_ENTRIES }),
      })
    );
    await page.goto("/history");
  });

  test("renders calendar header with current month", async ({ authPage: page }) => {
    const monthLabel = now.toLocaleDateString("en-US", {
      year: "numeric",
      month: "long",
    });
    await expect(page.getByText(monthLabel, { exact: true })).toBeVisible();
  });

  test("renders weekday headers", async ({ authPage: page }) => {
    for (const day of ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]) {
      await expect(page.getByText(day, { exact: true })).toBeVisible();
    }
  });

  test("days with entries show restaurant chip", async ({ authPage: page }) => {
    await expect(page.getByText("Suki Hot Plate").first()).toBeVisible();
  });

  test("click day with entries shows detail panel with count", async ({ authPage: page }) => {
    await page.getByText("10", { exact: true }).first().click();
    await expect(page.getByText("2 picks")).toBeVisible();
  });

  test("detail panel shows restaurant names after clicking day", async ({ authPage: page }) => {
    await page.getByText("10", { exact: true }).first().click();
    const panel = page.locator(".glass").last();
    await expect(panel.getByText("Suki Hot Plate")).toBeVisible();
    await expect(panel.getByText("Ramen House")).toBeVisible();
  });

  test("detail panel shows attendee names", async ({ authPage: page }) => {
    await page.getByText("10", { exact: true }).first().click();
    await expect(page.getByText("Fang, Boon")).toBeVisible();
  });

  test("empty day shows no lunches recorded message", async ({ authPage: page }) => {
    await page.getByText("1", { exact: true }).first().click();
    await expect(page.getByText("No lunches recorded")).toBeVisible();
  });

  test("click same day again shows default empty prompt", async ({ authPage: page }) => {
    await page.getByText("10", { exact: true }).first().click();
    await expect(page.getByText("2 picks")).toBeVisible();
    await page.getByText("10", { exact: true }).first().click();
    await expect(page.getByText("Click a day to see details")).toBeVisible();
  });

  test("Mine tab is active by default", async ({ authPage: page }) => {
    const mineBtn = page.getByRole("button", { name: "Mine" });
    await expect(mineBtn).toHaveClass(/bg-indigo-600/);
  });

  test("Team tab triggers /api/history/team call", async ({ authPage: page }) => {
    let teamCalled = false;
    await page.route("**/api/history/team**", (route) => {
      teamCalled = true;
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ entries: [] }),
      });
    });

    await page.getByRole("button", { name: "Team" }).click();
    await expect(async () => {
      expect(teamCalled).toBe(true);
    }).toPass({ timeout: 3000 });
  });

  test("prev month button changes month label", async ({ authPage: page }) => {
    const prevMonth = new Date(now.getFullYear(), now.getMonth() - 1, 1);
    const prevLabel = prevMonth.toLocaleDateString("en-US", {
      year: "numeric",
      month: "long",
    });

    await page.getByRole("button", { name: "Previous month" }).click();
    await expect(page.getByText(prevLabel, { exact: true })).toBeVisible();
  });

  test("next month button changes month label", async ({ authPage: page }) => {
    const nextMonth = new Date(now.getFullYear(), now.getMonth() + 1, 1);
    const nextLabel = nextMonth.toLocaleDateString("en-US", {
      year: "numeric",
      month: "long",
    });

    await page.getByRole("button", { name: "Next month" }).click();
    await expect(page.getByText(nextLabel, { exact: true })).toBeVisible();
  });
});
