# Security group rules (EC2 / Cloud9 instance)

| Direction | Protocol | Port | Source | Why |
|---|---|---|---|---|
| Inbound | TCP | 8080 | **My IP only** (`x.x.x.x/32`) | Test the ticket-api from my laptop |
| Inbound | TCP | 22 | AWS Cloud9 service (created by Cloud9) | IDE connection |
| Outbound | All | All | 0.0.0.0/0 | Pull base image, push/pull ECR, OS updates |

Port 8080 is never opened to `0.0.0.0/0`. Planned for later weeks: put the
`ticket-web` service on port 80 behind an Application Load Balancer and keep
the EC2 instance itself private.
