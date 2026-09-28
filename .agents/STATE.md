# STATE

## 2026-09-16 - baseline review batch-a
- Repo scope: prawn-family template repo. Provides scaffolding (AGENTS.md, .agents/STATE.template.md, README.md, SECURITY.md, dependabot/labeler workflows) for new hongyime repos.
- Health: main HEAD 76b3770 after fast-forward pull. Working tree had unrelated pre-existing local edits (.env.example, README.md, telemetry/{posthog,sentry}.js, .github/workflows/deploy.yml for Cloudflare Pages) — stashed as `pre-baseline-review-20260916-preserved-local-edits` for the owner to decide. NOT committed by this session.
- Open PRs: #3 (Dependabot: setup-python 6->7), #5 (Dependabot: labeler 6->7). Open issues: 0.
- Recent merged: #9 (Bun install fix for template builds).
- Free-tier surface: none (template only). No deploy.
- Next safe steps: owner review of stashed local edits (would add PostHog/Sentry/Cloudflare Pages workflow — evaluate before promoting; potential paid-service exposure violates $0 constraint if telemetry backends are paid).

## Privacy maintenance - 2026-09-27

Remove the optional personal security contact while retaining private vulnerability-reporting guidance. The narrow documentation patch is prepared from the current default branch; staged whitespace and the inherited identity hook are publication checks. Application behavior is unchanged.

## Repository standards manifest - 2026-09-27

Seed STANDARDS.md (authoritative fleet standards manifest) so new repos created from this template inherit it, plus opt-in GHCR packaging scaffolding under .github/optional/ (docker-publish.yml + ghcr-retention.cjs + README) for repos that publish containers. STANDARDS.md is also maintained in sourcerepo and propagated fleet-wide via the sync allowlist. Derived from a live 79-repo compliance audit.
