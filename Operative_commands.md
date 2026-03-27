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

## 2) Manual Sync Execution

Run sync now:
```powershell
.\.venv\Scripts\python.exe main.py
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

Quick Notion connectivity check:
```powershell
.\.venv\Scripts\python.exe -c "import os; from dotenv import load_dotenv; from notion_client import Client; load_dotenv(); c=Client(auth=os.environ['NOTION_TOKEN']); print(c.users.me()['object'])"
```

## 6) Safety Notes
- Keep `.env` out of version control.
- Prefer `NOTION_DATA_SOURCE_ID` over `NOTION_DATABASE_ID` on `notion-client` v3.
