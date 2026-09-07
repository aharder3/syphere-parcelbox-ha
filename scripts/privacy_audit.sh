#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# Scan tracked working-tree text for patterns that should never appear as live data.
# Placeholder/API variable names are intentionally allowed.
PATTERNS=(
  'Authorization: Bearer eyJ'
  'eyJ[a-zA-Z0-9_-]{20,}\.[a-zA-Z0-9_-]{20,}\.[a-zA-Z0-9_-]{20,}'
  'BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY'
)

for pattern in "${PATTERNS[@]}"; do
  if grep -RIE --exclude-dir=.git --exclude='privacy_audit.sh' "$pattern" . >/dev/null; then
    echo "Privacy audit failed: matched pattern: $pattern" >&2
    grep -RInE --exclude-dir=.git --exclude='privacy_audit.sh' "$pattern" . || true
    exit 1
  fi
done

if find . -type f \( -name '*.pcap' -o -name '*.pcapng' -o -name '*.mitm' -o -name '*.har' \) -print -quit | grep -q .; then
  echo "Privacy audit failed: network capture/export file found" >&2
  exit 1
fi

echo "Privacy audit passed."
