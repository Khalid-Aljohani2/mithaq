# MithaqAi design plan (Step 5A)

MithaqAi takes its name from ميثاق, the Arabic word for a binding covenant
between two parties. The interface borrows from the thing the name points at:
an official contract file. Each change request is a case in that file, with a
reference number, ruled sections, cited articles and a row of signature slots.

Requirements served by this plan: FR-02 (role switch), FR-03, FR-04, FR-05 to
FR-10 (display and actions), FR-15, NFR-13.

## 1. Principles

1. **Built like a contract file, not a SaaS dashboard.** The page is a
   sheet on a paper ground. Sections are separated by rules, not boxed into
   cards. References, article numbers and amounts are set like a formal
   document.
2. **Citations sit in the margin.** Each section has a narrow column on the
   start side (right in RTL) for its reference: article, breakdown line or CR
   number. You can read the claim and its authority on the same line.
3. **One bold place.** The stage trace and the approval seal carry the
   personality. Everything else stays quiet: one ink colour, three signal
   colours used only for meaning, and no decoration.
4. **Signal colours mean one thing each.** Seal green: approved, or the
   primary action. Amber: consent or escalation needed. Legal red: blocked.
   None of them is ever used for decoration.
5. **The agent recommends; people sign.** Wherever the agent's output appears,
   it is labelled as a recommendation. Decision controls appear only in the
   signature slot that belongs to the active role.
6. **Numbers are exact.** Western digits, tabular figures, SAR, and the
   value exactly as the API sent it. The browser never does arithmetic on
   money. Meter widths are computed by CSS `calc()` from the API's percentage
   strings, so no JavaScript float touches a percentage.

## 2. Tokens

### Colour

| Role | Light | Dark | Use |
| --- | --- | --- | --- |
| `paper` | `#F6F7F5` | `#1C232B` | page ground |
| `sheet` | `#FFFFFF` | `#232B34` | the case sheet, inputs |
| `ink` | `#1B2430` | `#E7EAE6` | body text, headings |
| `ink-muted` | `#505B66` | `#A8B0B8` | labels, secondary text |
| `rule` | `#D6DAD5` | `#36404B` | hairline rules (decorative, non-text) |
| `rule-strong` | `#7A837C` | `#6E7A86` | meter track edges, cap marks (≥ 3:1) |
| `seal` | `#0E6B4F` | `#6CC29E` | approved, primary action |
| `seal-wash` | `#E3EFE8` | `#1F3A31` | approved slot ground |
| `amber` | `#8A5D0E` | `#E2B45C` | consent or escalation needed |
| `amber-wash` | `#F5ECDA` | `#3A3020` | |
| `legal` | `#A3201D` | `#F2948D` | blocked by law |
| `legal-wash` | `#F7E4E2` | `#422726` | |

The dark theme is a blue slate night (`#1C232B`), not near-black, and it keeps
the same roles. Its greens and reds are lifted and desaturated so they read as
ink, not neon.

Measured contrast (WCAG 2.x), lowest pair per role:

| Text on ground | Light | Dark |
| --- | --- | --- |
| ink on paper / sheet | 14.57 / 15.65 | 13.07 / 11.80 |
| ink-muted on paper / sheet | 6.45 / 6.93 | 7.22 / 6.52 |
| seal on paper / seal-wash | 6.04 / 5.50 | 7.43 / 5.77 |
| amber on paper / amber-wash | 5.35 / 4.90 | 8.24 / 6.72 |
| legal on paper / legal-wash | 7.03 / 6.17 | 7.09 / 6.06 |
| button text on seal | 6.49 (white) | 8.35 (`#0F1A15`) |

Every pair passes AA (4.5:1) for body text.

### Type

- **IBM Plex Sans Arabic** (400, 500, 600) for the interface.
- **Noto Naskh Arabic** (400, 600) for quoted request text, legal text,
  recommendation reasons and the seal. Naskh marks "this is the document";
  Plex marks "this is the tool".
- Both are loaded with `next/font/google` and exposed as `--font-ui` and
  `--font-doc`.
- `font-variant-numeric: tabular-nums` on the root. Every number column lines
  up.

The scale is a 1.2 ratio from a 16px base, with generous Arabic line height:

