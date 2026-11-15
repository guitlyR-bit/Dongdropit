#!/usr/bin/env bash
# OnionRANK – automatická instalace na Debian 12 / Ubuntu 22.04+
# Spusť jako root:  sudo bash deploy/install.sh
# Opakované spuštění = aktualizace (data, .env a onion adresa zůstanou).
set -euo pipefail

APP_DIR=/opt/onionrank
REPO=${REPO:-https://github.com/guitlyR-bit/Dongdropit.git}
BRANCH=${BRANCH:-ccr-8278acdb-6fqxob}
PORT=8080
HS_DIR=/var/lib/tor/onionrank

say(){ printf '\033[1;32m[onionrank]\033[0m %s\n' "$*"; }
[ "$(id -u)" = 0 ] || { echo "Spusť jako root (sudo)."; exit 1; }

say "1/6 Instaluji balíčky (tor, python, git)…"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq tor python3 python3-venv git curl >/dev/null

say "2/6 Stahuji aplikaci do $APP_DIR…"
# the checkout is owned by the service user; let root's git work on it
git config --global --get-all safe.directory 2>/dev/null | grep -qx "$APP_DIR" \
  || git config --global --add safe.directory "$APP_DIR"
if [ -d "$APP_DIR/.git" ]; then
  git -C "$APP_DIR" fetch -q origin "$BRANCH"
  git -C "$APP_DIR" checkout -q "$BRANCH"
  git -C "$APP_DIR" reset -q --hard "origin/$BRANCH"
else
  git clone -q -b "$BRANCH" "$REPO" "$APP_DIR"
fi

say "3/6 Python prostředí…"
python3 -m venv "$APP_DIR/.venv"
"$APP_DIR/.venv/bin/pip" install -q --upgrade pip
"$APP_DIR/.venv/bin/pip" install -q -r "$APP_DIR/requirements.txt"

say "4/6 Tor onion služba…"
if ! grep -q "$HS_DIR" /etc/tor/torrc; then
  cat >> /etc/tor/torrc <<TORRC

# --- OnionRANK ---
HiddenServiceDir $HS_DIR/
HiddenServicePort 80 127.0.0.1:$PORT
TORRC
fi
systemctl enable -q tor
systemctl restart tor
for _ in $(seq 1 30); do [ -f "$HS_DIR/hostname" ] && break; sleep 1; done
ONION=$(cat "$HS_DIR/hostname")

say "5/6 Konfigurace (.env)…"
ENV="$APP_DIR/.env"
if [ ! -f "$ENV" ]; then
  cat > "$ENV" <<CONF
SECRET_KEY=$(openssl rand -hex 32)
ADMIN_TOKEN=$(openssl rand -hex 24)
SITE_URL=http://$ONION
DATABASE=$APP_DIR/instance/onionrank.sqlite
MIN_SATS=1000
PAYMENT_PROVIDER=demo
BTCPAY_URL=
BTCPAY_STORE_ID=
BTCPAY_API_KEY=
BTCPAY_WEBHOOK_SECRET=
#BTCPAY_PROXY=socks5h://127.0.0.1:9050
CONF
fi
chmod 600 "$ENV"
mkdir -p "$APP_DIR/instance"
id -u onionrank >/dev/null 2>&1 || useradd --system --home "$APP_DIR" --shell /usr/sbin/nologin onionrank
chown -R onionrank:onionrank "$APP_DIR"

say "6/6 Systemd služba…"
install -m 644 "$APP_DIR/deploy/onionrank.service" /etc/systemd/system/onionrank.service
systemctl daemon-reload
systemctl enable -q onionrank
systemctl restart onionrank
sleep 2
if curl -fsS -o /dev/null "http://127.0.0.1:$PORT/"; then STATE="běží ✔"; else STATE="NEBĚŽÍ – viz: journalctl -u onionrank -n 50"; fi

TOKEN=$(grep ^ADMIN_TOKEN= "$ENV" | cut -d= -f2)
MODE=$(grep ^PAYMENT_PROVIDER= "$ENV" | cut -d= -f2)
cat <<DONE

================================================================
 OnionRANK: $STATE
 Web:    http://$ONION
 Admin:  http://$ONION/admin?t=$TOKEN
 Platby: $MODE   (pro BTC nastav BTCPay v $ENV, viz INSTALL.md)

 ZÁLOHUJ klíče onion adresy: $HS_DIR/
================================================================
DONE
