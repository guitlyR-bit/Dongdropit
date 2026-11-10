#!/usr/bin/env bash
# Záloha databáze, konfigurace a klíčů onion adresy:  sudo bash deploy/backup.sh
set -euo pipefail
OUT=/root/onionrank-backup-$(date +%Y%m%d-%H%M).tar.gz
sqlite3 /opt/onionrank/instance/onionrank.sqlite ".backup /tmp/onionrank.sqlite" 2>/dev/null \
  || cp /opt/onionrank/instance/onionrank.sqlite /tmp/onionrank.sqlite
tar czf "$OUT" /tmp/onionrank.sqlite /opt/onionrank/.env /var/lib/tor/onionrank
rm -f /tmp/onionrank.sqlite
chmod 600 "$OUT"
echo "Záloha: $OUT  (stáhni ji mimo server, obsahuje tajné klíče)"
