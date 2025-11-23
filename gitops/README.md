# GitOps Deployment

This directory contains GitOps configuration for automated deployments using ArgoCD or Flux.

## Overview

GitOps is a methodology that uses Git as the single source of truth for infrastructure and application deployments. Changes to the Git repository automatically trigger deployments.

## Prerequisites

- Kubernetes cluster
- ArgoCD or Flux installed
- Git repository access
- kubectl configured

## ArgoCD Setup

### Install ArgoCD

```bash
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
```

### Create Application

```bash
kubectl apply -f gitops/argocd-application.yaml
```

### Access ArgoCD UI

```bash
kubectl port-forward svc/argocd-server -n argocd 8080:443
```

Access at: https://localhost:8080
Default username: admin
Password: Get with `kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d`

## Flux Setup

### Install Flux

```bash
flux install
```

### Create GitRepository

```bash
flux create source git social-media-scraper \
  --url=https://github.com/your-org/social-media-scraper \
  --branch=main \
  --interval=1m
```

### Create Kustomization

```bash
flux create kustomization social-media-scraper \
  --source=social-media-scraper \
  --path="./k8s" \
  --prune=true \
  --interval=5m
```

## Workflow

1. **Make Changes**: Update Kubernetes manifests or Helm values
2. **Commit**: Commit changes to Git repository
3. **Push**: Push to main branch
4. **Sync**: ArgoCD/Flux detects changes and syncs
5. **Deploy**: Application is automatically deployed

## Directory Structure

```
gitops/
├── argocd-application.yaml    # ArgoCD application definition
├── flux-gitrepository.yaml    # Flux GitRepository
├── flux-kustomization.yaml    # Flux Kustomization
└── README.md                  # This file
```

## Best Practices

1. **Separate Environments**: Use different branches or paths for dev/staging/prod
2. **Automated Testing**: Run tests before merging to main
3. **Approval Workflows**: Require approvals for production deployments
4. **Monitoring**: Monitor sync status and application health
5. **Rollback**: Use Git revert for rollbacks

