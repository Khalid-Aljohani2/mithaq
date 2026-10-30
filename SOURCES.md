# SOURCES.md

Every dependency installed in this repo, the exact pinned version, where that
version was verified, and the official documentation used for its setup.

Versions checked **2026-10-30** against the live npm registry (`npm view <pkg> version`)
and PyPI (`https://pypi.org/pypi/<pkg>/json`). No version here came from memory.

## Frontend — `frontend/package.json` (all exact pins, no ranges)

### Runtime dependencies

| Package | Version | Verified at | Official doc used |
| --- | --- | --- | --- |
| `next` | 16.4.3 | npm registry | https://nextjs.org/docs/app/getting-started/installation |
| `react` | 19.3.1 | npm registry | https://nextjs.org/docs/app/getting-started/installation |
| `react-dom` | 19.3.1 | npm registry | https://nextjs.org/docs/app/getting-started/installation |
| `motion` | 14.8.0 | npm registry | https://motion.dev/docs/react-quick-start |
| `radix-ui` | 1.8.1 | npm registry (installed by `shadcn init`) | https://ui.shadcn.com/docs/installation/next |
| `class-variance-authority` | 0.7.1 | npm registry (installed by `shadcn init`) | https://ui.shadcn.com/docs/installation/next |
| `cn` | 0.5.1 | npm registry (installed by `shadcn init`) | https://github.com/shadcn-ui/cn |
| `lucide-react` | 1.65.0 | npm registry (installed by `shadcn init`) | https://ui.shadcn.com/docs/installation/next |
| `tw-animate-css` | 1.4.0 | npm registry (installed by `shadcn init`) | https://ui.shadcn.com/docs/installation/next |

### Dev dependencies

| Package | Version | Verified at | Official doc used |
| --- | --- | --- | --- |
| `typescript` | 5.9.3 | npm registry | https://nextjs.org/docs/app/getting-started/installation |
| `tailwindcss` | 4.3.3 | npm registry | https://nextjs.org/docs/app/api-reference/cli/create-next-app |
| `@tailwindcss/turbopack` | 4.3.3 | npm registry | https://nextjs.org/docs/app/api-reference/cli/create-next-app |
| `eslint` | 10.13.0 | npm registry | https://nextjs.org/docs/app/getting-started/installation |
| `eslint-config-next` | 16.4.3 | npm registry | https://nextjs.org/docs/app/api-reference/config/eslint |
| `@types/node` | 22.20.5 | npm registry | https://nextjs.org/docs/app/getting-started/installation |
| `@types/react` | 19.3.0 | npm registry | https://nextjs.org/docs/app/getting-started/installation |
| `@types/react-dom` | 19.3.0 | npm registry | https://nextjs.org/docs/app/getting-started/installation |
| `shadcn` (CLI) | 4.23.0 | npm registry | https://ui.shadcn.com/docs/cli |

### Version choices that are not simply "npm latest"

| Package | npm `latest` | Pinned | Why |
| --- | --- | --- | --- |
| `@types/node` | 26.6.6 | **22.20.5** | `@types/node` majors track the Node runtime. This machine runs Node 22.14.0, so the 22.x line is the correct match; 26.x would type against APIs this runtime doesn't have. 22.20.5 is the current latest of the 22.x line per the npm registry. |
| `typescript` | 7.0.2 | **5.9.3** | `create-next-app` installs the `^5` line. TS 7 is the native rewrite and is not what Next.js 16.4.3 ships against. Left on the version the official scaffold chose. |
| `@types/react` / `@types/react-dom` | 19.3.0 | 19.3.0 | Matches installed React 19.3.1 major. |

## Backend — `backend/requirements.txt` / `requirements-dev.txt`

### Runtime

| Package | Version | Verified at | Official doc used |
| --- | --- | --- | --- |
| `fastapi` | 0.162.0 | PyPI | https://fastapi.tiangolo.com/tutorial/cors/ |
| `uvicorn[standard]` | 0.54.0 | PyPI | https://www.uvicorn.org/ |
| `pydantic` | 2.14.2 | PyPI | https://pydantic.dev/docs/validation/latest/concepts/models/ |
| `pydantic-settings` | 2.16.2 | PyPI | https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/ |
| `python-dotenv` | 1.2.4 | PyPI | https://saurabh-kumar.com/python-dotenv/ |
| `httpx` | 0.28.1 | PyPI | https://www.python-httpx.org/ |
| `pyyaml` | 6.0.3 | PyPI | https://pyyaml.org/wiki/PyYAMLDocumentation |

### Dev

| Package | Version | Verified at | Official doc used |
| --- | --- | --- | --- |
| `ruff` | 0.17.3 | PyPI | https://docs.astral.sh/ruff/configuration/ |
| `pytest` | 9.2.0 | PyPI | https://fastapi.tiangolo.com/tutorial/testing/ |
| `pytest-cov` | 7.1.0 | PyPI | https://pytest-cov.readthedocs.io/en/latest/config.html |