| Token | Size / line height | Use |
| --- | --- | --- |
| `text-2xs` | 12 / 18 | margin references, meter ticks |
| `text-xs` | 13 / 20 | labels, badges |
| `text-sm` | 14 / 22 | table cells, stage summaries |
| `text-base` | 16 / 28 | body |
| `text-doc` | 18 / 34 | Naskh request text |
| `text-lg` | 19 / 30 | section titles |
| `text-xl` | 23 / 34 | case title |
| `text-2xl` | 28 / 40 | contract title |

Weights: 400 for body, 500 for labels and values, 600 only for titles. No
uppercase anywhere, and Arabic has no case to begin with. Labels are not
tracked out.

### Spacing, radius, rules

- 4px base: 4, 8, 12, 16, 24, 32, 48, 64.
- Radius follows hierarchy rather than one value for everything:
  - 0 for sections and the sheet;
  - 2px for inputs, buttons and badges, a printed form box;
  - 50% only for the seal and the actor glyph discs.
- Rules: 1px `rule` between rows. A double rule (1px, 2px gap, 1px) under the
  letterhead and above the signature block, the way formal documents open and
  close. A 2px `ink` rule marks the active stage.
- No shadows except the open popover, which uses 1px `rule-strong` plus a
  0 8px 24px shadow at 12% ink.

### Motion

- **Stage trace (the orchestrated moment).** When "تحليل الطلب" runs, rows
  1 to 7 sit as "قيد الانتظار" and the current row shows a moving ruled
  underline. The backend returns all stages at once (see section 6), so when
  the response lands, stages are revealed in stage order, 140ms apart. Each
  row's marker fills, then its summary fades in.
- **Seal (motion answering an action).** Approving stamps the seal into the
  slot: it scales from 1.35 to 1 and settles from -14° to -8° over 260ms,
  with a brief ink-spread ring.
- Nothing else animates on load. `prefers-reduced-motion: reduce` turns both
  into instant state changes.

## 3. Language, direction, formatting

- `<html lang="ar" dir="rtl">`. Only logical properties (`ms-`, `me-`, `ps-`,
  `pe-`, `start-`, `end-`, `border-s`, `text-start`). No `left` or `right`
  in the code.
- Money: `Intl.NumberFormat("ar-SA", { numberingSystem: "latn", style:
  "currency", currency: "SAR" })`, fed the API's decimal **string**, never a
  parsed float.
- Dates: `Intl.DateTimeFormat("ar-SA-u-ca-gregory-nu-latn")` with a day,
  month and year. Times only on signatures.
- Percentages: the API's string, trimmed to two decimals, followed by `%`.
- Terms: each screen opens its body with a key line for every abbreviation
  that appears on it, for example "CR (طلب تغيير)، PCR (طلب تغيير موجب)". In the
  case file, the kind is written in full in the case header. After that,
  abbreviations stand alone. Doing this per screen keeps it deterministic,
  because "first appearance" no longer depends on render order.
- Parties: `GOVERNMENT_ENTITY` displays as "الجهة الحكومية" on government
  contracts and "المالك" on private ones. `CONTRACTOR` displays as "المقاول".

## 4. Screens and wireframes

All wireframes are RTL: the first column is drawn on the right.

### 4.1 App shell (letterhead)

```
+---------------------------------------------------------------------------+
|  MithaqAi      [ عقد CT-2027-0418  حكومي  v ]   [ المقاول / مدير المشروع v ]   (bell 3) |
+===========================================================================+  <- double rule
```

- Wordmark: "MithaqAi" in Plex 600 with "Ai" in ink-muted weight 400. It is a
  two-weight wordmark, not a coloured accent word.
- Contract switcher: a button showing the reference number, short title and a
  type badge ("حكومي" or "خاص"). It opens a listbox of both demo contracts.
- Role switcher: party and role, two native `<select>`s in one popover. The
  choice is stored in `localStorage` and sent wherever the backend expects
  it: `party` and `role` on `/api/notifications` and in the decision body.
- Bell: the count from `/api/notifications` for the active party and role,
  polled every 30s. The drawer belongs to 5B, so in 5A the bell only shows the
  count, with an `aria-label` that says how many are waiting.
- At 390px the letterhead becomes two rows: wordmark and bell, then the two
  switchers at full width.

### 4.2 Contract workspace (home)

