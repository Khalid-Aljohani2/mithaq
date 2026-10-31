# Screenshots (Step 5A)

`docs/design/screens/` holds every 5A screen at 1440 and 390 px wide, light and
dark: `<screen>-<width>-<scheme>.png`. Only the seeded demo requests appear.

## Reproduce

The run needs a backend whose state starts from the seed and whose AI stages
replay recorded outputs, so every run produces the same screens.

```powershell
# Terminal 1: backend from the main checkout, in-memory store, scripted provider.
# The variables apply to this process only; no .env file changes.
cd ..\ScopeGuardAi\backend
$env:DATABASE_URL = " "; $env:LLM_PROVIDER = "scripted"; $env:ALLOWED_ORIGINS = "http://localhost:3010"
$env:REMINDER_PENDING_APPROVAL_HOURS = "0"   # reminders show at once, for the drawer screen
$env:DEMO_RESET_TOKEN = "screens-demo-token" # the salami preset screens need the reset endpoint
.\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8010

# Terminal 2: this worktree's frontend, built against that backend.
cd frontend
"NEXT_PUBLIC_API_URL=http://localhost:8010" | Out-File -Encoding utf8 .env.local
npm run build; npx next start -p 3010

# Terminal 3
cd frontend
npx playwright install chromium   # once
npm run screens
```

The last block in the suite applies the `salami` demo preset, which resets the
backend and rebuilds the government contract at 945,000 of its 960,000 ceiling.
It is deliberately last; anything added after it would see a reset backend.

Restart the backend before each run. The suite moves the seeded requests into
a spread of states through the real API: CR-C through its whole chain and its
VO, CR-D (private) to the finance manager's step. The last tests change state:
the finance manager signs CR-D through the UI, a notification opens its case
file, and the VO is printed to PDF.

The in-memory store is used instead of the shared Postgres database so the run
never touches data another session depends on.

## Screens

| File prefix | What it shows |
| --- | --- |
| `workspace-government` | Contract header, Article 67 meters with cap marks, change-request register |
| `workspace-private` | The same for the private contract: no Article 67 meters, "المالك" for the client side |
| `shell-role-switcher` | Party and role chooser |
| `shell-contract-switcher` | Both demo contracts with their type badges |
| `new-request` | The new change-request form |
| `new-request-errors` | The same form after submitting empty: each error says what to do |
| `case-received` | A seeded request before analysis, with "تحليل الطلب" |
| `case-analysing` | The trace while analysis runs (the analyse call is held so the moment can be captured) |
| `case-closed-in-scope` | CR-A: closed as in scope, with the matching breakdown line as evidence |
| `case-recommended` | CR-B: recommended, chain shown, "بدء مسار الاعتماد" |
| `case-in-approval-my-step` | CR-D on the private contract viewed as the finance manager: policy exception, one seal, then this role's slot with its actions |
| `case-vo-issued` | CR-C after its full chain (project manager, technical manager) and VO issue: two seals and the link to the VO document |
| `case-legal-block` | CR-D on the government contract: legal block, articles cited, contractor consent slot active |
| `vo-document` | VO-001 as a document on screen, with the print button |
| `vo-document-print-a4.png`, `vo-document.pdf` | The same VO in print media: the A4 render and the browser's Print to PDF output, asserted to be exactly one page |
| `vo-document-government` (+ `-print-a4.png`, `.pdf`) | VO-001 on the government contract from CR-F-GOV-OK after its four-signature chain: cites Article 67 by its Arabic reference, one A4 page |
| `notifications-drawer` | The drawer for the client's finance manager: a reminder (amber, labelled) above the stored notifications, newest first |
| `case-awaiting-documents` | CR-B's seeded text resubmitted without its cost quote: the required checklist for its impact type, the missing one marked, and the resubmit form |
| `limits-government`, `limits-private` | Policy caps (cost and time) and, on the government contract, each Article 67 category with its Arabic reference; the VOs that make up the totals |
| `evaluation` | The published evaluation: headline first, then both label sets, latency and cost, the model comparison link, and the method |
| `audit-private`, `audit-government` | The append-only audit log for each contract |

The run's last tests change state: the finance manager signs CR-D through the
UI, a notification opens its case file, the awaiting request is resubmitted
with its missing document and re-analysed, and both VOs are printed to PDF and
asserted to be exactly one page each.

## Step 8: home, guide bar, both languages, both themes

`e2e/ux.spec.ts` runs after `screens.spec.ts` (Playwright runs files in name
order), so the government contract is already in the salami preset state. It
writes `docs/design/screens/ux/<screen>-<width>-<scheme>-<lang>.png`:

- home, government workspace, a VO-issued case, its VO document, the limits
  page near the Article 67 ceiling and the evaluation page, at 1440 wide, in
  Arabic and English, light and dark;
- home and workspace at 390 wide in both languages;
- the guide bar started from the home page, with Go driving Acts 1 and 2,
  and the presenter notes open (`guide-act1-notes-*`).

It also asserts that the theme choice is applied by the head script before
React runs, that print stays light under the dark theme, and that the
language toggle sets `lang` and `dir` and survives a reload.
