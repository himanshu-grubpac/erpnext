#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HRMS_DIR="${ROOT}/apps/hrms"

if [[ -d "${HRMS_DIR}/.git" ]]; then
  echo "HRMS already present at ${HRMS_DIR}"
  exit 0
fi

mkdir -p "${ROOT}/apps"
git clone -b version-16 https://github.com/frappe/hrms.git "${HRMS_DIR}"
echo "HRMS cloned. Run: docker compose -f docker-compose.yml -f docker-compose.hrms.yml up -d"
