# Security group rules (EC2 / Cloud9 instance)

| Direction | Protocol | Port | Source | Why |
|---|---|---|---|---|
| Inbound | TCP | 8080 | My IP only (`x.x.x.x/32`) | So I can test ticket-api from my laptop |
| Inbound | TCP | 22 | The AWS Cloud9 service (Cloud9 adds this rule) | The Cloud9 IDE connection |
| Outbound | All | All | 0.0.0.0/0 | Pulling the base image, pushing and pulling from ECR, OS updates |

I never open port 8080 to `0.0.0.0/0`. Later I want to put `ticket-web` on port 80 behind an Application Load Balancer and make the EC2 instance itself private.
