# Deployment and operations

## Local stack

`docker compose up --build` runs PostgreSQL, the FastAPI service, and the Next.js web app. The API applies Alembic migrations and seeds demo accounts only when `SEED_DEMO_DATA=true`; Compose sets this for local development. The API and web containers expose health checks.

## Production container settings

Build the API with `docker build -t medisphere-api:VERSION ./apps/api` and the web app with `docker build -f apps/web.Dockerfile -t medisphere-web:VERSION .`. GitHub Actions publishes both images to GHCR on a `v*` tag, after API, web, browser, and performance checks pass. Set package visibility and cluster pull credentials as needed; deploy an immutable release tag to the cluster.

Set these values in a secret manager and expose them to the API as a Kubernetes Secret named `medisphere-api-secrets`:

- `DATABASE_URL`: PostgreSQL connection string using the `postgresql+psycopg` SQLAlchemy driver.
- `JWT_SECRET`: a unique random value of at least 32 characters.
- `JWT_ISSUER`: an environment-specific issuer.
- `CORS_ORIGINS`: explicit public origin(s), without `*`.
- `WEB_BASE_URL`: the public HTTPS URL used in password recovery links.
- `SMTP_HOST`, `SMTP_PORT`, and `SMTP_SENDER`: an email relay for password recovery. Set `SMTP_USERNAME` and `SMTP_PASSWORD` when the relay requires authentication; `SMTP_STARTTLS` defaults to `true`.

Production startup checks require a strong JWT secret, secure cookies, explicit CORS origins, PostgreSQL, and SMTP settings for account recovery. Demo seeding is disabled by default. Back up the database before schema changes. For a first administrator, run the one-time `app.provision_admin` command using the separate bootstrap job and temporary secret described below; it creates one administrator and never seeds demo accounts.

## Kubernetes manifests

The manifests expect a Kubernetes cluster with an ingress controller, TLS secret `medisphere-tls`, a metrics server for autoscaling, and a managed PostgreSQL database. Update the two image references and public hostname in `deploy/kubernetes/medisphere.yaml`. Create the API secret through the cluster's secret manager integration; do not commit real secret values.

Create the namespace and API secret, then migrate the database before starting application replicas:

```sh
kubectl create namespace medisphere
kubectl create secret generic medisphere-api-secrets -n medisphere --from-env-file=/secure/path/medisphere-api.env
kubectl apply -f deploy/kubernetes/migration-job.yaml
kubectl wait -n medisphere --for=condition=complete job/medisphere-db-migrate --timeout=5m
kubectl create secret generic medisphere-bootstrap-secrets -n medisphere --from-env-file=/secure/path/medisphere-bootstrap.env
kubectl apply -f deploy/kubernetes/admin-provision-job.yaml
kubectl wait -n medisphere --for=condition=complete job/medisphere-admin-provision --timeout=5m
kubectl delete secret medisphere-bootstrap-secrets -n medisphere
kubectl apply -f deploy/kubernetes/medisphere.yaml
kubectl rollout status -n medisphere deployment/api
kubectl rollout status -n medisphere deployment/web
```

Prepare the API environment file through your secret manager; it must define `DATABASE_URL`, `JWT_SECRET`, `JWT_ISSUER`, and `CORS_ORIGINS`. Prepare a separate, temporary bootstrap environment file with `DATABASE_URL`, `SEED_ADMIN_EMAIL`, and a unique `SEED_ADMIN_PASSWORD` of at least 16 characters. Replace `YOUR_ORG`, `VERSION`, and the example hostname in all manifests before applying. The API serves Prometheus metrics at `/metrics`; scrape it only on the internal cluster network. Example scrape and alert rules are in `observability/`.

Self-signup creates a new organization and assigns one of the offered roles within that organization; it does not join an existing organization. Configure the SMTP values above to deliver password reset links. In local development only, the forgot-password screen displays the reset link directly.

## Terraform

`deploy/terraform` manages the namespace, API and web Deployments and Services, TLS ingress, and CPU-based autoscalers on an existing cluster. It does not create a cloud account, Kubernetes cluster, PostgreSQL instance, ingress controller, certificate, or secret. Provision those first. Apply the namespace Terraform target, create the API secret, and run the migration and one-time administrator Jobs above before applying the remaining Terraform resources:

```sh
cd deploy/terraform
terraform init
terraform apply -target=kubernetes_namespace_v1.app -var='kubeconfig_path=/path/to/kubeconfig' \
  -var='api_image=registry.example.com/medisphere-api:VERSION' \
  -var='web_image=registry.example.com/medisphere-web:VERSION' \
  -var='ingress_host=medisphere.example.com'
terraform plan -var='kubeconfig_path=/path/to/kubeconfig' \
  -var='api_image=registry.example.com/medisphere-api:VERSION' \
  -var='web_image=registry.example.com/medisphere-web:VERSION' \
  -var='ingress_host=medisphere.example.com'
terraform apply
```

## Telemetry

The API exposes database liveness/readiness at `/api/v1/health/live` and `/api/v1/health/ready`, Prometheus request totals and latency histograms at `/metrics`, and JSON request logs with generated request IDs. Metrics use route templates and do not include request bodies, cookies, or patient records. Connect Prometheus alert notifications to the operator's incident system; the sample rules cover server error rate and p95 latency.
