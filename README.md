# 🇮🇳 India News Telegram Bot

> **First time here?** Follow **[`SETUP_GUIDE.md`](SETUP_GUIDE.md)** — the complete
> step-by-step: BotFather → channel → API key → first post → 24×7.

Collects India news (RSS + public Telegram channels + optional X API), removes
duplicates, classifies every story with an LLM, writes a **neutral 2–4 sentence
summary**, and posts it to your Telegram channel — 24×7, from your own PC.
No cloud server required.

Built from the plan in the shared ChatGPT conversation: local/self-hosted,
Telegram as the only publishing platform, free + premium (Telegram Stars) tiers.

## How it works

```
RSS / public Telegram channels / X (paid API)
        │
        ▼
Collectors (collectors/)
        │
        ▼
Duplicate removal (dedupe.py)            ← URL hash + fuzzy title match
        │
        ▼
LLM analysis (llm.py)                    ← DeepSeek (or local Ollama, see .env)
   • political framing of the source: left / right / neutral / mixed
   • topics (multi-label) + religion topic (only when the story itself is
     about religion — never inferred from people's identity)
   • importance: breaking / high / normal
   • neutral summary in English / Hindi / both
        │
        ▼
SQLite (db.py)  → best stories picked (breaking first, 24h cap)
        │
        ▼
Telegram channel (publisher.py) + bot commands (bot.py, long polling)
```

## Sources (all probed 2026-10)

| Type | Count | Notes |
|---|---|---|
| Websites | 11 | The Hindu, Indian Express, NDTV, HT, Times of India, Livemint, India Today, Zee News, Economic Times, Scroll.in, BusinessLine |
| YouTube | 8 | keyless channel RSS — India Today, NDTV World, ABP, WION, Firstpost, News18, Zee News, HT (title + link only) |
| Telegram | 8 | @indianexpress, @hindustantimes, @livemint, @indiatodayin, @cnnnews18, @scroll_in, @moneycontrolcom, @zeenews |
| X | optional | needs a paid API tier — set `X_BEARER_TOKEN` in `.env` |
| Instagram | — | no official free API; optional via your own RSSHub instance (see `feeds.yaml`) |

Re-verify any time: `python scripts/probe_feeds.py`, `scripts/probe_channels.py @handle`,
`scripts/probe_youtube.py @handle`.

## What you need before the first real run

| # | Requirement | Where to get it |
|---|---|---|
| 1 | Telegram **bot token** | Message @BotFather → `/newbot` (free, 2 min) |
| 2 | A **channel** with the bot added as admin ("Post messages") | Telegram app |
| 3 | Your **user id** (enables `/stats`, `/collect`) | Message @userinfobot |
| 4 | **DeepSeek API key** | platform.deepseek.com → API keys (cheap; or run fully local with Ollama — see `.env.example`) |
| 5 | Python 3.10+ | python.org (this machine is fine) |
| 6 | Optional: **X API** bearer token — requires a **paid** tier | developer.x.com |
| 7 | Phase 2 only: premium channel + Telegram Stars | README → Phase 2 below |

## Setup

