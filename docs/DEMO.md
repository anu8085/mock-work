# Demo (≤ 3 minutes)

Target: tell a clear social-impact story aligned to the judging criteria (business
applicability, data relevance, creativity, thoroughness, well-architected).

## Suggested script

1. **Problem (20s).** Families miss benefits they qualify for because the system is
   confusing. Benefits Navigator turns a plain-language description into an action plan.
2. **Live run (90s).** Paste the main demo scenario (see [TESTING.md](TESTING.md)).
   - Show Claude extracting a profile and asking clarifying questions.
   - Answer them; show the 8 explainable matches grouped by category.
   - Show the warm, grounded action plan.
3. **Architecture (40s).** Trusted Unity Catalog data via SQL Warehouse; deterministic
   rules engine (explainable, not the LLM); Lakebase as the primary app-state store.
   Call out graceful fallbacks (JSON, SQLite) for reliability.
4. **Impact (20s).** Show Lakebase analytics (`sql/04_demo_analytics.sql`): families
   reached, programs connected, average feedback. Close on social value.
5. **Caveat (10s).** General information only; eligibility confirmed by agencies.

## Reliability tips

- Pre-warm Lakebase (scale-to-zero) before recording.
- Have Test A (JSON + SQLite) ready as a no-network backup demo.
- Never show secrets, tokens, or PATs on screen.
