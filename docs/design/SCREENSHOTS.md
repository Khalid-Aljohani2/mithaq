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
$env:DATABASE_URL = ""; $env:LLM_PROVIDER = "scripted"; $env:ALLOWED_ORIGINS = "http://localhost:3010"
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
| `notifications-drawer` | The drawer for the contractor's project manager, newest first, each item linking to its case file |
| `audit-private`, `audit-government` | The append-only audit log for each contract |

Not captured: **reminders** in the notifications drawer. They are styled
(amber edge, clock, "تذكير" badge) but the backend only creates them after a
configured delay in hours, which a screenshot run cannot wait for.

Not captured: **awaiting documents**. The view is built, but the backend
currently answers 500 when analysis finds missing documents
(`IllegalTransitionError: IN_ANALYSIS -> AWAITING_DOCUMENTS`), so there is no
real state to photograph.
