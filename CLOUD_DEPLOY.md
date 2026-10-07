# ☁️ CLOUD_DEPLOY — run the bot 24×7 without your PC

The bot is a single small Python process (collect → analyze → post every
5 minutes). Any always-on Linux box runs it; your PC can be switched off.

**Important rules for ANY option:**
- Run **only ONE instance** at a time. Two copies (e.g. local + cloud) cause
  `Conflict: terminated by other getUpdates` and flaky posting. Stop `run.bat`
  on your PC before the cloud copy starts.
- Secrets (`TELEGRAM_BOT_TOKEN`, `DEEPSEEK_API_KEY`) are set in the host's
  environment/variables panel — **never** commit `.env` to GitHub (already
  gitignored).
- Keep a **persistent disk** for SQLite (`DB_PATH`). Deploys with ephemeral
  storage would forget the story history → repeats would come back and the
  daily counter would reset.

First, put the project on GitHub (needed by Railway/Render):

```bat
cd "c:\Users\priyd\Desktop\lua files\india-news-bot"
git init
git add .
git commit -m "India news bot"
git remote add origin https://github.com/<you>/india-news-bot.git
git push -u origin main
```

---

## Option 1 — Railway (easiest, ~$5/month)

1. Create an account at **railway.app** (GitHub login works).
2. **New Project → Deploy from GitHub repo** → pick `india-news-bot`.
   Railway detects the `Dockerfile` automatically.
3. Open the service → **Variables** → add:
   ```
   TELEGRAM_BOT_TOKEN = 8747167872:AA...
   TELEGRAM_FREE_CHANNEL = @indian_news_nationalist
   DEEPSEEK_API_KEY = sk-...
   PUBLISH_INTERVAL_MINUTES = 5
   COLLECT_INTERVAL_MINUTES = 15
   DB_PATH = /data/newsbot.db
   ```
4. Service → **Settings → Volumes → Add volume**, mount path `/data`.
5. Deploy. In **Logs** you should see:
   `Bot is running (long polling).` then `Scheduled collect: ...`
6. Done — switch off your PC, posts keep coming.

## Option 2 — Oracle Cloud Always Free (₹0/month) — best free choice

**Cost: ₹0 forever.** A card is needed only for identity verification at signup
(nothing is charged if you stay on the Always Free resources). Latency: pick the
**Mumbai** home region for India.

1. Sign up at **cloud.oracle.com** → Home Region: **India West (Mumbai)**.
2. **Create the VM:** Menu → Compute → Instances → Create Instance
   - Name: `india-news-bot`
   - Image: **Ubuntu 24.04** (or 22.04)
   - Shape: **VM.Standard.A1.Flex** (Always Free) — 1 OCPU / 6 GB is plenty.
     If it errors with "out of capacity", retry later or choose
     **VM.Standard.E2.1.Micro** (x86, also Always Free).
   - Networking: keep defaults (public IP).
   - SSH keys: **Generate a key pair for me** → **download the private key** (`.key`).
   - Create, wait for state **Running**, copy the **Public IP**.
3. Put the project on the VM (pick ONE):
   - **GitHub:** push this project to GitHub, then on the VM run
     `git clone https://github.com/<you>/india-news-bot.git ~/india-news-bot`
   - **Or upload from your PC:**
     `scp -i <key-file> -r india-news-bot ubuntu@<PUBLIC-IP>:~/india-news-bot`
4. Connect from Windows PowerShell: `ssh -i <key-file> ubuntu@<PUBLIC-IP>`
   (first time: type `yes`), then:
   ```bash
   cd ~/india-news-bot
   bash deploy/oracle_setup.sh
   ```
   The script installs Docker, opens `.env` in an editor where you paste your
   3 secret lines (token, channel, DeepSeek key), then builds and starts the
   bot with auto-restart. It prints live logs at the end.
5. Reboot-proof: Docker + `restart: unless-stopped` bring the bot back
   automatically after VM reboots or crashes — 24×7 news checking.

## Option 3 — Any cheap VPS (Hetzner / DigitalOcean / Lightsail)

Same as Option 2 but a paid ~$4–6/month box; identical commands.

## Option 4 — Fly.io (CLI, small free allowance)

```bash
flyctl launch --no-deploy          # accept the Dockerfile it finds
flyctl volumes create botdata --size 1
flyctl secrets set TELEGRAM_BOT_TOKEN=... TELEGRAM_FREE_CHANNEL=@indian_news_nationalist DEEPSEEK_API_KEY=... DB_PATH=/data/newsbot.db
flyctl deploy
```
Mount the volume at `/data` when prompted (check `fly.toml` has a `[mounts]`
section with `source = "botdata"`, `destination = "/data"`).

---

## Verify after deploying

- Cloud logs show `Scheduled collect` / `Paced publish: one story posted`
  every few minutes.
- Your channel receives one post roughly every `PUBLISH_INTERVAL_MINUTES`.
- Bot `/stats` (as admin) shows counts increasing.

## Notes

- SQLite handles this workload easily (one writer, a few items/minute).
  If you ever run multiple channels or hires-volume pipelines, switch
  `db.py` to PostgreSQL — it is the only file that talks to storage.
- Deploys from Windows: the cloud builds the Docker image, so you don't need
  Docker installed locally.
