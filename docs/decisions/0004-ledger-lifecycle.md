# 0004 — The Article 67 ledger accumulates through the workflow

Status: accepted
Date: 2026-10-31
Requirements: FR-07, FR-10, FR-13, NFR-02, NFR-16

## Context

Mithaq's premise is that a contract's change orders are judged against the
contract's *cumulative* position, not one at a time. Article 67 caps are
cumulative for a reason: a 25% increase refused as one request can be waved
through as five requests of 5% if nobody is adding them up. That is the
failure the product exists to prevent.

The rules engine could always add them up. Nothing was putting anything in
front of it. `commit_ledger_entries` was written in Step 4A and never called by
any code path, so the v2 workflow approved change requests and the ledger
stayed empty. Cumulative enforcement existed only in the engine's own unit
tests — green tests over a ledger the application never wrote to.

## Decision

**A change request puts entries on the Article 67 ledger as it moves through
approval, and the caps are re-checked at the moment of commitment.**

### 1. Entries are written when the request enters approval, as pending

One entry per Article 67 category the request moves; a substitution writes
both halves, because Article 67 counts gross movements per category and a net
figure would understate both.

Pending means **"committed if approved"**: reported on the ledger so both
parties can see what is in flight, and counted toward no cumulative total. A
request under consideration must never silently consume headroom — otherwise
two parties racing to submit would each be blocked by the other's unapproved
paperwork.

Not at analysis time: a recommendation is not a commitment, and reserving
headroom for one would let an advisory opinion block a real approval.

### 2. Article 67 is re-evaluated at the final approval

Stage 6 checks the caps when the request is analysed. That check is necessary
and not sufficient: between analysis and the last signature, other requests may
have been approved against the same contract. The law counts the position at
the time of the commitment, not the position at the time somebody filled in a
form.

So the last approval in the chain re-reads the ledger and re-runs the check. If
the cumulative position would now breach a cap, **the approval is refused**:
nothing is recorded as approved, no entry is committed, the request is flagged
for legal review, the legal adviser is told, the refusal is audited, and the
caller is given the article it was refused under (NFR-02).

The check runs **before** anything is written. An approval that has to be taken
back is not the same thing as one that never happened.

There is deliberately **no override**. A policy cap can be escalated past by
the role the policy names; a legal cap cannot be lifted by any internal
approval (NFR-16), so an "approve anyway" path would be a lie about what the
system enforces.

### 3. Rejection and revision release what was never committed

On rejection the entries become `REJECTED` — kept rather than deleted, so the
ledger shows what was asked for and refused. On a revision request they are
also rejected, and written again by the same ids when the revised request
re-enters approval. Same ids, replaced: two sets would double-count one change.

Only *pending* entries ever move. An approved entry is part of the contract's
history and is not rewritten by a later decision.

### 4. Private contracts write the same entries

The ledger is one record of every change to every contract. What is restricted
to government contracts is the **evaluation** of Article 67, not the
**recording** of the change. Applying Article 67 to a private contract would be
inventing law; refusing to write down what happened to a private contract would
be keeping two sets of books.

### 5. The two limit layers report the same approved totals

The policy cap works on the net cost impact of approved requests; Article 67
works on gross movements per category. Different views, same facts: net equals
`NEW_ITEMS + INCREASE_EXISTING − DECREASE_EXISTING`, and a test asserts it over
a PCR, an NCR, a substitution and a government request.

`pending_totals` was narrowed to `IN_APPROVAL` so the two layers also agree on
what is in flight. Previously it counted `RECOMMENDED` as well, which no ledger
entry corresponds to — one record should not have two meanings of "pending".

## Consequences

- `ChangeRequest` now persists `added_value` and `removed_value` alongside
  `cost_impact`. A net figure cannot be split back into the addition and the
  removal that produced it, and the entries are written long after stage 5 ran.
  Both columns are nullable; a request analysed before the migration has to be
  re-analysed to gain them.
- A final approval can now fail with `409 LEGAL_CAP_EXCEEDED`, carrying an
  `articles` list. Any client that assumed the last approval always succeeds
  needs to handle it.
- `commit_ledger_entries` is deleted. It was the dead stub this replaces.
- Starting approval on a request that has no priced halves is refused with
  `409 NOT_PRICED`, telling the operator to re-analyse. Only a request analysed
  before the migration can be in that state; `ChangeOrder` already refuses a
  financial entry worth nothing, so this turns a validation error deep in the
  pipeline into a message that says what to do.
- The cost is one extra ledger read per final approval. Against the alternative
  — a contract quietly taken past a statutory cap — that is not a trade worth
  discussing.

## Revisit if

- Requests are ever approved concurrently against one contract. The re-check
  reads the ledger and then writes, so two final approvals racing could each
  see the other's entry as still pending. A transaction or a row lock over the
  contract would close that; it is not closed today, and the demo is
  single-user.
