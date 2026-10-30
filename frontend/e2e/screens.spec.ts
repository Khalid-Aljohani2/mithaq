import path from "node:path";

import { expect, request as apiRequest, test, type Page } from "@playwright/test";

/**
 * Captures every Step 5A screen at 1440 and 390 wide, light and dark, into
 * docs/design/screens/. Only the seeded demo requests are used. The backend
 * must be the scripted in-memory one, freshly started (see SCREENSHOTS.md).
 */

const API = process.env.SCREENS_API_URL ?? "http://localhost:8010";
const OUT = path.resolve(__dirname, "../../docs/design/screens");
const SCRATCH = process.env.SCREENS_SCRATCH;

const GOV = "CT-2027-0418";
const PRIV = "CT-2027-0419";

type Persona = { party: "GOVERNMENT_ENTITY" | "CONTRACTOR"; role: string };
const GOV_PM: Persona = { party: "GOVERNMENT_ENTITY", role: "PROJECT_MANAGER" };

type Screen = {
  name: string;
  url: string;
  persona?: Persona;
  ready: string;
  prepare?: (page: Page) => Promise<void>;
};

const caseUrl = (contract: string, cr: string) => `/contracts/${contract}/requests/${cr}`;

const SCREENS: Screen[] = [
  { name: "workspace-government", url: `/contracts/${GOV}`, ready: "سجل طلبات التغيير" },
  { name: "workspace-private", url: `/contracts/${PRIV}`, ready: "سجل طلبات التغيير" },
  {
    name: "shell-role-switcher",
    url: `/contracts/${GOV}`,
    ready: "سجل طلبات التغيير",
    prepare: async (page) => {
      await page.getByRole("button", { name: /تعمل بصفة/ }).click();
      await page.getByLabel("الدور").waitFor();
    },
  },
  {
    name: "shell-contract-switcher",
    url: `/contracts/${GOV}`,
    ready: "سجل طلبات التغيير",
    prepare: async (page) => {
      await page.getByRole("button", { name: /العقد/ }).first().click();
      await page.getByText("العقود المتاحة").waitFor();
    },
  },
  { name: "new-request", url: `/contracts/${PRIV}/new`, ready: "طلب تغيير جديد" },
  {
    name: "new-request-errors",
    url: `/contracts/${PRIV}/new`,
    ready: "طلب تغيير جديد",
    prepare: async (page) => {
      await page.getByRole("button", { name: "تقديم الطلب وتحليله" }).click();
      await page.getByText("صحّح الحقول المعلَّمة أعلاه").waitFor();
    },
  },
  { name: "case-received", url: caseUrl(PRIV, "CR-E-NCR"), ready: "لم يُحلَّل الطلب بعد" },
  {
    name: "case-analysing",
    url: caseUrl(PRIV, "CR-E-NCR"),
    ready: "لم يُحلَّل الطلب بعد",
    prepare: async (page) => {
      // Hold the analyse call so the running state can be captured. The call
      // never reaches the backend, so the request stays unanalysed.
      await page.route("**/analyse", () => new Promise<void>(() => undefined));
      await page.getByRole("button", { name: "تحليل الطلب" }).click();
      await page.getByText("يحلل الوكيل الطلب الآن").first().waitFor();
      await page.waitForTimeout(700);
    },
  },
  { name: "case-closed-in-scope", url: caseUrl(PRIV, "CR-A-INSCOPE"), ready: "أُغلق كطلب داخل النطاق" },
  { name: "case-recommended-policy", url: caseUrl(PRIV, "CR-D-POLICY"), ready: "بدء مسار الاعتماد" },
  {
    name: "case-in-approval-my-step",
    url: caseUrl(PRIV, "CR-C-SUBSTITUTION"),
    persona: { party: "GOVERNMENT_ENTITY", role: "TECHNICAL_MANAGER" },
    ready: "التوقيع باسم",
  },
  { name: "case-approved-seal", url: caseUrl(PRIV, "CR-B-PCR"), ready: "اعتُمد الطلب بجميع التواقيع" },
  {
    name: "case-legal-block",
    url: caseUrl(GOV, "CR-D-GOV"),
    persona: { party: "CONTRACTOR", role: "PROJECT_MANAGER" },
    ready: "محجوب نظامًا",
  },
];

