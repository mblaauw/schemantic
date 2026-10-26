# Deployment (fictional)

Two environments: test and production, each in its own cloud account.
Production has one Kubernetes cluster with three namespaces: `shop` (web, api), `jobs` (importer, reporter) and
`ops` (monitoring agent). Test mirrors production with one cluster and the same namespaces.
Outside the clusters, in each account: a managed PostgreSQL database and an object storage bucket.
Shared between environments: the container registry and the CI system, in a separate tooling account.
