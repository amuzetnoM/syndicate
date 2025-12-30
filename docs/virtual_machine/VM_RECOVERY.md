# Syndicate VM Recovery Procedures

> **Last Updated:** 2025-12-30

This document provides step-by-step recovery procedures for common failure scenarios on the Syndicate VM.

---

## 🚨 Emergency Quick Reference

```bash
# Restart all services
sudo systemctl restart syndicate-daemon syndicate-executor syndicate-discord syndicate-sentinel

# Check what's running
sudo systemctl status syndicate-*

# View recent errors
sudo journalctl -p err -n 50 --no-pager
```

---

## Scenario 1: VM Rebooted / Services Not Running

### Symptoms
- No Discord bot activity
- No reports being generated
- Services appear stopped

### Recovery Steps

```bash
# 1. Check service status
sudo systemctl status syndicate-*

# 2. If services are disabled, enable them
sudo systemctl enable syndicate-daemon syndicate-executor syndicate-discord syndicate-sentinel

# 3. Start all services
sudo systemctl start syndicate-daemon syndicate-executor syndicate-discord syndicate-sentinel

# 4. Verify they're running
sudo systemctl status syndicate-daemon
```

---

## Scenario 2: LLM Tasks Stuck

### Symptoms
- Tasks showing `in_progress` for hours
- No new reports being generated
- Executor daemon spinning

### Recovery Steps

```bash
# 1. Diagnose
cd ~/syndicate
~/miniforge3/envs/syndicate/bin/python scripts/check_status.py

# 2. Reset stuck tasks
~/miniforge3/envs/syndicate/bin/python -c "
import sqlite3
conn = sqlite3.connect('data/syndicate.db')
c = conn.cursor()
c.execute(\"UPDATE llm_tasks SET status='pending' WHERE status='in_progress'\")
print(f'Reset {c.rowcount} tasks')
conn.commit()
"

# 3. Restart executor
sudo systemctl restart syndicate-executor
```

---

## Scenario 3: Database Corruption

### Symptoms
- SQLite errors in logs
- Services crashing with database errors

### Recovery Steps

```bash
# 1. Stop all services
sudo systemctl stop syndicate-daemon syndicate-executor syndicate-discord

# 2. Backup current database
cp ~/syndicate/data/syndicate.db ~/syndicate/data/syndicate.db.bak.$(date +%Y%m%d)

# 3. Run integrity check
sqlite3 ~/syndicate/data/syndicate.db "PRAGMA integrity_check;"

# 4. If check fails, restore from backup or recreate
# The daemon will recreate tables on startup if missing

# 5. Restart services
sudo systemctl start syndicate-daemon syndicate-executor syndicate-discord
```

---

## Scenario 4: Out of Memory (OOM)

### Symptoms
- Services killed unexpectedly
- `dmesg` shows OOM killer messages
- LLM loads but crashes during inference

### Recovery Steps

```bash
# 1. Check current memory
free -h

# 2. Check for OOM events
dmesg | grep -i oom | tail -20

# 3. Clear any cached files
sudo sync && sudo echo 3 > /proc/sys/vm/drop_caches

# 4. If persistent, consider:
# - Reducing LLM context window
# - Upgrading VM instance type
# - Adding swap space

# 5. Restart services
sudo systemctl restart syndicate-daemon syndicate-executor
```

---

## Scenario 5: Discord Bot Authentication Failed

### Symptoms
- `LoginFailure: Improper token` in logs
- Bot appears offline

### Recovery Steps

```bash
# 1. Check the current token format
grep DISCORD_BOT_TOKEN ~/syndicate/.env

# Token should start with: MTQ... (base64 encoded)
# If it looks like a hex string (a95844a...), it's invalid

# 2. Update the token if needed
nano ~/syndicate/.env

# 3. Restart Discord service
sudo systemctl restart syndicate-discord

# 4. Check logs for success
sudo journalctl -u syndicate-discord -n 50
```

---

## Scenario 6: Notion Publishing Disabled/Failing

### Symptoms
- No pages appearing in Notion
- `notion_sync` table empty

### Recovery Steps

```bash
# 1. Check if publishing is enabled
cd ~/syndicate
~/miniforge3/envs/syndicate/bin/python -c "
import sqlite3
conn = sqlite3.connect('data/syndicate.db')
c = conn.cursor()
c.execute(\"SELECT value FROM system_config WHERE key='notion_publishing_enabled'\")
print('Status:', c.fetchone())
"

# 2. Enable if disabled
~/miniforge3/envs/syndicate/bin/python -c "
import sqlite3
conn = sqlite3.connect('data/syndicate.db')
c = conn.cursor()
c.execute(\"INSERT OR REPLACE INTO system_config (key, value) VALUES ('notion_publishing_enabled', 'true')\")
conn.commit()
print('Enabled!')
"

# 3. Test Notion API
~/miniforge3/envs/syndicate/bin/python -c "
from scripts.notion_publisher import NotionPublisher
p = NotionPublisher()
print('API Key:', p.config.api_key[:20], '...')
print('Database:', p.config.database_id)
"

# If "API token is invalid" error:
# - Go to notion.so/my-integrations
# - Regenerate the integration token
# - Update NOTION_API_KEY in .env
# - Ensure integration is shared with target database
```

---

## Scenario 7: LLM Model Not Loading

### Symptoms
- `Model not found` errors
- Fallback to cloud providers

### Recovery Steps

```bash
# 1. Check model exists
ls -lh ~/.cache/syndicate/models/

# 2. Verify model path in .env matches
grep LOCAL_LLM_MODEL ~/syndicate/.env

# 3. If model is missing, re-download
cd ~/.cache/syndicate/models/
wget https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q4.gguf

# 4. Restart services
sudo systemctl restart syndicate-daemon syndicate-executor
```

---

## Scenario 8: Full System Recovery

For complete system recovery after catastrophic failure:

```bash
# 1. Clone repository
git clone <repo-url> ~/syndicate

# 2. Restore .env from secure backup
cp /path/to/backup/.env ~/syndicate/.env

# 3. Install dependencies
cd ~/syndicate
~/miniforge3/envs/syndicate/bin/pip install -e .

# 4. Deploy systemd services
for f in deploy/systemd/normalized/*.service deploy/systemd/normalized/*.timer; do
    sudo cp "$f" /etc/systemd/system/
done
sudo systemctl daemon-reload

# 5. Enable and start services
sudo systemctl enable syndicate-daemon syndicate-executor syndicate-discord syndicate-sentinel
sudo systemctl start syndicate-daemon syndicate-executor syndicate-discord syndicate-sentinel

# 6. Verify
sudo systemctl status syndicate-*
```

---

## Log Locations

| Log | Command |
|-----|---------|
| All Syndicate logs | `sudo journalctl -u 'syndicate-*' -n 100` |
| Daemon logs | `sudo journalctl -u syndicate-daemon -f` |
| Sentinel file log | `cat ~/sentinel.log` |
| System errors | `sudo journalctl -p err -n 50` |
