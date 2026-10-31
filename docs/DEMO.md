# Recording the demo video

Everything needed to record Mithaq end to end: how to start it, how to reset
between takes, which persona to be at each moment, and the exact clicks.

The story in one line: **a change nobody would refuse, refused — because
somebody was adding it up.**

---

## 1. Start the app

Two terminals. Nothing here edits a `.env` file; the variables apply to that
process only.

### For recording with the guided demo (recommended)

In-memory store (every start is a clean seed, nothing touches the dev
database), the live provider, and `DEMO_MODE` on so the guide bar can reset
without a token. Needs `LLM_PROVIDER=anthropic` and `LLM_API_KEY` already set
in `backend/.env`.

```powershell
# Terminal 1: backend on 8000, in memory, live provider, demo mode
cd backend
$env:DATABASE_URL = " "   # one space: PowerShell deletes a variable set to "", and .env would win
$env:DEMO_MODE = "true"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000

# Terminal 2: frontend on 3000
cd frontend
npm run dev
```

`DEMO_MODE` lets `POST /api/demo/reset` run without the token **only from
localhost** (decision record 0005). Never set it on a deployed backend.

### With the live provider on the dev database

The four AI stages call the Claude API, so the trace reads **"live"** rather
than "recorded" and the latency is real. Needs `LLM_PROVIDER=anthropic` and
`LLM_API_KEY` already set in `backend/.env`.

```powershell
# Terminal 1 — backend on the dev database, live provider
cd backend
.\.venv\Scripts\Activate.ps1
.\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000

# Terminal 2 — frontend
cd frontend
npm run dev          # http://localhost:3000
```

Analysing one request takes roughly 25 seconds. **Plan for it**: start the
analysis, then talk over it, or cut.

### With the scripted provider (safe, instant, free)

Identical UI and identical numbers, replayed from recorded outputs. Use this
for rehearsals, for a flaky connection, or if the venue has no internet. The
trace labels every AI stage **"رد مسجل" (recorded)** — which is honest, and
worth saying out loud if you use it.

```powershell
# Terminal 1
cd backend
$env:LLM_PROVIDER = "scripted"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000
```

Close that terminal afterwards: the variable is set for that session only.

> **Reminders in the demo.** Add `$env:REMINDER_PENDING_APPROVAL_HOURS = "0"`
> and `$env:REMINDER_AWAITING_DOCUMENTS_HOURS = "0"` before starting the
> backend, and reminders appear immediately instead of a day later. Only do
> this if the video shows the notifications drawer.

---

## 2. Reset between takes

**With the guide bar:** open **Presenter notes** in the guide bar. With
`DEMO_MODE` on, the notes panel holds **Reset demo** and **Load salami
preset**. They sit inside the notes on purpose, so they are never on camera
unless you open the notes. The same two buttons are on `/demo`. After a
salami reset the guide remembers the eighth request, and Act 5 gets an
**Open the eighth request** button.

**Without demo mode:** `DEMO_RESET_TOKEN` must be set in `backend/.env`.
Substitute it below.

```powershell
# Back to the plain seed: five private requests and two government ones,
# all RECEIVED, nothing approved, the ledger empty.
curl.exe -X POST "http://localhost:8000/api/demo/reset" -H "X-Demo-Token: <token>"

# The salami preset: the government contract already at 945,000 of 960,000,
# with an eighth request one signature short of being refused.
curl.exe -X POST "http://localhost:8000/api/demo/reset?preset=salami" -H "X-Demo-Token: <token>"
```

From the command line, the preset response names the ids it built — `preset_detail.approved_request_ids`,
`preset_detail.awaiting_final_signature_id` — so you never have to guess which
request to open:

```powershell
curl.exe -s -X POST "http://localhost:8000/api/demo/reset?preset=salami" -H "X-Demo-Token: <token>" | ConvertFrom-Json | Select-Object -ExpandProperty preset_detail
```

The preset is built by driving the **real service functions** with recorded AI
outputs, so it takes a few seconds and the state it produces is one the product
can genuinely reach — full agent traces, real approval chains, real VOs.

Audit rows are never deleted. A reset appends a `DEMO_RESET` event instead, so
the audit page keeps growing across takes. That is worth showing, not hiding.

---

## 3. The guided demo

Open `http://localhost:3000`. The home page says what MithaqAi is, shows the
control principle (AI reads, code decides money and law, people approve) and
the measured recommendation accuracy. Click **Start the guided demo**.

While the demo is active, a guide bar sits under the letterhead on every
page:

| Control | What it does |
|---|---|
| Previous / Next | Move between the six acts |
| Act n of 6 and its title | Where you are |
| **Go** | Sets the persona and opens the act's screen. Never set the persona by hand. |
| Presenter notes | Two to four talking points for the act, in the current language. Closed on every page load, so they only appear if you open them. Also holds Reset demo and Load salami preset. |
| Leave demo | Hides the bar |

