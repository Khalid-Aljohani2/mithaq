import path from "node:path";

import { expect, test, type Page } from "@playwright/test";

/**
 * Step 9: project intake. A person creates a contract by hand, opens it, sees
 * its limits and submits a change request to it. Also captures the new screen
 * in both languages and both themes into docs/design/screens/ux/.
 *
 * Runs after screens.spec.ts, so a new contract in the switcher does not
 * change the earlier screenshots.
 */

const OUT = path.resolve(__dirname, "../../docs/design/screens/ux");
const GOV_PM = { party: "GOVERNMENT_ENTITY", role: "PROJECT_MANAGER" };

async function prime(page: Page, lang: "ar" | "en") {
  await page.addInitScript(
    ({ lang, persona }) => {
      window.localStorage.setItem("mithaqai.lang", lang);
      window.localStorage.setItem("mithaqai.persona", JSON.stringify(persona));
      window.localStorage.removeItem("mithaqai.demo");
    },
    { lang, persona: GOV_PM },
  );
}

async function shoot(page: Page, name: string) {
  await page.waitForLoadState("networkidle");
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(300);
  await page.screenshot({ path: path.join(OUT, `${name}.png`), fullPage: true });
}

// Two lines that add up exactly to the contract value.
const LINES = [
  { description_ar: "توريد خوادم تطبيقات", unit_ar: "عدد", quantity: "6", unit_rate: "85000" },
  { description_ar: "تطوير بوابة الخدمات", unit_ar: "مرحلة", quantity: "4", unit_rate: "210000.50" },
];
const VALUE = "1350002";

async function fillLine(page: Page, index: number, line: (typeof LINES)[number]) {
  const row = page.locator("[data-line-row]").nth(index);
  for (const [name, value] of Object.entries(line)) {
    await row.locator(`[name="${name}"]`).fill(value);
  }
}

for (const lang of ["ar", "en"] as const) {
  for (const scheme of ["light", "dark"] as const) {
    test(`new project screen (${lang} ${scheme})`, async ({ page }) => {
      await page.setViewportSize({ width: 1440, height: 900 });
      await page.emulateMedia({ colorScheme: scheme });
      await prime(page, lang);
      await page.goto("/projects/new");
      await page.locator('[name="title_ar"]').waitFor({ timeout: 20_000 });
      await shoot(page, `new-project-1440-${scheme}-${lang}`);
    });
  }
}

test("create a project by hand, open it, see its limits, submit a request", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await prime(page, "ar");

  // Entry point from the home page.
  await page.goto("/");
  await page.locator('a[href="/projects/new"]').first().click();
  await page.waitForURL(/\/projects\/new$/);

  await page.locator('[name="title_ar"]').fill("مشروع اختبار الاستلام");
  await page.locator('[name="entity_name"]').fill("أمانة افتراضية");
  await page.locator('[name="contractor_name"]').fill("شركة افتراضية");
  await page.locator('[name="contract_type"][value="GOVERNMENT"]').check();
  await page.locator('[name="start_date"]').fill("2027-03-01");
  await page.locator('[name="end_date"]').fill("2028-02-29");
  await page.locator('[name="created_by"]').fill("م. نورة الشهري");

  await fillLine(page, 0, LINES[0]);
  await page.locator("[data-add-line]").click();
  await fillLine(page, 1, LINES[1]);

  // A value that does not match the lines is refused, with the reason.
  await page.locator('[name="original_value"]').fill("1350000");
  await expect(page.locator("[data-grand-total]")).toContainText("1,350,002");
  await page.locator("[data-create-project]").click();
  await expect(page).toHaveURL(/\/projects\/new$/);
  await shoot(page, "new-project-mismatch-1440-light-ar");

  // The exact value is accepted and the new contract opens.
  await page.locator('[name="original_value"]').fill(VALUE);
  await page.locator("[data-create-project]").click();
  await page.waitForURL(/\/contracts\/CT-2027-\d+$/, { timeout: 20_000 });
  const contractUrl = page.url();

  // Its limits: the Article 67 meters appear for a government contract.
  await page.locator("#limits-title").waitFor({ timeout: 20_000 });
  // Two policy meters plus the Article 67 meters that carry a percentage cap.
  await expect(page.locator('#main [role="img"][aria-label]')).not.toHaveCount(0);
  expect(await page.locator('#main [role="img"][aria-label]').count()).toBeGreaterThanOrEqual(5);
  await page.goto(`${contractUrl}/limits`);
  await page.locator("main h1").first().waitFor();

  // A change request against it: submitted, analysed, and in its register.
  await page.goto(`${contractUrl}/new`);
  await page.locator("main h1").first().waitFor();
  await page.getByLabel("الاسم").fill("م. فهد القحطاني");
  await page
    .getByLabel("نص الطلب")
    .fill("نفيدكم بالحاجة إلى خادمين إضافيين من نفس الطراز المعتمد في البند الأول، وفق سعر الوحدة المتعاقد عليه.");
  for (const box of await page.locator('input[type="checkbox"]').all()) await box.check();
  await page.getByRole("button", { name: "تقديم الطلب وتحليله" }).click();
  await page.waitForURL(/\/requests\/CR-CT-2027-\d+-\d+$/, { timeout: 30_000 });
  await page.locator("main h1").first().waitFor();
  await shoot(page, "new-project-first-request-1440-light-ar");
});
