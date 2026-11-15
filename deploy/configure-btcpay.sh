#!/usr/bin/env bash
# Interactive BTCPay setup for OnionRANK: asks for the values, cleans up .env,
# restarts the app and tests the connection.
#   sudo bash /opt/onionrank/deploy/configure-btcpay.sh
# Press Enter at a prompt to keep the value already stored in .env.
set -euo pipefail

ENV=${ENV_FILE:-/opt/onionrank/.env}
LOCAL=${BTCPAY_LOCAL:-http://127.0.0.1:8081}       # BTCPay's nginx on this machine
VHOST=${BTCPAY_VHOST:-}                             # its BTCPAY_HOST (auto-detected)
[ -f "$ENV" ] || { echo "Soubor $ENV neexistuje – spusť nejdřív install.sh"; exit 1; }

cur() { grep -E "^$1=" "$ENV" | tail -1 | cut -d= -f2- || true; }

ask() { # ask VAR "prompt" regex default [secret]
  local __v __re="$3" __def="$4" __hint=""
  [ -n "$__def" ] && __hint=" [Enter = ponechat]"
  while true; do
    if [ "${5:-}" = secret ]; then read -rsp "$2$__hint: " __v; echo; else read -rp "$2$__hint: " __v; fi
    __v=$(printf '%s' "$__v" | tr -d '[:space:]')
    [ -z "$__v" ] && __v="$__def"
    if [[ "$__v" =~ $__re ]]; then printf -v "$1" '%s' "$__v"; return; fi
    echo "  ✗ Neplatná hodnota, zkus to znovu."
  done
}

OLD_PUBLIC=$(cur BTCPAY_PUBLIC_URL); [ -n "$OLD_PUBLIC" ] || OLD_PUBLIC=$(cur BTCPAY_URL)
[[ "$OLD_PUBLIC" =~ \.onion ]] || OLD_PUBLIC=""

echo "== Nastavení BTCPay pro OnionRANK =="
echo "Hodnoty vkládej po jedné (pravé tlačítko myši = vložit), pak Enter."
echo "API klíč a secret se při psaní nezobrazují – to je v pořádku."
echo
ask URL   "1/4 Onion adresa BTCPay (http://…onion)" '^(http://)?[a-z2-7]{56}\.onion/?$' "$OLD_PUBLIC"
URL="http://${URL#http://}"; URL="${URL%/}"
ask STORE "2/4 Store ID"       '^[A-Za-z0-9]{20,64}$'  "$(cur BTCPAY_STORE_ID)"
ask KEY   "3/4 API klíč"       '^[A-Za-z0-9]{20,128}$' "$(cur BTCPAY_API_KEY)" secret
ask HOOK  "4/4 Webhook secret" '^[A-Za-z0-9]{10,128}$' "$(cur BTCPAY_WEBHOOK_SECRET)" secret

# BTCPay on this machine? Then talk to it directly instead of through Tor.
if [ -z "$VHOST" ]; then
  for f in /opt/btcpay/btcpayserver-docker/.env /etc/profile.d/btcpay-env.sh; do
    [ -f "$f" ] && VHOST=$(grep -oE 'BTCPAY_HOST="?[^"[:space:]]+' "$f" | head -1 | sed -E 's/.*="?//') && [ -n "$VHOST" ] && break
  done
  VHOST=${VHOST:-btcpay.local}
fi
MODE=tor
if curl -s -m 10 -o /dev/null -H "Host: $VHOST" "$LOCAL/" 2>/dev/null; then MODE=local; fi

cp "$ENV" "$ENV.bak.$(date +%s)"
TMP=$(mktemp)
grep -E '^(#.*|[A-Z_]+=.*)?$' "$ENV" \
  | grep -vE '^#?(PAYMENT_PROVIDER|BTCPAY_[A-Z_]+|MIN_SATS)=' > "$TMP" || true
{
  echo "MIN_SATS=10000"
  echo "PAYMENT_PROVIDER=btcpay"
  echo "BTCPAY_STORE_ID=$STORE"
  echo "BTCPAY_API_KEY=$KEY"
  echo "BTCPAY_WEBHOOK_SECRET=$HOOK"
  if [ "$MODE" = local ]; then
    echo "BTCPAY_URL=$LOCAL"
    echo "BTCPAY_HOST_HEADER=$VHOST"
    echo "BTCPAY_PUBLIC_URL=$URL"
  else
    echo "BTCPAY_URL=$URL"
    echo "BTCPAY_PROXY=socks5h://127.0.0.1:9050"
  fi
} >> "$TMP"
cat "$TMP" > "$ENV"; rm -f "$TMP"
chmod 600 "$ENV"
echo "✔ $ENV uložen (režim: $MODE, záloha: $ENV.bak.*)"

if command -v systemctl >/dev/null && systemctl cat onionrank.service >/dev/null 2>&1; then
  systemctl restart onionrank && echo "✔ onionrank restartován"
fi

echo "… testuji spojení s BTCPay"
if [ "$MODE" = local ]; then
  CODE=$(curl -s -m 30 -o /dev/null -w '%{http_code}' -H "Host: $VHOST" \
    -H "Authorization: token $KEY" "$LOCAL/api/v1/stores/$STORE/invoices" || true)
else
  CODE=$(curl -s -m 90 -o /dev/null -w '%{http_code}' --socks5-hostname 127.0.0.1:9050 \
    -H "Authorization: token $KEY" "$URL/api/v1/stores/$STORE/invoices" || true)
fi
case "$CODE" in
  200) echo "✔ HTTP 200 – OnionRANK je propojený s BTCPay." ;;
  401|403) echo "✗ HTTP $CODE – API klíč je špatný nebo nemá oprávnění View/Create invoices." ;;
  404) echo "✗ HTTP 404 – špatné Store ID." ;;
  503) echo "✗ HTTP 503 – nginx nezná host '$VHOST'. Spusť znovu s BTCPAY_VHOST=<tvůj BTCPAY_HOST>." ;;
  *) echo "✗ HTTP ${CODE:-000} – BTCPay se nepodařilo zastihnout (režim $MODE)." ;;
esac
