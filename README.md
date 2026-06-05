# GrubPac ERPNext + HRMS (Docker)

Deploy-only repo for running ERPNext v16 with HRMS on Docker. Application code comes from the `frappe/erpnext` image, not from this repository.

## Start (AWS / server)

```bash
cd ~/erpnext
docker compose -f docker-compose.yml -f docker-compose.hrms.yml up -d
```

## HRMS (first time on server)

```bash
mkdir -p apps
git clone -b version-16 https://github.com/frappe/hrms.git apps/hrms
docker compose -f docker-compose.yml -f docker-compose.hrms.yml up -d
```

Or run `scripts/setup-hrms.sh`.

## Update compose files from GitHub

```bash
curl -fsSL https://raw.githubusercontent.com/himanshu-grubpac/erpnext/develop/docker-compose.yml -o docker-compose.yml
curl -fsSL https://raw.githubusercontent.com/himanshu-grubpac/erpnext/develop/docker-compose.hrms.yml -o docker-compose.hrms.yml
docker compose -f docker-compose.yml -f docker-compose.hrms.yml up -d
```

## Important

- Do **not** clone full ERPNext source on the server — use the Docker image.
- Site data lives in Docker volumes (`sites`, `db-data`), not in git.
- `apps/hrms` is on the host disk and is gitignored here.
