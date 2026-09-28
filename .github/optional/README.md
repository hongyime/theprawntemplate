# Optional: GHCR container packaging

These are **opt-in** scaffolding files for repositories that build and publish
container images to GitHub Container Registry (GHCR). New repositories created
from `theprawntemplate` do **not** publish containers by default. Adopt this only
if your repository ships container images.

They are copied from a verified working container repository and represent the
standard packaging pattern described in [`STANDARDS.md`](../../STANDARDS.md)
section 5.

## Files

| File here | Copy to | Purpose |
| --- | --- | --- |
| `docker-publish.yml` | `.github/workflows/docker-publish.yml` | Builds and pushes image(s) to `ghcr.io/<owner>/<repo>/<component>` on push to `main` / manual dispatch. |
| `ghcr-retention.cjs` | `.github/scripts/ghcr-retention.cjs` | Prunes old GHCR package versions to control storage. |

## How to enable

1. Add one or more `Dockerfile`s to your repository for the component(s) you
   want to publish.
2. Copy the two files above into their target locations:
   - `.github/optional/docker-publish.yml` → `.github/workflows/docker-publish.yml`
   - `.github/optional/ghcr-retention.cjs` → `.github/scripts/ghcr-retention.cjs`
3. Edit `docker-publish.yml` to match your image name(s), build context(s), and
   Dockerfile path(s). The workflow needs `packages: write` permission (already
   declared in the file).
4. Commit through a reviewed pull request.

## Package visibility (important)

Publishing an image does **not** make it public. Package visibility is governed
by the organization's package-creation policy (Org Settings → Packages) and then
set per package. For privacy-sensitive images (photo, OSINT, or security
tooling), the image layers become world-pullable when public — make that a
deliberate, reviewed decision per package, not a default.

## Why opt-in rather than always-on

Most repositories in the fleet are non-container (static sites, libraries,
tooling). Shipping a container-publish workflow to every repository would create
noise and failing/irrelevant CI. Keeping this opt-in matches the actual fleet
shape: 7 container repositories out of 79.
