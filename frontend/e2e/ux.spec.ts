import path from "node:path";

import { expect, test, type Page } from "@playwright/test";

/**
 * Step 8: the home page, the guide bar, both languages and both themes for
 * the key screens, into docs/design/screens/ux/.
 *
 * Runs after screens.spec.ts (files run in name order), so the government
 * contract is in the salami preset state. Only ids and attributes are used to
 * wait on, so the same steps work in both languages.
 */

const OUT = path.resolve(__dirname, "../../docs/design/screens/ux");

const GOV = "CT-2027-0418";
const SALAMI_VO_CR = "CR-CT-2027-0418-009";

type Lang = "ar" | "en";
type Scheme = "light" | "dark";

const GOV_PM = { party: "GOVERNMENT_ENTITY", role: "PROJECT_MANAGER" };

async function prime(
  page: Page,
  { lang, theme, demo }: { lang: Lang; theme?: Scheme; demo?: object },
) {
  await page.addInitScript(
    ({ lang, theme, demo, persona }) => {
      window.localStorage.setItem("mithaqai.lang", lang);
      window.localStorage.setItem("mithaqai.persona", JSON.stringify(persona));
      if (theme) window.localStorage.setItem("mithaqai.theme", theme);
      if (demo) window.localStorage.setItem("mithaqai.demo", JSON.stringify(demo));
      else window.localStorage.removeItem("mithaqai.demo");
    },
    { lang, theme, demo, persona: GOV_PM },
  );
}

async function settle(page: Page) {
  await page.waitForLoadState("networkidle");
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(300);
}

async function shoot(page: Page, name: string) {
  await settle(page);
  await page.screenshot({ path: path.join(OUT, `${name}.png`), fullPage: true });
}

const KEY_SCREENS = [
  { name: "home", url: "/", ready: "main h1" },
  { name: "workspace-government", url: `/contracts/${GOV}`, ready: "#register-title" },
  // The salami preset (run at the end of screens.spec.ts) issues seven VOs on
  // the government contract; the seventh is used for the case and its VO.
  { name: "case-vo-issued", url: `/contracts/${GOV}/requests/${SALAMI_VO_CR}`, ready: "main h1" },
  {
    name: "vo-document",
    url: `/contracts/${GOV}/variation-orders/${SALAMI_VO_CR}-VO`,
    ready: "main h1",
  },
  { name: "limits-near-cap", url: `/contracts/${GOV}/limits`, ready: "main h1" },
  { name: "evaluation", url: "/evaluation", ready: "main h1" },
] as const;

for (const lang of ["ar", "en"] as const) {
  for (const scheme of ["light", "dark"] as const) {
    test.describe(`${lang} ${scheme}`, () => {
      test.use({ viewport: { width: 1440, height: 900 }, colorScheme: scheme });
      for (const s of KEY_SCREENS) {
        test(s.name, async ({ page }) => {
          await prime(page, { lang });
          await page.goto(s.url);
          await page.locator(s.ready).first().waitFor({ timeout: 20_000 });
          await expect(page.locator("html")).toHaveAttribute("lang", lang);
          await expect(page.locator("html")).toHaveAttribute("dir", lang === "en" ? "ltr" : "rtl");
          await shoot(page, `${s.name}-1440-${scheme}-${lang}`);
        });
      }
    });
  }
}

test.describe("phone width", () => {
  test.use({ viewport: { width: 390, height: 844 }, colorScheme: "light" });
  for (const lang of ["ar", "en"] as const) {
    test(`home and workspace at 390 (${lang})`, async ({ page }) => {
      await prime(page, { lang });
      await page.goto("/");
      await page.locator("main h1").first().waitFor();
      await shoot(page, `home-390-light-${lang}`);
      await page.goto(`/contracts/${GOV}`);
      await page.locator("#register-title").waitFor({ timeout: 20_000 });
      await shoot(page, `workspace-government-390-light-${lang}`);
    });
  }
});

test.describe("guide bar", () => {
  test.use({ viewport: { width: 1440, height: 900 }, colorScheme: "light" });
  for (const lang of ["ar", "en"] as const) {
    test(`starts from home and drives act 1 (${lang})`, async ({ page }) => {
      await prime(page, { lang });
      await page.goto("/");
      await page.locator('a[href="/demo"], button[data-demo-start]').first().click();
      await page.waitForURL(/\/demo$/);
      await page.locator("[data-demo-start]").first().click();
      const bar = page.locator("[data-guide-bar]");
      await expect(bar).toBeVisible();
      // Presenter notes stay hidden until opened.
      await expect(page.locator("[data-presenter-notes]")).toHaveCount(0);
      await bar.locator("[data-guide-go]").click();
      await page.waitForURL(new RegExp(`/contracts/${GOV}$`));
      await page.locator("#register-title").waitFor({ timeout: 20_000 });
      await shoot(page, `guide-act1-1440-light-${lang}`);
      await bar.locator("[data-guide-notes]").click();
      await expect(page.locator("[data-presenter-notes]")).toBeVisible();
      await shoot(page, `guide-act1-notes-1440-light-${lang}`);
      await bar.locator("[data-guide-next]").click();
      await bar.locator("[data-guide-go]").click();
      await page.waitForURL(/\/requests\/CR-C-SUBSTITUTION$/);
      await shoot(page, `guide-act2-1440-light-${lang}`);
    });
  }
});

test("theme toggle is remembered and applied before paint", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await prime(page, { lang: "ar" });
  await page.goto("/evaluation");
  await page.locator("main h1").first().waitFor();
  await page.locator("[data-theme-toggle]").click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  // On reload the attribute is set by the head script, before React runs.
  await page.reload({ waitUntil: "commit" });
  const early = await page.evaluate(() => document.documentElement.getAttribute("data-theme"));
  expect(early).toBe("dark");
  // Print stays light whatever the screen theme.
  await page.emulateMedia({ media: "print" });
  const bg = await page.evaluate(() => getComputedStyle(document.body).backgroundColor);
  expect(bg).toBe("rgb(255, 255, 255)");
});

test("language toggle switches direction and is remembered", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.addInitScript(() => {
    if (!sessionStorage.getItem("primed")) {
      localStorage.removeItem("mithaqai.lang");
      sessionStorage.setItem("primed", "1");
    }
  });
  await page.goto(`/contracts/${GOV}`);
  await page.locator("#register-title").waitFor({ timeout: 20_000 });
  await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
  await page.locator("[data-lang-toggle]").click();
  await expect(page.locator("html")).toHaveAttribute("lang", "en");
  await expect(page.locator("html")).toHaveAttribute("dir", "ltr");
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("lang", "en");
  await page.locator("#register-title").waitFor({ timeout: 20_000 });
});
