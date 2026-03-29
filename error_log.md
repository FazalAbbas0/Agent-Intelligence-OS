# Error Log

## Project
Agent-Intelligence-OS

## Date
March 29, 2026

## Summary
This log records the latest runtime/sync issues seen in production runs, root causes, and the applied fixes after the final stability pass.

## Error History

### 1) Notion API method mismatch
- Symptom:
  - `'DatabasesEndpoint' object has no attribute 'query'`
- Root cause:
  - `notion-client` version `3.0.0` no longer supports `databases.query`.
  - Query operations moved to `data_sources.query`.
- Resolution:
  - Updated sync logic to use `notion.data_sources.query`.

### 2) Wrong Notion object type
- Symptom:
  - `Provided database_id ... is a page, not a database`
- Root cause:
  - The configured ID pointed to a page, not a database/data source.
- Resolution:
  - Added validation and normalization for Notion IDs.
  - Added support for explicit `NOTION_DATA_SOURCE_ID`.

### 3) Database not found by integration
- Symptom:
  - `Could not find database with ID ...`
- Root cause:
  - Target database/data source was not visible to the integration, or wrong ID was used.
- Resolution:
  - Shared target with integration `Agent Intelligence Engine`.
  - Set `NOTION_DATA_SOURCE_ID` to a valid shared data source ID.

### 4) Repeated per-entry write errors
- Symptom:
  - Large number of repeated `Entry Error` lines for each row.
- Root cause:
  - Script continued writes after configuration-level failure.
- Resolution:
  - Added fail-fast configuration check before row loop.

### 5) Windows console Unicode logging errors
- Symptom:
  - `UnicodeEncodeError: 'charmap' codec can't encode character ...`
- Root cause:
  - Emoji characters in log messages were incompatible with default Windows console code page.
- Resolution:
  - Replaced emoji-prefixed status strings with ASCII-safe log/output prefixes.

### 6) NaN conversion failure during Notion payload build
- Symptom:
  - `cannot convert float NaN to integer`
- Root cause:
  - Missing context window values were cast directly to `int`.
- Resolution:
  - Added safe null/NaN handling with default `Context Window = 4096`.
  - Added safe fallback for `Review Score`.

### 7) Notion schema mismatch on Industry/Quantization
- Symptom:
  - `Industry is expected to be multi_select`
  - `Quantization is not a property that exists`
- Root cause:
  - Payload assumed fixed property types and presence.
- Resolution:
  - Added live schema introspection via `notion.data_sources.retrieve(...)`.
  - Made `Industry` type-adaptive (`multi_select` or `select`).
  - Send `Quantization` only when the property exists.

### 8) Gemini SDK deprecation warning
- Symptom:
  - FutureWarning for `google.generativeai` deprecation.
- Root cause:
  - Current implementation uses deprecated Gemini SDK package.
- Resolution:
  - Non-blocking for runtime; script still executes.
  - Pending enhancement: migrate to `google.genai` SDK.

### 9) Architect enrichment not filling Docker/Gumroad columns
- Symptom:
  - `Docker Payload` and `Gumroad Copy` stayed blank for top architect candidates.
- Root cause:
  - Existing rows were skipped by de-dup logic before enrichment update step.
- Resolution:
  - Added Architect-Force flow:
    - Existing non-architect rows: `[SKIPPED]`
    - Existing architect rows: update blank rich_text columns via `notion.pages.update(...)`
    - New rows: create via `notion.pages.create(...)`

### 10) Notion API resilience gaps during create/update
- Symptom:
  - A single API failure could reduce visibility into why a row failed.
- Root cause:
  - Generic exception handling was too broad around Notion write operations.
- Resolution:
  - Added targeted `APIResponseError` handling for both create and update.
  - Error logs now include action, model, status, and code.

### 11) Rich text payload length risk
- Symptom:
  - Potential `Value too long` errors for long Gemini outputs.
- Root cause:
  - Rich text chunking was not explicitly constrained to Notion's strict per-block limit.
- Resolution:
  - `_build_rich_text_blocks` now strictly chunks to `<= 2000` characters per block.

### 12) Gemini model availability mismatch (active)
- Symptom:
  - `404 models/gemini-1.5-flash is not found for API version v1beta...`
- Root cause:
  - Model alias availability differs by Gemini endpoint/version/project.
- Resolution:
  - Added model fallback sequence:
    - `gemini-1.5-flash`
    - `gemini-1.5-flash-latest`
  - If all fail, sync continues without crashing.

## Current Status
- Sync script compiles and executes successfully.
- Hugging Face fetch, Notion resolve, and schema-aware sync are working.
- Architect-Force flow is implemented (existing top candidates are processed for enrichment updates).
- Progress logging now uses `[SKIPPED]`, `[ENRICHING EXISTING]`, and `[CREATED NEW]` for clear 09:00 run visibility.
- Startup environment warnings now surface missing `HF_TOKEN` / `GEMINI_API_KEY`.
- Current observed run state:
  - New records can still be added (`Added 23 new records` observed).
  - Existing architect updates may remain `Updated 0` when Gemini generation fails due to model 404.

## Prevention Notes
- Prefer `NOTION_DATA_SOURCE_ID` for `notion-client>=3.0.0`.
- Validate integration sharing before first sync.
- Treat Notion property types as dynamic and inspect schema at runtime.
- Guard all numeric casts from NaN/null.
- Keep logs ASCII-safe for Windows terminals.
- Keep Notion rich_text chunks at `<= 2000` chars.
- Handle `APIResponseError` separately for clear 400/429 diagnostics.
- Verify Gemini model availability in the target API version and project before production runs.
- Rotate exposed secrets immediately if `.env` values were shared.
