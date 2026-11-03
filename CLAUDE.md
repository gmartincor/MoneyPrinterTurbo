# Project Instructions

Fork of [harry0703/MoneyPrinterTurbo](https://github.com/harry0703/MoneyPrinterTurbo) maintained by gmartincor. It is being adapted into an automated, data-driven, faceless video system that produces and distributes original videos built from fresh, verifiable data.

## Session Start (Mandatory)

Complete these steps at the start of every session, before planning, answering implementation questions, or changing any file:

1. Read this file completely.
2. Read `.claude/skills/_shared/project-constraints.md` and `.claude/skills/_shared/definition-of-done.md`.
3. Read every skill below in full so its workflow stays active for the whole session:
   - `.claude/skills/ai-prompt-engineering-safety-review/SKILL.md`
   - `.claude/skills/api-and-interface-design/SKILL.md`
   - `.claude/skills/code-review-and-quality/SKILL.md`
   - `.claude/skills/code-simplification/SKILL.md`
   - `.claude/skills/context-engineering/SKILL.md`
   - `.claude/skills/debugging-and-error-recovery/SKILL.md`
   - `.claude/skills/devops-rollout-plan/SKILL.md`
   - `.claude/skills/find-skills/SKILL.md`
   - `.claude/skills/incremental-implementation/SKILL.md`
   - `.claude/skills/multi-stage-dockerfile/SKILL.md`
   - `.claude/skills/observability-and-instrumentation/SKILL.md`
   - `.claude/skills/planning-and-task-breakdown/SKILL.md`
   - `.claude/skills/receiving-code-review/SKILL.md`
   - `.claude/skills/security-and-hardening/SKILL.md`
   - `.claude/skills/shipping-and-launch/SKILL.md`
   - `.claude/skills/spec-driven-development/SKILL.md`
   - `.claude/skills/test-driven-development/SKILL.md`
   - `.claude/skills/verification-before-completion/SKILL.md`
   - `.claude/skills/writing-skills/SKILL.md`
4. Read the remaining `.claude/skills/_shared/*.md` checklists whenever a skill points to them.
5. Apply each skill whenever its description matches the task. When a skill conflicts with this file or with `project-constraints.md`, this file and the constraints win.

If a new skill is added under `.claude/skills/`, add it to the list above in the same change.

## Product Direction

Agreed with the owner:

- Primary platform: YouTube (daily Shorts plus a weekly long-form video). Instagram Reels and carousels and Facebook are secondary distribution of the same original content.
- First channel: Spanish-language household finance built from official open data (electricity prices, fuel prices, Euribor, CPI, housing).
- No face, avatar, or voice clone of any real person.
- Every video is built from fresh, real data. The LLM writes narration only; every figure comes from a data source and is verified against the script before rendering. A failed check blocks publication.
- Visuals are code-generated charts, maps, and figures. Stock footage is secondary background only. Use only music and voices with a clear commercial license; the bundled `resource/songs` files are not used until their license is verified.
- Disclose synthetic or altered content wherever YouTube, Meta, or the EU AI Act require it.
- Automatic quality gates decide publication; Telegram alerts the owner only for blocked items plus a weekly digest.
- One engine, many channel profiles. New channels are added one at a time, each with its own niche, data, and identity. Never build channel farms, duplicate content across channels, evade platform detection, fake engagement, or reupload third-party content.
- Upload through an already-audited publishing gateway while the YouTube Data API audit is pending. The OAuth consent screen must be in Production status, never Testing.

Pending confirmation from the owner (do not build on these until confirmed):

- Social gateway: Zernio as the single gateway for publishing, comments, and analytics, keeping the upstream Upload-Post integration as fallback.
- Comment handling: automatic spam and scam moderation, factual replies drawn only from the channel's own data, everything else routed to the owner. No generic bot replies and no personalized financial advice.
- Owner's country of residence (affects TikTok eligibility and tax setup).

## Upstream Compatibility

- Keep the fork easy to merge with upstream. Put new functionality in new modules and keep edits to upstream files minimal and focused.
- Do not delete upstream providers or integrations; disable them through configuration instead.
- Sync upstream with `git remote add upstream https://github.com/harry0703/MoneyPrinterTurbo.git` (once) and `git fetch upstream main`.

## Commands

- Install: `uv sync --frozen`
- Compile check: `uv run --no-sync python -m compileall app cli.py main.py webui test docs/skill`
- Lint: `uv run --no-sync ruff check app cli.py main.py webui test docs/skill`
- Tests: `uv run --no-sync python -X utf8 -m pytest -q test`
- Native rendering tests need `ffmpeg` installed.

## Code Principles

- Apply SOLID principles strictly, especially Single Responsibility
- Follow DRY and reuse existing code before creating new code
- Follow KISS and choose the simplest solution that works
- Follow YAGNI and do not add functionality that is not currently needed
- Write clean, maintainable, and scalable code
- Extract reusable logic into shared modules and utilities
- Remove anything that becomes unused
- Do not add inline comments or docstrings in new code; use self-documenting names

## Tech Stack & Patterns

- Python 3.11+ managed with `uv`; FastAPI API, Streamlit WebUI, CLI
- MoviePy and FFmpeg for rendering, loguru for logging, Pydantic schemas in `app/models`
- Configuration through `config.toml` and `app/config`
- Respect the existing design patterns, file naming conventions, and module boundaries

## Security

- Secrets live only in `config.toml` (gitignored) or environment variables
- Any deployed instance sets `api_key` and listens on `127.0.0.1` unless the owner approves otherwise
- Tests and experiments never publish to real social accounts

## Documentation

- Do not create or add documentation files unless explicitly requested
- Do not add inline comments or docstrings unless explicitly requested
