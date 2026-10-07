# 🚀 SETUP GUIDE — from zero to a live news channel (do it yourself)

Total time: ~10 minutes. You need: your phone/PC with Telegram, this PC, and the
project folder (`india-news-bot`).

> The only steps a machine cannot do for you are Telegram's own account actions
> (creating the bot, the channel). Everything else — collecting, AI summaries,
> posting, pinning — is handled by this project. Never share your bot token or
> API key with anyone; they go ONLY into `.env`.

---

## Part A — Create your Telegram bot (2 min)

1. Open Telegram, search for **@BotFather** (the one with the blue checkmark) and open it.
2. Send `/newbot`
3. It asks for a **name** → reply, e.g. `India News Bot` (this is the display name).
4. It asks for a **username** → reply, e.g. `my_india_news_bot`
   - Username must be unique and MUST end in `bot`.
   - If taken, try another (`my_india_news_24_bot`, …).
5. BotFather replies with a token like:
   ```
   8123456789:AAF-abc123ExampleTokenDoNotShare
   ```
   **Copy it. This is your `TELEGRAM_BOT_TOKEN`.** If it leaks later: send
   `/revoke` to @BotFather to get a new one.

Optional polish (nice so the bot looks real when people open it):
- `/setdescription` → e.g. `India news 24×7 — AI-summarised, always linked.`
- `/setabouttext` → same idea
- `/setuserpic` → upload a logo

Recommended — set the bot's command menu: send `/setcommands` to BotFather,
pick your bot, then paste this whole block:
```
start - Welcome and instructions
help - How the bot works
latest - Last published stories
premium - About the premium channel
stats - Bot statistics (admin only)
collect - Run one collection cycle (admin only)
```

---

## Part B — Create the channel and connect the bot (3 min) — click by click

Everything in this part happens in **YOUR Telegram app** (phone or desktop).
A bot cannot do it — Telegram requires a human account to create a channel.

### Step 1: Create the channel
1. Open Telegram.
2. Find "New Channel" in your app:
   - **Phone (Android):** tap **☰** (top-left) → **New Channel**
   - **Phone (iPhone):** tap the **✏️ icon** (top-right) → **New Channel**
   - **Desktop:** click **☰** (top-left) → **New Channel**
3. Channel name → type `India News Nationalist` → tap **Next / →**
4. Description (optional) → e.g. `India news 24×7 — AI-summarised from top sources, always linked.` → tap **Next**
5. Choose **Public Channel** → type the link name: `indian_news_nationalist`
   (the app previews `t.me/indian_news_nationalist`).
   If it says *already taken*: try `india_news_nationalist`, `indianews_24x7`,
   or add a number, e.g. `indian_news_nationalist7`.
   *(Private channel also works — then skip the link and see step 3 below.)*
6. Tap **Create** (✓ / paper-plane). The channel now exists.

### Step 2: Add YOUR bot as administrator
1. Open the channel you just created.
2. Tap the **channel name at the very top** → the channel info page opens.
3. Tap **Administrators**.
4. Tap **Add Admin** (may say "Add Administrator").
5. In the search box type your bot's exact username:
   **`@indian_news_nationalist_bot`**
   → it appears with a little **bot** badge → tap it.
6. Turn ON these two switches (nothing else needed):
   - ✅ **Post Messages** (lets the bot publish news)
   - ✅ **Pin Messages** (lets the bot pin the welcome post)
7. Tap the **✓** (top-right corner) to save. Done!

### Step 3: Continue
- **Public channel:** its reference is `@indian_news_nationalist`
  (whatever link you set in step 1.5) — put it in `.env` as
  `TELEGRAM_FREE_CHANNEL=@indian_news_nationalist`
