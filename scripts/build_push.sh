#!/usr/bin/env bash
# Build the ticket-api image and push it to a private Amazon ECR repository.
# Run on the EC2 instance (AWS Cloud9 terminal) from the repo root:
#   bash scripts/build_push.sh
set -euo pipefail
cd "$(dirname "$0")/.."

REGION="${AWS_REGION:-us-east-1}"
REPO="${ECR_REPO:-ticketing/ticket-api}"
ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
REGISTRY="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"
TAG="$(git rev-parse --short HEAD 2>/dev/null || date +%Y%m%d%H%M)"

echo "==> Account ${ACCOUNT_ID} | Region ${REGION} | Repository ${REPO} | Tag ${TAG}"

# 1. Create the private ECR repository once (scan on push, encrypted at rest)
if ! aws ecr describe-repositories --repository-names "${REPO}" --region "${REGION}" >/dev/null 2>&1; then
  echo "==> Creating ECR repository ${REPO}"
  aws ecr create-repository --repository-name "${REPO}" --region "${REGION}" \
    --image-scanning-configuration scanOnPush=true \
    --encryption-configuration encryptionType=AES256 \
    --tags Key=Project,Value=ticketing >/dev/null
  # Keep only the 10 newest images so storage cost stays near zero
  aws ecr put-lifecycle-policy --repository-name "${REPO}" --region "${REGION}" \
    --lifecycle-policy-text file://infra/ecr-lifecycle-policy.json >/dev/null
fi

# 2. Log Docker in to ECR with a 12-hour token from IAM (no stored passwords)
aws ecr get-login-password --region "${REGION}" \
  | docker login --username AWS --password-stdin "${REGISTRY}"

# 3. Build, tag (git commit + latest) and push
docker build --build-arg APP_VERSION="${TAG}" -t "ticket-api:${TAG}" app/
docker tag "ticket-api:${TAG}" "${REGISTRY}/${REPO}:${TAG}"
docker tag "ticket-api:${TAG}" "${REGISTRY}/${REPO}:latest"
docker push "${REGISTRY}/${REPO}:${TAG}"
docker push "${REGISTRY}/${REPO}:latest"

echo "==> Images in ECR:"
aws ecr describe-images --repository-name "${REPO}" --region "${REGION}" \
  --query "sort_by(imageDetails,&imagePushedAt)[].{tags:join(',',imageTags),pushed:imagePushedAt,sizeMB:to_string(imageSizeInBytes)}" \
  --output table
echo "Image URI: ${REGISTRY}/${REPO}:${TAG}"
