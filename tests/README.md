# tests

Manual test scenarios for the mock dry run live in [../docs/TESTING.md](../docs/TESTING.md).

Quick syntax check of all core modules (no app run, no network):

```powershell
py -3.11 -m py_compile app.py agent.py benefits_rules.py databricks_client.py lakebase_client.py local_state_client.py
```

Automated unit tests (e.g. `benefits_rules.screen_programs` against the main demo
profile expecting 8 matches) can be added here later; they are out of scope for the
Prompt 2 skeleton.
