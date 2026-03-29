# Agent-Intelligence-OS Setup Guide (Current Status)

This guide reflects the current implementation in main.py as of March 29, 2026.

## Current Engine Capabilities
- Pulls top Hugging Face agent models (sorted by downloads).
- Extracts metadata: Industry, Quantization (GGUF/AWQ/EXL2), Context Window, Review Score.
- Resolves Notion target through data source APIs (notion-client 3.x compatible).
- Uses schema-aware payload mapping:
   - Industry supports select or multi_select automatically.
   - Quantization is sent only if that property exists.
- Architect mode (Gemini):
   - Runs only for top candidates (Review Score >= 4.0), limited by MODEL_LIMIT (default 4).
   - Generates Docker/no-code setup, freelance gig copy, golden prompt, objection handling, and Gumroad copy.
- Notion protection:
   - 1 second rate limit between page writes.
   - Per-row error handling without stopping whole sync.
- Health logging to metadata/factory_health.log.

## Step 1: Open project
Use this folder in VS Code:
- C:\Users\My Computer\Agent-Intelligence-OS

## Step 2: Create and activate virtual environment
```powershell
python -m venv .venv
& .\.venv\Scripts\Activate.ps1
```

## Step 3: Install dependencies
```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Required libraries:
- pandas
- huggingface_hub
- notion-client
- python-dotenv
- google-generativeai

## Step 4: Configure .env
Create or update .env in project root:

```env
NOTION_TOKEN=your_notion_integration_token
NOTION_DATA_SOURCE_ID=your_notion_data_source_id
# Optional fallback only:
# NOTION_DATABASE_ID=your_database_id_or_url

GEMINI_API_KEY=your_gemini_key
MODEL_LIMIT=4
HF_TOKEN=optional_hf_token
LOG_LEVEL=INFO
```

## Step 5: Prepare Notion data source
Share the target database/data source with your integration (edit permission).

Recommended/used properties:
- Name (title)
- Model ID (rich_text)
- Downloads (number)
- Source (url)
- Status (select)
- Industry (select or multi_select)
- VRAM Required (select)
- Minimum RAM (select)
- Context Window (number)
- Run Command (rich_text)
- Review Score (number)
- Quantization (optional: rich_text/select/multi_select)
- Docker Payload (optional: rich_text)
- Gumroad Copy (optional: rich_text)
- Implementation Link (optional: url or rich_text)

Notes:
- Implementation Link is initialized as null/empty and can be filled manually later.
- If Docker Payload or Gumroad Copy do not exist, architect text is skipped for those columns.

## Step 6: Run manually
```powershell
.\.venv\Scripts\python.exe main.py
```

Expected output:
- [FETCH] stage starts.
- data source is resolved.
- rows are either skipped (already exists) or created.
- final completion summary is printed.

## Step 7: Validate health logs
```powershell
Get-Content .\metadata\factory_health.log -Tail 80
```

Use logs to confirm:
- [ARCHITECT] rows vs [SYNC-ONLY] rows
- Notion API responses
- sync completion counts

## Step 8: Enable daily scheduler (Windows)
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup_scheduled_task.ps1 -DailyAt 09:00 -TaskName AgentIntelligenceNotionSync -Force
```

Validate:
```powershell
Start-ScheduledTask -TaskName AgentIntelligenceNotionSync
Get-ScheduledTask -TaskName AgentIntelligenceNotionSync | Get-ScheduledTaskInfo
```

## Common Issues and Fixes

### Issue: DatabasesEndpoint has no attribute query
Cause: notion-client 3.x changed endpoints.
Fix: use notion.data_sources.query (already implemented).

### Issue: Industry is expected to be multi_select
Cause: payload/schema mismatch.
Fix: current script auto-detects Industry property type.

### Issue: Quantization is not a property that exists
Cause: column absent in Notion.
Fix: current script sends Quantization only if property exists.

### Issue: Sync added 0 records
Cause: all fetched model IDs already exist.
Fix: normal behavior; review logs for skipped rows.

### Issue: Gemini deprecation warning
Current package may warn that google.generativeai is deprecated.
Fix option: migrate to google.genai SDK in a future update.

## Security and Maintenance
- Rotate tokens/keys immediately if exposed.
- Keep requirements and lock versions stable for scheduled jobs.
- Re-run scheduler setup with -Force after command/path changes.
