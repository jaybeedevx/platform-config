# CLAUDE.md

Guidance for Claude Code working in this repo.

## What this repo is

`platform-config` is the **ArgoCD GitOps control-plane layer** for a production platform (`jaybeedevx`). It tells ArgoCD *what* to deploy and *where* its charts live — it is not the Terraform infrastructure and it is not the app source.

### The 4-layer production model (do not blur these)

1. **`platform-infrastructure`** (separate repo, `~/platform-infrastructure`) — Terraform EKS/VPC/IAM, installs platform add-ons (ArgoCD, ingress-nginx, cert-manager, prometheus-operator, external-secrets). Do NOT put app manifests here.
2. **`platform-config`** *(this repo)* — the ArgoCD app-of-apps: one `Application` per app under `apps/`, root app under `bootstrap/`. Charts are hosted here for the current webapp.
3. **Per-app repos** — in a full production split, each app owns its source + Helm chart + CI. The current `webapp` lives here for now but is structured to be split out cleanly.
4. **Image registry** — ECR/GAR; CI builds images, ArgoCD pulls at sync.

## How ArgoCD is wired here

- `bootstrap/root-app.yaml` — the root `Application`, `directory.recurse: true`, watches the `apps/` directory. Do not delete this.
- Per-app `Application` manifests go flat under `apps/` (e.g. `apps/webapp.yaml`, `apps/test-nginx.yaml`).
- Standard Application shape: `argoproj.io/v1alpha1`, `namespace: argocd`, `project: default`, `destination.server: https://kubernetes.default.svc`, automated sync (`prune: true`, `selfHeal: true`), `syncOptions: CreateNamespace=true`.

### CRITICAL constraint
Because the root app recurses `apps/` and applies every YAML there as a raw manifest, **Helm chart template files must never be placed under `apps/`** — the root app would apply them raw *and* the rendered chart would apply them again. Charts live under `charts/<name>/`. Only `Application` manifests go under `apps/`.

## Current application: `webapp`

- **Stack:** FastAPI backend (`src/backend/`) + React/Vite frontend served by Nginx (`src/frontend/`). Namespace: `webapp`.
- **ArgoCD Application:** `apps/webapp.yaml` → Helm chart at `charts/webapp/` (uses `values-prod.yaml`).
- **Chart:** `charts/webapp/` renders backend + frontend Deployments/Services/HPAs/PDBs, Ingress+TLS, NetworkPolicy, RBAC, ConfigMap+Secret, ServiceMonitor. All values-driven.
- **Source:** `src/backend/` (FastAPI, `/api`, `/healthz`, `/readyz`, `/metrics`; pytest tests), `src/frontend/` (Vite React; `nginx.conf` proxies `/api` → `webapp-backend:8000`).
- **Naming convention (deliberate):** resources are `webapp-backend` / `webapp-frontend` etc. (no release-name prefix), matching the nginx proxy target and the manifests. `webapp.fullname` == `webapp.name` by design; two releases of this chart cannot share a cluster.
- **Design/spec:** `docs/superpowers/specs/2026-08-06-webapp-design.md`. **Plan:** `docs/superpowers/plans/2026-08-06-webapp.md`.

## Conventions & environment notes

- Working branch for the webapp work: `feat/webapp`.
- `helm` is available at `/tmp/linux-amd64/helm` (not on PATH) if you need to lint/render: `helm lint charts/webapp` and `helm template webapp charts/webapp --namespace webapp`.
- `python3` is available; backend tests need a venv (`src/backend/.venv`) with `pip install -r requirements.txt`, then `python -m pytest tests/ -q`.
- `node`/`npm` are available; frontend builds with `cd src/frontend && npm install && npm run build`.
- **Docker is NOT available in this sandbox** — images can't be built/run here; image tags in `charts/webapp/values.yaml` are placeholders to swap for a real registry.
- Each app has a scoped `.gitignore` (e.g. `src/backend/.gitignore` excludes the venv). There is no repo-root `.gitignore` — keep generated/venv/`dist`/`node_modules`/`.pytest_cache` out of git via scoped ignores.
- The `.superpowers/` directory is git-ignored scratch (SDD workspace, plans, review packages) — safe to delete; the git history is the source of truth.

## Design docs

Specs live in `docs/superpowers/specs/`, implementation plans in `docs/superpowers/plans/`. Follow the superpowers brainstorming → writing-plans → execution flow for new features.