const VARIANTS = [
  { width: 1440, height: 900, scheme: "light" },
  { width: 1440, height: 900, scheme: "dark" },
  { width: 390, height: 844, scheme: "light" },
  { width: 390, height: 844, scheme: "dark" },
] as const;

/** Bring the seeded requests into a spread of states, through the real API. */
test.beforeAll(async () => {
  const api = await apiRequest.newContext({ baseURL: API });
  const state = async (cr: string): Promise<string> =>
    (await (await api.get(`/api/change-requests/${cr}`)).json()).request.state;
  const post = async (url: string, data?: object) => {
    const res = await api.post(url, data ? { data } : undefined);
    expect(res.ok(), `${url}: ${await res.text()}`).toBeTruthy();
  };
  const analyse = async (cr: string) => {
    if ((await state(cr)) === "RECEIVED") await post(`/api/change-requests/${cr}/analyse`);
  };
  const start = async (cr: string) => {
    if ((await state(cr)) === "RECOMMENDED") await post(`/api/change-requests/${cr}/start-approval`);
  };
  const approve = async (cr: string, persona: Persona, name: string) => {
    if ((await state(cr)) !== "IN_APPROVAL") return;
    await post(`/api/change-requests/${cr}/decide`, {
      ...persona,
      decided_by: name,
      decision: "APPROVED",
      reason: null,
    });
  };

  for (const cr of ["CR-A-INSCOPE", "CR-B-PCR", "CR-C-SUBSTITUTION", "CR-D-POLICY", "CR-D-GOV"]) {
    await analyse(cr);
  }
  for (const cr of ["CR-B-PCR", "CR-C-SUBSTITUTION", "CR-D-GOV"]) await start(cr);
  await approve("CR-B-PCR", GOV_PM, "م. نورة الشهري");
  await approve("CR-C-SUBSTITUTION", GOV_PM, "م. نورة الشهري");
  await api.dispose();
});

for (const v of VARIANTS) {
  test.describe(`${v.width} ${v.scheme}`, () => {
    test.use({ viewport: { width: v.width, height: v.height }, colorScheme: v.scheme });

    for (const s of SCREENS) {
      test(s.name, async ({ page }) => {
        const persona = s.persona ?? GOV_PM;
        await page.addInitScript((p) => {
          window.localStorage.setItem("mithaqai.persona", JSON.stringify(p));
        }, persona);
        await page.goto(s.url);
        await page.getByText(s.ready).first().waitFor({ timeout: 20_000 });
        await page.waitForLoadState("networkidle");
        await page.evaluate(() => document.fonts.ready);
        if (s.prepare) await s.prepare(page);
        await page.waitForTimeout(300);
        await page.screenshot({
          path: path.join(OUT, `${s.name}-${v.width}-${v.scheme}.png`),
          fullPage: true,
        });
      });
    }
  });
}

/**
 * The approval action end to end, run last because it changes state: reject
 * without a reason is refused, then approving stamps the seal.
 */
test("approval action stamps the seal", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.addInitScript(() => {
    window.localStorage.setItem(
      "mithaqai.persona",
      JSON.stringify({ party: "GOVERNMENT_ENTITY", role: "TECHNICAL_MANAGER" }),
    );
  });
  await page.goto(caseUrl(PRIV, "CR-C-SUBSTITUTION"));
  await page.getByLabel("التوقيع باسم").fill("م. خالد العتيبي");

  await page.getByRole("button", { name: "رفض", exact: true }).click();
  await page.getByRole("button", { name: "تأكيد الرفض" }).click();
  await expect(page.getByText("يصل السبب إلى مقدم الطلب")).toHaveClass(/text-legal/);
  await page.getByRole("button", { name: "تراجع" }).click();

  await page.getByRole("button", { name: "اعتماد", exact: true }).click();
  await expect(page.getByText("اعتُمد الطلب بجميع التواقيع")).toBeVisible();
  await expect(page.getByRole("img", { name: /معتمد/ })).toHaveCount(2);
  if (SCRATCH) {
    await page.waitForTimeout(800);
    await page.screenshot({ path: path.join(SCRATCH, "seal-stamped.png"), fullPage: true });
  }
});
