# Repository Guidelines

## Project Structure & Module Organization
- `app/app.py`: Streamlit entrypoint (UI wiring and orchestration).
- `app/core/`: Core logic placeholders — `ingest.py` (Box → chunks → embeddings → store), `rag.py` (retrieval/answer), `config.py`, `utils.py`.
- `app/prompts/`: Prompt templates.
- `app/stores/`: Local vector index (FAISS) artifacts; safe to delete/rebuild.
- Root: `.env` runtime config, `requirements.txt` pinned deps, `REQUIREMENTS.md` system design/requirements.

## Build, Test, and Development Commands
- Setup venv: `python3 -m venv .venv && source .venv/bin/activate`
- Install deps: `pip install -r requirements.txt`
- Run UI: `streamlit run app/app.py`
- Env config: create `.env` (see examples in repo) with `OPENAI_API_KEY`, `BOX_*`, and LangSmith vars.
- Optional tooling (if installed): `black .` to format, `ruff .` to lint.

## Coding Style & Naming Conventions
- Python 3.11+, PEP 8, 4-space indentation.
- Names: modules/functions `snake_case`, classes `PascalCase`, constants `UPPER_SNAKE_CASE`.
- Keep UI code in `app/app.py`; keep pure logic and external I/O in `app/core/*` with small, testable functions.
- Avoid hardcoding paths; prefer `.env` + `config.py` for settings (e.g., `VECTOR_DIR`, `TOP_K`).

## Testing Guidelines
- Framework: prefer `pytest` (not bundled). Install with `pip install pytest`.
- Location: `app/tests/` with files named `test_*.py` (e.g., `app/tests/test_utils.py`).
- Scope: unit tests for `utils.py`, retrieval composition in `rag.py` (mock network/LLM); no external API calls.
- Run: `pytest -q` (use `-k <name>` to filter). Add minimal fixtures for `.env` via `monkeypatch`.

## Commit & Pull Request Guidelines
- Commits: use Conventional Commits — `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`. Write imperative, concise subject (≤72 chars) and a focused body when needed.
- PRs: include purpose, linked issues, test steps (commands), and screenshots of the Streamlit UI if UI changes. Note any schema/setting changes in `REQUIREMENTS.md`.
- Hygiene: no secrets in diffs; run formatter/linter; ensure local app starts.

## Security & Configuration Tips
- Keep secrets in `.env` (loaded via `python-dotenv`); never commit credentials.
- Validate required vars at startup (OpenAI, Box, LangSmith). Avoid logging PII; use `LOG_LEVEL` for verbosity.
- See `REQUIREMENTS.md` for architecture and environment details.

