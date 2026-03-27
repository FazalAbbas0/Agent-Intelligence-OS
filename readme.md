# Agent-Intelligence-OS

Automates syncing trending Hugging Face agent models into a Notion data source.

## Features
- Fetches top Hugging Face models tagged as agent-related.
- Normalizes and maps model details to Notion properties.
- Avoids duplicate inserts using existing `Model ID` values.
- Supports Notion `data_sources` API (`notion-client` v3).
- Includes one-command Windows Task Scheduler automation.

## Requirements
- Python 3.11+
- Windows PowerShell (for scheduled automation scripts)
- A Notion integration token with access to the target data source

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
```

Notes:
- `NOTION_DATA_SOURCE_ID` is preferred for `notion-client 3.x`.
- Ensure the target data source is shared with your integration.

## Manual Run
```powershell
.\.venv\Scripts\python.exe main.py
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

## Security
- Do not commit `.env`.
- Rotate token immediately if it is exposed.
