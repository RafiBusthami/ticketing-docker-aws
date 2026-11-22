#!/usr/bin/env bash
# Stop the container and delete the ECR repository to save lab budget.
#   bash scripts/teardown.sh
# (Stop or delete the Cloud9/EC2 environment from the console afterwards.)
set -uo pipefail

REGION="${AWS_REGION:-us-east-1}"
REPO="${ECR_REPO:-ticketing/ticket-api}"

docker rm -f ticket-api 2>/dev/null
docker volume rm ticket-data 2>/dev/null
docker network rm ticketing-net 2>/dev/null
aws ecr delete-repository --repository-name "${REPO}" --region "${REGION}" --force >/dev/null \
  && echo "Deleted ECR repository ${REPO}"
echo "Done."
