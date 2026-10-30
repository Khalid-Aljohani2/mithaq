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
  /** A function when the URL depends on an id created in setup. */
  url: string | (() => string);
  persona?: Persona;
  ready: string;
  /** Overlays (the drawer) are captured at the viewport, not the full page. */
  viewportOnly?: boolean;
  prepare?: (page: Page) => Promise<void>;
};

const caseUrl = (contract: string, cr: string) => `/contracts/${contract}/requests/${cr}`;
const VO_ID = "CR-C-SUBSTITUTION-VO";
const VO_URL = `/contracts/${PRIV}/variation-orders/${VO_ID}`;
const GOV_VO_URL = `/contracts/${GOV}/variation-orders/CR-F-GOV-OK-VO`;

/** Set in setup: CR-B's seeded text resubmitted without its cost quote. */
let awaitingId = "";

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
  { name: "case-recommended", url: caseUrl(PRIV, "CR-B-PCR"), ready: "بدء مسار الاعتماد" },
  {
    name: "case-in-approval-my-step",
    url: caseUrl(PRIV, "CR-D-POLICY"),
    persona: { party: "GOVERNMENT_ENTITY", role: "FINANCE_MANAGER" },
    ready: "التوقيع باسم",
  },
  { name: "case-vo-issued", url: caseUrl(PRIV, "CR-C-SUBSTITUTION"), ready: "عرض أمر التغيير وطباعته" },
  {
    name: "case-legal-block",
    url: caseUrl(GOV, "CR-D-GOV"),
    persona: { party: "CONTRACTOR", role: "PROJECT_MANAGER" },
    ready: "محجوب نظامًا",
  },
  { name: "vo-document", url: VO_URL, ready: "التواقيع" },
  { name: "vo-document-government", url: GOV_VO_URL, ready: "التواقيع" },
  {
    name: "notifications-drawer",
    url: `/contracts/${PRIV}`,
    // The finance manager has CR-D waiting; the run's backend sets the
    // reminder delay to zero, so the reminder shows beside the request.
    persona: { party: "GOVERNMENT_ENTITY", role: "FINANCE_MANAGER" },
    ready: "سجل طلبات التغيير",
    viewportOnly: true,
    prepare: async (page) => {
      await page.getByRole("button", { name: /الإشعارات/ }).click();
      await page.getByRole("dialog").getByText("تذكير", { exact: true }).first().waitFor();
    },
  },
  {
    name: "case-awaiting-documents",
    url: () => caseUrl(PRIV, awaitingId),
    persona: { party: "CONTRACTOR", role: "PROJECT_MANAGER" },
    ready: "إرسال المستندات وإعادة التحليل",
  },
  { name: "limits-government", url: `/contracts/${GOV}/limits`, ready: "أوامر التغيير المعتمدة" },
  { name: "limits-private", url: `/contracts/${PRIV}/limits`, ready: "أوامر التغيير المعتمدة" },
  { name: "evaluation", url: "/evaluation", ready: "كيف بُنيت مجموعة التقييم" },
  { name: "audit-private", url: `/contracts/${PRIV}/audit`, ready: "سجل إلحاقي" },
  { name: "audit-government", url: `/contracts/${GOV}/audit`, ready: "سجل إلحاقي" },
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
  // Idempotent: setup runs again if Playwright restarts the worker after a
  // failure, so only sign when this persona's slot is the one pending.
  const approve = async (cr: string, persona: Persona, name: string) => {
    const detail = await (await api.get(`/api/change-requests/${cr}`)).json();
    if (detail.request.state !== "IN_APPROVAL") return;
    type Step = { party: string; role: string; decision: string; position: number };
    const next = (detail.chain as Step[])
      .sort((a, b) => a.position - b.position)
      .find((st) => st.decision === "PENDING");
    if (!next || next.party !== persona.party || next.role !== persona.role) return;
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
  for (const cr of ["CR-C-SUBSTITUTION", "CR-D-POLICY", "CR-D-GOV"]) await start(cr);
  // CR-C through its whole chain (project manager, then technical manager),
  // then the VO is issued: the document screens need a real one.
  await approve("CR-C-SUBSTITUTION", GOV_PM, "م. نورة الشهري");
  await approve(
    "CR-C-SUBSTITUTION",
    { party: "GOVERNMENT_ENTITY", role: "TECHNICAL_MANAGER" },
    "م. خالد العتيبي",
  );
  if ((await state("CR-C-SUBSTITUTION")) === "APPROVED") {
    await post("/api/change-requests/CR-C-SUBSTITUTION/variation-order");
  }
  // CR-D (private) waits at the finance manager after the project manager signs.
  await approve("CR-D-POLICY", GOV_PM, "م. نورة الشهري");

  // CR-F on the government contract stays within Article 67: its whole chain,
  // contractor consent first, then a VO that cites the article.
  await analyse("CR-F-GOV-OK");
  await start("CR-F-GOV-OK");
  await approve("CR-F-GOV-OK", { party: "CONTRACTOR", role: "PROJECT_MANAGER" }, "م. فهد القحطاني");
  await approve("CR-F-GOV-OK", GOV_PM, "م. نورة الشهري");
  await approve("CR-F-GOV-OK", { party: "GOVERNMENT_ENTITY", role: "FINANCE_MANAGER" }, "أ. ريم الحربي");
  await approve("CR-F-GOV-OK", { party: "GOVERNMENT_ENTITY", role: "LEGAL_ADVISOR" }, "أ. سلمان العمري");
  if ((await state("CR-F-GOV-OK")) === "APPROVED") {
    await post("/api/change-requests/CR-F-GOV-OK/variation-order");
  }

  // Awaiting documents: CR-B's seeded text again, without its cost quote.
  const list = await (await api.get(`/api/contracts/${PRIV}/change-requests`)).json();
  type Row = { id: string; body_ar: string; requester_name: string; state: string; attachments: string[] };
  const rows: Row[] = list.requests;
  const existing = rows.find((r) => r.state === "AWAITING_DOCUMENTS");
  if (existing) {
    awaitingId = existing.id;
  } else {
    const seed = rows.find((r) => r.id === "CR-B-PCR");
    expect(seed).toBeTruthy();
    const created = await api.post(`/api/contracts/${PRIV}/change-requests`, {
      data: {
        requester_name: seed?.requester_name,
        requester_party: "CONTRACTOR",
        body_ar: seed?.body_ar,
        attachments: ["طلب تغيير رسمي"],
      },
    });
    expect(created.ok()).toBeTruthy();
    awaitingId = (await created.json()).request.id;
    await post(`/api/change-requests/${awaitingId}/analyse`);
  }
  expect(await state(awaitingId)).toBe("AWAITING_DOCUMENTS");
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
        await page.goto(typeof s.url === "function" ? s.url() : s.url);
        await page.getByText(s.ready).first().waitFor({ timeout: 20_000 });
        await page.waitForLoadState("networkidle");
        await page.evaluate(() => document.fonts.ready);
        if (s.prepare) await s.prepare(page);
        await page.waitForTimeout(300);
        await page.screenshot({
          path: path.join(OUT, `${s.name}-${v.width}-${v.scheme}.png`),
          fullPage: !s.viewportOnly,
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
      JSON.stringify({ party: "GOVERNMENT_ENTITY", role: "FINANCE_MANAGER" }),
    );
  });
  await page.goto(caseUrl(PRIV, "CR-D-POLICY"));
  await page.getByLabel("التوقيع باسم").fill("أ. ريم الحربي");

  await page.getByRole("button", { name: "رفض", exact: true }).click();
  await page.getByRole("button", { name: "تأكيد الرفض" }).click();
  await expect(page.getByText("يصل السبب إلى مقدم الطلب")).toHaveClass(/text-legal/);
  await page.getByRole("button", { name: "تراجع" }).click();

  await page.getByRole("button", { name: "اعتماد", exact: true }).click();
  await expect(page.getByRole("img", { name: /معتمد/ })).toHaveCount(2);
  // The chain moves on to the CEO, whose slot this persona cannot act on.
  await expect(page.getByText(/الخطوة التالية لـالرئيس التنفيذي/)).toBeVisible();
  if (SCRATCH) {
    await page.waitForTimeout(800);
    await page.screenshot({ path: path.join(SCRATCH, "seal-stamped.png"), fullPage: true });
  }
});

