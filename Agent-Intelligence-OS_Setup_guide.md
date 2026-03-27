# Agent-Intelligence-OS Setup Guide

This guide covers initial setup, Notion integration configuration, and full automation on Windows.

## Step 1: Clone or open project
Open the project folder in VS Code:
- `C:\Users\My Computer\Agent-Intelligence-OS`

## Step 2: Create virtual environment
```powershell
python -m venv .venv
```

## Step 3: Install dependencies
```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Step 4: Create Notion integration
1. Go to Notion integrations.
2. Create integration named `Agent Intelligence Engine` (or your preferred name).
3. Copy integration token.

## Step 5: Prepare Notion target
1. Create a Notion database (table) for model tracking.
2. Add and verify these properties:
   - `Name` (title)
   - `Model ID` (rich text)
   - `Framework` (select)
   - `Downloads` (number)
   - `Source` (url)
   - `Status` (select)
3. Share this database/data source with your integration and grant edit rights.

## Step 6: Configure environment file
Create or update `.env` in project root:

```env
NOTION_TOKEN=your_notion_integration_token
NOTION_DATA_SOURCE_ID=your_data_source_id
# Optional fallback only:
# NOTION_DATABASE_ID=your_database_id_or_url
```

## Step 7: Test manual run
```powershell
.\.venv\Scripts\python.exe main.py
```

Expected behavior:
- Hugging Face fetch starts.
- Sync target is shown.
- Sync completion summary is printed.

## Step 8: Enable automated daily run
Use one command:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup_scheduled_task.ps1 -DailyAt 09:00 -TaskName AgentIntelligenceNotionSync -Force
```

## Step 9: Validate scheduler
Run once manually:
```powershell
Start-ScheduledTask -TaskName AgentIntelligenceNotionSync
```

Check run result:
```powershell
Get-ScheduledTask -TaskName AgentIntelligenceNotionSync | Get-ScheduledTaskInfo
```

## Common Issues and Fixes

### Issue: `DatabasesEndpoint has no attribute query`
Fix: update code to use `notion.data_sources.query`.

### Issue: ID is a page, not a database
Fix: use the real data source ID and share it with integration.

### Issue: Could not find database/data source
Fix checklist:
- ID is correct
- integration is shared on target object
- token is valid and active

### Issue: Zero records added
Possible reason: all fetched model IDs already exist.

## Maintenance
- Rotate Notion token if exposed.
- Keep dependencies updated.
- Re-run scheduler setup command with `-Force` after script changes.
