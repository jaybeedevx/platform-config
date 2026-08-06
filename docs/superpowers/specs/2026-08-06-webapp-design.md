# webapp — Full-Stack Application Deployed via ArgoCD

**Date:** 2026-08-06
**Status:** Approved design (ready for implementation plan)

## Purpose

Build a production-grade full-stack web application — a Python (FastAPI) backend and a React (Vite) frontend — packaged as a Helm chart and deployed to EKS through ArgoCD, using this `platform-config` repo as the GitOps app-of-apps control plane.

## Repo & Layering Model

This repo (`platform-config`) is the **ArgoCD control-plane layer** in a four-layer production setup:

1. **`platform-infrastructure`** (separate repo) — Terraform provisions the EKS cluster, VPC, IAM, and installs platform add-ons (ArgoCD, ingress-nginx, cert-manager, prometheus-operator, external-secrets). Not touched by this task.
2. **`platform-config`** *(this repo)* — the app-of-apps: `bootstrap/root-app.yaml` + one `Application` per app under `apps/`. It owns the chart for the simulation.
3. **Per-app repos** — in a full split, `webapp` would live in its own repo (source + chart + CI). For this simulation the source, chart, and Application are all hosted here so it is self-contained and portable.
4. **Image registry** — ECR/GAR; CI builds images and ArgoCD pulls them at sync.

**Portability rule:** Dockerfiles, the Helm chart, and the CI workflow are written so that splitting `webapp` into its own repo later only requires changing the chart's `repoURL` and the image tag — no structural rework.

## Structure

```
platform-config/
├─ apps/
│  ├─ test-nginx.yaml   (existing, untouched)
│  └─ webapp.yaml       (NEW: ArgoCD Application → points at charts/webapp)
├─ charts/
│  └─ webapp/
│     ├─ Chart.yaml
│     ├─ values.yaml
│     ├─ values-prod.yaml     (prod override: replicas, resources, host, TLS)
│     └─ templates/
│        ├─ _helpers.tpl
│        ├─ backend/          (Deployment, Service, HPA, PDB)
│        ├─ frontend/         (Deployment, Service, HPA, PDB)
│        ├─ ingress.yaml
│        ├─ networkpolicy.yaml
│        ├─ rbac.yaml         (ServiceAccount + Role + RoleBinding)
│        ├─ configmap.yaml
│        ├─ secret.yaml
│        └─ servicemonitor.yaml
└─ src/
   ├─ backend/   (FastAPI + Dockerfile + tests)
   └─ frontend/  (React/Vite + Dockerfile)
```

**Key structural constraint:** the existing root app uses `directory.recurse: true` on `apps/`. Helm templates must therefore live under `charts/` (outside `apps/`) so the root app does not try to apply raw chart templates directly. The `Application` manifest (`apps/webapp.yaml`) is the only ArgoCD resource in `apps/`.

## Components

### Namespace
`webapp`, created via `syncOptions: CreateNamespace=true` on the Application.

### Backend — FastAPI
- REST API under `/api`, liveness probe `/healthz`, readiness probe `/readyz`, Prometheus metrics at `/metrics`.
- Config from a ConfigMap (mounted) + env; credentials from a Secret.
- Runs as non-root with `readOnlyRootFilesystem`.

### Frontend — React (Vite)
- Static SPA built into an Nginx image; proxies `/api` → backend Service.
- Health via Nginx location block (`/healthz`) and a static readiness check.

## Production-Grade Requirements (all four buckets)

### 1. Core hardening
- Resource `requests`/`limits` on every container.
- Liveness, readiness, and startup probes on backend; liveness + readiness on frontend.
- `RollingUpdate` strategy with explicit `maxUnavailable`/`maxSurge`.
- `securityContext`: non-root user, `readOnlyRootFilesystem`, dropped capabilities, `allowPrivilegeEscalation: false`.
- Affinity (preferred anti-affinity between replicas), tolerations, and `nodeSelector`.
- `imagePullPolicy: IfNotPresent`.

### 2. Scalability & security
- `HorizontalPodAutoscaler` per workload (backend + frontend) targeting CPU + memory, with min/max replicas from values.
- `PodDisruptionBudget` `minAvailable` per workload.
- `NetworkPolicy`: backend reachable only from the frontend and ingress; egress restricted (DNS + cluster API only). Frontend reachable only from ingress.
- Least-privilege `ServiceAccount` + `Role`/`RoleBinding` scoped to the namespace.

### 3. Ingress + TLS + config
- `Ingress` with TLS (host + secret from values), cert-manager `cert-manager.io/cluster-issuer` annotation.
- Application config via `ConfigMap` + env; secrets via `Secret` (base64 placeholder for the simulation; the README notes External-Secrets as the production path).

### 4. Observability
- `ServiceMonitor` scraping the backend `/metrics` (Prometheus operator).
- A ready-to-import **Grafana dashboard** JSON shipped as a bundled artifact (no CRD dependency on grafana-operator; importable into any Grafana).

## Values / Configuration Surface
`values.yaml` exposes: image repo/tag per workload, replica counts, resources, HPA min/max + targets, probes tuning, affinity, ingress host + TLS secret + clusterIssuer, namespace, and config content. `values-prod.yaml` overrides for the production profile.

## App Source
- **Backend:** FastAPI app with `/api`, health endpoints, `/metrics` (via prometheus-fastapi-instrumentator or similar), config handling, and a small test suite (pytest). Multi-stage Dockerfile (python slim runtime).
- **Frontend:** Vite + React app with a build step, Nginx config (SPA fallback + `/api` proxy), multi-stage Dockerfile (node build → nginx runtime).
- **CI:** a GitHub Actions workflow per repo that builds, tests, and (optionally) pushes images; included to demonstrate the split-out path. Image tags in `values.yaml` are placeholders to swap for the registry.

## Error Handling / Behavior
- Probes drive rollout/restart behavior; readiness gates traffic behind the Service.
- PDB prevents disruptive updates under HPA-managed replica counts.
- NetworkPolicy isolates blast radius; RBAC bounds the ServiceAccount.
- Chart uses standard Helm helpers (`_helpers.tpl`) for consistent naming/labels.

## Testing
- **Chart:** `helm template` renders cleanly; `helm lint` passes; values validations where applicable.
- **Backend:** pytest unit tests for API + health endpoints.
- **Frontend:** build succeeds; Nginx config validated.
- **End-to-end (documented, not required to run):** `argocd app sync` against a live cluster.

## Out of Scope (noted for the real split)
- Live EKS cluster provisioning (in `platform-infrastructure`).
- Image registry + push pipeline execution.
- External-secrets integration (documented as the production path).
- Multi-environment promotion (dev/staging/prod) — single-profile chart now; `values-prod.yaml` scaffolds it.
