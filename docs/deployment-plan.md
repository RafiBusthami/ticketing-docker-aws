# Deployment Plan (Track B: EC2 + Docker + ECR)

I deploy everything in my AWS Academy lab account, in region us-east-1. The lab has a $40 budget that can't be reset, so I tried to keep costs low.

## 1. Why I picked Track B

I started by planning Track C (serverless), but when I tested my lab account, a few things didn't work:

| What I found | What it means |
|---|---|
| `iam:CreatePolicy` is denied and there is no `LabRole` | Lambda can't get the execution role it needs, so I can't deploy Track C |
| AWS CloudShell is blocked | I use an AWS Cloud9 environment instead. It's an EC2 instance that already has Docker and the AWS CLI |
| EC2, ECR, Docker and `LabVPC` all work | Track B fits this account |

## 2. Resources I use

| Resource | Name / setting | What it's for |
|---|---|---|
| VPC and subnet | `LabVPC`, `Public Subnet1` | The network for the instance (it has a route to the internet gateway) |
| EC2 (through Cloud9) | `ticketing-dev` (`i-03bda32a1d6131c7a`), t3.small, Amazon Linux 2023, SSH connection, turns off after 30 min idle | Where I build the image and run the containers |
| Security group | `sg-07058327339476ad1`: the Cloud9 SSH rules plus TCP 8080 from my IP only | Lets me test the API from my laptop ([rules](../infra/security-group-rules.md)) |
| ECR repository | `ticketing/ticket-api`, private, scan on push, AES-256, keeps 10 images | Stores the Docker image |
| Docker volume | `ticket-data` | Keeps the SQLite database when the container restarts |
| Docker network | `ticketing-net` | So `ticket-web` can reach `ticket-api` by name later |

## 3. Steps

```bash
# 1. In the lab console, open Cloud9 > ticketing-dev and use the terminal
git clone https://github.com/RafiBusthami/ticketing-docker-aws.git
cd ticketing-docker-aws

# 2. (Optional) run the unit tests on the instance
pip install -r requirements-dev.txt && python3 -m pytest -q

# 3. Create the ECR repo if it doesn't exist, build the image, tag it with the git commit and push it
bash scripts/build_push.sh

# 4. Pull the image back from ECR and run it
bash scripts/run_from_ecr.sh

# 5. Run the smoke test and save the output as evidence
bash scripts/smoke_test.sh
```

6. In the EC2 console, add an inbound rule to the instance's security group: Custom TCP, port 8080, source "My IP". Then open `http://<public-ip>:8080/health` from the laptop.

## 4. How I check that it works

| Check | How | What I expect |
|---|---|---|
| AWS credentials | `aws sts get-caller-identity` | The lab account and the `voclabs` role |
| EC2 instance | Instance metadata (IMDSv2) | t3.small, us-east-1, a public IP |
| Push to ECR | `aws ecr describe-images` | Tags `<commit>` and `latest`, scan COMPLETE |
| Pull from ECR | `run_from_ecr.sh` deletes the local image first | `docker pull` works |
| Container | `docker ps` | `ticket-api` is healthy on `0.0.0.0:8080->8080/tcp` |
| CRUD | `curl` POST, GET, PUT, DELETE | 201, 200, 200, 204, then 404 |
| Data stays | `docker restart ticket-api`, then GET | The ticket is still there |
| Access from outside | Browser on my laptop to `:8080/health` | 200 from my IP, other IPs time out |

## 5. Result

I did all of this on 22 Nov 2026 and every check in section 4 passed. The proof is in [evidence](evidence/README.md).

## 6. Cost estimate

| Item | Price (us-east-1) | Week 12 usage | Cost |
|---|---|---|---|
| EC2 t3.small | about $0.0208 per hour | about 4 hours (Cloud9 turns it off after 30 min idle) | about $0.08 |
| EBS gp3 10 GB | about $0.08 per GB-month | 1 week | about $0.19 |
| ECR storage | $0.10 per GB-month | about 0.06 GB | less than $0.01 |
| Data transfer | first 100 GB per month free | a few MB | $0.00 |
| Total | | | about $0.30 |

To save budget, I let Cloud9 turn the instance off when I'm not using it, I end the lab session when I'm done, and the ECR lifecycle rule deletes old images.

## 7. Rolling back and cleaning up

- If a new image is broken, I can run an older one with `TAG=<previous-commit> bash scripts/run_from_ecr.sh`, because every push keeps its commit tag.
- To remove everything: `bash scripts/teardown.sh`, then delete the Cloud9 environment `ticketing-dev`.

## 8. Plans for the next weeks

| Week | Plan |
|---|---|
| 13 | Start `ticket-web` (service 2) with `docker compose --profile planned up -d`, and add paging and search to the API. |
| 14 | Move from one EC2 instance to Amazon ECS behind an Application Load Balancer, and send container logs to CloudWatch. |
| 15 | Build and push to ECR automatically from GitHub Actions or CodePipeline, then the final demo and report. |
