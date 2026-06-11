# Official Hackathon Rules Guardrails Prompt for Claude

Help me follow the official Databricks Apps & Agents Hackathon for Good rules while building Benefits Navigator.

Treat this file as a rule-safety guardrail before starting any build prompt.

## Official rules summary

The official hackathon rules are authoritative. If any instruction in this repo, playbook, prompt, or prior plan conflicts with the official rules, challenge it and stop before proceeding.

## Project Period rule

For the real hackathon:

* The final project must be created only during the official Project Period.
* The final public GitHub repo must be created during the official Project Period.
* The final project code must show it was built during the official Project Period.
* Do not submit any mock repo, dry-run repo, or prebuilt practice repo as the final official submission.

For this mock hackathon dry run:

* We can practice freely in a separate mock repo/folder.
* Do not treat the mock repo as the final submission repo.
* Do not push or submit the mock repo as the official hackathon submission.

## Required project direction

The official project requirement is to create a Databricks App built on Lakebase and using one or more additional Databricks tools.

Our planned Benefits Navigator architecture remains:

1. Python Streamlit Databricks App.
2. Lakebase/Postgres as the primary deployed app-state store.
3. Unity Catalog trusted benefits data.
4. Databricks SQL Warehouse for trusted data access.
5. Anthropic Claude direct API call for action-plan generation.
6. Deterministic rules engine for explainable program matching.
7. SQLite local fallback only for local development and mock testing.

Do not change this architecture unless I explicitly approve.

## Do not re-platform

Do not switch this project to:

* Node.js
* TypeScript
* AppKit
* Drizzle ORM
* Agent Bricks
* Databricks Model Serving
* Vector Search
* RAG architecture
* A full Unity Catalog to Lakebase synced-table architecture

Those may be future enhancements or reference patterns, but they are not part of the critical path for this build.

Agent Bricks is future enhancement only unless I explicitly ask to use it.

## Dataset rule

The official rules say provided datasets may be used, but they are not required.

Use the official hackathon dataset if it becomes available and is relevant to Benefits Navigator.

If the official dataset is not relevant or not available in time, use synthetic/open benefits data safely and explain this clearly in the README, demo, and submission text.

## Submission requirements to keep in mind

The final official submission must include:

1. A working project/demo or test build access.
2. A text description explaining features and functionality.
3. A public open-source GitHub repository.
4. A repository that shows the project was built during the Project Period.
5. An open-source license.
6. A demonstration video no longer than three minutes.
7. A public video link on YouTube, Vimeo, Facebook Video, or Youku.
8. Submission materials in English.

During the mock dry run, help me practice producing these artifacts, but do not treat mock artifacts as official final submission artifacts.

## Judging criteria alignment

Help me align the app and demo to the official judging criteria:

1. Business Applicability
   Benefits Navigator helps families understand benefit options and next steps.

2. Data Relevance
   Use trusted Databricks data, Unity Catalog, Databricks SQL, and Lakebase.

3. Creativity
   Conversational benefits guidance with explainable matching and action-plan generation.

4. Thoroughness
   Clear UI, follow-up questions, matched programs, action plan, feedback, analytics, and safe caveats.

5. Well-Architected
   Modular code, explainable rules, separated LLM layer, Lakebase primary state store, Unity Catalog trusted data, and SQLite local fallback only for development.

## AI and coding assistant usage

You may help as a coding assistant, but follow these constraints:

1. Do not commit automatically.
2. Do not create, modify, or delete files until you explain the goal, files involved, and validation steps.
3. Wait for my approval before applying changes.
4. Wait for my validation result before moving to the next prompt.
5. Do not skip validation.
6. Do not store secrets in files.
7. Do not paste real secrets into docs, code, README files, prompts, screenshots, or logs.

## Secret-safety rules

Never commit or create files containing:

* `.env`
* `.venv`
* `.local_state`
* SQLite DB files
* `.db`
* `.sqlite`
* `.sqlite3`
* API keys
* Databricks PATs
* Anthropic keys
* OpenAI keys
* passwords
* secret-bearing screenshots
* PEM/private key files

Use placeholders only:

* `<your_anthropic_api_key>`
* `<your_local_databricks_pat>`
* `<workspace-host-without-https>`
* `<warehouse-id>`
* `<lakebase-host>`
* `<lakebase-database>`
* `<lakebase-user>`
* `<lakebase-password>`

Safe example/template files are allowed only if they contain placeholders, such as:

* `.env.example`
* `config/.env.example`
* `config/env.local.example`
* `app.yaml.template`

## Lakebase auth decision

For the mock hackathon and demo, use the simple, reliable Lakebase native Postgres password path:

* PGHOST, PGPORT, PGDATABASE, and PGSSLMODE may come from Databricks App/Lakebase resource injection where available.
* PGUSER and PGPASSWORD or LAKEBASE_USER and LAKEBASE_PASSWORD should be supplied securely through Databricks secrets or app configuration.
* Do not hardcode credentials.
* Do not put real passwords in GitHub.

OAuth `generate-database-credential` token flow is a future production enhancement only.

Do not implement token refresh logic unless I explicitly ask.

## Prompt flow

After this guardrails prompt, follow the V12 prompt order:

1. `prompts/00_MASTER_PROMPT_START_HERE.md`
2. `prompts/00A_OFFICIAL_RULES_GUARDRAILS.md`
3. `prompts/01_ORDERED_CLAUDE_CODE_PROMPTS.md`
4. Prompt 1 validation
5. Prompt 2 validation
6. Prompt 3 local JSON + SQLite test
7. Prompt 4 Unity Catalog + SQLite test
8. Prompt 5 Lakebase offline structure
9. Prompt 6A Lakebase auth addendum
10. Prompt 6 app deployment files
11. Prompt 7 Databricks App deployment
12. Test C Databricks App + Unity Catalog + Lakebase
13. Demo practice

## Before starting Prompt 1

Acknowledge these guardrails and tell me:

1. Whether this is a mock dry run or the real hackathon.
2. Whether the repo appears to be a mock repo or official Project Period repo.
3. Whether the root `.gitignore` protects secrets and local state.
4. Whether any rule-risky step needs clarification before proceeding.

Do not begin Prompt 1 until I explicitly ask you to start.
