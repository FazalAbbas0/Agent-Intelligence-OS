# Operative Commands

This file lists day-to-day commands for running, verifying, and maintaining the project.

## 1) Environment and Dependencies

Create virtual environment:
```powershell
python -m venv .venv
```

Install dependencies:
```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Upgrade pip (optional):
```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip
```

## 2) Manual Sync Execution

Run sync now:
```powershell
.\.venv\Scripts\python.exe main.py
```

Run with unbuffered live logs:
```powershell
.\.venv\Scripts\python.exe -u main.py
```

Syntax check before run:
```powershell
.\.venv\Scripts\python.exe -m py_compile main.py
```

## 3) Configure Daily Task (One Command)

Create or replace scheduled task at 09:00 daily:
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup_scheduled_task.ps1 -DailyAt 09:00 -TaskName AgentIntelligenceNotionSync -Force
```

## 4) Scheduled Task Operations

Run task immediately:
```powershell
Start-ScheduledTask -TaskName AgentIntelligenceNotionSync
```

Show task details:
```powershell
Get-ScheduledTask -TaskName AgentIntelligenceNotionSync | Get-ScheduledTaskInfo
```

Show last task result and time fields only:
```powershell
Get-ScheduledTask -TaskName AgentIntelligenceNotionSync | Get-ScheduledTaskInfo | Select-Object LastRunTime, LastTaskResult, NextRunTime
```

Delete task:
```powershell
Unregister-ScheduledTask -TaskName AgentIntelligenceNotionSync -Confirm:$false
```

## 5) Useful Diagnostics

Check Python executable:
```powershell
.\.venv\Scripts\python.exe -c "import sys; print(sys.executable)"
```

Show installed notion client version:
```powershell
.\.venv\Scripts\python.exe -c "import notion_client; print(notion_client.__version__)"
```

Show Gemini SDK availability:
```powershell
.\.venv\Scripts\python.exe -c "import google.generativeai as g; print('google-generativeai OK')"
```

Check current env keys used by main.py:
```powershell
.\.venv\Scripts\python.exe -c "import os; from dotenv import load_dotenv; load_dotenv(); print({'NOTION_DATA_SOURCE_ID': bool(os.getenv('NOTION_DATA_SOURCE_ID')), 'GEMINI_API_KEY': bool(os.getenv('GEMINI_API_KEY')), 'MODEL_LIMIT': os.getenv('MODEL_LIMIT', '4')})"
```

Quick Notion connectivity check:
```powershell
.\.venv\Scripts\python.exe -c "import os; from dotenv import load_dotenv; from notion_client import Client; load_dotenv(); c=Client(auth=os.environ['NOTION_TOKEN']); print(c.users.me()['object'])"
```

Show data source property schema (type map):
```powershell
.\.venv\Scripts\python.exe -c "import os; from dotenv import load_dotenv; from notion_client import Client; load_dotenv(); c=Client(auth=os.environ['NOTION_TOKEN']); ds=os.environ['NOTION_DATA_SOURCE_ID']; r=c.data_sources.retrieve(data_source_id=ds); print({k:v.get('type') for k,v in r.get('properties',{}).items() if isinstance(v,dict)})"
```

Tail health logs:
```powershell
Get-Content .\metadata\factory_health.log -Tail 120
```

Find architect vs sync-only rows in logs:
```powershell
Select-String -Path .\metadata\factory_health.log -Pattern "\[ARCHITECT\]|\[SYNC-ONLY\]" | Select-Object -Last 40
```

Run and capture output to file:
```powershell
.\.venv\Scripts\python.exe main.py *> .\metadata\latest_run.log
```

Tail captured run output:
```powershell
Get-Content .\metadata\latest_run.log -Tail 120
```

## 6) Architect Mode Operations

Default architect limit is read from .env (`MODEL_LIMIT`, default `4`).

Run once with default limit:
```powershell
.\.venv\Scripts\python.exe main.py
```

Run once with temporary limit override (current shell only):
```powershell
$env:MODEL_LIMIT="2"; .\.venv\Scripts\python.exe main.py
```

Disable architect generation for one run:
```powershell
$env:GEMINI_API_KEY=""; .\.venv\Scripts\python.exe main.py
```

## 7) Safety Notes
- Keep `.env` out of version control.
- Prefer `NOTION_DATA_SOURCE_ID` over `NOTION_DATABASE_ID` on `notion-client` v3.
- Rotate secrets immediately if tokens/keys are exposed.
- Avoid `python main.py 2>&1 | head -100` in PowerShell (use `-u` and `Get-Content -Tail` instead).