- **Private channel:** just run `python scripts/check_bot.py` — the moment the
  bot is added as admin, the channel (with its `-100…` id) appears there.
  Put that id into `.env` as `TELEGRAM_FREE_CHANNEL=-1001234567890`
  (if it doesn't show up, post any message in the channel, then re-run).

---

## Part C — Get a DeepSeek API key (optional, recommended) (2 min)

Without a key the bot still works, but summaries come from the offline mock
heuristics. For real AI summaries:

1. Go to **platform.deepseek.com** → sign up → open **API Keys**.
2. **Create new API key** → copy it (starts with `sk-`).
3. If the account requires credit, add a small top-up. Per-article cost is a
   fraction of a cent.
4. *(Fully-local alternative: install Ollama, `ollama pull qwen3:4b`, and use
   the commented Ollama values in `.env.example` — no key needed.)*

---

## Part D — Fill in `.env` (1 min)

Open this file in an editor (VS Code or Notepad):

```
c:\Users\priyd\Desktop\lua files\india-news-bot\.env
```

Fill it like this (your real values):

```ini
TELEGRAM_BOT_TOKEN=8123456789:AAF-abc123ExampleTokenDoNotShare
TELEGRAM_FREE_CHANNEL=@my_india_news

DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat

SUMMARY_LANGUAGE=en
COLLECT_INTERVAL_MINUTES=15
FREE_DAILY_CAP=15
```

Optional lines (uncomment / add when you want them):

| Variable | What it does |
|---|---|
| `ADMIN_USER_ID=123456789` | Enables `/stats` and `/collect` for you (get your id from **@userinfobot**) |
| `TELEGRAM_PREMIUM_CHANNEL=@my_premium` | Phase 2 premium channel |
| `LLM_MOCK=1` | Force offline summaries (test without spending) |
| `SUMMARY_LANGUAGE=hi` or `both` | Hindi or bilingual summaries |
| `X_BEARER_TOKEN=...` | Enable X/Twitter collection (paid X API tier) |

Save the file. **Tip for the very first live test:** set `FREE_DAILY_CAP=3`,
then raise it to 15+ once you like how it looks.

---

## Part E — Run it (end to end)

Run these in order. Double-click the `.bat` files (they create the Python
environment on first run — a console window will install packages once).

| Step | Double-click | What happens |
|---|---|---|
| 1 | `dry_run.bat` | **No Telegram, no cost.** Collects real news, prints ready-to-send posts in the console so you can check formatting. |
| 2 | `send_intro.bat` | **First live write.** Posts a welcome message to your channel and pins it. If this works, your token + admin setup are correct. |
| 3 | `run_once.bat` | **One real cycle now.** Collects → AI-analyzes → publishes up to your daily cap. Check your channel! |
| 4 | `run.bat` | **24×7 mode.** Collects every `COLLECT_INTERVAL_MINUTES` and posts one story every `PUBLISH_INTERVAL_MINUTES` (5 min). Keep the window open — or deploy to the cloud: [`CLOUD_DEPLOY.md`](CLOUD_DEPLOY.md). |

Verify inside Telegram:
- Your channel shows the pinned intro + news posts with the source link.
- Open a private chat with your bot → `/start`, then `/latest` (shows recent stories).

> ⚠️ Only run ONE instance at a time. Two copies at once cause
> `Conflict: terminated by other getUpdates` and posting becomes unreliable.

---

## Part F — Run 24×7 automatically (optional)

Keep the PC on and connected. Two options:

**A. Simplest:** leave `run.bat` open (minimised).

**B. Auto-start with Windows:**
1. Start menu → **Task Scheduler** → **Create Task** (not "Basic").
2. General: name `India News Bot`; select *Run only when user is logged on*.
3. Triggers → New → Begin the task: **At log on**.
4. Actions → New → Start a program:
   - Program: `C:\Users\priyd\Desktop\lua files\india-news-bot\run.bat`
   - Start in: `C:\Users\priyd\Desktop\lua files\india-news-bot`
5. Settings → check **If the task fails, restart every: 1 minute**.
6. OK. (For a true Windows service without a window, see NSSM — README links.)

---

## Part G — Premium tier: ₹25/month (optional, after the free channel works)

What premium members get: **every story** (not just the paced highlights),
**early access**, and **morning + evening digests** — all billed by Telegram
auto-renewing monthly.

1. Telegram → **New Channel** → choose **Private** → name `India News — Premium`.
2. Add your bot (**@indian_news_nationalist_bot**) as admin with:
   ✅ **Post messages**  ✅ **Pin messages**  ✅ **Invite users via link**
3. Get the channel id: forward any message from that channel to **@userinfobot**
   → copy the `-100...` id.
4. Open `.env` and set:
   `TELEGRAM_PREMIUM_CHANNEL=-100...`
   (`PREMIUM_PRICE_STARS=15` ≈ ₹25/month — change if you like.)
5. Double-click **`premium_setup.bat`** → it creates the monthly Stars
   subscription link and saves it to `.env` automatically.
6. Restart the bot (`run.bat`). In chat with the bot, `/premium` and `/subscribe`
   now give the join link. Telegram collects the ₹25 (~15 Stars) monthly, renews
   automatically, and members can cancel anytime in their app.

Notes: if `premium_setup.bat` prints an error, it tells you the exact reason —
usually the *Invite users via link* admin right or paid content not enabled for
the channel yet. Revenue accrues in Stars to the channel owner and follows
Telegram's payout schedule (check the official Stars docs for current terms).

## Part H — Troubleshooting

| Symptom | Fix |
|---|---|
| `Forbidden: bot is not a member of the channel chat` | Add the bot as channel admin with **Post messages** |
| `chat not found` | Wrong handle — it must match the t.me link exactly; private channels need the `-100…` id |
| Posts not appearing, but cycle runs | Daily cap reached (check `/stats` in the bot, or raise `FREE_DAILY_CAP`) |
| `401 / invalid api key` (DeepSeek) | Fix the key in `.env`, or set `LLM_MOCK=1` to keep running offline |
| `Conflict: terminated by other getUpdates` | You have two instances running — close one |
| `CERTIFICATE_VERIFY_FAILED` | Already handled via `truststore`; on odd networks set `SSL_CERT_FILE` to your corporate root CA |
| `python` not recognised | Install Python 3.10+ from python.org and tick **Add python.exe to PATH** |
| PowerShell refuses scripts | Use the `.bat` files (already the pattern on this PC) |
| Token leaked anywhere | @BotFather → `/revoke` → paste the new token into `.env` |

---

## The whole flow in one picture

```
You (once):  BotFather → token ──┐
             Channel + bot admin ┤
             DeepSeek key ───────┤
                                 ▼
                          .env  (your secrets only)
                                 ▼
dry_run.bat → send_intro.bat → run_once.bat → run.bat (24×7)
                                 ▼
             Channel: pinned intro + AI news posts
             Bot: /start /latest /stats /collect /premium
```

Next (optional): premium tier with monthly **Telegram Stars** and video posts —
see the README sections *Phase 2* and *Phase 3*.