Transitive packages pinned by pip resolution (not declared directly):
`starlette 1.10.0`, `pydantic-core 2.50.2`, `anyio 4.15.1`, `h11 0.16.0`,
`httpcore 1.0.9`, `httptools 0.9.0`, `websockets 17.3`, `watchfiles 1.3.0`,
`click 8.5.0`, `pyyaml 6.0.3`, `certifi 2026.10.23`, `idna 3.20`,
`typing-extensions 4.16.0`, `annotated-types 0.8.0`, `annotated-doc 0.0.5`,
`typing-inspection 0.4.4`, `opentelemetry-api 1.45.2`, `coverage 7.17.0`.

## Setup commands and where each flag came from

| Command | Source |
| --- | --- |
| `npx create-next-app@latest frontend --ts --eslint --tailwind --app --src-dir --use-npm --no-react-compiler --no-cache-components --no-agents-md --no-agent-feedback --disable-git` | Flag table at https://nextjs.org/docs/app/api-reference/cli/create-next-app |
| `npx shadcn@latest init -y -b radix -p nova` | https://ui.shadcn.com/docs/cli |
| `npx shadcn@latest add button card input textarea badge -y` | https://ui.shadcn.com/docs/cli |
| `npm install --save-exact motion@14.8.0` | https://motion.dev/docs/react-quick-start — the package is `motion`; `framer-motion` is the old name |
| `python -m venv backend\.venv` + `.\.venv\Scripts\Activate.ps1` | https://docs.python.org/3/library/venv.html |
| `uvicorn app.main:app --reload --port 8000` | https://fastapi.tiangolo.com/tutorial/first-steps/ |
| `ruff check .` / `ruff format --check .` | https://docs.astral.sh/ruff/configuration/ |
| CORS middleware setup in `app/main.py` | https://fastapi.tiangolo.com/tutorial/cors/ |
| `Settings(BaseSettings)` + `SettingsConfigDict(env_file=...)` in `app/config.py` | https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/ |
| `TestClient` usage in `tests/test_health.py` | https://fastapi.tiangolo.com/tutorial/testing/ |

## Legal source: the regulation file

`backend/app/regulations/gtpl_2026.yaml` is **generated, never hand-written**.

| Field | Value |
| --- | --- |
| Law | نظام المنافسات والمشتريات الحكومية (Government Tenders and Procurement Law) |
| Official page | https://www.uqn.gov.sa/decisions-and-regulations/4001762 |
| Publisher | جريدة أم القرى (Umm Al-Qura) |
| Published | 1448-03-22 H / 2026-09-04 G |
| Effective | 120 days after publication (Article 101) |
| Replaces | the law issued by Royal Decree M/128 of 1440/11/13 H (Article 100) |
| Retrieved | 2026-10-30, HTTP GET, 45,607 Arabic characters of body text |

Articles stored verbatim: **52(2)**, **67 (entire)**, **72(1)**, **59(2)(z)**,
plus **100** and **101** for the replacement and effective-date rules.

How verbatim fidelity is guaranteed: the page was fetched once, stripped to
text, and each article was sliced out programmatically. Every stored string is
asserted with `assert text in page_text` both when generated and again after
being read back from the YAML. No Arabic legal text was retyped by hand, and
none was written from memory.

Percentages are stored as YAML **strings** and parsed with `Decimal(str)`, so no
binary float ever touches a legal limit (NFR-01). They appear nowhere in Python.

## Supply-chain verification: the `cn` package (checked 2026-10-30)

`shadcn init` pulls in a package literally named `cn`. A two-letter name on npm
with a 2013 creation date is exactly the shape of a hijacked package, so it was
audited before being kept.

| Check | Result |
| --- | --- |
| npm maintainer | `shadcn <m@shadcn.com>` — the shadcn/ui maintainer |
| Repository | `git+https://github.com/shadcn-ui/cn.git` — the official `shadcn-ui` GitHub org |
| Publisher | GitHub Actions via npm trusted publishing (`npm-oidc-no-reply@github.com`) |
| Provenance | SLSA v1 attestation present (`https://registry.npmjs.org/-/npm/v1/attestations/cn@0.5.1`) |
| Runtime dependencies | none |
| `0.5.1` published | 2026-10-30T05:48:54Z |

Confirmed that the `nova` preset genuinely references it, straight from the
official registry rather than from the CLI binary:

- `https://ui.shadcn.com/r/styles/radix-nova/index.json` → `"dependencies": ["class-variance-authority", "cn", "lucide-react", "radix-ui"]`
- `https://ui.shadcn.com/r/styles/radix-nova/utils.json` → `"dependencies": ["cn"]` and file content `export { cn } from "cn"`

Per the project README, `cn` "replaces tailwind-merge and clsx. Same APIs. Full
parity." It is kept. `clsx` + `tailwind-merge` are **not** installed; the manual
shadcn install path (https://ui.shadcn.com/docs/installation/manual) would use
those two instead, and remains the fallback if `cn` is ever dropped.

The same registry response lists `shadcn` under `devDependencies`, which
confirms moving the CLI out of runtime `dependencies` matches upstream intent.

## Could not verify from an official source

- **`[tool.ruff] src`** — accepted by `ruff 0.17.3` (it errors on unknown keys),
  but not shown on the configuration page fetched above.
