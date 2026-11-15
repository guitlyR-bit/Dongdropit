#!/usr/bin/env bash
# Interactive BTCPay setup for OnionRANK: asks for the values, cleans up .env,
# restarts the app and tests the connection.
#   sudo bash /opt/onionrank/deploy/configure-btcpay.sh
set -euo pipefail

ENV=${ENV_FILE:-/opt/onionrank/.env}
[ -f "$ENV" ] || { echo "Soubor $ENV neexistuje – spusť nejdřív install.sh"; exit 1; }

ask() { # ask VAR "prompt" regex [secret]
  local __v __re="$3"
  while true; do
    if [ "${4:-}" = secret ]; then read -rsp "$2: " __v; echo; else read -rp "$2: " __v; fi
    __v=$(printf '%s' "$__v" | tr -d '[:space:]')
    if [[ "$__v" =~ $__re ]]; then printf -v "$1" '%s' "$__v"; return; fi
    echo "  ✗ Neplatná hodnota, zkus to znovu."
  done
}

echo "== Nastavení BTCPay pro OnionRANK =="
echo "Hodnoty vkládej po jedné (pravé tlačítko myši = vložit), pak Enter."
echo "API klíč a secret se při psaní nezobrazují – to je v pořádku."
echo
ask URL   "1/4 Onion adresa BTCPay (např. http://abc…xyz.onion)" '^(http://)?[a-z2-7]{56}\.onion/?$'
URL="http://${URL#http://}"; URL="${URL%/}"
ask STORE "2/4 Store ID"                 '^[A-Za-z0-9]{20,64}$'
ask KEY   "3/4 API klíč"                 '^[A-Za-z0-9]{20,128}$' secret
ask HOOK  "4/4 Webhook secret"           '^[A-Za-z0-9]{10,128}$' secret

cp "$ENV" "$ENV.bak.$(date +%s)"
# keep only well-formed KEY=value lines and comments, drop BTCPay/payment keys we rewrite
TMP=$(mktemp)
grep -E '^(#.*|[A-Z_]+=.*)?$' "$ENV" \
  | grep -vE '^#?(PAYMENT_PROVIDER|BTCPAY_URL|BTCPAY_STORE_ID|BTCPAY_API_KEY|BTCPAY_WEBHOOK_SECRET|BTCPAY_PROXY|MIN_SATS)=' \
  > "$TMP" || true
cat >> "$TMP" <<CONF
MIN_SATS=10000
PAYMENT_PROVIDER=btcpay
BTCPAY_URL=$URL
BTCPAY_STORE_ID=$STORE
BTCPAY_API_KEY=$KEY
BTCPAY_WEBHOOK_SECRET=$HOOK
BTCPAY_PROXY=socks5h://127.0.0.1:9050
CONF
cat "$TMP" > "$ENV"; rm -f "$TMP"
chmod 600 "$ENV"
echo "✔ $ENV uložen (záloha: $ENV.bak.*)"

if command -v systemctl >/dev/null && systemctl list-unit-files onionrank.service >/dev/null 2>&1; then
  systemctl restart onionrank && echo "✔ onionrank restartován"
fi

echo "… testuji spojení s BTCPay přes Tor (může trvat až minutu)"
CODE=$(curl -s -m 90 -o /dev/null -w '%{http_code}' --socks5-hostname 127.0.0.1:9050 \
  -H "Authorization: token $KEY" "$URL/api/v1/stores/$STORE/invoices" || true)
case "$CODE" in
  200) echo "✔ HTTP 200 – OnionRANK je propojený s BTCPay." ;;
  401|403) echo "✗ HTTP $CODE – API klíč je špatný nebo nemá oprávnění View/Create invoices." ;;
  404) echo "✗ HTTP 404 – špatné Store ID." ;;
  *) echo "✗ HTTP ${CODE:-000} – BTCPay se nepodařilo zastihnout. Zkontroluj onion adresu a že běží Tor (systemctl status tor)." ;;
esac