```
+---------------------------------------------------------------------------+
| ref   | مشروع تنفيذ نظام إدارة الخدمات الرقمية                       [حكومي]   |
| CT-…  | الجهة الحكومية  أمانة منطقة الواحة     المقاول  شركة أفق …              |
|       | القيمة 4,800,000 ر.س   البداية 15/01/2027   النهاية 14/01/2028          |
+-------+-------------------------------------------------------------------+
| م 67  | حدود التغيير التراكمية                                              |
| (1)(أ)| بنود جديدة      [=====|·····:········]  0 من 480,000 ر.س (10%)        |
| (1)(ب)| زيادة كميات     [==========:········]  …                             |
| (1)(ج)| تخفيض كميات     …                                                 |
| (2)   | الإجمالي        …                                                  |
+-------+-------------------------------------------------------------------+
|       | سجل طلبات التغيير                              [ طلب تغيير جديد ]   |
|       | key: CR (طلب تغيير)، PCR (…)، NCR (…)                               |
|       | المرجع | الحالة | النوع | أثر التكلفة | التوصية | المعتمد الحالي       |
|       | CR-B-PCR | بانتظار الاعتماد | PCR | 135,000 | اعتماد | مدير المشروع     |
+-------+-------------------------------------------------------------------+
```

- The header is a definition table, not a hero number. The contract value is
  one fact among several.
- Meter: the track runs to 1.5× the cap. A tall `rule-strong` tick marks the
  cap. "Used" is solid ink; "pending" is ink hatching. Anything beyond the cap
  is legal red. The value and cap sit after the bar, and the article sits in
  the margin.
- Policy meters (20% cost and time) are **not** shown: the API does not expose
  the policy caps (gap 1). Private contracts show no Article 67 meters,
  because the law applies to government contracts only. In their place is one
  line saying the policy limits appear on each case file.
- The register is a real `<table>` at 1440. At 390 each row becomes a ruled
  block: reference and state on one line, then kind, cost and recommendation.

### 4.3 New change request

```
+-------+-------------------------------------------------------------------+
|       | طلب تغيير جديد على العقد CT-2027-0418                              |
| 1     | مقدم الطلب   [ الاسم ]   الطرف [ المقاول v ]                         |
| 2     | نص الطلب (Naskh textarea, 8 rows)                                   |
| 3     | المرفقات   [x] طلب تغيير رسمي  [ ] عرض سعر …   [ + إضافة مرفق ]        |
| 4     | المبالغ والمدة  المبلغ [   ] ر.س   سعر الوحدة [   ]   الأيام [   ]       |
|       | "المبالغ يُدخلها الأشخاص دائمًا، ولا يقترحها الوكيل."                    |
|       |                                   [ تقديم الطلب وتحليله ]           |
+-------+-------------------------------------------------------------------+
```

The numbered margin is justified here: it is a form with sections in a fixed
order. Submitting runs `POST …/change-requests`, then
`POST …/analyse`, then opens the case file. The button names both steps.

### 4.4 Case file (core)

```
+---------------------------------------------------------------------------+
| CR-B-PCR   PCR (طلب تغيير موجب)                       بانتظار الاعتماد       |
| key line                                                                  |
+----------------------+-----------------------+----------------------------+
| نص الطلب (Naskh)       | مسار الطلب               | التوصية: اعتماد   88%       |
| …                    | 1 الاستلام      AI  ●   | الأسباب / الإجراءات التالية   |
| البنود المطابقة        | 2 المستندات     code ●  | التنبيهات                    |
| ITM-04  …  rate      | 3 النطاق        AI  ●   | الأثر: 135,000 ر.س  0 يوم    |
| المرفقات               | …                     | ===== سلسلة الاعتماد =====   |
|                      | 8 الاعتماد      human ◐ | [1] الجهة الحكومية، مدير…  |
|                      | 9 أمر التغيير    human ○ |     [اعتماد][رفض][طلب تعديل] |
|                      | 10 السجلات      code  ○  | [2] …                       |
|                      | 11 المتابعة     human ○ |                             |
+----------------------+-----------------------+----------------------------+
```

- Column widths at 1440: request 30%, trace 34%, decision 36%. Below 1024px
  the three zones stack in the order the brief asks for: summary and actions,
  then trace, then request.
