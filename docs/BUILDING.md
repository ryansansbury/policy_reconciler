# Building and changing it

Every command runs from the repo's root folder, and nothing in this repo calls a model.

## Build and check

1. `python3 build.py` generates the synthetic world when the generator changed, reviews the demo library, replays and scores the recorded AI steps, times the scale library when the engine changed, and writes the page to `site/`.
2. `python3 -m tests.run` runs the test suite.
3. `python3 ci/run_gate.py` runs the gate, and the workflow in `.github/workflows/gate.yml` runs the same gate after a build on every push and pull request.

Every AI result comes from a recording in `data/ai_runs/` that carries its step, its prompt's hash, its model, and the masked input it was made from. The build checks every recording again before it uses one, and `data/ai_runs/audit.jsonl` has a line for every call.

## When the gate fails

- **A test fails.** The output names the test and its last lines. Fix the code or the test, and never loosen a test to make it pass.
- **The build or the strip check fails.** A never-word reached the page. The message names the word so find the file that holds it and take it out.
- **The key scan finds something.** Treat it as a leaked key, rotate it at once, and then remove the file's copy.
- **A regression threshold fails.** The message says which result fell below its bar in `config/gate.json`. A change that lowers recall or adds a false alarm doesn't ship.

## When a recording no longer matches

Replay uses a recording only when the prompt and the input it was made from still match, and anything else counts as missing. The recordings were made once, and this repo carries no way to make new ones. A change to a prompt or to what code sends a model leaves that step without an answer. Items a model failed twice show on the page as held with their reasons.

## The words and the code links

Every visible word lives in `WORDS.md`, and `profiles/general/words.md` sets the footer. The page carries no source. The code panel on How it works and each box on its diagram link their files to this repo on GitHub, and `config/site.json` holds the repo's address and branch along with the page's own address.

## Adding a document format

Write a parser in `engine/parse.py` that returns the same shape as the others with the metadata first and then the sections and their clauses. Add a test that a file in the new format parses clause for clause. Because the parser is part of the engine the change needs a new engine version that's frozen before it's scored once on fresh seeds.

## Freezes

A held-out library is scored once for each frozen version, and a new version is scored on seeds no earlier version saw. The hashes live in `evals/frozen.json`, `evals/engine_freeze.json`, and `evals/prompt_freeze.json`, and tests fail if the generator, the engine, or a prompt drifts from them.
