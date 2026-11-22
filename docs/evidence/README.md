# AWS Evidence: Week 12 (22 Nov 2026)

Everything below was run in the AWS Academy lab account (`767397656598`, us-east-1) on the EC2 instance of the Cloud9 environment `ticketing-dev`.

| Item | Value |
|---|---|
| EC2 instance | `i-03bda32a1d6131c7a`, t3.small, Amazon Linux 2023, us-east-1a |
| Network | `LabVPC` (`vpc-0c078d2d0256179d7`), Public Subnet1 (`subnet-0fdc0f137b19ab4b7`), public IP 54.146.204.119 |
| Security group | `sg-07058327339476ad1`: SSH 22 from the Cloud9 service ranges, **TCP 8080 from my IP /32 only** |
| ECR repository | `767397656598.dkr.ecr.us-east-1.amazonaws.com/ticketing/ticket-api` |
| Images | `fc528cb` (first build), `564d581` + `latest` (OS packages patched, running now) |
| Container | `ticket-api`, healthy, user `appuser`, 256 MB / 0.5 CPU, restart `unless-stopped`, volume `ticket-data` |

## Results

| # | Check | Result | Evidence |
|---|---|---|---|
| 1 | EC2 instance in LabVPC public subnet | Running, IMDSv2 required | [01](01-ec2-instance-labvpc-public-subnet.jpg) |
| 2 | Unit tests on the instance | **14 / 14 passed** | [02](02-unit-tests-on-ec2.jpg) |
| 3 | `docker build` + push to private ECR | Pushed `fc528cb` + `latest` | [03](03-docker-build-push-to-ecr.jpg) |
| 4 | Pull from ECR and run | Container **healthy**, non-root, limits applied | [04](04-run-container-from-ecr.jpg) |
| 5 | AWS connectivity + ECR scan + create | `sts` identity OK, scan COMPLETE, POST → 201 | [05](05-smoke-test-ecr-scan-and-create.jpg) |
| 6 | CRUD + persistence | GET 200 · PUT 200 · LIST 200 · after restart 200 · DELETE 204 · GET 404 | [06](06-smoke-test-crud-and-persistence.jpg) |
| 7 | Rebuild with Debian security updates | 7 packages upgraded, pushed `564d581` | [07](07-rebuild-patched-image.jpg) |
| 8 | ECR scan before vs after patch | **34 → 18 findings** (HIGH 11 → 8, MEDIUM 19 → 9, LOW 4 → 1) | [08](08-ecr-scan-before-after-patch.jpg) |
| 9 | Redeploy patched image + full smoke test | All checks pass, incl. validation → 400 | [09](09-final-deploy-and-smoke-test.jpg), [text output](smoke-test-output.txt) |
| 10 | ECR repository in the console | 2 images, sizes, digests, last pulled | [10](10-ecr-repository-images.jpg) |
| 11 | Security group rule | TCP 8080 from My IP /32 only (IP hidden) | [11](11-security-group-8080-my-ip-only.jpg) |
| 12 | API reached from my laptop over the internet | `/health` and `/tickets` OK; 3 tickets created, 1 set to RESOLVED | [12](12-api-called-from-laptop-browser.jpg) |

The full text log of check 9 is in [`smoke-test-output.txt`](smoke-test-output.txt), produced by `scripts/smoke_test.sh`.

## Open items (honest notes)

- **8 HIGH CVEs remain** in the Debian base image (openssl, glibc). Debian has no fixed package yet; they are rechecked on every push (scan on push).
- Port 8080 is plain **HTTP**. It is limited to my IP for testing; HTTPS through an Application Load Balancer with an ACM certificate is planned.
- `docker login` saves the ECR token in `~/.docker/config.json`. The token expires after 12 hours; a credential helper (`amazon-ecr-credential-helper`) would remove it from disk.
- SQLite on one instance is fine for Week 12, but it is a single point of failure. Moving to Amazon RDS is the plan when the service runs on more than one host.
