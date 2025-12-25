# VM Verification Checklist — Odyssey

Purpose: A concise, operator-friendly checklist to verify the VM (`odyssey`) is healthy and ready to run Syndicate autonomously (daily reports, LLM worker, Discord bot, backups, and observability).

How to use: Run the checks below and mark each item as PASS / FAIL with timestamp and short notes. Aim for fully automated checks where possible; commands are provided.

---

## Quick health checks (daily)
- [ ] 1. Boot & systemd health
  - Command: sudo journalctl -b --no-pager | tail -n 200
  - Expected: No repeated service crashes; system boot within expected time.

- [ ] 2. Disk usage and inodes
  - Command: df -h / && df -i /
  - Expected: < 85% used on root; inodes not exhausted.

- [ ] 3. Available memory & CPU
  - Command: free -h && top -bn1 | head -n 10
  - Expected: No OOM events; swap usage acceptable (low).

- [ ] 4. Filesystem errors
  - Command: sudo dmesg -T | grep -i "ext4\|error\|I/O" || true
  - Expected: No recent filesystem I/O errors.

## Service-level checks (daily / after deploy)
- [ ] 5. LLM worker
  - Command: systemctl status syndicate-llm-worker.service --no-pager
  - Expected: Active (running). Check `journalctl -u syndicate-llm-worker.service -n 200` for errors.

- [ ] 6. Discord bot
  - Command: systemctl status syndicate-discord-bot.service --no-pager
  - Expected: Active (running); bot logs show connection to gateway and PID; no repeated "Command 'digest' already registered" errors.

- [ ] 7. Daily LLM report timer
  - Command: systemctl status syndicate-daily-llm-report.timer && systemctl list-timers --all | grep daily-llm || true
  - Expected: Timer active and last-run / next-run timestamps sane.

- [ ] 8. Prometheus & Grafana (if installed)
  - Commands: curl -sf http://localhost:9090/-/ready || true ; curl -sf http://localhost:3000/api/health || true
  - Expected: Services respond and report healthy status.

- [ ] 9. Healthcheck & retry services (if enabled)
  - Command: systemctl list-units --type=service 'syndicate-*' --no-pager
  - Expected: healthcheck and retry services either succeed or are intentionally disabled/masked when not installed.

## Application checks (weekly / on release)
- [ ] 10. Test run: Dry-run daily report
  - Command: /home/adam/.venv/bin/python -m digest_bot.daily_report --dry-run
  - Expected: Prints markdown report, exit code 0.

- [ ] 11. Test run: Post test alert (webhook)
  - Command: /home/adam/.venv/bin/python -m digest_bot.daily_report --dry-run --webhook <TEST_WEBHOOK_URL>
  - Expected: Webhook call succeeds and returns 200/204; check Discord ops channel for the message.

- [ ] 12. Disk cleanup policy
  - Command: sudo apt autoremove -y && sudo journalctl --vacuum-size=500M --vacuum-time=2weeks
  - Expected: Disk free space controlled; historical logs retained per retention policy.

- [ ] 13. Backup snapshot validation
  - Command: Validate latest backup/snapshot exists and restore test (dry-run) is possible.
  - Expected: Latest snapshot < 24h old for critical data dirs.

## Security & secrets
- [ ] 14. `.env` keys review
  - Action: Verify no secrets are accidentally committed. Ensure `DISCORD_WEBHOOK_URL`, API keys are in lxd/vault or systemd `EnvironmentFile` and have correct permissions (600).

- [ ] 15. GitHub Actions / Secrets
  - Action: Confirm `DISCORD_WEBHOOK_URL`, Pages deploy tokens, and any Notion keys are present in repo secrets and correct.

## Observability & Alerts
- [ ] 16. Prometheus metrics (LLM gauges)
  - Command: curl -sf http://localhost:8000/metrics | grep gost_llm || true
  - Expected: Metrics (gost_llm_queue_length, gost_llm_worker_running, gost_llm_tasks_processing, gost_llm_sanitizer_corrections_total) present.

- [ ] 17. Alert rules sanity
  - Action: Check `deploy/prometheus/syndicate_llm_rules.yml` is loaded into Prometheus & Alertmanager routes to the ops channel.

## Deployment & pages
- [ ] 18. GitHub Pages publish (changelog/site)
  - Action: Trigger `.github/workflows/publish-changelog.yml` with a test artifact or push; verify Pages updated under `artifactvirtual.com` (or GH pages URL) if DNS is configured.

- [ ] 19. Output snapshot publication
  - Command: Run `scripts/deploy_output_to_pages.sh` in dry-run mode (or dispatch `publish-output` workflow) and verify `gh-pages` branch gets updated with timestamped snapshot.

## Recovery & Runbook checks
- [ ] 20. Reboot resilience
  - Command: sudo reboot (schedule a test window or run a VM snapshot beforehand)
  - Expected: All essential services (LLM worker, Discord bot, daily report timer) auto-start and report healthy after reboot.

- [ ] 21. Incident runbook accessibility
  - Action: Confirm runbooks and incident response docs exist in repo (`docs/incident_response.md`) and that on-call contact is set in `README` or team handbook.

---

Notes:
- Record pass/fail with timestamp and short notes each time you run the checklist and push a short `vm-check` entry to the repo or a team log for auditability.
- Customize thresholds (disk %, memory) to your tolerance.

