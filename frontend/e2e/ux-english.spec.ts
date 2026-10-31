import { expect, request as apiRequest, test, type Page } from "@playwright/test";

/**
 * English mode shows no Arabic where nothing Arabic was written: the new
 * request form (its document checklist included) and the case file of a
 * request written in English. Runs after screens.spec.ts.
 */

const API = process.env.SCREENS_API_URL ?? "http://localhost:8010";
const PRIV = "CT-2027-0419";
const ARABIC = /[؀-ۿݐ-ݿﭐ-﷿ﹰ-﻿]/;

async function primeEnglish(page: Page) {
  await page.addInitScript(() => {
    window.localStorage.setItem("mithaqai.lang", "en");
    window.localStorage.setItem(
      "mithaqai.persona",
      JSON.stringify({ party: "CONTRACTOR", role: "PROJECT_MANAGER" }),
    );
    window.localStorage.removeItem("mithaqai.demo");
  });
}

async function arabicIn(page: Page): Promise<string[]> {
  const text = await page.locator("main").innerText();
  return text.split("\n").filter((line) => ARABIC.test(line));
}

test("English: the new request form has no Arabic", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await primeEnglish(page);
  await page.goto(`/contracts/${PRIV}/new`);
  await page.locator("main h1").first().waitFor({ timeout: 20_000 });
  await page.locator('main input[type="checkbox"]').first().waitFor();
  await page.waitForLoadState("networkidle");
  expect(await arabicIn(page)).toEqual([]);
});

test("English: the case file of an English request has no Arabic", async ({ page }) => {
  const api = await apiRequest.newContext({ baseURL: API });
  const created = await api.post(`/api/contracts/${PRIV}/change-requests`, {
    data: {
      requester_name: "Eng. Sara Malik",
      requester_party: "CONTRACTOR",
      body_ar:
        "Please add two more application servers of the approved model, priced at the contract unit rate.",
      attachments: ["طلب تغيير رسمي", "عرض سعر أو تحليل تكلفة"],
    },
  });
  expect(created.ok(), await created.text()).toBeTruthy();
  const id = (await created.json()).request.id as string;
  await api.dispose();

  await page.setViewportSize({ width: 1440, height: 900 });
  await primeEnglish(page);
  await page.goto(`/contracts/${PRIV}/requests/${id}`);
  await page.locator("main h1").first().waitFor({ timeout: 20_000 });
  await page.waitForLoadState("networkidle");
  // The English request text reads left to right, with no "Original Arabic" label.
  await expect(page.getByText("Original Arabic")).toHaveCount(0);
  expect(await arabicIn(page)).toEqual([]);
});
