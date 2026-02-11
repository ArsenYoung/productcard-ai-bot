# ProductCard AI Bot - Implementation Plan (MVP)

This document covers the goal, MVP boundaries, architecture, project structure, dialog logic, prompting strategy, data model, configuration/deployment requirements, work stages, and acceptance criteria.

See also the release roadmap: `docs/ROADMAP.md`.

## 1) Goal and value proposition
- Generate fast, selling, SEO-optimized product listings for marketplaces (Ozon, Wildberries, Etsy, Shopify, etc.).
- Remove routine for sellers: title, description, keywords, SEO tags from a single request.
- Provide a ready-to-use tool for a commercial service and portfolio.

## 2) MVP scope
- Platforms in the UI: Ozon, Wildberries, Etsy, Shopify (logic and hints come from presets; strict platform rules live in config and can be extended).
- Generation: title, description, keywords, SEO tags based on product name and features.
- Style choices: selling / concise / expert (single switch in MVP).
- Length choices: short / medium / full.
- Export: text in chat + .txt and .csv files.
- Storage: keep the last N (default 5) generations per user in SQLite.
- Simple FSM: choose platform → enter data → choose style/length → generate → export/retry.

Out of scope for MVP (future):
- Extracting data from photos (keywords → description).
- Google Sheets API export.
- Brand-specific editing/fine-tuning and templates.

## 3) Tech stack
- Telegram Bot: aiogram 3.x (FSM, inline buttons, middlewares).
- NLP/LLM: local phi-3-mini-4k-instruct (via Ollama or Hugging Face Transformers). Optionally any OpenAI-compatible backend.
- Storage: SQLite (via `sqlite3`/`aiosqlite`), JSON cache if needed.
- Configuration: `python-dotenv` (.env).
- Export: standard I/O for .txt and .csv.
- Logging: built-in `logging` + optional file rotation.

## 4) Architecture and layers
- handlers/ - command/button handlers, scenario logic, FSM states.
- services/
  - `generation_service.py` - orchestration (prompt build, LLM call, post-processing).
  - `llm_client.py` - low-level client for phi-3 (via Ollama or Transformers) with a unified interface.
  - `export_service.py` - prepares text, .txt, and .csv.
- repositories/ (or storage/)
  - `sqlite_repo.py` - users, sessions, generations (async CRUD).
- keyboards/ - inline buttons: platform, style, length, export.
- states/ - FSM states (e.g., `GenerationStates`).
- config/
  - `config.py` - .env reading, constants, marketplace profiles.
- utils/
  - `validators.py` - basic validation (length limits, required fields).
  - `text.py` - shared text helpers (truncate, slug, etc.).

Flow in words: Telegram ↔ aiogram.handlers → services.generation_service → services.llm_client → phi-3 → services.export_service → aiogram → user. Data is persisted through repositories.sqlite_repo.

## 5) Dialog logic (FSM)
Minimal finger-friendly script:
1. /start → greeting + platform choice [Ozon] [Wildberries] [Etsy] [Shopify].
2. After platform → prompt: "Enter name and features" (single message, free text).
3. Ask for style: [Selling] [Concise] [Expert].
4. Ask for length: [Short] [Medium] [Full].
5. Generate → show result blocks: Title, Description, Keywords, SEO tags.
6. Export: [Send .txt] [Send .csv] [Generate again] [Change platform].

Cancel handling: "Back" button at each step (or /cancel).
Throttling: limit generation frequency per user and global rate (configurable).

## 6) Marketplace profiles (config)
Store soft limits and hints in a dictionary so they are not hardcoded:
```python
MARKETPLACE_PROFILES = {
  "Ozon": {
    "title_max": 120,
    "desc_target": "medium",
    "keywords_sep": ", ",
    "locale": "ru",
    "style_hint": "business, clear, no spam"
  },
  "Wildberries": {
    "title_max": 120,
    "desc_target": "medium",
    "keywords_sep": ", ",
    "locale": "ru",
    "style_hint": "short, to the point, benefits"
  },
  "Etsy": {
    "title_max": 140,
    "desc_target": "medium",
    "keywords_sep": ", ",
    "locale": "en",
    "style_hint": "friendly, handmade, benefits"
  },
  "Shopify": {
    "title_max": 150,
    "desc_target": "medium",
    "keywords_sep": ", ",
    "locale": "en",
    "style_hint": "conversion-focused, clean"
  }
}
```
Note: actual limits depend on real platform rules. In the MVP they are "soft" goals and hints; strict validation is optional.

