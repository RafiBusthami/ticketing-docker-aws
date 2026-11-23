# AWS Evidence: Week 12 (22 Nov 2026)

These are the screenshots and test output from my AWS lab account (`767397656598`, us-east-1). I ran everything on the EC2 instance of my Cloud9 environment `ticketing-dev`.

| Item | Value |
|---|---|
| EC2 instance | `i-03bda32a1d6131c7a`, t3.small, Amazon Linux 2023, us-east-1a |
| Network | `LabVPC` (`vpc-0c078d2d0256179d7`), Public Subnet1 (`subnet-0fdc0f137b19ab4b7`), public IP 54.146.204.119 |
| Security group | `sg-07058327339476ad1`: SSH 22 from the Cloud9 address ranges, TCP 8080 from my IP only |
| ECR repository | `767397656598.dkr.ecr.us-east-1.amazonaws.com/ticketing/ticket-api` |
| Images | `fc528cb` (first build), and `564d581` + `latest` (with security updates, this is the one running) |
| Container | `ticket-api`, healthy, runs as `appuser`, 256 MB / 0.5 CPU, restarts automatically, uses the `ticket-data` volume |

## What I checked

| # | Check | Result | Screenshot |
|---|---|---|---|
| 1 | EC2 instance in a LabVPC public subnet | Running, IMDSv2 required | [01](01-ec2-instance-labvpc-public-subnet.jpg) |
| 2 | Unit tests on the instance | All 14 passed | [02](02-unit-tests-on-ec2.jpg) |
| 3 | Build the image and push it to ECR | Pushed `fc528cb` and `latest` | [03](03-docker-build-push-to-ecr.jpg) |
| 4 | Pull from ECR and run | Container is healthy, not root, with limits | [04](04-run-container-from-ecr.jpg) |
| 5 | AWS connection, ECR scan, create a ticket | Identity check OK, scan complete, POST 201 | [05](05-smoke-test-ecr-scan-and-create.jpg) |
| 6 | CRUD and persistence | GET 200, PUT 200, list 200, after restart 200, DELETE 204, GET 404 | [06](06-smoke-test-crud-and-persistence.jpg) |
| 7 | Rebuild with Debian security updates | 7 packages upgraded, pushed `564d581` | [07](07-rebuild-patched-image.jpg) |
| 8 | ECR scan before and after the update | 34 findings down to 18 (HIGH 11 to 8, MEDIUM 19 to 9, LOW 4 to 1) | [08](08-ecr-scan-before-after-patch.jpg) |
| 9 | Redeploy the updated image and run the full test | Everything passes, bad input gives 400 | [09](09-final-deploy-and-smoke-test.jpg), [log](smoke-test-output.txt) |
| 10 | ECR repository in the console | 2 images, sizes, digests, last pulled | [10](10-ecr-repository-images.jpg) |
| 11 | Security group rule | TCP 8080 from my IP only (I hid the IP) | [11](11-security-group-8080-my-ip-only.jpg) |
| 12 | Calling the API from my laptop | `/health` and `/tickets` work; I created 3 tickets and set one to RESOLVED | [12](12-api-called-from-laptop-browser.jpg) |

The full output of check 9 is in [`smoke-test-output.txt`](smoke-test-output.txt). It was made by `scripts/smoke_test.sh`.

## Things I still want to improve

- There are still 8 HIGH findings in the Debian base image (openssl and glibc). Debian hasn't released a fix yet, and ECR scans every new push, so I'll see when it's fixed.
- Port 8080 uses plain HTTP. That's fine for testing because only my IP can reach it, but later I want HTTPS through a load balancer with an ACM certificate.
- `docker login` saves the ECR token in `~/.docker/config.json`. The token expires after 12 hours, but using `amazon-ecr-credential-helper` would keep it off the disk.
- SQLite on one instance is enough for Week 12, but if that instance goes down the app goes down too. I plan to move to Amazon RDS when the app runs on more than one server.
