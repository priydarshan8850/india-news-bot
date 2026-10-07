# 🐦 X Mode — Twitter/X posting, the affordable way

## Why not "the same as Telegram" every 5 min?

X's API is pay-per-usage (official rates, Oct 2026):

| Action | Cost |
|---|---|
| Post **with a link** | **$0.20** per post |
| Post **text-only** | **$0.015** per post |
| Welcome gift | **$20 free credits** after saving a card |

- 288 posts/day with links ≈ **$1,730/month** ❌
- 288 posts/day text-only ≈ **$130/month** ❌
- **X Mode: 15 text-only posts/day ≈ $6.75/month**, and the $20 free credits
  cover roughly the first **3+ months** ✅

## What X Mode does

- Runs inside the **same free GitHub robot** (the 5-minute chain)
- **Top stories only** — walks the same importance-sorted queue
- **Text-only tweets**: `🇮🇳 headline + 2-line summary + hashtags + Telegram pointer`
  (deliberately no URL — it keeps the cheap rate AND funnels followers to your Telegram)
- Paced: at most one tweet per `X_MIN_GAP_MINUTES` (default **60**), capped at
  `X_DAILY_LIMIT` (default **15**) per UTC day
- Skips gracefully if X refuses a tweet 3 times in a row

## Enable it (5 minutes)

1. Go to **console.x.com** and sign in with your X account (create one if needed).
2. Create a **Project → App**.
3. In the app's **Settings → User authentication settings**: set permission to
   **Read and write** — do this FIRST.
4. **Keys and tokens** → copy:
   - API Key & API Secret
   - Access Token & Access Secret (regenerate them *after* step 3)
5. **Billing** → save a payment card → you immediately get **$20 free credits**.
6. Give the 4 keys to your helper (or add them yourself as repository secrets:
   `X_API_KEY`, `X_API_SECRET`, `X_ACCESS_TOKEN`, `X_ACCESS_SECRET`).
7. That's it — the robot tweets the top stories automatically.

## Useful knobs (optional repo variables / secrets)

| Name | Default | Meaning |
|---|---|---|
| `X_HANDLE` | — | Your X @handle to feature in tweets (optional) |
| `X_FOOTER` | `📲 Full feed on Telegram: @indian_news_nationalist` | Line at the bottom of every tweet |
| `X_DAILY_LIMIT` | `15` | Max tweets per day |
| `X_MIN_GAP_MINUTES` | `60` | Minimum minutes between tweets |

To change a knob: repo → Settings → Secrets and variables → Actions → **Variables**,
or edit `queue/x_state.json` day counters if needed.

## Testing

- Repo → Actions → "Post queued news" → **Run workflow** — the run will also
  tweet if one is due; check the log lines starting with `Tweeted` / `X ...`.
- First tweet after enabling goes out on the next chain run (within ~5 minutes).
