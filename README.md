# FastAPI Joke Service — DevOps Interview Task

A small Python/FastAPI service that should build, containerize, and operate like a production app. The service exposes
an authenticated API that fetches jokes from `https://official-joke-api.appspot.com/random_joke`, persists them, and
serves them to users.

Your job as the interviewee is to go through the app and outline any issues that
you see from DevOps perspective: reliability, security, observability, automation, and
deployability.

Imagine the app to serve the purpose of helping depressed people to cheer them up
whenever the need arises, so it should be up 24/7, reachable when needed.
If something makes it go down (faulty updates, db issues, internet outages),
you should think about processes to bring it back up as soon as possible.

### Functional requirements

- **Auth**
    - Implement JWT-based auth (e.g., `/auth/register`, `/auth/token`) or OAuth2 password flow.
    - Protect all business endpoints
- **Joke ingestion**
    - Endpoint to fetch jokes from the external API and **persist** them:
        - `POST /jokes/fetch?count=N` (N≥1): calls the external endpoint N times, persists unique jokes.
        - Handle duplicates by external joke `id` (if present) or content hash.
    - Endpoint(s) to read what’s stored:
        - `GET /jokes` — list with pagination & filtering (e.g., `type`, `setup` contains).
        - `GET /jokes/{id}` — retrieve one.
        - `DELETE /jokes/{id}` — remove one (authorized).

### Running locally

```Bash
docker build -t minimal-joke-api .
docker run --rm -p 8000:8000 minimal-joke-api
# Get a token
curl -s -X POST -d 'username=admin&password=admin' http://localhost:8000/auth/token
```

### Provision infrastructure

```Bash
cd terraform
cp terraform.tfvars.dev terraform.tfvars
# edit values (project_id, github_repo, etc.)
terraform init
terraform apply
# Copy outputs:
# - workload_identity_provider  -> set as repo secret GCP_WORKLOAD_IDENTITY_PROVIDER
# - deployer_service_account_email -> set as repo secret GCP_DEPLOYER_SA_EMAIL
# - artifact_registry_repo (informational)
```