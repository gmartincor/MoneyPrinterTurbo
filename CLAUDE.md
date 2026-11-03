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
5. Read `docs/datavideo/handoff.md` (current state, next steps, accounts) and `docs/datavideo/architecture.md` (confirmed architecture). Continue from the next steps listed there unless the owner asks for something else.
6. Apply each skill whenever its description matches the task. When a skill conflicts with this file or with `project-constraints.md`, this file and the constraints win.

If a new skill is added under `.claude/skills/`, add it to the list above in the same change.

## Product Direction

Agreed with the owner:

- The owner lives in Spain. Income is declared under Spanish tax rules, and TikTok's Creator Rewards Program is not available there, so TikTok is optional reach only.
- Primary platform: YouTube (Shorts plus weekly and search-driven long-form videos). Instagram Reels and carousels and Facebook are secondary distribution of the same original content.
- Four channels, launched one after another a few weeks apart, each with its own profile in `channels/`: `tu_dinero_es` (household finance, Spain, Spanish), `your_money_us` (household finance, US, English), `mundo_es` (the world in data, Spanish), `space_en` (space and science, English). Sports channels are out: paid sports APIs grant no rights over the competitions and sports RPM is low; a later experiment may use public-domain openfootball data, never match footage.
- Only data sources whose licence allows commercial use. A source is used in a published video only when `Source.license_verified` is true.
- Topics are never typed in by a person: the story detector picks them from each channel's official data, the judge chooses, the writer scripts. The LLM does not search the web.
- Text models: GPT-6.1 Sol through the official OpenAI API for writer and judge roles, configurable per channel; compare with GPT-6.1 Terra on the prompt test bench. No video-generation models.
- Reuse the upstream engine instead of rebuilding it: `llm._generate_response` for text, `voice.tts` for voice and word timings, `task.generate_subtitle` and `task.generate_final_videos` for subtitles, music and FFmpeg assembly, `upload_post.py` for publishing. Voice is chosen per channel with the upstream voice name: official Azure Speech by default, ElevenLabs only when a channel's data justifies it, Edge TTS only in development.
- No face, avatar, or voice clone of any real person.
- Every video is built from fresh, real data. The LLM writes narration only; every figure comes from a data source and is verified against the script before rendering. A failed check blocks publication.
- Visuals are code-generated charts, maps, and figures. Stock footage is secondary background only. Use only music and voices with a clear commercial license; the bundled `resource/songs` files are not used until their license is verified.
- Disclose synthetic or altered content wherever YouTube, Meta, or the EU AI Act require it. Every video description credits its data sources, states that the script was generated with AI from official data, and discloses affiliate links.
- Automatic quality gates decide publication; Telegram alerts the owner only for blocked items plus a weekly digest.
- One engine, many channel profiles. Each channel has its own niche, data, and identity. Never build channel farms, duplicate content across channels, evade platform detection, fake engagement, or reupload third-party content.
- Spend only where a channel proves it with data; pause a channel that shows no growth at its 3- and 6-month reviews.
- Publishing gateway: the upstream Upload-Post integration (`app/services/upload_post.py`) for YouTube, Instagram, Facebook, and TikTok. Instagram carousels use Upload-Post's `/api/upload_photos` endpoint, which extends the existing service when carousels are built. Zernio is not used.
- Request the YouTube Data API audit in parallel. Switching YouTube uploads to the direct API is optional once the audit passes. The OAuth consent screen must be in Production status, never Testing.
- Comments are not automated. Moderation relies on native platform settings configured by the owner: YouTube Studio blocked words with "hold potentially inappropriate comments for review", and Instagram Hidden Words. Revisit automated moderation or replies only if comment volume or scam spam makes manual settings insufficient; replies would then be factual, drawn only from the channel's own data, never generic, and never personalized financial advice.

## Upstream Compatibility

- Keep the fork easy to merge with upstream. Put new functionality in new modules and keep edits to upstream files minimal and focused.
- Do not delete upstream providers or integrations; disable them through configuration instead.
- Data-video code lives in `app/datavideo/` and channel profiles in `channels/`. Its tests live in `test/services/test_datavideo_*.py`, because `.gitignore` only tracks `test_*.py` files under `test/services/` and the `test/` root.
- Sync upstream with `git remote add upstream https://github.com/harry0703/MoneyPrinterTurbo.git` (once) and `git fetch upstream main`.

## Commands

- Install: `uv sync --frozen`
- Compile check: `uv run --no-sync python -m compileall app cli.py main.py webui test docs/skill`
- Lint: `uv run --no-sync ruff check app cli.py main.py webui test docs/skill`
- Tests: `uv run --no-sync python -X utf8 -m pytest -q test`
- Data-video tests: `uv run --no-sync python -X utf8 -m pytest -q test/services/test_datavideo_*.py`
- With secrets from a local `.env`: add `--env-file .env` after `uv run`
- Native rendering tests need `ffmpeg` installed.

## Verification Policy

- After each change: run the data-video tests and lint the touched paths. This takes seconds and is the default verification for work inside `app/datavideo/`, `channels/` and `test/services/test_datavideo_*.py`.
- Run the full upstream suite locally only when a change touches files outside those paths. Otherwise GitHub Actions runs it on every push to `main`; check that run before calling a release done.
- The upstream suite has 9 known failures in audio tests under Python 3.13 (`test_bgm_decoded_audio`, `test_remote_speech_complete_decode`, `test_webui_bgm`, `test_webui_custom_audio_upload`). They predate this fork's work; any other failure is a regression.

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

- The owner requested two living documents: keep `docs/datavideo/handoff.md` current at the end of every work session (state, next steps, accounts), and update `docs/datavideo/architecture.md` before implementing any design change
- Do not create or add other documentation files unless explicitly requested
- Do not add inline comments or docstrings unless explicitly requested