- **Trace row:** a stage number in a 2ch tabular column, then the stage name,
  then the actor glyph in a 20px disc. Code is a calculator glyph (it computes),
  AI is a scanning glyph (it reads), and a human is a pen nib (they sign).
  After that comes the status, the duration in ms, and one line of summary.
  A connecting vertical rule runs through the markers. A filled marker means
  done, a half marker means in progress, an empty one means not started, and a
  red marker means blocked. Rows expand (`<button aria-expanded>`) to show the
  payload as a labelled definition list, never raw JSON. Recorded outputs
  carry "رد مسجل".
- **Stages 8 to 11:** stage 8 is built from the approval chain (who has signed
  and who is next). Stages 9 to 11 show "لم يبدأ" until their records exist;
  they are actioned in 5B.
- **Recommendation:** the verb in Naskh 600 ("يوصي الوكيل بالاعتماد"),
  confidence as a percentage, reasons and next actions as ruled lists, and a
  standing line: "توصية فقط، والقرار لأصحاب الصلاحية".
- **Flags:** one line per flag with a signal-colour bar at the start edge. Each
  flag says what it means and cites its source: article refs from the stage-6
  payload, or policy.
- **Approval chain:** signature slots behind a double rule. Each slot shows its
  position, party, role, why it is in the chain, and then either a
  dotted signature line or the signer's name and time. Only the slot for the
  active party and role, if it is the next pending slot, shows a name field
  and three buttons. Reject and request revision open a reason field that
  must be filled in before they submit. An approved slot shows the seal.
- **Awaiting documents:** the decision zone shows the gap list (required and
  missing) and "إعادة التقديم للتحليل".
- **Closed in scope:** the decision zone shows "أُغلق كطلب داخل النطاق" with the
  matched breakdown lines restated as evidence.

## 5. Engineering choices

- **Types:** `openapi-typescript` 7.13.0 generates `src/lib/api-types.ts`
  (`npm run gen:api`). One client, `src/lib/api.ts`, exports a typed function
  per endpoint. The untyped `payload` and `usage` objects are read through
  small type guards in `src/lib/payload.ts`. There is no `any`.
- **Fetching:** no new library. A 40-line `useResource` hook (fetch, abort on
  unmount, `reload()`) covers every view. The only polling is the bell, every
  30s, done with `setInterval`. A caching library such as SWR or TanStack Query
  would add a dependency to solve problems this step does not have: one user,
  two contracts, and a few views that refetch after each action.
- **State:** the active contract and persona live in a React context backed by
  `localStorage`.
- **States:** every view renders loading (ruled skeleton rows), empty (an
  invitation to act) and error (what failed and what to do, plus a retry).
- **Focus:** a 2px `ink` outline with 2px offset on every interactive element,
  via `:focus-visible`.
- **Screenshots:** `@playwright/test` 1.64.1, `npm run screens`. The script
  analyses the seeded demo requests through the API, then captures every
  screen at 1440 and 390, light and dark (`colorScheme` emulation), into
  `docs/design/screens/`.

## 6. API gaps found while planning

1. **Policy caps.** No endpoint exposes the 20% cost and time policy caps or
   contract-level usage against them. The workspace shows only the Article 67
   meters. Per CR, the stage-6 payload (`policy.cost_cap_pct`, `time_cap_pct`)
   is shown in the case file.
2. **Resubmit with new attachments.** No endpoint updates a CR's attachments.
   "إعادة التقديم" calls `POST /analyse` again, which re-checks the same list.
3. **Article per usage scope.** `UsageSnapshot` carries no article reference,
   and Arabic references are not exposed anywhere. The frontend maps each scope
   to the English ref the API already returns in `regulation.article_refs`.
   NFR-02 would prefer `article_ref_ar` and `article_ref_en` on each snapshot.
4. **Live stage progress.** `POST /analyse` is synchronous and returns all
   stages at once. The trace reveals them in order after the response; it does
   not stream progress.
5. **Required-documents list.** The checklist on the new-request form uses the
   document names seen in the seeded data. No endpoint lists the
   required documents per change type.

## 7. Review against the brief and against generic defaults

I wrote a first pass, then checked it against the brief and against what I'd
produce for any "AI dashboard" prompt. These are the changes:

