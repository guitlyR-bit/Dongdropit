# OnionRANK – propagační balíček (zdarma)

Adresa: `http://ubjysvxwkvmi2adqnzwpodl2v3qd5b3ksyjbjzqdtwli3xf35yugasad.onion/`

Texty příspěvků jsou anglicky (publikum Toru a Bitcoinu je mezinárodní). Návody jsou česky.

## 0. Než začneš – anonymita
- Založ si **jednu pseudonymní identitu** „OnionRANK“ a používej ji všude. Nic, co vede k tvému jménu,
  e-mailu, telefonu nebo běžným účtům.
- E-mail na registrace: anonymní schránka (např. Proton/Tuta založená přes Tor Browser).
- Účty zakládej a příspěvky piš **přes Tor Browser**.
- Nepiš o tom, kde server běží (Contabo, Česko), ani nic, co by prozradilo tvůj časový pás – posílej
  příspěvky v různou denní dobu.

## 1. Pořadí (týden 1)
| Den | Kanál | Čas |
|---|---|---|
| 1 | Zapiš OnionRANK do vlastního žebříčku přes `./submit.sh` a schval ho – ať má odznak | 2 min |
| 1 | Ahmia (vyhledávač onion webů) | 5 min |
| 1 | Nostr – účet + úvodní příspěvek | 20 min |
| 2 | Stacker News | 10 min |
| 3 | Reddit r/onions (po kontrole pravidel) | 10 min |
| 4–7 | Oslovení provozovatelů onion webů (5–10 denně) | 30 min/den |
| 7 | Hacker News „Show HN“ | 10 min |
| každý týden | Nostr: týdenní výsledky žebříčku | 5 min |

## 2. Ahmia
1. V Tor Browseru otevři ahmia.fi (nebo jejich onion – správná adresa začíná `juhanurmihxlp77`
   a končí `4csyd.onion`, jinak jde o podvrh).
2. Najdi stránku pro přidání onion služby (odkaz „Add onion“ / sekce pro provozovatele, dříve `ahmia.fi/add`).
3. Vlož `http://ubjysvxwkvmi2adqnzwpodl2v3qd5b3ksyjbjzqdtwli3xf35yugasad.onion/`.

Ahmia vyřazuje weby s nelegálním obsahem – OnionRANK je v pořádku, ale proto je důležité, aby žebříček
byl moderovaný.

## 3. Nostr
Klient: např. Primal, Damus (iOS) nebo Amethyst (Android) – na počítači webový klient přes Tor Browser.
Profil:
- **Name:** OnionRANK
- **About:** `A just-for-fun leaderboard of .onion sites. Rank = sats paid. List your site for free, pay to climb. No JS, Tor only.`
- **Website:** onion adresa výše

### Úvodní příspěvek
```
Built a silly thing for Tor: OnionRANK 🧅

A leaderboard of .onion sites where the only ranking factor is how many sats get paid.
No algorithms, no reviews, no SEO. Just sats.

• list your onion site for free
• pay in BTC (self-hosted BTCPay, no KYC) to climb
• amounts stay private, only the rank is public
• works on Tor Browser "Safest" – zero JavaScript
• embeddable rank badge for your site

http://ubjysvxwkvmi2adqnzwpodl2v3qd5b3ksyjbjzqdtwli3xf35yugasad.onion/

#tor #bitcoin #nostr #privacy #onion
```

### Další příspěvky (1–2 týdně)
```
Weekly OnionRANK 🏆
🥇 <name>
🥈 <name>
🥉 <name>
New this week: <name>, <name>
Is your onion site on the board yet? Free listing → ./submit.sh
http://ubjysvxwkvmi2adqnzwpodl2v3qd5b3ksyjbjzqdtwli3xf35yugasad.onion/
```
```
Fun fact: OnionRANK runs with no JavaScript at all.
Leaderboard, payments, badges – all plain HTML, so it works on Tor Browser's Safest level.
Payments go through self-hosted BTCPay straight to a watch-only wallet.
```
```
#1 on OnionRANK is up for grabs 👀
One boost can flip the 7-day board. Who's taking it this week?
```

