#!/usr/bin/env bash
# Pull ticket-api from ECR and run it on this EC2 instance with a persistent volume.
#   bash scripts/run_from_ecr.sh            (uses :latest)
#   TAG=abc1234 bash scripts/run_from_ecr.sh
set -euo pipefail

REGION="${AWS_REGION:-us-east-1}"
REPO="${ECR_REPO:-ticketing/ticket-api}"
TAG="${TAG:-latest}"
PORT="${PORT:-8080}"
ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
REGISTRY="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"
IMAGE="${REGISTRY}/${REPO}:${TAG}"

aws ecr get-login-password --region "${REGION}" \
  | docker login --username AWS --password-stdin "${REGISTRY}" >/dev/null

# Remove the local copy first so the image really comes from ECR
docker rmi -f "${IMAGE}" >/dev/null 2>&1 || true
docker pull "${IMAGE}"

docker network create ticketing-net >/dev/null 2>&1 || true
docker volume create ticket-data >/dev/null
docker rm -f ticket-api >/dev/null 2>&1 || true

docker run -d --name ticket-api \
  --network ticketing-net \
  -p "${PORT}:8080" \
  -v ticket-data:/data \
  --restart unless-stopped \
  --memory 256m --cpus 0.5 \
  "${IMAGE}"

echo "==> Waiting for the container health check"
for _ in $(seq 1 20); do
  state="$(docker inspect -f '{{.State.Health.Status}}' ticket-api)"
  [ "${state}" = "healthy" ] && break
  sleep 2
done
docker ps --filter name=ticket-api --format "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"
curl -s "http://localhost:${PORT}/health"; echo