| First pass | Changed to | Why |
| --- | --- | --- |
| Contract header as a hero: large contract value, smaller label beneath | Definition table: title, parties, value, dates, type | A big-number hero is the stock dashboard opener. In a contract file the value is one clause among others. |
| Limits as four cards with circular gauges | Ruled linear meters in one section, cap tick, article in the margin | Identical rounded cards are the SaaS kit the brief rules out. Gauges hide the cap, and the brief asks for "marks at the cap". |
| CR list as cards with a coloured status pill each | A `<table>` register, stacked ruled rows on mobile | A register is how a file lists its cases, and columns let you scan cost and state. |
| Section labels as small grey caption lines above every block | Section titles only where a section starts; references in the margin | This avoids the eyebrow-label tell, and the margin column carries real information instead. |
| Meta line "PCR · 135,000 ر.س · بانتظار الاعتماد" | Labelled fields in the case header | Middle-dot strings are a template tell, and labelled fields read better in Arabic. |
| One 8px radius on everything | 0 for sections, 2px for controls, round only for seal and glyphs | Radius now encodes hierarchy instead of being a default. |
| Stage status as coloured dots | Markers on a connecting rule, plus an actor glyph disc that carries the code / AI / human distinction | The trace is where boldness goes, and actor type is the point of FR-15. |
| Approval as a green check badge | A circular double-ring seal with "معتمد" and the date in Naskh, stamped at a slight angle | The brief asks for a seal. A check badge is generic, and the seal is the one memorable mark. |
| Dark theme on `#111` with a bright green | Slate `#1C232B` with lifted, desaturated signal colours | The brief rules out near-black with a neon accent. |
| Numbered markers in the register and the flags | Numbers only on the 11 stages, the chain positions and the form sections | Only those are real sequences. |
| "Run analysis" as an arrow button | "تحليل الطلب", and on the form "تقديم الطلب وتحليله" | No arrows appended, and each button names exactly what happens. |

## 8. Changes after the screenshot review

I looked at every screen at 1440 and 390, light and dark, and fixed what was
wrong before committing:

| Seen in the screenshots | Fix |
| --- | --- |
| Percentages rendered as "%10" inside Arabic sentences | Each percentage is wrapped in Unicode isolates (`⁦…⁩`), so the bidi algorithm keeps "10%" intact |
| Whole amounts showed ".00" (`4,800,000.00 ر.س.`) | `minimumFractionDigits: 0`; halalas still show when the API sends them |
| The reasons list repeated itself: the agent's reasons and the code labels said the same thing twice | Show the agent's reasons, and fall back to the code labels only when it gave none |
| Stage 5 showed an English line ("Cost impact 132000 SAR") because code stages return no Arabic summary | Compose the Arabic line from the stage's own numbers |
| The contract reference wrapped onto two lines in the 390 switcher | References never wrap (`white-space: nowrap`) |
| The seal was too small to read at 1440 | Raised from 96 to 112px |
| The register said "1 طلبات" | Arabic count agreement (طلب واحد، طلبان، 3 طلبات، 11 طلبًا) |

## 9. Step 5B, part 1

- **VO document** (`/contracts/[id]/variation-orders/[voId]`). It is the one
  screen that is a document rather than a tool, so it is set in Naskh. It has
  a letterhead naming both parties, then four numbered clauses: the change,
  the affected lines with contract rates, value and time, and the cited
  articles. Signature blocks follow, with the seal stamped beside them. Print
  CSS restores the light palette whatever the screen theme, hides the app
  chrome and the print button, and sets `@page` to A4 portrait. The run
  asserts that the browser's PDF is exactly one page.
- **Notifications drawer.** A side sheet from the end edge, newest first.
  Reminders get an amber edge, a clock and a "تذكير" badge, the only amber
  in the list. Each item links to its case file and closes the drawer.
- **Audit page.** A ruled table: number, time, actor, action, entity, previous
  state, new state, reason. One line under the title says the log is
  append-only. Analysis entries record the recommendation code as their
  reason, so it is shown as "التوصية: اعتماد".
- **Issuing the VO.** When the chain is complete, the case file shows
  "إصدار أمر التغيير", a human action. Once the VO exists, a block links to the
  document.

Fixed after reviewing the screenshots: the seal overlapped the double rule
above the signatures, so it now sits inside the signature block in its own
reserved space. The drawer's scrim lightened the page in dark mode and is now
a fixed dark tint. The drawer is captured at the viewport, not the full page.
Analysis reasons appeared as raw codes ("APPROVE") in the audit log. The
notification kind `APPROVAL_PENDING` is also sent when a chain completes, so
it is labelled "مسار الاعتماد" rather than "اعتماد مطلوب".
