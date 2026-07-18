# telegram-gpt-bot

A Telegram bot you can add to group chats. Mention it (`@yourbot what is...`) and it
streams a live-updating answer back from OpenAI. It also works as a normal DM bot.

## How it works

- Built with [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) (async, polling by default).
- On `@mention` in a group, or any message in a private chat, it sends a placeholder
  reply, then streams the OpenAI response and edits that message every ~1.2s as
  tokens arrive.
- Keeps a short rolling conversation history per chat in memory (lost on restart —
  swap in Redis/a DB later if you need persistence).
- Telegram bot privacy mode can stay **on** (default) — mentions and replies to the
  bot are always delivered even when the bot can't see every group message.

## 1. Create the bot and get credentials

1. Talk to [@BotFather](https://t.me/BotFather) on Telegram, run `/newbot`, and copy
   the token it gives you.
2. Get an API key from the [OpenAI dashboard](https://platform.openai.com/api-keys).
3. Add the bot to your group as a member (no admin rights needed).

## 2. Configure

```bash
cp .env.example .env
# then edit .env and fill in TELEGRAM_BOT_TOKEN and OPENAI_API_KEY
```

| Variable             | Required | Default                                  | Notes                                      |
|-----------------------|----------|-------------------------------------------|---------------------------------------------|
| `TELEGRAM_BOT_TOKEN`  | yes      | —                                          | From BotFather                             |
| `OPENAI_API_KEY`      | yes      | —                                          | From OpenAI dashboard                      |
| `OPENAI_MODEL`        | no       | `gpt-4o-mini`                              | Any chat-completions-capable model         |
| `HISTORY_LIMIT`       | no       | `10`                                       | Messages of context kept per chat          |
| `WEBHOOK_URL`         | no       | unset (polling mode)                       | Set to run in webhook mode instead         |
| `WEBHOOK_PORT`        | no       | `8080`                                     | Only used when `WEBHOOK_URL` is set        |

The bot's system prompt lives in [`bot/system_prompt.py`](bot/system_prompt.py), not
in an env var — edit the `SYSTEM_PROMPT` constant there to change the bot's
behavior/tone.

## 3. Run locally

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m bot.main
```

## 4. Deploy

### Docker (recommended)

```bash
docker compose up -d --build
```

This builds the image and runs the bot in polling mode using your `.env` file —
works on any VPS with Docker, no public URL or open ports required.

To run without compose:

```bash
docker build -t telegram-gpt-bot .
docker run -d --restart unless-stopped --env-file .env --name telegram-gpt-bot telegram-gpt-bot
```

### Plain VPS with systemd

```ini
# /etc/systemd/system/telegram-gpt-bot.service
[Unit]
Description=telegram-gpt-bot
After=network.target

[Service]
WorkingDirectory=/opt/telegram-gpt-bot
EnvironmentFile=/opt/telegram-gpt-bot/.env
ExecStart=/opt/telegram-gpt-bot/.venv/bin/python -m bot.main
Restart=always
User=telegram-gpt-bot

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now telegram-gpt-bot
```

### Platforms like Railway / Render / Fly.io

- Polling mode (default, no `WEBHOOK_URL` set) works out of the box — just set the
  env vars in the platform's dashboard and deploy the Dockerfile. No public port
  needed.
- If the platform requires a bound HTTP port, set `WEBHOOK_URL` to the app's public
  HTTPS URL and `WEBHOOK_PORT` to the port the platform expects; the bot will
  register a webhook and listen there instead of polling.

## Notes / limitations

- Conversation history is in-memory per process — restarting the bot clears it.
- Replies are truncated to Telegram's 4096-character message limit.
- Message edits are throttled to ~1 per 1.2s to stay well under Telegram's rate
  limits; adjust `EDIT_INTERVAL_SECONDS` in `bot/handlers.py` if needed.
