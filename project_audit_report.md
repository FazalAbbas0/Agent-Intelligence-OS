# Project Audit Report

Date: March 30, 2026
Scope: Deep-system audit of blank Docker Payload and Gumroad Copy behavior in current codebase
Mode: Audit plus surgical remediation status

## Executive Summary
The current project is mostly aligned with the Google GenAI SDK migration and already contains 2000-character rich_text splitting logic. The main remaining risk for blank architect columns is not the splitter itself, but architect generation availability and gating conditions.

Primary findings:
- SDK wiring is correct for google-genai package usage.
- The model call is now variable-driven through ARCHITECT_MODEL, with fallback to gemini-2.0-flash.
- The code does include a splitter and applies it in both create and update flows.
- Rows are marked SYNC-ONLY when they are not in the architect candidate pool and do not meet force-enrichment conditions.
- _is_rich_text_empty now treats placeholder values ("-", ".", "n/a", "N/A") as empty-equivalent.

Remediation state:
- All 5 surgical edits have been applied in main.py.
- Top-4 elite limiting behavior remains intact through MODEL_LIMIT.

---

## 1) API and SDK Compatibility Audit

### 1.1 Import/Dependency Consistency
Audit result: Compatible.

Observed in main.py:
- Line 13: from google import genai
- Line 41: client = genai.Client(api_key=GEMINI_API_KEY)

Observed in requirements.txt:
- google-genai

Conclusion:
- main.py import path matches requirements.txt package selection.
- Legacy google-generativeai import is no longer used.

### 1.2 Initialization Audit for 404 "Not Found"
Audit result: Initialization is syntactically correct, but runtime model availability risk remains.

Evidence:
- Line 41 creates client with API key correctly.
- Line 38 initializes ARCHITECT_MODEL from .env with fallback.
- Line 241 routes generation through model=ARCHITECT_MODEL.

Interpretation:
- Client initialization is not the direct defect.
- 404 model errors in Google AI Studio are more consistent with model availability/lifecycle mismatch for the selected model ID, not client construction syntax.

### 1.3 Model String Audit
Audit result: Implemented correctly and now configurable.

Evidence:
- Line 38: ARCHITECT_MODEL = os.getenv("GEMINI_ARCHITECT_MODEL", "gemini-2.0-flash").strip()
- Line 241: model=ARCHITECT_MODEL

Assessment:
- This is a valid implementation pattern in code.
- The fallback remains gemini-2.0-flash for backward continuity; production hardening should set GEMINI_ARCHITECT_MODEL to a newer stable model.

---

## 2) Notion Payload Analysis (The 2000-Char Wall)

### 2.1 Does the code lack splitter logic?
Audit result: No. Splitter exists and is used.

Evidence:
- _build_rich_text_blocks function exists and enforces strict_limit = min(max_chars, 2000).
- Update path uses splitter:
  - Line 589 for Docker Payload
  - Line 596 for Gumroad Copy
- Create path uses splitter:
  - Line 669 for Docker Payload
  - Line 673 for Gumroad Copy

Conclusion:
- The 2000-char splitter is implemented and correctly integrated in both update and create property writes.

### 2.2 Why >2000 in one rich_text block causes blank columns
Technical explanation:
- Notion rich_text content has a per-item size ceiling (2000 chars).
- If a single rich_text item exceeds this limit, Notion rejects the write request for that property payload.
- In this codebase, API failures are caught and loop execution continues, so from dashboard perspective the row can look unchanged/blank while pipeline continues.

Important nuance for current state:
- Current code already chunks Docker Payload and Gumroad Copy, so this specific failure path is mitigated for these two fields.

---

## 3) Logic Flow and Enrichment Audit

### 3.1 Why rows become [SYNC-ONLY]
This is expected under current logic when both conditions are false:
- should_architect is false
- force_enrichment is false

Evidence:
- Line 545: run_architect_pass = should_architect or force_enrichment
- Line 574: if run_architect_pass: [ELITE-ARCHITECT]
- Else branch logs [SYNC-ONLY]

How should_architect is computed:
- Top MODEL_LIMIT rows (default 4) by downloads from architect_pool become Architect Candidate.
- Non-candidates default to SYNC-ONLY unless force_enrichment triggers.

How force_enrichment is computed:
- Checks now rely directly on _is_rich_text_empty at lines 536 and 539.
- This removes prior strict rich_text-type gate in the trigger condition.

Runtime corroboration from logs:
- Recent logs show both behaviors:
  - Many [ELITE-ARCHITECT] + [ENRICHING EXISTING]
  - [SYNC-ONLY] for non-candidate rows

### 3.2 _is_rich_text_empty(prop) White Space detection audit
Audit result: Updated and fit-for-purpose for blank/placeholder detection.

Evidence:
- Line 376 now ignores placeholder tokens using lower() not in {"-", ".", "n/a"}.

Behavior:
- Correctly treats spaces/tabs/newlines as empty.
- Treats "-", ".", and any case-variant of "n/a" as empty-equivalent.

Impact:
- Some visually blank or placeholder-filled rows will be skipped as "already enriched".

---

## Root-Cause Matrix for Blank Column Crisis

1. Architect content generation unavailable (most critical)
- If model call fails (404 or other), architect_suite becomes None and no Docker/Gumroad payload is generated.

2. Enrichment gating too strict on property type (resolved)
- force_enrichment no longer requires strict rich_text type checks in trigger logic.

3. Placeholder content treated as non-empty (resolved)
- _is_rich_text_empty now classifies placeholder tokens as empty-equivalent.

4. SYNC-ONLY is currently intentional for non-candidates
- Non-top candidate rows are not architected unless force_enrichment triggers.

---

## Surgical Checklist (5 Exact Lines) - Applied

Note: These surgical line edits were executed and validated.

1) main.py line 38
- Current:
  ARCHITECT_MODEL = os.getenv("GEMINI_ARCHITECT_MODEL", "gemini-2.0-flash").strip()
- Status:
  Applied

2) main.py line 241
- Current:
  model=ARCHITECT_MODEL,
- Status:
  Applied

3) main.py line 536
- Current:
  _is_rich_text_empty(existing_props.get("Docker Payload", {}))
- Status:
  Applied

4) main.py line 539
- Current:
  _is_rich_text_empty(existing_props.get("Gumroad Copy", {}))
- Status:
  Applied

5) main.py line 376
- Current:
  if plain_text and plain_text.lower() not in {"-", ".", "n/a"}:
- Status:
  Applied

Expected effect of these 5 edits:
- Stabilizes model routing by moving to configurable model selection.
- Preserves top-4 architect behavior while improving forced enrichment detection for practical blank states.
- Reduces false "already enriched" outcomes caused by placeholder text.

## Post-Apply Verification
- No editor errors detected in main.py.
- Top-4 limiter remains active at architect_pool.head(MODEL_LIMIT).
- Updated line probes confirm all five surgical edits are present.
