# Helpdesk Ticketing on AWS (EC2 + Docker + ECR)

This is my individual project for Cloud Computing (Komputasi Awan), Week 12: Design and AWS Setup.

Rafi Busthami (24/532760/TK/58998), S1 Teknologi Informasi, DTETI UGM

## What it is

A small helpdesk ticketing backend for a campus IT team. Someone reports a problem as a ticket (for example "Wi-Fi drops in the lab"), and the IT staff can read it, change its priority and status, and close it when it's fixed.

| | |
|---|---|
| Track | B: Containers (EC2 + Docker + ECR) |
| Services | `ticket-api`, the REST API (Flask + gunicorn), built and deployed this week<br>`ticket-web`, an nginx web page and proxy, planned for later |
| Docker image | `ticket-api`, stored in my private ECR repo `ticketing/ticket-api` |
| Server | One EC2 t3.small (Amazon Linux 2023), created through the Cloud9 environment `ticketing-dev` |
| Database | SQLite, saved on the Docker volume `ticket-data` |
| AWS account | AWS Academy lab account ($40 budget), region `us-east-1` |

I first wanted to do Track C (serverless), but my lab account doesn't allow creating the IAM role that Lambda needs, so I switched to Track B. The details are in [`docs/deployment-plan.md`](docs/deployment-plan.md).

## Architecture

![Architecture diagram](docs/architecture.png)

How a request travels: the client calls the EC2 public IP on port 8080, the security group only lets my IP through, Docker passes the request to the `ticket-api` container, and the API reads or writes the SQLite file on the `ticket-data` volume before sending back JSON.

How I deploy: I clone this repo in Cloud9, build the image, log in to ECR with `aws ecr get-login-password`, push the image, then pull it back from ECR and run it.

The diagram is made from [`docs/architecture.html`](docs/architecture.html) with the script [`docs/diagram/build_diagram.py`](docs/diagram/build_diagram.py).

## Week 12 status

Everything below was tested on AWS on 22 Nov 2026.

| Check | Result |
|---|---|
| Unit tests on EC2 | All 14 passed |
| Image in ECR | `ticketing/ticket-api:564d581` (also `latest`), scanned on push |
| Container on EC2 | Healthy, pulled from ECR, runs as a non-root user, limited to 256 MB and 0.5 CPU |
| CRUD over HTTP | POST 201, GET 200, PUT 200, DELETE 204, GET after delete 404, bad input 400 |
| Data persistence | The ticket was still there after `docker restart` |
| Access from my laptop | Works on `http://<EC2 public IP>:8080`; the security group only allows my IP |
| Image security | After adding Debian security updates, ECR findings went from 34 to 18 |

The screenshots and the full test log are in [`docs/evidence/`](docs/evidence/README.md).

## Data entity: Ticket

| Field | Type | Rules |
|---|---|---|
| `ticketId` | TEXT (UUID v4) | Primary key, created by the API |
| `title` | TEXT | Required, 3 to 120 characters |
| `description` | TEXT | Optional, up to 2000 characters |
| `requesterEmail` | TEXT | Required, must be a valid email, saved in lowercase |
| `category` | Enum | `HARDWARE`, `SOFTWARE`, `NETWORK`, `ACCOUNT`, `OTHER` |
| `priority` | Enum | `LOW`, `MEDIUM` (default), `HIGH`, `URGENT` |
| `status` | Enum | `OPEN` (default), `IN_PROGRESS`, `RESOLVED`, `CLOSED` (has an index) |
| `createdAt`, `updatedAt` | TEXT (ISO 8601, UTC) | Filled in by the API |

## Endpoints (`ticket-api`, port 8080)

| # | Method | Path | What it does | Success | Errors |
|---|---|---|---|---|---|
| 1 | `POST` | `/tickets` | Create a ticket | `201` + ticket | `400` invalid input |
| 2 | `GET` | `/tickets/{ticketId}` | Read one ticket | `200` + ticket | `400` bad id, `404` |
| 3 | `PUT` | `/tickets/{ticketId}` | Update title, description, category, priority or status | `200` + ticket | `400`, `404` |
| 4 | `DELETE` | `/tickets/{ticketId}` | Delete a ticket | `204` | `400`, `404` |
| extra | `GET` | `/tickets?status=OPEN&limit=20` | List tickets | `200` + `{count, items}` | `400` |
| extra | `GET` | `/health` | Check that the service is up | `200` | |

Example:

```bash
curl -X POST http://<EC2_PUBLIC_IP>:8080/tickets -H 'Content-Type: application/json' \
  -d '{"title":"Projector not working","requesterEmail":"me@mail.ugm.ac.id","category":"hardware","priority":"high"}'
```

## Folders

```
├── app/
│   ├── app.py               the ticket-api code (routes, validation, SQLite)
│   ├── Dockerfile           python:3.12-slim from ECR Public, non-root user, health check
│   └── requirements.txt
├── web/                     ticket-web (planned): nginx.conf and index.html
├── docker-compose.yml       both services (ticket-web is under the "planned" profile)
├── infra/
│   ├── ecr-lifecycle-policy.json
│   ├── iam-least-privilege-policy.json
│   └── security-group-rules.md
├── scripts/
│   ├── build_push.sh        creates the ECR repo, builds, tags and pushes the image
│   ├── run_from_ecr.sh      pulls the image from ECR and runs it with the volume
│   ├── smoke_test.sh        tests AWS, EC2, ECR, the container and CRUD, saves output to docs/evidence/
│   └── teardown.sh          removes the container and the ECR repo
├── tests/test_api.py        14 unit tests (pytest)
└── docs/
    ├── architecture.png     the diagram (made from architecture.html)
    ├── deployment-plan.md   steps, costs and checks
    └── evidence/            12 screenshots and smoke-test-output.txt
```

## How to deploy (in the Cloud9 terminal)

```bash
git clone https://github.com/RafiBusthami/ticketing-docker-aws.git
cd ticketing-docker-aws
bash scripts/build_push.sh     # create the ECR repo, build and push
bash scripts/run_from_ecr.sh   # pull from ECR and run on port 8080
bash scripts/smoke_test.sh     # run the tests and save the output to docs/evidence/
```

More detail is in [`docs/deployment-plan.md`](docs/deployment-plan.md).

## Running it on your own computer

```bash
pip install -r requirements-dev.txt && pytest -v
docker compose up -d --build && curl localhost:8080/health
```

On every push, GitHub Actions runs the tests, builds the image and checks `/health` ([`.github/workflows/ci.yml`](.github/workflows/ci.yml)).

## Security

- Port 8080 is only open to my own IP (/32).
- No AWS access keys are saved anywhere. Docker logs in to ECR with a token from the lab role that lasts 12 hours.
- The ECR repo is private, scans every image on push, is encrypted with AES-256 and only keeps the 10 newest images.
- The image installs Debian security updates when it's built. That brought the scan findings down from 34 to 18. The 8 HIGH findings left don't have a Debian fix yet.
- The container runs as a non-root user, with CPU and memory limits, a health check and automatic restart.
- The API checks every input field and uses parameterised SQL.
