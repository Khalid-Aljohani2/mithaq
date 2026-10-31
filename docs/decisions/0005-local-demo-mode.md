# 0005 — Local demo mode: a token-free reset for loopback clients

Status: accepted
Date: 2026-10-31
Requirements: FR-15, NFR-08

## Context

`POST /api/demo/reset` is guarded by `DEMO_RESET_TOKEN` (404 when unset, 403
when wrong). A reset button in the UI would have to send that token from the
browser, which puts a secret in client code and in every network tab. The
token must never be needed by, or sent to, the browser.

## Decision

A new setting, `DEMO_MODE` (default `false`), adds one narrow exemption:

- When `DEMO_MODE=true` **and** the request's direct client address is
  loopback (`127.0.0.1`, `::1` or `localhost`), the reset runs without a token,
  with or without `?preset=`.
- In every other case the token rules apply exactly as before, including the
  404 when no token is configured.
- `GET /api/demo/status` returns `{"demo_mode": bool}` so the UI can decide
  whether to show the reset button. It is always available and says nothing
  about whether a token is configured.

## Caveat: the client address and proxy headers

The check reads `request.client.host`, the address the ASGI server reports,
not a header. Uvicorn rewrites that address from `X-Forwarded-For` when proxy
headers are enabled (`--proxy-headers`, on by default) and the TCP peer is in
`forwarded_allow_ips` (default `127.0.0.1`). Two consequences:

1. A remote caller cannot spoof loopback by sending `X-Forwarded-For` directly,
   because its own peer address is not trusted.
2. Behind a reverse proxy on the same machine, every request reaches uvicorn
   from loopback. If that proxy does not set `X-Forwarded-For`, or if
   `forwarded_allow_ips` is widened to `*`, remote callers can look local.

So demo mode is for a developer laptop only. It must stay off on any deployed
instance (Vercel included), where the token remains the only way to reset.

## Consequences

- A local demo can offer a reset button with no secret in the frontend.
- Deployments are unchanged: `DEMO_MODE` defaults to off, and `.env.example`
  ships it as `false`.
- Tests (`tests/test_demo_mode.py`) pin both sides of the guard.
