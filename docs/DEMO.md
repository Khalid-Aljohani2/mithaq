# Recording the demo video

Everything needed to record Mithaq end to end: how to start it, how to reset
between takes, which persona to be at each moment, and the exact clicks.

The story in one line: **a change nobody would refuse, refused — because
somebody was adding it up.**

---

## 1. Start the app

Two terminals. Nothing here edits a `.env` file; the variables apply to that
process only.

### With the live provider (what the video should show)

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

`DEMO_RESET_TOKEN` must be set in `backend/.env`. Substitute it below.

```powershell
# Back to the plain seed: five private requests and two government ones,
# all RECEIVED, nothing approved, the ledger empty.
curl.exe -X POST "http://localhost:8000/api/demo/reset" -H "X-Demo-Token: <token>"

# The salami preset: the government contract already at 945,000 of 960,000,
# with an eighth request one signature short of being refused.
curl.exe -X POST "http://localhost:8000/api/demo/reset?preset=salami" -H "X-Demo-Token: <token>"
```

The preset response names the ids it built — `preset_detail.approved_request_ids`,
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

## 3. Switching persona

Top right of every screen: **"تعمل بصفة"** (acting as). The switcher sets the
party and the role. It is a stand-in for sign-in — say so once, early, so
nobody thinks it is an authentication bypass.

What matters on camera: **the role checks are enforced by the backend.** If you
try to sign a step that is not yours, the server refuses it; the UI is not
merely hiding a button. Worth demonstrating once if you have 20 seconds spare.

---

## 4. The run of show

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

## 5. Request reference

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

## 6. Before you record

- [ ] Backend answers: `curl.exe http://localhost:8000/api/health`
- [ ] Frontend loads at `http://localhost:3000`
- [ ] Reset to the state the take needs
- [ ] Persona set **before** you start recording, not during
- [ ] Browser zoom 100%, window 1440 wide to match the committed screenshots
- [ ] Try one analyse first — with the live provider, the first call is the
      slowest
- [ ] If a take goes wrong, reset rather than clicking back: the state matters
      more than the clicks