| Act | Go opens | Persona set by Go |
|---|---|---|
| 1. The contract and its limits | `CT-2027-0418` workspace | Government entity, Project manager |
| 2. A new request and the 11 stages | `CR-C-SUBSTITUTION` on `CT-2027-0419`, ready to analyse | Contractor, Project manager |
| 3. Recommendation and approval chain | The same request | Government entity, Project manager (then switch to Technical manager for the second signature) |
| 4. The variation order | The VO of `CR-C-SUBSTITUTION` (the request itself, with a note, if no VO yet) | Government entity, Project manager |
| 5. The salami case | `CT-2027-0418` limits page; **Open the eighth request** after a salami reset | Government entity, Legal advisor |
| 6. Measured results | `/evaluation` | unchanged |

Take order: reset to the plain seed, run Acts 1 to 4, then load the salami
preset from the notes and run Acts 5 and 6. The run of show in section 6
has the clicks and lines for each moment.

### Act 0: project intake (optional, before Act 1)

A new contract, created in the app, ready for change requests. Persona:
**Government entity, Project manager** (only the client side's project
manager or CEO may create a contract; the backend enforces it).

1. From the home page, or the bottom of the contract switcher, open **New
   project**.
2. **With the live provider:** paste the contents of
   `docs/demo/sample-project-ar.txt` (or upload it as a PDF) under **Upload
   project details** and click **Draft the form with AI**. Every field the
   model filled carries an **AI draft** mark until a person edits or
   confirms it. Say it: the AI drafts, nothing is saved yet.
   **With the scripted provider:** drafting shows a message that it needs the
   live provider; fill the form by hand from the same file.
3. Review the seven lines. The grand total, computed by code, must equal the
   contract value exactly (2,495,000 SAR in the sample); change one rate to
   show the form refusing and saying why, then put it back.
4. Type your name and click **Create**. The new contract opens with its
   policy and Article 67 meters at zero, and accepts change requests like the
   seeded ones.

> **Say:** the model reads the document and drafts; code checks every number;
> a person creates the contract.

A demo reset rebuilds the seed (see section 2), so record Act 0 after any
reset you need, or accept that the new contract disappears on the next reset.

## 4. Language and theme

The letterhead has two toggles: **English / العربية** and light or dark.
Both are remembered per browser and applied before the page paints.

