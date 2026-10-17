#!/usr/bin/env bash
# Record the upstream facts behind the phase 0 atopile decisions (ARCHITECTURE.md log).
#
#   scripts/roundtrip/upstream_checks.sh > reports/phase0/upstream-checks.txt
#
# Needs network access and an authenticated `gh` (read-only calls).
set -uo pipefail

echo "date_utc: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo
echo "## atopile part/package servers (atopile 0.15.7 defaults)"
for h in components.atopileapi.com packages.atopileapi.com legacy.atopileapi.com; do
  printf '%s: ' "$h"
  host "$h" 2>&1 | head -1
done
echo
echo "## when the servers disappeared (upstream issue atopile/atopile#1829)"
gh issue view 1829 -R atopile/atopile --json title,createdAt,closedAt \
  -q '"\(.title)\ncreated \(.createdAt), closed \(.closedAt)"'
gh issue view 1829 -R atopile/atopile --json body -q .body | grep -m1 -i 'since'
echo
echo "## legacy endpoint used by 0.15.8+ (no login)"
printf 'GET https://legacy.atopileapi.com/v0/health -> HTTP '
curl -s -m 10 -o /dev/null -w '%{http_code}\n' https://legacy.atopileapi.com/v0/health
printf 'GET https://legacy.atopileapi.com/v0/motd -> '
curl -s -m 10 -H 'User-Agent: atopile/0.15.8' https://legacy.atopileapi.com/v0/motd
echo
echo
echo "## atopile releases on PyPI (newest first)"
curl -s https://pypi.org/pypi/atopile/json | python3 -c '
import json, sys
d = json.load(sys.stdin)
rel = sorted(((f[0]["upload_time"] if f else "", v) for v, f in d["releases"].items()), reverse=True)[:4]
for t, v in rel:
    print(t, v)'
