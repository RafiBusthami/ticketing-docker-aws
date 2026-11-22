#!/usr/bin/env bash
# Collect evidence that the AWS setup works and save it to docs/evidence/.
#   bash scripts/smoke_test.sh
# 1) AWS + EC2 connectivity  2) ECR image  3) container  4) CRUD over HTTP
# 5) data persists after a container restart
set -uo pipefail
cd "$(dirname "$0")/.."

REGION="${AWS_REGION:-us-east-1}"
REPO="${ECR_REPO:-ticketing/ticket-api}"
API="${API:-http://localhost:8080}"
OUT="docs/evidence/smoke-test-output.txt"
mkdir -p docs/evidence
exec > >(tee "${OUT}") 2>&1

json() { python3 -m json.tool 2>/dev/null || cat; }
imds() {
  local token
  token="$(curl -s -X PUT http://169.254.169.254/latest/api/token -H 'X-aws-ec2-metadata-token-ttl-seconds: 60')"
  curl -s -H "X-aws-ec2-metadata-token: ${token}" "http://169.254.169.254/latest/meta-data/$1"
}

echo "### Smoke test - $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo
echo "## 1. AWS identity and EC2 instance"
aws sts get-caller-identity --query "{Account:Account,Arn:Arn}" --output table
echo "Instance ID   : $(imds instance-id)"
echo "Instance type : $(imds instance-type)"
echo "AZ            : $(imds placement/availability-zone)"
echo "VPC subnet    : $(imds network/interfaces/macs/$(imds mac)/subnet-id)"
echo "Public IPv4   : $(imds public-ipv4)"
echo "Docker        : $(docker --version)"
echo

echo "## 2. Image in Amazon ECR (${REPO})"
aws ecr describe-images --repository-name "${REPO}" --region "${REGION}" \
  --query "imageDetails[].{tags:join(',',imageTags),digest:imageDigest,pushed:imagePushedAt}" --output table
aws ecr describe-image-scan-findings --repository-name "${REPO}" --region "${REGION}" \
  --image-id imageTag=latest --query "{scanStatus:imageScanStatus.status,findings:imageScanFindings.findingSeverityCounts}" \
  --output json 2>/dev/null || echo "(scan result not available yet)"
echo

echo "## 3. Running container"
docker ps --filter name=ticket-api --format "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"
echo

echo "## 4. CRUD over HTTP (${API})"
echo "--- GET /health"
curl -s "${API}/health" | json
echo
echo "--- [CREATE] POST /tickets"
CREATE="$(curl -s -w '\n%{http_code}' -X POST "${API}/tickets" -H 'Content-Type: application/json' \
  -d '{"title":"Wi-Fi drops in DTETI lab","description":"Connection drops every few minutes.","requesterEmail":"rafi@mail.ugm.ac.id","category":"network","priority":"high"}')"
echo "HTTP $(tail -n1 <<<"${CREATE}")"; head -n -1 <<<"${CREATE}" | json
ID="$(head -n -1 <<<"${CREATE}" | python3 -c 'import sys,json; print(json.load(sys.stdin)["ticketId"])')"
echo
echo "--- [READ] GET /tickets/${ID}"
curl -s -w '\nHTTP %{http_code}\n' "${API}/tickets/${ID}"
echo
echo "--- [UPDATE] PUT /tickets/${ID}"
curl -s -w '\nHTTP %{http_code}\n' -X PUT "${API}/tickets/${ID}" -H 'Content-Type: application/json' \
  -d '{"status":"in_progress","priority":"urgent"}'
echo
echo "--- [LIST] GET /tickets?status=IN_PROGRESS"
curl -s -w '\nHTTP %{http_code}\n' "${API}/tickets?status=IN_PROGRESS"
echo

echo "## 5. Persistence: restart the container, the ticket must still exist"
docker restart ticket-api >/dev/null
for _ in $(seq 1 20); do curl -sf "${API}/health" >/dev/null && break; sleep 1; done
curl -s -w '\nHTTP %{http_code}\n' "${API}/tickets/${ID}"
echo

echo "--- [DELETE] DELETE /tickets/${ID}"
curl -s -o /dev/null -w 'HTTP %{http_code}\n' -X DELETE "${API}/tickets/${ID}"
echo "--- [READ after delete] expect 404"
curl -s -w '\nHTTP %{http_code}\n' "${API}/tickets/${ID}"
echo "--- [VALIDATION] bad body, expect 400"
curl -s -w '\nHTTP %{http_code}\n' -X POST "${API}/tickets" -H 'Content-Type: application/json' \
  -d '{"title":"x","category":"food"}'
echo
echo "### Smoke test finished. Output saved to ${OUT}"
