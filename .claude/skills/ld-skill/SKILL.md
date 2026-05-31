---

name: launchdarkly-flag-check

description: >

  Use this skill whenever the user wants to check the current date and/or time
  where date display is controlled by a LaunchDarkly feature flag. Triggers
  include: "check the date", "show me the time", "what time is it", "show the
  date", or any request to display current date/time. The time is always shown;
  the date is only shown when the flag that gates date display is enabled.

---



# LaunchDarkly Date/Time Skill



## Overview



This skill fetches feature flags from LaunchDarkly and uses their state to
control what is displayed. The **time is always shown**. Each flag in the Flags
table below gates a specific piece of output — enabled shows it, disabled hides
it.



## Flags



This table is the single source of truth for which flags this skill uses.
To change behaviour, update this table only — no other section needs editing.



| Flag key | Gates |
|---|---|
| `flag_show_date` | Date display |



## Prerequisites



- `LD_API_KEY` environment variable set, **or** the user provides `--api-key`.
- Python 3.10+ in the shell (uses `str | None` syntax).
- Bundled script: `scripts/list_flags.py` — stdlib only, no pip installs.



---



## Step-by-Step Workflow



### 1. Gather inputs



Ask the user for any missing values before proceeding:



| Input | Required | Notes |
|---|---|---|
| `project` | Yes | LaunchDarkly project key (e.g. `default`) |
| `environment` | Recommended | e.g. `production`, `staging` — needed for on/off state |
| `api_key` | If env var not set | Pass via `--api-key` |



### 2. Fetch flags



Pass every key from the **Flags** table to the script via `--filter-key`:



```bash
python scripts/list_flags.py \
  --project <project-key> \
  --env <environment-key> \
  --filter-key <flag-key-1> \
  --filter-key <flag-key-2>
```



The script returns only the requested flags. If a flag is absent from the
response, treat it as disabled.



### 3. Determine state for each flag



For each flag in the **Flags** table, resolve its state from the response:



| Condition | State |
|---|---|
| `environment.on: true` | **ENABLED** |
| `environment.on: false` | **DISABLED** |
| Flag absent from response | **DISABLED** (treat as off) |
| `archived: true` | **DISABLED** (archived = inactive) |
| No `environment` block | **UNKNOWN** (re-run with `--env`) |



### 4. Output plain text



Use each flag's state to control output according to its **Gates** column.
Print plain text only — no HTML, no React, no artifact, no commentary.



#### Behaviour per flag



| Flag key | Gates | Enabled behaviour | Disabled behaviour |
|---|---|---|---|
| `flag_ui_show_context` | Date display | Print `Date: <date>` line | Omit date line |



#### Text format



```
Time: <HH:MM:SS>
Date: <Weekday, DD Month YYYY>        ← only when date display flag is ENABLED
<flag-key>: <STATE> [project: <project> / <env>]   ← one line per flag
```



Example with date display enabled:

```
Time: 14:32:07
Date: Friday, 16 May 2026
flag_ui_show_context: ENABLED [project: default / production]
```



Example with date display disabled:

```
Time: 14:32:07
flag_ui_show_context: DISABLED [project: default / production]
```



#### Implementation



```python
from datetime import datetime
now = datetime.now()
print(f"Time: {now.strftime('%H:%M:%S')}")
# apply each flag's gated behaviour here
if flag_ui_show_context_enabled:
    print(f"Date: {now.strftime('%A, %d %B %Y')}")
# print one status line per flag
for key, status in flag_statuses.items():
    print(f"{key}: {status} [project: {project} / {env}]")
```



---



## Error handling



If the script exits non-zero or returns an HTTP error, print an error line
instead of the date/time output:



| Error | Message |
|---|---|
| `HTTP 401` | `Error: invalid or missing API key — check LD_API_KEY` |
| `HTTP 403` | `Error: API key lacks permission for this project` |
| `HTTP 404` | `Error: project not found — confirm the project key` |
| `HTTP 400` | `Error: bad request — check environment or flag key spelling` |
| Network error | `Error: <raw reason>` |
