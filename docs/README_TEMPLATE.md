# Policy Reconciler

**[Open the live demo]({site_url})** and press Run the review. It runs in your browser, and there's nothing to install.

![Policy Reconciler after a review of a synthetic bank's library with every stage done and the findings counted](docs/images/overview.png)

A bank's policies, procedures, job aids, FAQ pages, and bulletins are written by different teams over years, and nobody can say for sure whether they still agree. Policy Reconciler reads the whole library and finds the rules that contradict each other, the steps copied between documents, and the older versions still published, and it leaves alone the rules that differ on purpose. Code makes every decision it can, five AI steps handle only what code can't read for certain, and a person settles what the evidence can't and approves every change before it publishes.

Every bank, person, policy, and number here is synthetic. Every AI result on the page was recorded once and replays on each build after code checks it again, and that means the demo makes no model calls, needs no keys, and costs nothing to run.

## Open it

The live demo is at {site_url}, and it's the same page this repo builds. To build it yourself run `python3 build.py` from this folder and open `site/index.html` in a browser. The first build generates the synthetic world and takes under ten seconds on a recent laptop, and later builds take a few seconds. The page works straight from the file system, and nothing on it reaches the network. The project needs only Python's standard library and has been tested on Python 3.15.

## What's on the page

The Library tab shows the bank's 185 documents before the review, Run the review fills in each stage from reading the files to the ranked findings, and Change a rule shows one edit rerunning only what it touches. Findings ranks every finding by risk with the weights open to change, and each one shows both clauses side by side with the rule that decided it. Decisions holds the four places the two synthetic experts disagreed and the written decision for each, Drafts shows each consolidated rule with the gate's check and the judge's grades, and Assistant compares an employee's answers before and after reconciliation. Readiness is a report code writes from the results with no AI prose, and How it works covers the architecture, the AI map, model routing, the embeddings experiment, cost at scale, the production kit, links to the six files that matter most, and the known limits.

![A contradiction on the Findings tab with both clauses side by side and the rule that decided which value to keep](docs/images/finding.png)

![A consolidated draft on the Drafts tab where an injected value that no clause supports fails the gate](docs/images/drafts.png)

## Results

Every number in this table is read from a results file, and none is typed in. Each held-out library was scored once after the code and prompts it measures were frozen. The two rows on the newer libraries came from a round with Claude Sonnet on both AI steps before routing moved the classifier to Gemini 3.8 Flash.

{results}

## Where it's deterministic, probabilistic, and human

{ai_map}

![Model routing on How it works with one chart for each AI step that plots every model's quality against its cost](docs/images/routing.png)

## The rules the code holds to

- AI runs only where code can't decide, and the AI never sees what code can settle.
- Every AI output is checked by code against its clause, a fixed vocabulary, and quoted spans, and a failed check gets one repair request and then a hold with the reasons.
- People's decisions are versioned and become rules and tests.
- The judge is calibrated against the experts and never comes from the drafter's model family.
- Customer details were masked before every recorded model call, and every call has a line in the audit log.
- The page replays recorded runs and validates each one again, and it carries no source because the code lives here.

## Testing

`python3 -m tests.run` runs the whole suite, and `python3 ci/run_gate.py` runs the gate that CI runs with the tests, the build and its strip check, the key scan, and the regression thresholds. Build once before testing because the tests that need the generated world skip until it exists. The page test also clicks through the built page in Node when Node is installed.

## Structure

| Folder | What it holds |
|---|---|
| `generate/` | The synthetic bank, its library, the planted problems, the answer key, and the evaluation sets |
| `engine/` | The code-only review, the gate, the diff, search, the publisher, and incremental runs |
| `agents/` | The AI steps' inputs, masking, validation, replay, routing, and the combined review |
| `prompts/` | One prompt for each of the five AI steps |
| `data/ai_runs/` | Every recorded AI result and the audit log that the build replays and checks |
| `evals/` | Scoring, the freezes, agreement, and every results file |
| `config/` | The models and their prices, routing, risk weights, readiness thresholds, the gate's bars, and the page's address |
| `app/` | The page's view model, renderer, script, and styles |
| `tests/` | The test suite and a click-through of the built page |
| `ci/` | The gate that `.github/workflows/gate.yml` runs on every push and pull request |
| `docs/` | The design Q&A, the build guide, the decision records, and the screenshots in this README |

## Limitations

{limits}

## License

The code is under the [PolyForm Noncommercial License 1.0.0](LICENSE), and the docs, the screenshots, and the synthetic data are under [Creative Commons Attribution-NonCommercial 4.0](https://creativecommons.org/licenses/by-nc/4.0/). You're welcome to read it, run it, and change it for personal, educational, research, or other noncommercial use, and commercial use isn't permitted.
