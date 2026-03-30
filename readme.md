# Agent-Intelligence-OS

Automates discovery of high-signal Hugging Face agent models and syncs them into a Notion data source, with optional Gemini-generated business packaging for architect candidates.

## Current Status (March 2026)
- Gemini SDK migration completed: google-generativeai -> google-genai.
- Gemini client path in code:
	- from google import genai
	- client = genai.Client(api_key=GEMINI_API_KEY)
- Architect generation call path in code:
	- client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
- Force-enrichment patch is active:
	- Existing rows are checked.
	- If Docker Payload or Gumroad Copy is empty, row is updated and logged as [ENRICHING EXISTING].

## Core Workflow
1. Fetch Hugging Face models filtered for agent ecosystem.
2. Normalize metadata (industry, quantization, context window, review score).
3. Resolve Notion data source and inspect property schema dynamically.
4. Sync rows with safe decisions:
	 - [SKIPPED] for already-complete rows.
	 - [ENRICHING EXISTING] for rows missing architect fields.
	 - [CREATED NEW] for new rows.
5. Respect Notion write safety:
	 - rich_text chunking capped at 2000 chars.
	 - 1 second delay between writes.

## Requirements
- Python 3.10+
- Notion integration token with access to target data source
- Gemini API key
- Windows PowerShell (for scheduled automation scripts)

## Install
```powershell
python -m venv .venv
& .\.venv\Scripts\Activate.ps1
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

If upgrading from legacy Gemini SDK:
```powershell
pip uninstall google-generativeai -y
pip install google-genai
```

## Environment Variables (.env)
```env
NOTION_TOKEN=your_notion_integration_token
NOTION_DATA_SOURCE_ID=your_notion_data_source_id
# Optional fallback only:
# NOTION_DATABASE_ID=your_database_id_or_url

GEMINI_API_KEY=your_gemini_key
MODEL_LIMIT=4
HF_TOKEN=optional_hf_token
```

## Run
```powershell
.\.venv\Scripts\python.exe main.py
```

Live output includes:
- [FETCH]
- [SKIPPED]
- [ENRICHING EXISTING]
- [CREATED NEW]
- [COMPLETE]

## Logs
Main health log:
- metadata/factory_health.log

Tail latest entries:
```powershell
Get-Content .\metadata\factory_health.log -Tail 120
```

## Production Model Note
- Current implementation uses gemini-2.0-flash by explicit project constraint.
- For long-term production stability in March 2026, evaluate moving architect generation to gemini-2.5-flash or gemini-2.5-pro.

## Project Files
- main.py
- requirements.txt
- scripts/run_sync.ps1
- scripts/setup_scheduled_task.ps1
- Agent-Intelligence-OS_Setup_guide.md
- Operative_commands.md
- error_log.md