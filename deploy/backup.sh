#!/usr/bin/env bash
set -euo pipefail
STAMP=$(date +%F-%H%M)
cd /srv/agentforge/app
docker compose -f compose.prod.yml exec -T postgres pg_dump -U forge -Fc agentforge > "/srv/agentforge/backups/agentforge-$STAMP.dump"
find /srv/agentforge/backups -name "*.dump" -mtime +7 -delete
