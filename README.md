# Project Name

Short description of what this project does and who it is for.

## Start Here

This repository was created from `hongyime/theprawntemplate`.

For project work:

1. Replace this README with the real project name and description.
2. Add setup instructions before asking someone else to run it.
3. Keep secrets out of git. Use environment variables and `.env.example`.
4. Open pull requests for review instead of committing directly to `main`.

For agents:

1. Read `AGENTS.md`.
2. If `.agents/STATE.md` exists, read it before changing files.
3. Do not write secrets or personal details into `.agents/`.

## What It Does

Describe the concrete workflow or product behavior here.

## Stack

List the runtime, framework, database, APIs, and deployment target.

## Setup

Add exact commands needed to install dependencies and run locally.

## Deploy

Add deployment instructions, or state clearly that this repo is not deployed.

> **Warning:** Cloudflare Workers are restricted to the Free Tier limit of 100,000 requests per day. Ensure `wrangler.toml` is configured to fail-open so static assets continue to serve if the limit is exceeded.

## Checks

Run the project checks before opening a pull request. Add the real commands once
the stack is chosen.

## License

Apache-2.0. See `LICENSE` and `NOTICE`.
