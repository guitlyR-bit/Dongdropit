# OnionRANK – kompletní návod ke zprovoznění

Celkem 4 fáze: **server → instalace → test v Tor Browseru → BTC platby**.
Fáze 1–3 zaberou asi 20 minut, BTCPay (fáze 4) počítej na pár hodin až den kvůli synchronizaci blockchainu.

---

## Fáze 1 – Server

Potřebuješ linuxový server s **Debian 12** nebo **Ubuntu 22.04/24.04**:

| Varianta | Bez BTCPay (demo) | S BTCPay na stejném stroji |
|---|---|---|
| RAM | 1 GB | 4 GB |
| Disk | 10 GB | 80 GB (pruned node) / 700+ GB (plný) |

* VPS: vyber poskytovatele, který toleruje Tor a ideálně přijímá platbu v kryptu (pro soukromí).
* Nebo vlastní počítač / mini PC doma – onion služba nepotřebuje veřejnou IP ani otevřené porty.

Připoj se: `ssh root@IP_SERVERU`

> Tip: hned nastav přihlášení SSH klíčem a vypni heslo (`PasswordAuthentication no` v `/etc/ssh/sshd_config`).

---

## Fáze 2 – Instalace (jeden příkaz)

```bash
apt update && apt install -y git
git clone -b ccr-8278acdb-6fqxob https://github.com/guitlyR-bit/Dongdropit.git /opt/onionrank
sudo bash /opt/onionrank/deploy/install.sh
```

