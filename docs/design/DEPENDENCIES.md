# Frontend dependencies added in Step 5A

Recorded here because this step is limited to `frontend/` and `docs/design/`;
copy these rows into `SOURCES.md` when the branch is merged.

Versions checked 2026-10-30 with `npm view <pkg> version` against the live npm
registry. Exact pins, dev dependencies only.

| Package | Version | Why | Official doc used |
| --- | --- | --- | --- |
| `openapi-typescript` | 7.13.0 | Generates `src/lib/api-types.ts` from the backend OpenAPI schema (`npm run gen:api`) | https://openapi-ts.dev/introduction |
| `@playwright/test` | 1.64.1 | Screenshot run for `docs/design/screens/` (`npm run screens`) | https://playwright.dev/docs/intro |

Chromium for Playwright is installed with `npx playwright install chromium`
(https://playwright.dev/docs/browsers).

## No data-fetching library

Polling and caching were considered. The only polling is the notification
count, every 30 seconds, done with `setInterval`. Every other view loads once
and reloads after an action, through a 40-line `useResource` hook
(`src/lib/use-resource.ts`). SWR or TanStack Query would add a runtime
dependency to solve cache invalidation and deduplication problems that one
user, two contracts and a handful of views do not have.
