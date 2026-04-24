import { test, expect } from "./fixtures";

test.describe("Error states", () => {
  test("blacklist page renders with no restaurants", async ({ authPage: page }) => {
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
    await expect(page.getByText("All restaurants are blacklisted")).toBeVisible();
  });

  test("blacklist page shows no-match message when search has no results", async ({ authPage: page }) => {
    await page.route("**/api/restaurants**", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          restaurants: [
            { id: "r1", name: "Ramen House", rating: 4.5, source: "google_maps", vicinity: null },
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
    await page.getByPlaceholder("Filter restaurants...").fill("zzz no match");
    await expect(page.getByText("No matching restaurants")).toBeVisible();
  });

  test("history page shows prompt when no day selected and no data", async ({ authPage: page }) => {
    await page.route("**/api/history**", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ entries: [] }),
      })
    );
    await page.goto("/history");
    await expect(page.getByText("Click a day to see details")).toBeVisible();
  });

  test("history page shows no-lunches message when clicking empty day", async ({ authPage: page }) => {
    await page.route("**/api/history**", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ entries: [] }),
      })
    );
    await page.goto("/history");
    await page.getByText("15").click();
    await expect(page.getByText("No lunches recorded")).toBeVisible();
  });

  test("blacklist page handles API error without crashing", async ({ authPage: page }) => {
    await page.route("**/api/restaurants**", (route) =>
      route.fulfill({ status: 500, body: "Internal Server Error" })
    );
    await page.route("**/api/blacklist**", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ entries: [] }),
      })
    );
    await page.goto("/blacklist");
    await expect(page).toHaveURL("/blacklist");
    await expect(page.getByText("Blacklist")).toBeVisible();
  });
});