## 7) Prompting strategy (phi-3-mini-4k-instruct)
phi-3 is an instruction-tuned causal LM (not chat-native), so use a single-turn prompt and demand strict JSON output.

Call structure:
- Instructions: roles and constraints (language, style, length, platform, bans).
- Input: "name + features" as one line from the user.
- Output format: exactly one JSON object, no explanations or backticks.

Required JSON format:
```json
{
  "title": "...",
  "description": "...",
  "keywords": ["...", "..."],
  "seo_tags": ["...", "..."]
}
```

Prompt template (English):
```
You are an assistant that creates marketplace product cards. Write in {locale}.
Style: {style}. Length: {length}. Platform: {platform} ({style_hint}).
Title up to ~{title_max} characters. Avoid banned promises, spam, and ALL CAPS.
Return EXACTLY one JSON object with fields: title, description, keywords[], seo_tags[].
No explanations, no backticks, no prefixes. If unsure, make reasonable assumptions.

User input:
{title_and_attrs}
```

Suggested generation params:
- max_new_tokens: 600-800 (for "medium" description)
- temperature: 0.4-0.7
- top_p: 0.9
- stop: if needed (for example, on double newline after JSON)

Post-processing:
- Validate and safely parse JSON; on failure, retry with "return only JSON" reminder.
- Trim title if it exceeds the platform profile.
- Normalize and deduplicate keywords/seo_tags.

Resource control:
- Keep prompts concise; limit max_new_tokens.

### 7.1) Local phi-3 integration: options

Option A - Ollama (simple and convenient):
- Install by the Ollama docs.
- Pull the model: `ollama pull phi3:mini` (alias for phi-3-mini-4k-instruct).
- Smoke test: `ollama run phi3:mini "Say ok"`.
- Bot config:
  - `LLM_PROVIDER=ollama`
  - `LLM_MODEL=phi3:mini`
  - `LLM_BASE_URL=http://localhost:11434`
- HTTP request (non-stream):
```http
POST /api/generate HTTP/1.1
Host: localhost:11434
Content-Type: application/json

{
  "model": "phi3:mini",
  "prompt": "<prompt from section 7>",
  "stream": false,
  "options": { "temperature": 0.6, "num_predict": 800 }
}
```
- Response: `response` holds the text; then parse JSON.

Option B - Hugging Face Transformers (max control):
- Dependencies: `pip install transformers accelerate torch` (+ optionally `bitsandbytes` for 4-bit on GPU).
- Model/tokenizer: `microsoft/Phi-3-mini-4k-instruct`.
- Inference pseudocode:
```python
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

name = "microsoft/Phi-3-mini-4k-instruct"
tok = AutoTokenizer.from_pretrained(name)
model = AutoModelForCausalLM.from_pretrained(
    name, torch_dtype=torch.float16, device_map="auto"
)

prompt = build_prompt(...)  # template from section 7
inputs = tok(prompt, return_tensors="pt").to(model.device)
out = model.generate(
    **inputs,
    max_new_tokens=800,
    temperature=0.6,
    do_sample=True,
    top_p=0.9,
)
text = tok.decode(out[0], skip_special_tokens=True)
payload = safe_parse_json(text)
```
- Bot config: `LLM_PROVIDER=transformers`, `LLM_MODEL=microsoft/Phi-3-mini-4k-instruct`.

Performance and resources:
- CPU works but slower; GPU is preferred when available.
- Reduce `max_new_tokens` and `temperature` for faster, more stable runs.
