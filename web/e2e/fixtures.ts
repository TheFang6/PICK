import { test as base, Page } from "@playwright/test";

export const FAKE_USER = { user_id: "user-123", name: "Test User" };

export async function mockSession(page: Page) {
  await page.route("**/api/me", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(FAKE_USER),
    })
  );
}

export async function mockNoSession(page: Page) {
  await page.route("**/api/me", (route) =>
    route.fulfill({
      status: 401,
      contentType: "application/json",
      body: JSON.stringify({ detail: "Not authenticated" }),
    })
  );
}

export async function mockLogout(page: Page) {
  await page.route("**/api/logout", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({}),
    })
  );
}

export const test = base.extend<{ authPage: Page }>({
  authPage: async ({ page }, use) => {
    await mockSession(page);
    await use(page);
  },
});

export { expect } from "@playwright/test";