/** A notification opens its case file. */
test("notification links to its case file", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.addInitScript(() => {
    window.localStorage.setItem(
      "mithaqai.persona",
      JSON.stringify({ party: "CONTRACTOR", role: "PROJECT_MANAGER" }),
    );
  });
  await page.goto(`/contracts/${PRIV}`);
  await page.getByRole("button", { name: /الإشعارات/ }).click();
  await page
    .getByRole("dialog")
    .getByRole("link")
    .filter({ hasText: "صدر أمر التغيير" })
    .filter({ hasText: "CR-C-SUBSTITUTION" })
    .first()
    .click();
  await expect(page).toHaveURL(new RegExp(`/requests/CR-C-SUBSTITUTION$`));
  await expect(page.getByRole("dialog")).toHaveCount(0);
});

/** Resubmitting the missing document sends the list and re-runs the analysis. */
test("awaiting documents: resubmit and re-analyse", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.addInitScript(() => {
    window.localStorage.setItem(
      "mithaqai.persona",
      JSON.stringify({ party: "CONTRACTOR", role: "PROJECT_MANAGER" }),
    );
  });
  await page.goto(caseUrl(PRIV, awaitingId));
  await page.getByRole("checkbox", { name: "عرض سعر أو تحليل تكلفة" }).check();
  await page.getByLabel("مقدَّم من").fill("م. فهد القحطاني");
  await page.getByRole("button", { name: "إرسال المستندات وإعادة التحليل" }).click();
  await expect(page.getByText("بدء مسار الاعتماد")).toBeVisible({ timeout: 20_000 });
});

/** Print to PDF gives exactly one A4 page with no app chrome. */
for (const [label, url, file] of [
  ["private", VO_URL, "vo-document"],
  ["government", GOV_VO_URL, "vo-document-government"],
] as const) {
test(`variation order prints on one A4 page (${label})`, async ({ page }) => {
  await page.emulateMedia({ media: "print", colorScheme: "light" });
  await page.goto(url);
  await page.getByText("التواقيع").first().waitFor();
  await page.evaluate(() => document.fonts.ready);
  await expect(page.getByRole("button", { name: "طباعة" })).toBeHidden();
  await expect(page.getByRole("banner").filter({ hasText: "تعمل بصفة" })).toBeHidden();
  const pdf = await page.pdf({ path: path.join(OUT, `${file}.pdf`), preferCSSPageSize: true, printBackground: true });
  const pages = pdf.toString("latin1").match(/\/Type\s*\/Page[^s]/g) ?? [];
  expect(pages.length).toBe(1);
  await page.setViewportSize({ width: 794, height: 1123 });
  await page.screenshot({ path: path.join(OUT, `${file}-print-a4.png`), fullPage: true });
});
}
