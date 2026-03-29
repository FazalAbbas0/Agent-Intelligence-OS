# Agent-Intelligence-OS

Automates syncing trending Hugging Face agent models into a Notion data source, with optional Gemini-powered business packaging for top models.

## Features
- Fetches top Hugging Face models tagged as agent-related.
- Extracts and maps metadata to Notion properties:
  - Industry
  - Quantization (GGUF/AWQ/EXL2)
  - Context Window
  - Review Score
- Avoids duplicate inserts using existing `Model ID` values.
- Supports Notion `data_sources` API (`notion-client` v3).
- Uses schema-aware Notion payloads (auto-handles `Industry` as `select` or `multi_select`).
- Sends `Quantization` only when that property exists in Notion.
- Optional Architect mode (Gemini 1.5 Flash) for top models:
  - Docker and no-code setup
  - Freelance gig copy
  - Golden prompt
  - Client objection FAQ
  - Gumroad copy
- Adds rate limiting (`time.sleep(1)`) to reduce Notion 429 risk.
- Writes operational logs to `metadata/factory_health.log`.
- Includes one-command Windows Task Scheduler automation.

## Requirements
- Python 3.11+
- Windows PowerShell (for scheduled automation scripts)
- A Notion integration token with access to the target data source
- Docker Desktop (assumed by architect-generated setup payload)

## Installation
```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Environment Variables
Create a `.env` file in project root:

```env
NOTION_TOKEN=your_notion_integration_token
NOTION_DATA_SOURCE_ID=your_data_source_id
# Optional fallback:
# NOTION_DATABASE_ID=your_database_id_or_url

GEMINI_API_KEY=your_gemini_key
MODEL_LIMIT=4
HF_TOKEN=optional_hf_token
LOG_LEVEL=INFO
```

Notes:
- `NOTION_DATA_SOURCE_ID` is preferred for `notion-client 3.x`.
- Ensure the target data source is shared with your integration.
- `MODEL_LIMIT` controls how many top candidates are architected (default `4`).
- Architect candidates are selected from highest-download models with `Review Score >= 4.0`.

## Manual Run
```powershell
.\.venv\Scripts\python.exe main.py
```

Optional pre-run syntax check:
```powershell
.\.venv\Scripts\python.exe -m py_compile main.py
```

Optional unbuffered run (live logs):
```powershell
.\.venv\Scripts\python.exe -u main.py
```

## Scheduled Automation
Use the installer script to create/update a daily task:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup_scheduled_task.ps1 -DailyAt 09:00 -TaskName AgentIntelligenceNotionSync -Force
```

Run the task immediately:

```powershell
Start-ScheduledTask -TaskName AgentIntelligenceNotionSync
```

Check recent sync logs:
```powershell
Get-Content .\metadata\factory_health.log -Tail 120
```

## Project Structure
- `main.py`: data fetch + transformation + Notion sync
- `requirements.txt`: Python dependencies
- `scripts/run_sync.ps1`: runner used by Task Scheduler
- `scripts/setup_scheduled_task.ps1`: one-command task setup
- `error_log.md`: issue history and fixes
- `Operative_commands.md`: command reference
- `Agent-Intelligence-OS_Setup_guide.md`: full setup guide

## Troubleshooting
- If you see `Could not find database/data source`, verify:
  - ID correctness
  - integration sharing on the target
  - token validity in `.env`
- If sync adds `0` records, records may already exist by `Model ID`.
- If you see `Industry is expected to be multi_select`, verify the Notion schema still matches and integration has access; script already adapts to select/multi_select.
- If you see `Quantization is not a property that exists`, add the property in Notion or leave it absent (script skips it automatically).
- If PowerShell output appears truncated or odd, avoid `head`; use `-u` and `Get-Content -Tail`.
- If you see Gemini deprecation warning for `google.generativeai`, it is non-blocking for now.

## Security
- Do not commit `.env`.
- Rotate secrets immediately if exposed (`NOTION_TOKEN`, `GEMINI_API_KEY`, `HF_TOKEN`).