## 4. Stacker News
Do teritoria (sekce) o Toru / soukromí, případně `~bitcoin` nebo „Show SN“ styl. Typ: **Link** nebo **Discussion**.

**Titulek:** `I built a leaderboard of .onion sites ranked purely by sats paid`

**Text:**
```
OnionRANK is a just-for-fun ranking of Tor onion sites. The only ranking factor: sats.

How it works:
- anyone can list an onion site for free (manual review against illegal content)
- anyone can boost a site by paying in BTC; the more sats, the higher it ranks
- there's an all-time board plus 7-day and 30-day boards, so small sites can top the weekly one
- amounts are private – visitors only see the rank and number of boosts
- site owners get an embeddable rank badge

Tech: Flask + SQLite, no JavaScript anywhere (works on Tor Browser "Safest"),
payments through self-hosted BTCPay Server on a pruned node, watch-only wallet.

http://ubjysvxwkvmi2adqnzwpodl2v3qd5b3ksyjbjzqdtwli3xf35yugasad.onion/

Feedback welcome – what would make you want to boost a site?
```
Na komentáře odpovídej – Stacker News odměňuje aktivitu sats.

## 5. Reddit (r/onions, r/TOR)
Nejdřív si **přečti pravidla subredditu** – r/onions sdílení onion odkazů obvykle povoluje,
r/TOR spíš ne (tam jen diskuze). Nový účet bez historie často skončí ve spamu – pár dní nejdřív
normálně komentuj.

**Titulek:** `OnionRANK – a leaderboard of onion sites ranked by sats paid (free listing, no JS)`

**Text:** použij text ze Stacker News, poslední řádek změň na
`Looking for feedback and for onion sites that want to be listed.`

## 6. Hacker News (Show HN)
Hacker News odkazy na `.onion` neotevře, proto napiš hlavně o technice.

**Titulek:** `Show HN: OnionRANK – a JavaScript-free leaderboard of Tor sites ranked by Bitcoin paid`

**Text:**
```
I wanted a toy project that runs entirely as a Tor onion service and accepts Bitcoin without any third party.

OnionRANK ranks .onion sites purely by the sats paid for them. Anyone can list a site for free; paying moves it up.

Some details that might be interesting:
- No JavaScript at all, so it works in Tor Browser's "Safest" mode (which also blocks SVG – badges are PNG)
- Payments via self-hosted BTCPay Server (pruned node) behind Tor; webhooks over Tor are flaky,
  so a 5-minute reconciliation job is the real source of truth
- Anti-spam for the free listing is a signed arithmetic challenge (no JS CAPTCHA possible)
- Whole thing runs on a ~€6/month VPS

Address (needs Tor Browser): http://ubjysvxwkvmi2adqnzwpodl2v3qd5b3ksyjbjzqdtwli3xf35yugasad.onion/
```

## 7. Přímé oslovení provozovatelů onion webů
Najdi weby v adresářích, na Ahmii nebo na Nostru (hashtag #onion). Napiš na kontakt uvedený na jejich webu
(e-mail, Nostr, kontaktní formulář). **Max. 5–10 denně, každou zprávu trochu uprav** – hromadné rozesílání = spam.

```
Hi,

I run OnionRANK, a small just-for-fun leaderboard of onion sites:
http://ubjysvxwkvmi2adqnzwpodl2v3qd5b3ksyjbjzqdtwli3xf35yugasad.onion/

I'd like to list <SITE NAME> there for free. You can submit it yourself at ./submit.sh,
or just reply and I'll add it.

Once listed, there's a rank badge you can put on your site (plain PNG, no JS).
No obligation to pay anything – boosts are optional.

Cheers,
OnionRANK
```

## 8. Co nedělat
- Nepropaguj na tržištích ani fórech s nelegálním obsahem.
- Nevkládej odkazy do cizích vláken bez souvislosti, nespamuj.
- Nepřidávej do žebříčku smyšlené weby ani falešné platby.
- Neodpovídej na provokace v komentářích – věcně, nebo vůbec.

## 9. Jak měřit úspěch (bez sledování návštěvníků)
- počet zápisů zdarma v `/admin`
- počet plateb (`CONFIRMED_TX` na hlavní stránce)
- reakce/zapy na Nostru a Stacker News
