# Deployment Plan (Track B: EC2 + Docker + ECR)

Environment: **AWS Academy Lab Project account**, region **us-east-1**, budget **$40, cannot be reset**.

## 1. Why Track B in this environment

| Finding in the lab account | Consequence |
|---|---|
| IAM actions are restricted (`iam:CreatePolicy` is denied, no `LabRole`) | Lambda cannot get an execution role, so Track C (serverless) cannot be deployed |
| AWS CloudShell is blocked | Use an **AWS Cloud9** environment (an EC2 instance with Docker + AWS CLI) as the build host |
| EC2, ECR, Docker and the `LabVPC` are available | Track B fits the account exactly |

## 2. Resources

| Resource | Name / setting | Purpose |
|---|---|---|
| VPC / subnet | `LabVPC` / `Public Subnet1` | Network for the instance (internet gateway route) |
| EC2 (via Cloud9) | `ticketing-dev`, t3.small, Amazon Linux 2023, SSH connection, auto-hibernate 30 min | Build host and runtime for the containers |
| Security group | Cloud9 SG + inbound TCP 8080 from my IP /32 | Test access to the API ([rules](../infra/security-group-rules.md)) |
| ECR repository | `ticketing/ticket-api`, private, scan on push, AES-256, keep 10 images | Stores the Docker image |
| Docker volume | `ticket-data` | Keeps the SQLite database across container restarts |
| Docker network | `ticketing-net` | Lets `ticket-web` reach `ticket-api` by name (planned) |

## 3. Steps

```bash
# 1. In the lab console: Cloud9 > ticketing-dev > Open (terminal)
git clone https://github.com/RafiBusthami/ticketing-docker-aws.git
cd ticketing-docker-aws

# 2. Unit tests on the instance (optional)
pip install -r requirements-dev.txt && python3 -m pytest -q

# 3. Create the ECR repo (first run), build, tag with the git commit, push
bash scripts/build_push.sh

# 4. Pull the image back from ECR and run it
bash scripts/run_from_ecr.sh

# 5. Collect evidence
bash scripts/smoke_test.sh
```

6. In the EC2 console, add an inbound rule to the instance's security group: **Custom TCP 8080, source "My IP"**. Then open `http://<public-ip>:8080/health` from the laptop.

## 4. Verification checklist

| Check | How | Expected |
|---|---|---|
| AWS credentials | `aws sts get-caller-identity` | lab account, `voclabs` role |
| EC2 instance | instance metadata (IMDSv2) | t3.small, us-east-1, public IP |
| ECR push | `aws ecr describe-images` | tags `<sha>` and `latest`, scan COMPLETE |
| Pull from ECR | `run_from_ecr.sh` deletes the local image first | `docker pull` succeeds |
| Container | `docker ps` | `ticket-api` **healthy**, `0.0.0.0:8080->8080/tcp` |
| CRUD | `curl` POST/GET/PUT/DELETE | 201 / 200 / 200 / 204, then 404 |
| Persistence | `docker restart ticket-api`, then GET | ticket still exists |
| External access | browser on laptop → `:8080/health` | 200 from my IP; other IPs time out |

## 5. Cost estimate (lab budget)

| Item | Rate (us-east-1) | Week 12 usage | Cost |
|---|---|---|---|
| EC2 t3.small | ~$0.0208 / hour | ~4 h (Cloud9 hibernates after 30 min idle) | ~$0.08 |
| EBS gp3 10 GB | ~$0.08 / GB-month | 1 week | ~$0.19 |
| ECR storage | $0.10 / GB-month | ~0.06 GB image | < $0.01 |
| Data transfer | first 100 GB/month free | a few MB | $0.00 |
| **Total** | | | **≈ $0.30** |

Budget habits: Cloud9 auto-hibernates after 30 minutes; end the lab session when not working; the ECR lifecycle rule keeps only 10 images.

## 6. Rollback / clean-up

- Bad image: `TAG=<previous-sha> bash scripts/run_from_ecr.sh` (every push keeps a commit tag).
- Remove project resources: `bash scripts/teardown.sh`, then delete the Cloud9 environment `ticketing-dev`.

## 7. Next steps (proposed)

| Week | Plan |
|---|---|
| 13 | Run `ticket-web` (service 2) with `docker compose --profile planned up -d`; add pagination and search to the API. |
| 14 | Move from a single EC2 host to Amazon ECS with an Application Load Balancer; send container logs to CloudWatch. |
| 15 | CI/CD: build and push to ECR from GitHub Actions or CodePipeline; final demo and report. |
