# platform-config

The **ArgoCD GitOps control-plane layer** for the `jaybeedevx` production platform. This repo tells ArgoCD *what* to deploy and *where* its charts live. It is **not** the Terraform infrastructure and **not** the app source — see the four-layer model below.

## The 4-layer production model

1. **`platform-infrastructure`** (separate repo, `~/platform-infrastructure`) — Terraform EKS/VPC/IAM; installs platform add-ons (ArgoCD, ingress-nginx, cert-manager, prometheus-operator, external-secrets). App manifests never go here.
2. **`platform-config`** *(this repo)* — the ArgoCD app-of-apps: `bootstrap/root-app.yaml` (recurses `apps/`) + one `Application` per app under `apps/`. Charts live under `charts/`.
3. **Per-app repos** — in a full production split each app owns its source + Helm chart + CI. The current `webapp` lives here for now but is structured to split out cleanly.
4. **Image registry** — ECR/GAR; CI builds images, ArgoCD pulls them at sync.

### Critical constraint

`bootstrap/root-app.yaml` recurses `apps/` with `directory.recurse: true` and applies every YAML there raw. Therefore **Helm chart templates must never live under `apps/`** — only `Application` manifests go there. Charts live under `charts/<name>/`.

## Layout

```
bootstrap/   root Application (recurses apps/)
apps/        one ArgoCD Application per app
charts/      Helm charts referenced by apps/
src/         app source (backend + frontend for webapp)
```

---

## webapp

A full-stack web application — **FastAPI backend** + **React (Vite) frontend served by Nginx** — packaged as a Helm chart and deployed to EKS through ArgoCD. Namespace: `webapp`.

- **ArgoCD Application:** `apps/webapp.yaml` → Helm chart `charts/webapp/` (uses `values-prod.yaml`).
- **Chart:** renders backend + frontend Deployments/Services/HPAs/PDBs, Ingress+TLS, NetworkPolicy, RBAC, ConfigMap+Secret, ServiceMonitor. All values-driven.
- **Source:** `src/backend/` (FastAPI: `/api`, `/healthz`, `/readyz`, `/metrics`; pytest tests) and `src/frontend/` (Vite React; `nginx.conf` proxies `/api` → `webapp-backend:8000`).
- **Four production-grade buckets:** (1) core hardening — resources, probes, rolling-update, securityContext, affinity/tolerations/nodeSelector; (2) scalability & security — HPA, PDB, NetworkPolicy, least-privilege RBAC; (3) ingress + TLS + config — cert-manager issuer, ConfigMap + Secret; (4) observability — ServiceMonitor + bundled Grafana dashboard (`charts/webapp/dashboards/webapp.json`).

### Split-out path

The source (`src/`), chart (`charts/webapp/`), and workflow (`.github/workflows/webapp.yml`) are structured so that moving `webapp` into its own `platform-webapp` repo requires only changing the chart's `repoURL` and the image tags in `values.yaml` — no structural rework.

### References

- Design spec: `docs/superpowers/specs/2026-08-06-webapp-design.md`
