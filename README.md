# oj-problem-agent

`oj-problem-agent` is a resumable Python 3.11+ pipeline for generating, verifying, saving, committing, and pushing 999 original Korean online judge problems with an OpenAI-compatible chat-completions model.

The plan is intentionally explicit:

- Levels 1..30 have 33 standard problems each: 990 problems.
- Levels 22..30 have one additional bonus problem each, index `034`: 9 problems.
- Total: 999 problems.
- Standard metadata has `bonus: false`; bonus metadata has `bonus: true`.

## Setup

```bash
cd oj-problem-agent
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` and `config.yaml`.

Example local model path for llama.cpp:

```text
/Volumes/SSD/models/ojg/qwen3_6_35b_a3b_ojgen_vl-Q5_K_M.gguf
```

Start an OpenAI-compatible server separately, for example `llama-server`, vLLM, SGLang, or a compatible gateway. This project talks to `/chat/completions` using `requests`; it does not use the OpenAI SDK.

## Commands

```bash
python -m oj_agent.main plan
python -m oj_agent.main status
python -m oj_agent.main generate --max-problems 10
python -m oj_agent.main generate --levels 1,2,3
python -m oj_agent.main generate-one --level 13 --tags "dynamic programming,greedy"
python -m oj_agent.main resume
python -m oj_agent.main retry-failed
python -m oj_agent.main validate-all
python -m oj_agent.main dry-run-one --level 13
```

Script wrappers are available in `scripts/`.

## Verification

Each candidate problem goes through five stages:

1. Structural validation, schema checks, markdown safety, SVG checks, and similarity checks.
2. LLM adversarial review.
3. C++17 compilation, sample execution, hidden generator execution, and optional brute-force comparison.
4. Counterexample search from the LLM plus deterministic edge cases.
5. Final LLM review and answer writing.

If any round fails, the revision loop restarts from round 1 until `max_revision_attempts`. Exhausted slots are written to `generated/retry_queue/`.

Verification effort scales by difficulty through `verification.effort_by_level` in `config.yaml`.

## GitHub Coordination

Generation is safe for concurrent workers using GitHub as the shared progress source:

- A worker pulls with rebase.
- It claims a slot by writing `generated/locks/{slot_id}.lock.json`.
- The lock is committed and pushed immediately.
- Conflicting pushes cause a pull/rebase and a new slot selection.
- Accepted problems remove the lock, update state, commit, and push.
- Failed slots are queued for retry, committed, and pushed.

Tokens are read from `.env` and are never printed or tracked. For HTTPS remotes, authenticated push URLs are passed to Git commands without writing tokens into tracked files.

## Output Layout

Accepted problems are written under:

```text
generated/problems/level_13/L13-001_slug/
  problem.md
  answer.md
  metadata.json
  verification.json
  solutions/
    reference.cpp
    brute_force.py
    generator.py
  tests/
    samples/
    hidden/
    counterexamples/
  assets/
    diagram.svg
```

Global state is stored at `generated/metadata/state.json`.
