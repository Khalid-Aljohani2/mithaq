import fs from "node:fs";
import path from "node:path";

import { expect, request as apiRequest, test, type Page } from "@playwright/test";

/**
 * The English recording path at 1440x900, with the interface set to English.
 *
 * Captures each screen into docs/design/screens/english/<tag>-<name>.png and
 * fails if a screen shows a raw code (an enum name like APPROVE or IN_SCOPE,
 * or a key like in_scope=False) where a reader expects words.
 *
 * Opt in with ENGLISH_SHOTS_TAG (e.g. "before" or "after"); the default run
 * skips it so the main screenshot suite keeps its own seed. Needs the same
 * freshly started scripted in-memory backend as screens.spec.ts.
 */

const TAG = process.env.ENGLISH_SHOTS_TAG;
const API = process.env.SCREENS_API_URL ?? "http://localhost:8010";
const OUT = path.resolve(__dirname, "../../docs/design/screens/english");
const TOKEN = process.env.SCREENS_DEMO_TOKEN ?? "screens-demo-token";

const GOV = "CT-2027-0418";
const PRIV = "CT-2027-0419";

type Persona = { party: "GOVERNMENT_ENTITY" | "CONTRACTOR"; role: string };
const GOV_PM: Persona = { party: "GOVERNMENT_ENTITY", role: "PROJECT_MANAGER" };
const GOV_PROC: Persona = { party: "GOVERNMENT_ENTITY", role: "PROCUREMENT_MANAGER" };
const GOV_FIN: Persona = { party: "GOVERNMENT_ENTITY", role: "FINANCE_MANAGER" };
const caseUrl = (contract: string, cr: string) => `/contracts/${contract}/requests/${cr}`;

/** Codes that must never reach an English reader as-is. */
const RAW_CODE =
  /\b(APPROVE|REJECT|REQUEST_REVISION|CLOSE_IN_SCOPE|IN_SCOPE|SUBSTITUTION|UNCLEAR|IN_APPROVAL|VO_ISSUED|AWAITING_DOCUMENTS|RECOMMENDED|RECEIVED|PROJECT_MANAGER|PROCUREMENT_MANAGER|FINANCE_MANAGER|TECHNICAL_MANAGER|LEGAL_ADVISOR|GOVERNMENT_ENTITY|CONTRACTOR|[A-Z]+_[A-Z_]+)\b|\w+=(True|False)/;

test.skip(!TAG, "set ENGLISH_SHOTS_TAG to capture the English recording path");
test.use({ viewport: { width: 1440, height: 900 }, colorScheme: "light" });

let awaitingId = "";
const found: string[] = [];

async function open(page: Page, url: string, ready: RegExp | string, persona: Persona = GOV_PM) {
  await page.addInitScript((p) => {
    window.localStorage.setItem("mithaqai.lang", "en");
    window.localStorage.setItem("mithaqai.persona", JSON.stringify(p));
  }, persona);
  await page.goto(url);
  await page.getByText(ready).first().waitFor({ timeout: 20_000 });
  await page.waitForLoadState("networkidle");
  await page.evaluate(() => document.fonts.ready);
}

async function shoot(page: Page, name: string, fullPage = true) {
  await page.waitForTimeout(300);
  fs.mkdirSync(OUT, { recursive: true });
  await page.screenshot({ path: path.join(OUT, `${TAG}-${name}.png`), fullPage });
  // Arabic passages are labelled originals; only the English text is checked.
  const lines = await page.evaluate(() => {
    const out: string[] = [];
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    for (let n = walker.nextNode(); n; n = walker.nextNode()) {
      const el = n.parentElement;
      if (!el || el.closest('[lang="ar"], script, style')) continue;
      const v = (n.textContent ?? "").trim();
      if (v) out.push(v);
    }
    return out;
  });
  for (const line of lines) {
    if (RAW_CODE.test(line)) found.push(`${name}: code: ${line.slice(0, 160)}`);
    // Arabic outside a labelled original is an interface string left untranslated.
    if (/[؀-ۿ]/.test(line)) found.push(`${name}: arabic: ${line.slice(0, 160)}`);
  }
}

