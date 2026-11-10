# 🧅 OnionRANK

Zábavný žebříček `.onion` domén – pořadí určuje **jen součet zaplacených BTC**.
Kdokoli (vlastník i fanoušek) může doménu „posunout“ platbou v bitcoinu.

* Python + Flask + SQLite, **bez JavaScriptu** (funguje v Tor Browseru v režimu *Safest*)
* žebříčky: celkově / 30 dní / 7 dní, detail domény, veřejné vzkazy u plateb
* platby přes **BTCPay Server** (self-hosted, jednorázová adresa pro každou platbu, podepsaný webhook + kontrola stavu přímo u BTCPay)
* admin: vyřazení domén, ruční označení objednávek
* přísná CSP, žádné externí zdroje, žádný referrer, adresy domén nejsou klikací odkazy

## Lokální spuštění (demo platby)

```bash
pip install -r requirements.txt
ADMIN_TOKEN=tajne flask --app onionrank run
```

Otevři http://127.0.0.1:5000, admin je na `/admin?t=tajne`.
V demo režimu se objednávka „zaplatí“ tlačítkem.

Testy: `pip install pytest && pytest`

## Produkce na Toru

1. **BTCPay Server** – nainstaluj (umí běžet i jako onion služba), vytvoř store a:
   * API klíč s oprávněními `btcpay.store.cancreateinvoice` a `btcpay.store.canviewinvoices`
   * webhook na `http://<tvoje>.onion/webhook/btcpay` s událostmi *Invoice settled / expired / invalid*, zkopíruj secret
2. Zkopíruj `.env.example` → `.env` a vyplň (`PAYMENT_PROVIDER=btcpay`).
   Pokud je BTCPay dostupný jen přes Tor, nastav `BTCPAY_PROXY=socks5h://127.0.0.1:9050`.
3. Spusť aplikaci jen na localhostu:
   ```bash
   set -a; . ./.env; set +a
   gunicorn -w 2 -b 127.0.0.1:8080 'onionrank:create_app()'
   ```
4. `/etc/tor/torrc`:
   ```
   HiddenServiceDir /var/lib/tor/onionrank/
   HiddenServicePort 80 127.0.0.1:8080
   ```
   Po restartu Toru najdeš adresu v `/var/lib/tor/onionrank/hostname` – tu dej do `SITE_URL`.

## Jak se počítá pořadí

`skóre = součet sats ze všech potvrzených (Settled) plateb`. Při shodě je výš doména,
která daného skóre dosáhla dřív. Nezaplacené/vypršelé objednávky se nepočítají.

## Moderace a právo

Žebříček obsah webů neověřuje. Počítej s tím, že sem někdo zkusí zaplatit za
propagaci nelegálního obsahu – vyřazuj takové domény v adminu (`/admin`) a
platby za ně nevracej, jak uvádí FAQ. Před spuštěním si ověř právní a daňové
povinnosti spojené s přijímáním BTC ve své zemi.