```bat
cd india-news-bot
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Edit `.env` and fill in `TELEGRAM_BOT_TOKEN`, `TELEGRAM_FREE_CHANNEL`,
`DEEPSEEK_API_KEY` (and optionally `ADMIN_USER_ID`).

> Company PC note: `truststore` is already wired in (`main.py`) to fix
> `CERTIFICATE_VERIFY_FAILED` from HTTPS-inspecting proxies — the same fix
> used in the AIRREV project.

## Run

- **Quick test (no Telegram, no API key, no cost):** double-click `dry_run.bat`
  — collects real feeds, uses offline mock analysis, prints ready-to-send posts
  to the console. Great for checking formatting.
- **Post one cycle right now:** double-click `run_once.bat` (needs `.env` set up).
- **Brand the channel:** double-click `send_intro.bat` — posts and pins a
  welcome/intro message so the channel looks professional.
- **Real run:** double-click `run.bat` (or `.venv\Scripts\python.exe main.py`).
  Collects every `COLLECT_INTERVAL_MINUTES` and posts **one story every
  `PUBLISH_INTERVAL_MINUTES`** (5 min default) — steady pacing, no bursts,
  and a story that is already on the channel is never posted again.
- **Run it in the cloud (PC off):** see [`CLOUD_DEPLOY.md`](CLOUD_DEPLOY.md).

## Bot commands

| Command | What it does |
|---|---|
| `/start`, `/help` | Welcome + instructions |
| `/latest` | Last 8 published stories with links |
| `/stats` | Counts: collected / processed / published (admin only) |
| `/collect` | Run one pipeline cycle immediately (admin only) |
| `/premium` | Info about the premium tier |

## Configuration (`.env`)

| Variable | Default | Meaning |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | — | BotFather token (required) |
| `TELEGRAM_FREE_CHANNEL` | — | `@name` or `-100…` numeric id (required) |
| `TELEGRAM_PREMIUM_CHANNEL` | — | Phase 2 premium channel |
| `ADMIN_USER_ID` | — | Your user id for admin commands |
| `DEEPSEEK_API_KEY` | — | DeepSeek key (empty → mock mode) |
| `DEEPSEEK_BASE_URL` / `DEEPSEEK_MODEL` | `https://api.deepseek.com` / `deepseek-chat` | Any OpenAI-compatible endpoint (works with local Ollama: `http://localhost:11434/v1`, model `qwen3:4b`) |
| `LLM_MOCK` | `0` | `1` = offline heuristics, no API calls |
| `SUMMARY_LANGUAGE` | `en` | `en` / `hi` / `both` |
| `COLLECT_INTERVAL_MINUTES` | `15` | How often sources are collected and analyzed |
| `PUBLISH_INTERVAL_MINUTES` | `5` | Paced posting: one story every N minutes |
| `FREE_DAILY_CAP` | `300` | Safety cap on posts per rolling 24 h |
| `DEDUPE_THRESHOLD` | `0.87` | Fuzzy title-match threshold (higher = stricter) |
| `X_BEARER_TOKEN` | — | Enables the X collector (paid tier) |

Sources are edited in **`feeds.yaml`** (RSS URLs, Telegram channels, X accounts).
Before adding a Telegram channel, check it with
`python scripts/probe_channels.py @handle` — several official-looking handles
are squatted by ad/scam accounts and would flood your feed with junk.

## Make the channel look real

1. In the Telegram app, set the channel **name**, **photo** and description.
   Sample description to copy:
   > 🇮🇳 India news, 24×7 — AI-summarised from top sources, always linked.
   > Neutral summaries • Sources credited • Breaking alerts
2. Double-click **`send_intro.bat`** — posts a welcome message and pins it.
   (If pinning fails: give the bot the *Pin messages* admin right.)
3. Start posting: `run_once.bat` for one cycle, or `run.bat` to run 24×7.
4. Optional: tune `PUBLISH_INTERVAL_MINUTES` (5 = one post every 5 min) or
   `FREE_DAILY_CAP` (default 300).

## Growing subscribers

Built into the bot:
- **Paced posting** — one story every `PUBLISH_INTERVAL_MINUTES` (default 5 min)
  keeps the channel steadily active in subscribers' feeds (that is what drives views).
- **📤 Share + ➕ Invite buttons** on every post (added automatically after posting).
- **@handle in every post footer** — every forward carries your channel name.
- **Pinned welcome post** — explains the value and invites sharing.
- **No repeats** — a story already on the channel (same URL, similar title, or
  same event from another outlet) is never posted twice.

Growth playbook (do these from the app, they cost nothing):
1. Put the channel link `https://t.me/indian_news_nationalist` everywhere:
   WhatsApp status, Instagram/X bio, YouTube video descriptions.
2. Share breaking posts into relevant groups (where allowed) together with the
   channel link — the share button makes this one tap.
