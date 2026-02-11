# Version roadmap

This document outlines planned versions and "done" criteria. We follow SemVer (MAJOR.MINOR.PATCH).

- MAJOR - incompatible changes (DB schema, API/JSON format, command protocol).
- MINOR - backward-compatible features and improvements.
- PATCH - fixes, stability, documentation.

Current project status: v1.2. Added category presets and admin commands (limits/logs/stats/backups/health-check) while keeping format/DB compatibility.

## 0.x - Pre-releases (internal milestones)
- 0.1 - Local generator and CLI - DONE  
  - Ollama, default model `phi3:mini`, JSON output, base prompt.  
  - Minimal HTTP client, generation service, CLI demo.
- 0.2 - Telegram skeleton - DONE  
  - aiogram 3.x, /start, simple flow: platform → data input → single generation.  
  - No DB, no file export.
- 0.3 - Storage and export - DONE  
  - SQLite: store last N generations per user.  
  - Export .txt and .csv to chat.
- 0.4 - Platforms and presets - DONE  
  - Ozon/WB/Etsy/Shopify profiles: limits, fields, hints.  
  - Style/length settings, basic validation of lengths and fields.
- 0.5 - Reliability and configuration - CURRENT  
  - Stable JSON parsing (retries/repair), timeouts/retries.  
  - .env configuration, logging, basic metrics.

## 1.x - MVP and improvements
- 1.0 - MVP (Ollama)  
  - Full Telegram flow with FSM: platform → style/length → data input → generation → export/retry.  
  - Local model via Ollama (`phi3:mini`), settings via .env.  
  - Export .txt/.csv, store last N generations in SQLite.  
  - Logs and deployment guide.
- 1.1 - Quality  
  - Streaming responses where possible, progress indicators.  
  - Prompt tuning per platform, resilient JSON (self-healing regeneration).  
  - Throttling/task queue, cancel request, input cache.
- 1.2 - UX and support  
  - Category templates/presets, RU/EN localization.  
  - Admin commands: limits, log view, stats export.  
  - SQLite backups, log rotation, health-check.

## 2.0 - Provider extensibility
- LLM provider abstraction: Ollama by default + option for Transformers/OpenAI-compatible backends.
- Runtime model switching, platform/model templates.
- If load grows: move generation to a separate HTTP service with a queue.

## 3.0 - Advanced capabilities
- Multimodality: extract features from photos (Qwen-VL/LLaVA) and auto-drafts.
- Bulk generation via CSV/Google Sheets, job progress, reports.
- Personalization: saved tones/templates/brand lexicon.

## Definition of Done
- 1.0: stable Telegram flow, export, SQLite, works on CPU-only with a quantized model, deployment docs.  
- 1.1: better UX/speed, no regressions in DB/format.  
- 2.0: extra providers without breaking flows; migrations documented.

## Release process
- Semantic Git tags: `vX.Y.Z`.
- CHANGELOG with concise bullets (Added/Changed/Fixed/Docs).
- For DB/format changes - migrations and instructions in `docs/migrations/` or release notes.
- Questions/ideas - raise tickets/issues per version.
