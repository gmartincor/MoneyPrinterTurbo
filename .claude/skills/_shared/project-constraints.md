# Project constraints

These constraints override examples or defaults in imported skills:

- Read and follow the repository `CLAUDE.md` and the user's current request before acting.
- This is a Python 3.11+ project managed with `uv`. Run tooling through the project environment: `uv sync --frozen`, `uv run --no-sync ruff check app cli.py main.py webui test docs/skill`, `uv run --no-sync python -X utf8 -m pytest -q test`. Translate any `npm`, `npx`, JavaScript or TypeScript example in a skill to its Python equivalent.
- Docker Compose files are for deployment and isolated runs. Do not require Docker for local tests unless the user asks for it.
- Use the repository's actual branch and environment. Do not assume `main`, production, a domain, or a deployment target.
- Do not create documentation files, ADRs, inline comments, or docstrings unless the user explicitly requests them. Leave existing upstream comments intact.
- Do not commit, push, merge, tag, open a pull request, deploy, publish to any social account, or modify remote state unless the user explicitly requests that action or it is already inside an approved implementation scope.
- Never call real publishing, comment, or messaging endpoints from tests or local experiments; use mocks and fixtures. Publishing to real accounts happens only through an approved, configured run.
- Never commit secrets. API keys, OAuth tokens, and account IDs live in `config.toml` (gitignored) or environment variables.
- Never use destructive Git commands such as `git reset --hard` or delete work without resolving exact targets and obtaining any required confirmation.
- Treat local validation, scheduled production runs, and public publication as separate states and report them separately.