3. List the channel in Telegram directories (tgstat, telemetr, etc.); public
   channels also get indexed by Google.
4. Post consistently and keep summaries neutral + sourced — credibility is
   what makes people forward posts to friends.
5. Monetization comes after growth: keep the free channel strong, then launch
   the premium tier (Telegram Stars) — see Phase 2 below.

## Phase 2 — Premium tier: ₹25/month (implemented)

The premium channel is the **paid exclusive tier**:
- ⭐ **Full feed** — every analyzed story (the free channel gets the paced highlights)
- ⚡ **Early access** — premium batches publish continuously, ahead of the free pace
- 🗞 **Morning + evening digests** — exclusive roundups at 08:00 / 20:00 IST
- 🔁 Same duplicate-free guarantee as the free channel

**Billing is handled by Telegram Stars subscriptions**: the bot creates a
*paid invite link* (`createChatInviteLink` with `subscription_period` = 30 days
and `subscription_price` in Stars). Telegram charges the member monthly,
auto-renews, and pays out to the channel owner; members cancel anytime in the
Telegram app.

### Enable it (5 minutes)
1. Create a **private channel** (e.g. `India News — Premium`).
2. Add your bot as admin with **Post messages + Pin messages + Invite users via link**.
3. Put its id in `.env`: `TELEGRAM_PREMIUM_CHANNEL=-100...` (or `@username`).
4. Double-click **`premium_setup.bat`** — creates the monthly subscription link
   and saves `PREMIUM_INVITE_LINK` to `.env` automatically.
5. Restart the bot. `/premium` and `/subscribe` now hand out the join link, and the
   premium full feed + digests start automatically.

Pricing: `PREMIUM_PRICE_STARS=15` ≈ **₹25/month** (Telegram Stars sell for roughly
₹1.5–2 each in India; Telegram displays the exact local price). If
`createChatInviteLink` errors, the script prints the exact reason — usually a
missing admin right or paid content not enabled for the channel yet.

## Phase 3 — Video + scaling

- **Video:** add `FFmpeg` to generate thumbnails / compress clips, then send via
  `sendVideo` with a caption + source credit. Bot API uploads are limited to
  **50 MB** — larger videos need a self-hosted local Bot API server.
  **Only use footage you have rights to** (licensed, public domain, or your own
  explainers). For third-party stories: post the summary + link.
- **Scale:** if SQLite becomes a bottleneck, swap in PostgreSQL (articles) and
  Redis (queue); wrap the pipeline in Celery. `db.py` is the only file that
  touches storage, so the swap is contained.
- **Docker:** optional; a `python:3.12-slim` image running `main.py` is enough
  for a single-process deployment.
- **24×7 on Windows:** Task Scheduler ("At log on", restart on failure) or
  [NSSM](https://nssm.cc) to run `run.bat` as a service.

## Legal & platform rules (important)

- Don't re-upload copyrighted articles/videos — summary + source link is the
  safe pattern (that's what this bot does by default).
- Respect the terms of each source, X API rules, and Telegram's Bot/API ToS.
- If you take Stars payments: add a privacy policy + terms, and handle refunds.
- The classifier is a *framing* label of the source, not a truth verdict —
  the summary itself is written neutral on purpose, to avoid becoming a
  misinformation amplifier.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `Telegram sendMessage failed: Forbidden` | Bot is not an admin in the channel, or wrong `TELEGRAM_FREE_CHANNEL` |
| `CERTIFICATE_VERIFY_FAILED` | Already handled via `truststore`; if it persists, set `SSL_CERT_FILE` to the corporate root CA |
| Nothing gets collected | A feed moved — test URLs in `feeds.yaml` in a browser; some feeds also block non-browser clients occasionally |
| X collector logs "paid tier" | Expected: X's free tier can't read others' posts |
| PowerShell blocks scripts | Use the `.bat` files (execution-policy workaround, same as AIRREV) |
| Start fresh | Delete `newsbot.db` (and `dryrun.db` for dry runs) |
