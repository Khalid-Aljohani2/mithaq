import { expect, test } from "@playwright/test";

/**
 * Step 12: the guided flow on one request, in English. Analyse, then the
 * "Start approval" next step; "Sign as" switches the role, focuses the name
 * field and (demo mode) prefills it; the chain completes, then "Issue
 * variation order"; then "Open the variation order" and "See updated limits";
 * "Back to contract" on the request and the VO pages. Runs after
 * screens.spec.ts, whose last block resets the backend to the seed, so CR-B
 * on the private contract is RECEIVED again.
 */

const PRIV = "CT-2027-0419";
const CR = "CR-B-PCR";

test("next steps, sign as, and back to contract along one request", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.addInitScript(() => {
    window.localStorage.setItem("mithaqai.lang", "en");
    window.localStorage.removeItem("mithaqai.demo");
    if (!sessionStorage.getItem("primed")) {
      window.localStorage.setItem(
        "mithaqai.persona",
        JSON.stringify({ party: "CONTRACTOR", role: "PROJECT_MANAGER" }),
      );
      sessionStorage.setItem("primed", "1");
    }
  });
  await page.goto(`/contracts/${PRIV}/requests/${CR}`);
  await expect(page.locator("[data-back-to-contract]")).toHaveAttribute("href", `/contracts/${PRIV}`);

  await page.getByRole("button", { name: "Analyse request" }).click();
  const start = page.locator('[data-next-step="start-approval"]');
  await expect(start).toBeVisible({ timeout: 30_000 });
  await start.getByRole("button", { name: "Start approval" }).click();

  // The contractor is acting. The owner's approvals run project manager,
  // procurement manager, finance manager; each slot is signed through Sign as,
  // which switches the role and prefills the demo directory name.
  for (const signer of ["Reem Al-Shehri", "Nasser Al-Harthi", "Majed Al-Harbi"]) {
    const signAs = page.locator("[data-sign-as]");
    await expect(signAs).toBeVisible({ timeout: 20_000 });
    await signAs.click();
    const name = page.locator("[data-sign-name]");
    await expect(name).toBeFocused();
    await expect(name).toHaveValue(signer);
    await page.getByRole("button", { name: "Approve", exact: true }).click();
  }

  const issue = page.locator('[data-next-step="issue-vo"]');
  await expect(issue).toBeVisible({ timeout: 20_000 });
  await issue.getByRole("button", { name: "Issue variation order" }).click();

  const issued = page.locator('[data-next-step="vo-issued"]');
  await expect(issued).toBeVisible({ timeout: 20_000 });
  await expect(issued.locator("[data-see-limits]")).toHaveAttribute("href", `/contracts/${PRIV}/limits`);
  await issued.locator("[data-open-vo]").click();
  await page.waitForURL(/\/variation-orders\//);
  const back = page.locator("[data-back-to-contract]");
  await expect(back).toBeVisible();
  await back.click();
  await page.waitForURL(new RegExp(`/contracts/${PRIV}$`));
});
