# Agent-Intelligence-OS Setup Guide (Current Status)

This guide reflects the current implementation in main.py as of March 30, 2026.

## Current Engine Capabilities
- Pulls top Hugging Face agent models (sorted by downloads).
- Extracts metadata: Industry, Quantization (GGUF/AWQ/EXL2), Context Window, Review Score.
- Resolves Notion target through data source APIs (notion-client 3.x compatible).
- Uses schema-aware payload mapping:
   - Industry supports select or multi_select automatically.
   - Quantization is sent only if that property exists.
- Architect mode (Gemini):
   - Runs for top candidates (Review Score >= 0.0), limited by MODEL_LIMIT (default 4).
   - Generates Docker/no-code setup, freelance gig copy, objection handling, and Gumroad copy.
   - Current code path uses google-genai client.models.generate_content with model gemini-2.0-flash.
- De-dup + force-enrichment behavior:
   - Existing non-architect rows are skipped.
   - Existing architect rows are updated when Docker Payload/Gumroad Copy are blank.
   - New rows are created normally.
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

If you are upgrading from legacy Gemini SDK packages, run:
```powershell
pip uninstall google-generativeai -y
pip install google-genai
```

If `pip` is not found in PowerShell, use the virtual environment Python explicitly:
```powershell
& ".\.venv\Scripts\python.exe" -m pip uninstall google-generativeai -y
& ".\.venv\Scripts\python.exe" -m pip install google-genai
```

Verify installation:
```powershell
& ".\.venv\Scripts\python.exe" -c "from google import genai; import importlib.metadata as m; print('google-genai', m.version('google-genai'))"
```

Latest verified state in this workspace:
- `google-genai 1.69.0`

Required libraries:
- pandas
- huggingface_hub
- notion-client
- python-dotenv
- google-genai

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
- rows are logged as [SKIPPED], [ENRICHING EXISTING], or [CREATED NEW].
- final completion summary is printed.

## Step 7: Validate health logs
```powershell
Get-Content .\metadata\factory_health.log -Tail 80
```

Use logs to confirm:
- [ELITE-ARCHITECT] rows vs [SYNC-ONLY] rows
- [SKIPPED] / [ENRICHING EXISTING] / [CREATED NEW] outcomes
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

### Issue: Legacy Gemini SDK still installed
Cause: environment still contains google-generativeai.
Fix: uninstall google-generativeai and install google-genai.

### Issue: `pip` command not found in PowerShell
Cause: terminal PATH does not expose pip even though virtual environment exists.
Fix: run package operations via `.\.venv\Scripts\python.exe -m pip`.

### Issue: Gemini model 404 during enrichment
Cause: configured Gemini alias is not available for the current project/API version.
Fix: verify available Gemini models for your key/project and update model aliases; sync continues even when enrichment fails.

### Issue: gemini-2.0-flash lifecycle risk (March 2026)
Cause: gemini-2.0 family is listed under previous/deprecated models in current Gemini docs.
Fix: for production-grade agentic pipelines, move to gemini-2.5-flash (throughput/cost) or gemini-2.5-pro (deeper reasoning) when you are ready to change model baseline.

## Security and Maintenance
- Rotate tokens/keys immediately if exposed.
- Keep requirements and lock versions stable for scheduled jobs.
- Re-run scheduler setup with -Force after command/path changes.