- **English mode** switches every label, button, heading, empty and error
  state and the VO document chrome, and mirrors the layout left to right.
  Contract content written in Arabic (request text, item descriptions, the
  VO scope paragraph, legal text, the agent's Arabic reasoning) stays Arabic
  and is labelled **Original Arabic**. Where the backend sends both
  languages (stage summaries, notifications), the English is shown.
- The legal refusal in Act 5 reads in English, still naming Article 67(1)(b)
  and 67(2).
- Printing the VO is always light, whatever the screen theme.

Suggested: record in Arabic, and show English once (toggle it on the
workspace in Act 1) so a non-Arabic-speaking judge sees the same screen in
their language.

## 5. Switching persona

With the guided demo, **Go** sets the persona for you. By hand: the
letterhead's **"تعمل بصفة"** (acting as) switcher. The switcher sets the
party and the role. It is a stand-in for sign-in — say so once, early, so
nobody thinks it is an authentication bypass.

What matters on camera: **the role checks are enforced by the backend.** If you
try to sign a step that is not yours, the server refuses it; the UI is not
merely hiding a button. Worth demonstrating once if you have 20 seconds spare.

---

## 6. The run of show

Reset to the **plain seed** before this section.

### Act 1 — The shared ledger (≈45 s)

**Persona:** الجهة الحكومية · مدير المشروع (Government entity · Project
manager)
**Contract:** `CT-2027-0418` (government)

1. Land on the workspace. One contract, one request log, both parties.
2. Point at the **limits panel**: two layers, visibly different. Organisation
   policy, which a named role can escalate past; Article 67, which is blocking
   and cites its article.
3. Switch the persona to **المقاول · مدير المشروع** (Contractor · Project
   manager). Same ledger, same totals, different available actions.

> **Say:** one contract, two parties, one record. Nobody is keeping a second
> set of books.

### Act 2 — A request the contract already covers (≈45 s)

**Persona:** المقاول · مدير المشروع · **Contract:** `CT-2027-0419` (private)

1. Open **`CR-A-INSCOPE`** — state `RECEIVED`.
2. Click **تحليل الطلب** (analyse). *Live provider: ~25 s.*
3. Result: **`CLOSED_IN_SCOPE`**, 0 SAR. The agent found it already covered by
   the breakdown.
4. Open the **trace**. Eleven stages, each labelled with its actor: 🤖 model,
   📋 code, ✍️ person.

> **Say:** the cheapest change order is the one that was never a change order.

### Act 3 — The decision boundary (≈60 s)

**Persona:** المقاول · مدير المشروع · **Contract:** `CT-2027-0419`

1. Open **`CR-C-SUBSTITUTION`** and analyse it.
2. Open **stage 3** in the trace: the model found the matching line and said
   why, in Arabic, quoting the request.
3. Open **stage 5**: the money. **Point out the actor badge — this stage is
   code.** 540,000 out at the contract rate, 672,000 in at the proposed rate.
4. The unit-rate flag: 56,000 against a contract rate of 45,000 is a 24.44%
   deviation, above the 20% policy limit, so it is flagged.

> **Say:** the model read the request and matched the line. It did not compute
> one riyal. It *cannot* — there is no money field in its output schema.

### Act 4 — A human approves (≈45 s)

1. Still on `CR-C-SUBSTITUTION`, click **بدء مسار الاعتماد** (start approval).
2. Switch to **الجهة الحكومية · مدير المشروع**. Type a name, click **اعتماد**.
   The **seal** stamps with the name and the time.
3. Switch to **الجهة الحكومية · المدير الفني** and approve. The chain
   completes.
4. Click through to the **variation order**. Code assembled the values and the
   citations; the model drafted only the Arabic scope paragraph. Hit
   **طباعة** — one A4 page, no app chrome.

> **Say:** every signature is a person's. The agent recommended; it approved
> nothing.

### Act 5 — The salami (≈90 s, the centrepiece)

**Reset with the preset now**, on camera if you like — it is one call.

**Persona:** الجهة الحكومية · مدير المشروع · **Contract:** `CT-2027-0418`

1. Open **حدود التغيير** (the limits page). **Article 67(1)(b): 945,000 of
   960,000 approved. 135,000 pending. 15,000 left.** Let that sit.
2. Scroll to **أوامر التغيير المعتمدة** — seven variation orders, 135,000 each.
   Each was approved on its own and each was entirely legitimate.
3. Open the eighth request (`preset_detail.awaiting_final_signature_id`). Note
   its recommendation: **APPROVE**. It was analysed when the ledger was empty.
   Nothing about it is wrong.
4. Switch to the persona holding the final signature — the preset leaves it
   with **الجهة الحكومية · المستشار القانوني** (Legal advisor). Type a name.
5. Click **اعتماد**.
6. **Refused.** Red banner, in Arabic: the approval would exceed a cumulative
   legal limit, **Article 67(1)(b)** and **Article 67(2)**, no internal
   approval lifts it, and the request has gone to legal review.
7. Return to the limits page: **still 945,000.** Nothing moved.

> **Say:** eight requests. Not one of them looked wrong. Seven were approved and
> the eighth was refused — not because it was large, but because of the seven
> before it. That is the whole product.

### Act 6 — Receipts (≈30 s)

1. Open the **audit page**. Every state change, with the party and the person
   who made it — and the refusal, recorded as its own action.
2. Open **نتائج التقييم** (the evaluation page) from the header. 92.0%
   recommendation accuracy on a held-out split, 0 errors, 3/3 injection
   attempts turned away, scored against both label sets, traceable to a commit.

> **Say:** we measured it, we published the measurement, and we published the
> labels we changed and why.

---

## 7. Request reference

After a plain reset. Government contract `CT-2027-0418`, private
`CT-2027-0419`, both 4,800,000 SAR.

| Request | Contract | State | What it demonstrates |
|---|---|---|---|
| `CR-A-INSCOPE` | private | RECEIVED | Already covered → closed, 0 SAR |
| `CR-B-PCR` | private | RECEIVED | A clean increase within every limit |
| `CR-C-SUBSTITUTION` | private | RECEIVED | Product swap, unit-rate deviation flagged |
| `CR-D-POLICY` | private | RECEIVED | 21% → policy cap exceeded, CEO exception required |
| `CR-E-NCR` | private | RECEIVED | A decrease |
| `CR-F-GOV-OK` | government | RECEIVED | Inside Article 67 → a government VO citing it |
| `CR-D-GOV` | government | RECEIVED | The same 21%, **blocked** by Article 67 |

`CR-D-POLICY` and `CR-D-GOV` are the same request on different contract types —
a policy cap that a CEO can lift, and a legal cap that nobody can. A good
30-second aside if you have room.

---

## 8. Before you record

- [ ] Backend answers: `curl.exe http://localhost:8000/api/health`
- [ ] Frontend loads at `http://localhost:3000`
- [ ] Reset to the state the take needs
- [ ] Guided demo started from the home page; presenter notes closed
- [ ] Persona set by **Go**, not by hand
- [ ] Browser zoom 100%, window 1440 wide to match the committed screenshots
- [ ] Try one analyse first — with the live provider, the first call is the
      slowest
- [ ] If a take goes wrong, reset rather than clicking back: the state matters
      more than the clicks