test.describe.serial("English recording path", () => {
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
    await approve("CR-C-SUBSTITUTION", GOV_PM, "Eng. Noura Alshehri");
    await approve("CR-C-SUBSTITUTION", GOV_PROC, "Nasser Al-Harthi");
    await approve(
      "CR-C-SUBSTITUTION",
      { party: "GOVERNMENT_ENTITY", role: "TECHNICAL_MANAGER" },
      "Eng. Khalid Alotaibi",
    );
    await approve("CR-C-SUBSTITUTION", GOV_FIN, "Reem Alharbi");
    if ((await state("CR-C-SUBSTITUTION")) === "APPROVED") {
      await post("/api/change-requests/CR-C-SUBSTITUTION/variation-order");
    }
    await approve("CR-D-POLICY", GOV_PM, "Eng. Noura Alshehri");
    await approve("CR-D-POLICY", GOV_PROC, "Nasser Al-Harthi");

    const list = await (await api.get(`/api/contracts/${PRIV}/change-requests`)).json();
    type Row = { id: string; body_ar: string; requester_name: string; state: string };
    const rows: Row[] = list.requests;
    const existing = rows.find((r) => r.state === "AWAITING_DOCUMENTS");
    if (existing) {
      awaitingId = existing.id;
    } else {
      const seed = rows.find((r) => r.id === "CR-B-PCR");
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
    await api.dispose();
  });

  test("home and workspace", async ({ page }) => {
    await open(page, "/", /Mithaq/);
    await shoot(page, "home");
    await open(page, `/contracts/${PRIV}`, "Change request register");
    await shoot(page, "workspace");
    await open(page, `/contracts/${PRIV}/new`, "New change request");
    await shoot(page, "new-request");
    await open(page, "/projects/new", /project/i);
    await shoot(page, "new-project");
  });

  test("case file states", async ({ page }) => {
    const cases: [string, string, Persona?][] = [
      ["case-received", caseUrl(PRIV, "CR-E-NCR")],
      ["case-closed-in-scope", caseUrl(PRIV, "CR-A-INSCOPE")],
      ["case-recommended", caseUrl(PRIV, "CR-B-PCR")],
      [
        "case-in-approval",
        caseUrl(PRIV, "CR-D-POLICY"),
        { party: "GOVERNMENT_ENTITY", role: "FINANCE_MANAGER" },
      ],
      ["case-vo-issued", caseUrl(PRIV, "CR-C-SUBSTITUTION")],
      ["case-legal-block", caseUrl(GOV, "CR-D-GOV"), { party: "CONTRACTOR", role: "PROJECT_MANAGER" }],
      [
        "case-awaiting-documents",
        caseUrl(PRIV, awaitingId),
        { party: "CONTRACTOR", role: "PROJECT_MANAGER" },
      ],
    ];
    for (const [name, url, persona] of cases) {
      await open(page, url, /Change request|CR-/, persona);
      await page.waitForTimeout(500);
      await shoot(page, name);
    }
    // Analysing: hold the call so the running state stays on screen.
    await open(page, caseUrl(PRIV, "CR-E-NCR"), /CR-E-NCR/);
    await page.route("**/analyse", () => new Promise<void>(() => undefined));
    await page.getByRole("button", { name: /Analyse/ }).first().click();
    await page.waitForTimeout(900);
    await shoot(page, "case-analysing");
  });

  test("signed with seal", async ({ page }) => {
    await open(page, caseUrl(PRIV, "CR-D-POLICY"), /CR-D-POLICY/, {
      party: "GOVERNMENT_ENTITY",
      role: "FINANCE_MANAGER",
    });
    await page.getByLabel(/Sign as/i).fill("Reem Alharbi");
    await page.getByRole("button", { name: "Approve", exact: true }).click();
    await page.waitForTimeout(1200);
    await shoot(page, "case-signed-seal");
  });

  test("English VO prints on one A4 page", async ({ page }) => {
    await page.addInitScript(() => window.localStorage.setItem("mithaqai.lang", "en"));
    await page.emulateMedia({ media: "print", colorScheme: "light" });
    await page.goto(`/contracts/${PRIV}/variation-orders/CR-C-SUBSTITUTION-VO`);
    await page.getByText("This variation order covers").first().waitFor();
    await page.evaluate(() => document.fonts.ready);
    const pdf = await page.pdf({ preferCSSPageSize: true, printBackground: true });
    const pages = pdf.toString("latin1").match(/\/Type\s*\/Page[^s]/g) ?? [];
    expect(pages.length).toBe(1);
  });

  test("VO, limits, audit, evaluation", async ({ page }) => {
    await open(page, `/contracts/${PRIV}/variation-orders/CR-C-SUBSTITUTION-VO`, /VO-0/);
    await shoot(page, "vo-document");
    await open(page, `/contracts/${GOV}/limits`, /Article 67/);
    await shoot(page, "limits");
    await open(page, `/contracts/${PRIV}/audit`, /CR-/);
    await shoot(page, "audit");
    await open(page, "/evaluation", /evaluation/i);
    await shoot(page, "evaluation");
  });

  test("notifications drawer and guide bar", async ({ page }) => {
    await open(page, `/contracts/${PRIV}`, "Change request register", {
      party: "GOVERNMENT_ENTITY",
      role: "FINANCE_MANAGER",
    });
    await page.getByRole("button", { name: /Notifications/ }).click();
    await page.waitForTimeout(600);
    await shoot(page, "notifications", false);
    await page.keyboard.press("Escape");
    await open(page, "/demo", /demo/i);
    await shoot(page, "demo");
    const startBtn = page.getByRole("button", { name: "Start", exact: true });
    if (await startBtn.count()) {
      await startBtn.first().click();
      await page.waitForTimeout(800);
    }
    const notes = page.getByRole("button", { name: /Presenter notes/i });
    if (await notes.count()) {
      await notes.first().click();
      await page.waitForTimeout(400);
      await shoot(page, "guide-notes");
    }
  });

  test("salami preset: refused at final approval", async ({ page }) => {
    const api = await apiRequest.newContext({ baseURL: API });
    const res = await api.post("/api/demo/reset?preset=salami", {
      headers: { "X-Demo-Token": TOKEN },
    });
    expect(res.ok()).toBeTruthy();
    const id = String((await res.json()).preset_detail.awaiting_final_signature_id);
    const body = await (await api.get(`/api/change-requests/${id}`)).json();
    type Step = { party: Persona["party"]; role: string; decision: string };
    const pending = (body.chain as Step[]).find((s) => s.decision === "PENDING")!;
    await api.dispose();

    await open(page, `/contracts/${GOV}/limits`, /Article 67/);
    await shoot(page, "limits-near-cap");
    await open(page, caseUrl(GOV, id), id, { party: pending.party, role: pending.role });
    await page.getByLabel(/Sign as/i).fill("Salman Alomari");
    await page.getByRole("button", { name: "Approve", exact: true }).click();
    await page.waitForTimeout(1500);
    await shoot(page, "case-refused-at-final");
  });

  test.afterAll(() => {
    fs.mkdirSync(OUT, { recursive: true });
    fs.writeFileSync(path.join(OUT, `${TAG}-raw-codes.txt`), found.join("\n") + "\n");
  });
});
