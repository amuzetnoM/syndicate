# Syndicate — Autonomous Social Media Strategy

Last updated: 2025-12-24

This document describes a fully autonomous, quota-safe, low-cost social media publishing system for Syndicate. It is written to run as a detached process, integrated with the existing pipeline (digests, insights, charts, and report outputs) while minimizing external API quota usage.

Goals
- Reliable, hands-off operation with predictable throughput (e.g. 1–2 posts/day per platform).
- Polished, high-signal content: research notes, short analyses, charts, threadable insights, and evergreen articles.
- Quota-resilient architecture: local generation where possible, graceful degradation, and multi-provider fallbacks for networked services.
- Use free tiers and self-hosted options primarily; avoid paid API dependence except where unavoidable and provide throttling/fallbacks.

Overview
- Ingest: existing outputs in `output/` and `archives/` (reports, charts, digest summaries).
- Content generator: local LLM (llama, Ollama) prioritized; cloud Gemini only as tertiary fallback. Templates + sanitizer produce final post text.
- Media: generate images locally (matplotlib/plotting) or use deterministic chart renders; optional AI image generation using local models (Stable Diffusion local) if desired — avoid remote image APIs to reduce quota issues.
- Scheduler: lightweight scheduler (cron/systemd timer) with rate-limit guard and DB-based fingerprint dedupe (store in `discord_messages` / new `social_posts` table).
- Publisher: modular platform adapters — Twitter/X, Mastodon, LinkedIn, Threads — prefer platforms with permissive free APIs (Mastodon federated servers, X via community clients with rate limits). Push with webhooks where available.

Architecture

- Data Sources
  - Daily digests (`output/reports/*`), LLM insights (`src/digest_bot`), charts (`output/charts`), and historical archives.

- Content Pipeline
  1. Discover: a small worker scans `output/` for new artifacts (file watcher or scheduled scan).
  2. Extract: extract key points, numeric highlights, and chart references using existing `daily_report` and `writer` logic.
  3. Draft: create multiple candidate posts using a local LLM provider (Ollama or local GGUF model) with strict templates (length, hashtags, CTA, tone).
  4. Sanitize: run the existing sanitizer to validate numbers, dates, and claims; mark any draft needing human review.
  5. Render: attach images/charts (static renders from `charts/`) and format threads (1–4 posts with references).
  6. Dedupe & Fingerprint: compute SHA256 fingerprint (source+template+images) and check `social_posts` DB table to avoid duplicates.
  7. Queue & Rate-limit: enqueue to publisher with delay windows; paused if provider quotas near limits.

- Publishing Adapters (modular)
  - Mastodon (preferred for free, high throughput): activitypub adapters exist and can post to self-hosted instances.
  - X/Twitter: use community libraries with backoff and conservative pacing; keep content batches small.
  - LinkedIn/Threads: optional; treat as lower-frequency channels (weekly).
  - Logging: every outgoing post is recorded (platform, post_id, fingerprint, payload_hash, sent_at) in DB for audit and possible resend.

Quota & Rate-Limit Strategy
- Prefer local generation (Ollama/local) to avoid cloud LLM costs.
- Limit posts to 1–2/day per platform; use jittered timers and scheduled windows (e.g. 09:00 and 17:00 UTC).
- Maintain counters in DB: per-platform sends/day and per-hour to enforce limits.
- Implement graceful fallback: if a platform rejects (429 or quota) then postpone and try alternate channel or reduced content (text-only).
- Backoff policy: exponential up to a configurable ceiling; add operator alerts via Discord only when persistent failures occur.

Content Quality & Templates
- Post categories: Quick Insight (1–2 sentences + chart), Threaded Analysis (3–6 tweets/parts), Research Note (longer LinkedIn/Medium), Snapshot (daily market numbers + short commentary).
- Always include: concise title, 1–2 highlighted metrics, an interpretive sentence, and an optional link to the Notion report or full article (Notion links gated by frontmatter). Avoid ambiguous claims.
- Hashtags: curated small set per post (max 3). Use deterministic hashtag generation from categories (e.g. #Gold #Macro #Comex).
- Images: use deterministic chart renders (no generative imagery unless local SD is available). Ensure images are pre-sized, optimized, and stored under `output/social/`.

Safety & Compliance
- Sanitizer is mandatory: any numeric claims must be validated against canonical data or omitted.
- No automatic posts flagged as draft or with frontmatter `publish_to_social: false`.
- Create a quarantine queue for drafts that fail sanitizer: operator review required before publish.

Operational Details
- DB tables: add `social_posts` (platform, fingerprint, payload_hash, sent_at, status, external_id).
- Admin UI / CLI: `scripts/social_preview.py` to preview payloads, and `scripts/social_send.py --platform mastodon --dry-run` for safe tests.
- Monitoring: expose `gost_social_posts_sent_total` Prometheus metric and alerts for repeated failures or quota hits.
- Systemd: run social worker as `syndicate-social.service` with safe restart/backoff and `DISABLE_SOCIAL_PUBLISH` env toggle for emergency pause.

Implementation Plan (minimum viable)
1. Add `src/social/worker.py` that scans `output/` and produces post candidates via local LLM.
2. Add `scripts/social_preview.py` for local preview and `scripts/social_send.py` for sending/dry-run.
3. Add `social_posts` DB schema and helpers in `db_manager.py`.
4. Integrate fingerprint dedupe logic reusing digest/discord code paths.
5. Create `systemd` unit `syndicate-social.service` and add scheduling (daily windows).
6. Configure Prometheus metrics and Grafana panels for social activity.

Optional: Low-cost media generation
- If richer imagery is desired, use local Stable Diffusion (AUTOMATIC1111 or Diffusers local) with deterministic seeds; fall back to static charts only when GPU resources are absent.

Privacy & Account Management
- Store credentials (API keys / tokens) only in host `.env` and restrict file permissions. Rotate keys regularly.
- Use separate accounts for production posting; store operator contact for emergency kill-switch.

Maintenance & Human-in-the-loop
- Set up weekly operator digest summarizing social sends, failures, and flagged drafts.
- Provide a manual override CLI for resending, editing, or canceling queued posts.

Conclusion

This strategy focuses on safety-first autonomous posting: local generation, strong sanitization, minimal external API dependence, deterministic imagery (charts), and strict rate-limit enforcement. It is designed to be robust against quota fluctuations and to produce polished, consistent content twice daily while remaining fully auditable and reversible.
