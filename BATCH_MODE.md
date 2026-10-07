# 📦 Batch mode — news keeps posting even when your PC is off

```
PC ON (1 minute)                          GITHUB CLOUD (free, always on)
─────────────────                         ─────────────────────────────
collect + AI-analyse everything           every 5 minutes:
render ready-to-send posts          ─▶    take next post from queue/posts.json
stock queue + git push                    send it to your Telegram channel
                                          save cursor, commit, repeat
```

So: stock the queue once → GitHub posts one story every 5 minutes for as long
as the queue lasts (300 stories ≈ **25 hours**), while your PC can be off.

## Stock + ship the queue

1. **On the PC:** double-click **`push_queue.bat`**
   (exports every ready story into the queue, marks it in the database so it is
   never posted twice, commits and pushes to GitHub)
2. Done. GitHub takes it from there.

Top up any time by running `push_queue.bat` again — it only appends new stories.

## Keep it fully automatic (`auto_queue.bat`)

Double-click **`auto_queue.bat`** once (or just use `start_bot.bat`, which
starts it too): a helper then runs **every 20 minutes while the PC is on** —
it exports new stories and pushes them to GitHub automatically. You rarely
need `push_queue.bat` by hand any more.

The queue keeps a **~24 h stock** (288 stories): that is how long the cloud can
keep posting when the PC goes off, and it bounds how old the oldest queued
story can be when it is sent. New stories flow in as the stock drains.

Stop everything with `stop_bot.bat` (bot + auto-queue together).

## Good to know

| Topic | Detail |
|---|---|
| 💰 Cost | **₹0** — free on a public GitHub repository (no card, no bills) |
| ⏱ Timing | A self-sustaining ~5-minute chain (each run wakes the next) - independent of GitHub's delayed scheduler; cron kept as backup, throttle prevents double posts |
| 🔁 No repeats | Exported stories are marked in the local DB — the PC bot and future batches never repeat them |
| ♻️ 60-day rule | GitHub disables unused scheduled workflows — ours commits every send, so it stays alive |
| 👀 PC-on overlap | While the PC bot runs *and* the queue drains you may see up to ~2 posts / 5 min. The daily cap makes the PC bot pause automatically after an export |
| 📭 Empty queue | The workflow writes "Queue empty" in its log and waits; top up with `push_queue.bat` |
| 🌐 Full 24/7 | This posts from a stock queue. For 24×7 **collection** too, move everything to a tiny cloud VM — see `CLOUD_DEPLOY.md` (Oracle free tier = ₹0) |

## Files

- `queue/posts.json` — ready-to-send posts (public repo: headlines only, no secrets)
- `queue/state.json` — cursor: which post goes next
- `.github/workflows/post_queue.yml` — the every-5-minutes sender
- `scripts/export_queue.py` — stocks the queue from the local database
- `scripts/action_send_next.py` — executed by the GitHub runner