> Repozitář je teď pravděpodobně soukromý. Buď ho na GitHubu přepni na public, nebo
> na serveru použij [deploy key / token](https://docs.github.com/en/authentication).

Skript automaticky:
1. nainstaluje Tor, Python a Git,
2. stáhne aplikaci do `/opt/onionrank` a vytvoří Python prostředí,
3. vytvoří onion službu (`/var/lib/tor/onionrank/`),
4. vygeneruje `.env` s náhodným `SECRET_KEY` a `ADMIN_TOKEN`,
5. vytvoří systémového uživatele `onionrank` a službu `onionrank.service`,
6. vypíše **adresu webu** a **adresu administrace**.

Výstup na konci vypadá takto:
```
 OnionRANK: běží ✔
 Web:    http://abc…xyz.onion
 Admin:  http://abc…xyz.onion/admin?t=…
```
**Admin odkaz si ulož a nikomu ho nedávej.**

### Aktualizace na novou verzi
Stačí skript spustit znovu – data, `.env` i onion adresa zůstanou:
```bash
sudo bash /opt/onionrank/deploy/install.sh
```

---

## Fáze 3 – Test

1. Stáhni Tor Browser z torproject.org a otevři svou `.onion` adresu.
   (První načtení po spuštění může trvat 1–2 minuty, než se služba v Toru publikuje.)
2. Klikni na `./boost.sh`, zadej libovolnou v3 onion adresu a částku → `EXECUTE_PAYMENT` → `SIMULATE_PAYMENT`.
3. Doména se objeví v žebříčku. Smazat/vyřadit ji můžeš v adminu.

Web je v **demo režimu** (žlutý pruh nahoře). Před ostrým spuštěním demo data smaž:
```bash
sudo systemctl stop onionrank
sudo rm /opt/onionrank/instance/onionrank.sqlite
sudo systemctl start onionrank
```

---

## Fáze 4 – Skutečné BTC platby (BTCPay Server)

BTCPay je zdarma, open-source, peníze jdou **rovnou do tvé peněženky** a nikdo třetí do toho nevidí.

### 4.1 Peněženka
Založ si BTC peněženku, ze které umíš exportovat **xpub/zpub** – např. Sparrow Wallet nebo hardware
peněženku (Trezor, Coldcard). Seed slova si bezpečně zapiš offline. Na server nikdy nedávej seed, jen xpub.

### 4.2 Instalace BTCPay na stejný server
```bash
mkdir -p /opt/btcpay && cd /opt/btcpay
git clone https://github.com/btcpayserver/btcpayserver-docker
cd btcpayserver-docker
export BTCPAY_HOST="btcpay.local"
export NBITCOIN_NETWORK="mainnet"
export BTCPAYGEN_CRYPTO1="btc"
export BTCPAYGEN_REVERSEPROXY="nginx"
export BTCPAYGEN_ADDITIONAL_FRAGMENTS="opt-save-storage-s"   # pruned node (~80 GB)
export BTCPAY_ENABLE_SSH=false
export BTCPAYGEN_LIGHTNING="none"
# BTCPay jen přes Tor – webový port nebude dostupný z internetu:
export REVERSEPROXY_HTTP_PORT="127.0.0.1:8081"
export REVERSEPROXY_HTTPS_PORT="127.0.0.1:8443"
. ./btcpay-setup.sh -i
```
Instalace zapne i Tor. Onion adresu BTCPay zjistíš příkazem
`cat /var/lib/docker/volumes/generated_tor_servicesdir/_data/BTCPayServer/hostname`.
**Hned ji otevři v Tor Browseru a zaregistruj se – první registrovaný účet je admin.**
Pak počkej, než se node zesynchronizuje (stav vidíš v BTCPay nahoře).

> Ověř aktuální postup v dokumentaci docs.btcpayserver.org – může se mezi verzemi měnit.

### 4.3 Nastavení BTCPay (přes Tor Browser na onion adresu BTCPay)
1. Zaregistruj admin účet (první účet je admin).
2. **Create store** → název „OnionRANK“, výchozí měna BTC.
3. **Wallet → Connect an existing wallet** → vlož xpub.
4. **Account → Manage Account → API Keys → Generate key** s oprávněními:
   * `View invoices` (`btcpay.store.canviewinvoices`)
   * `Create invoice` (`btcpay.store.cancreateinvoice`)
5. **Store Settings → Webhooks → Create webhook**:
   * Payload URL: `http://TVOJE_ONIONRANK.onion/webhook/btcpay`
   * události: *An invoice has been settled*, *expired*, *invalid*
   * zkopíruj **Secret**.
6. Store ID najdeš v *Store Settings → General*.

### 4.4 Propojení s OnionRANK
```bash
sudo nano /opt/onionrank/.env
```
```
PAYMENT_PROVIDER=btcpay
BTCPAY_URL=http://BTCPAY_ONION_ADRESA.onion
BTCPAY_STORE_ID=…
BTCPAY_API_KEY=…
BTCPAY_WEBHOOK_SECRET=…
BTCPAY_PROXY=socks5h://127.0.0.1:9050
```
```bash
sudo systemctl restart onionrank
```
Žlutý DEMO pruh zmizí. Udělej testovací platbu s minimální částkou a zkontroluj, že se po potvrzení
objeví v žebříčku. Kdyby webhook přes Tor nedorazil, aplikace si stav ověří sama při otevření stránky
objednávky; v nejhorším ji potvrdíš ručně v adminu.

---

## Provoz

| Co | Příkaz |
|---|---|
| Stav aplikace | `systemctl status onionrank` |
| Logy | `journalctl -u onionrank -f` |
| Restart | `systemctl restart onionrank` |
| Onion adresa | `cat /var/lib/tor/onionrank/hostname` |
| Admin token | `grep ADMIN_TOKEN /opt/onionrank/.env` |
| Záloha | `sudo bash /opt/onionrank/deploy/backup.sh` |

**Zálohuj** (a stáhni mimo server): `/var/lib/tor/onionrank/` (bez toho přijdeš o adresu),
`/opt/onionrank/.env` a databázi. Skript `backup.sh` to zabalí do jednoho souboru.

Bezpečnost:
* aplikace poslouchá jen na `127.0.0.1` – nikdy ji nevystavuj na veřejnou IP,
* `apt update && apt upgrade` pravidelně (nebo zapni `unattended-upgrades`),
* moderuj žebříček – domény s nelegálním obsahem vyřaď v adminu,
* zjisti si daňové povinnosti k příjmům v BTC.

## Nastavení (`/opt/onionrank/.env`)

| Proměnná | Význam |
|---|---|
| `MIN_SATS` / `MAX_SATS` | minimální / maximální platba v sats |
| `PAYMENT_PROVIDER` | `demo` nebo `btcpay` |
| `SITE_URL` | tvoje onion adresa (kam BTCPay přesměruje po platbě) |
| `ADMIN_TOKEN` | heslo do `/admin?t=…` |

Po každé změně: `sudo systemctl restart onionrank`.
