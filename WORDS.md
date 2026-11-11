# WORDS.md

Every visible word on the page lives here, and wording changes happen in one place. Edit the text under any key heading and run the build again. Words in curly braces are filled in by the build and should stay as they are. A profile in profiles/ can override any key so this file holds the neutral wording and a client's version changes only what it needs.

## page.title
Policy Reconciler

## page.line
One consistent set of rules across the bank's policies and procedures.

## page.footer
Built by Ryan Sansbury. Every bank, person, policy, and number here is synthetic.

## page.recorded
Every AI result was recorded once and replays here without a single model call.

## page.site
ryansansbury.com

## page.repo
github.com/ryansansbury/policy_reconciler

## page.source
Source code on GitHub

## page.description
A working demo that reads a synthetic bank's whole policy library, finds every rule stated two different ways, and drafts each fix for a person to approve.

## page.skip
Skip to the content

## header.bank
A synthetic regional bank named {bank}

## tab.label
Tabs

## tab.library
Library

## tab.findings
Findings

## tab.decisions
Decisions

## tab.readiness
Readiness

## strip.run
Run the review

## strip.replay
Run it again

## strip.ingested
Ingested

## strip.ingested.detail
{documents} documents and {clauses} clauses

## strip.extracted
Extracted

## strip.extracted.detail
{atoms} rules read by code and {queued} clauses for the AI

## strip.paired
Paired

## strip.paired.detail
{comparisons} pairs that state one rule

## strip.compared
Compared

## strip.compared.detail
{conflicts} contradictions and {variations} variations left alone

## strip.classified
Classified

## strip.classified.detail
{pairs} pairs the AI settled

## strip.classified.detail_waiting
{waiting} of {pairs} pairs wait for the AI

## strip.ready
Ready for review

## strip.ready.detail
{findings} findings ranked by risk

## tile.conflicts
Contradictions

## tile.conflicts.note
Code {code} · rule or AI {rest}

## tile.duplicates
Duplicate steps

## tile.duplicates.note
Copied runs of steps

## tile.superseded
Outdated versions

## tile.superseded.note
Old versions in use

## tile.variations
Variations left alone

## tile.variations.note
Narrowed on purpose

## tile.decisions
Open decisions

## tile.decisions.note
Where experts disagree

## tile.held
Held items

## tile.held.note
Failed a check

## library.title
The library

## library.intro
{bank} keeps {documents} documents in its library. They hold {clauses} clauses across policies, procedures, job aids, FAQ pages, bulletins, and state addenda, and {older} of them are older versions that are still published. Different teams wrote them over many years, and nobody can say for sure whether they still agree.

## library.before
Run the review to read every document, compare every statement of every rule, and rank what needs fixing.

## library.by_type
By type

## library.by_topic
By topic

## library.by_format
By format

## labels.doc_type
- policy = Policy
- procedure = Procedure
- job_aid = Job aid
- faq = FAQ
- bulletin = Bulletin
- addendum = State addendum

## labels.format
- docx = Word
- html = Web page
- md = Markdown

## labels.category
- conflict = Contradiction
- duplicate = Duplicate steps
- superseded = Outdated version

## labels.decider
- code = Code
- ai = AI classifier
- rule = Specialist's decision

## labels.kind
- exception_path = An exception one document leaves out
- unit = Days against business days
- role_generic = A general role against a specific one
- older_version = An older version still published

## labels.decided
- conflict = It's a conflict.
- consistent = It's consistent.
- superseded = It's a cleanup task.

## side.meta
{type} · version {version} · effective {date}

## side.version
version {version}

## side.applies
Applies to

## side.keep
Keep

## side.change
Change

## side.old
Older version

## side.current
Current version

## resolution.conflict
Keep the value in {keep} and update {change} to match it.

## resolution.duplicate
Keep the steps in {keep} and link to them from {change}.

## resolution.superseded
Archive the older version of {change} because the current version replaces it.

## finding.live
The specialist decided that an older version still published is a live conflict until it's archived.

## risk.title
How findings are ranked

## risk.formula
Risk is the category's weight times the sum of three things. They're the topic's severity, the customer weight when the topic faces customers, and the breadth weight times the share of the bank's states and business lines the finding reaches. Change any weight above and the whole list ranks again at once.

## risk.customer
Customer weight

## risk.breadth
Breadth weight

## filter.type
Category

## filter.topic
Topic

## filter.decided_by
Decided by

## filter.all
All

## findings.col.rank
Rank

## findings.col.type
Category

## findings.col.rule
Rule

## findings.col.where
Keep and change

## findings.col.who
Decided by

## findings.col.risk
Risk

## findings.before
Run the review to see the findings.

## findings.where
Keep {keep} and change {change}

## findings.count
{n} of {total} findings

## nf.title
Why these weren't flagged

## nf.intro
{variations} clauses set a different value on purpose inside a narrower scope they state, and {decoys} planted look-alikes resemble a tracked rule. None of them is a contradiction, and staying quiet about them is half of what makes a review trustworthy. Every false alarm costs a specialist time on a rule that already works as written.

## nf.variation
Variation

## nf.variation.others
It differs from {others}.

## nf.decoys
Planted look-alikes

## nf.decoys.note
These come from the evaluation's answer key, and code never reads the key. Each one shows what code read instead.

## nf.decoy.read
Code read this as the rule “{read}” and never compared it with “{near}” because those are different rules.

## nf.decoy.none
Code found no tracked rule here, and it never compared this clause with “{near}.”

## decision.title
Where the experts disagree

## decision.intro
An operations lead and a compliance officer labeled every evaluation pair, and both are synthetic. They agree on the clear cases and disagree in four groups where reasonable people do. Each group gets one decision with its reason, and the decision becomes a rule code applies, a new version of the answer key, and a test.

## decision.kappa
Their agreement beyond chance is a kappa of {before} before any decision and {after} with {decided} of {groups} groups decided.

## decision.count
{n} pairs

## decision.q.exception_path
One document states a rule with an exception path and another states it without one. Is that a conflict?

## decision.q.unit
One document gives a deadline in days and another gives the same number in business days. Is that a conflict?

## decision.q.role_generic
One document names a specific role and another says “a manager.” Does the general wording widen who can approve?

## decision.q.older_version
An older version of a document is still published beside the current one. Is that a live conflict or a cleanup task?

## decision.made
Decided

## decision.open
Waiting for a decision

## decision.changed
It now settles every pair in this group by rule, it labels them in version {version} of the answer key, and a test holds code to it.

## ready.kicker
Readiness report

## ready.title
Is the review ready for a supervised pilot?

## ready.by_code
Code writes this report from the results files and no AI writes any of it. That keeps it from overstating.

## ready.s1
What was reviewed

## ready.reviewed
The demo library holds {documents} synthetic documents with {clauses} clauses in {formats} formats across {topics} topics.

## ready.s2
How it was checked

## ready.checked
Every problem in the library was planted on purpose and recorded in an answer key that froze before any detector existed. The engine was tuned on two development libraries and then frozen. It was scored once on three libraries it had never seen, and no later version of the engine was ever scored on them again.

## ready.s3
Results on held-out data

## ready.results
On the three held-out libraries code alone caught {caught} of {planted} planted problems.

## ready.col.cat
What was planted

## ready.col.result
Result

## ready.cat.C
Contradictions

## ready.cat.P
Contradictions in different words

## ready.cat.D
Duplicate steps

## ready.cat.S
Outdated versions

## ready.cat.V_alarms
False alarms on deliberate variations

## ready.cat.N_alarms
False alarms on look-alikes

## ready.s4
The experts' agreement and the decisions

## ready.agreement
The two experts agree beyond chance at a kappa of {before} before any decision and {after} with {decided} of {groups} groups decided. Each decision becomes a rule code applies.

## ready.s5
The judge and where people still review

## ready.judge
The judge is trusted on {trusted} of {of} criteria where it matched both experts on drafts with known defects. A specialist still approves every draft.

## ready.judge_none
The judge's calibration isn't recorded yet so a person checks every criterion and a specialist approves every draft before it publishes.

## ready.s6
Cost and time

## ready.cost
Code reviews the whole demo library in {seconds} seconds.

## ready.cost_ai
The recorded AI steps cost ${dollars} across {calls} calls.

## ready.s7
Known limits

## ready.s8
Recommendation

## ready.rec.ready
Ready for a supervised pilot in which every change goes to a specialist before it publishes.

## ready.rec.not
Not ready for a pilot yet. These conditions aren't met.

## ready.unmet
The {about} measured {value} against a bar of {need}.

## ready.unmeasured
nothing yet

## tab.drafts
Drafts

## tab.assistant
Assistant

## drafts.title
Consolidated drafts

## drafts.intro
Each contradicted rule gets one consolidated section that replaces every clause that disagrees with the kept one. {done} of {groups} rules have a draft so far.

## drafts.rule
Each value in a draft is a citation that code fills from its clause, and a gate fails any draft with a value it can't trace. A specialist approves every draft.

## drafts.gate.pass
Passed the gate

## drafts.gate.held
Held by the gate

## drafts.waiting
Waiting for the drafter's recording

## drafts.approved
Approved by {by}

## drafts.on_hold
On hold

## drafts.needs_approval
Needs a specialist's approval

## drafts.inject
Inject an untraced value

## drafts.inject.note
This is a labeled test. It adds one value outside any citation, and the gate fails the draft until it's removed.

## drafts.diff
What changes in the replaced clauses

## drafts.grades
The judge's grades

## drafts.sources
The {n} clauses behind this draft

## judge.title
The judge

## judge.intro
The judge comes from a different model family than the drafter, and it grades every draft on four criteria. It's trusted on a criterion only where it agreed with both experts on drafts with known defects, and a person checks every other criterion. Each draft below shows the judge's grades and the words it quoted.

## judge.keeps_rules
Keeps every rule

## judge.adds_no_rule
Adds no rule

## judge.keeps_scope
Keeps every scope

## judge.plain
Reads plainly

## judge.trusted
Graded by the judge

## judge.person
A person checks this

## judge.col.criterion
Criterion

## judge.col.agree
Agreed with the experts

## judge.col.who
Who grades it

## judge.waiting
The judge's calibration appears here once it's recorded.

## assist.title
The assistant before and after

## assist.intro
An employee's question retrieves the five best clauses by keyword search, and the assistant answers from those alone with a citation for every value. Before reconciliation the library disagrees with itself, and the answer has to say so. After reconciliation the answer cites the one consolidated rule and nothing else.

## assist.before
Before reconciliation

## assist.after
After reconciliation

## assist.disagree
Sources disagree

## assist.waiting
This answer appears here once it's recorded.

## tab.how
How it works

## arch.title
How the review works

## arch.text
Code reads the library, compares every rule, and makes every decision it can. Two AI steps read only what code can't, people settle what the evidence can't, and three more AI steps write the fix under code's checks. Open any box to read the code behind it on GitHub. It's the same code that built every number on this page.

## arch.lane.review
Find the problems

## arch.lane.fix
Fix them

## arch.kind.code
Code

## arch.kind.ai
AI step

## arch.kind.people
People

## arch.parse
Parse the files

## arch.extract
Read clear values

## arch.a1
A1 reads rules

## arch.compare
Compare every rule

## arch.a2
A2 classifies

## arch.decide
Experts decide

## arch.a3
A3 drafts

## arch.gate
The gate

## arch.a4
A4 judges

## arch.approve
A specialist approves

## arch.publish
Publish

## arch.a5
A5 answers

## aimap.title
Where it's deterministic, probabilistic, and human

## aimap.text
Code settles every rule it can read, and the AI never sees those. Code checks every AI output, and people own what the evidence can't decide.

## aimap.head
- step = Step
- by = Done by
- type = Type
- honest = How it's kept honest

## aimap.rows
- parse = Parse documents into sections and clauses with stable IDs | Code | Deterministic | Byte-identical rebuilds and a fingerprint for every library
- values = Read clear values like dollar amounts, times, deadlines, percentages, counts, roles, and must or may | Code | Deterministic | Unit tests on every pattern
- a1 = Read rules from free text into a fixed form | AI step A1 | Probabilistic | Every value quoted from the clause, roles from a fixed list, inferred fields flagged, and one repair
- pair = Find the statements of the same rule | Code | Deterministic | The rule vocabulary within each topic was tuned on development seeds and scored on held-out seeds
- compare = Compare values on the same rule | Code | Deterministic | Exact and explainable with unit tests
- scope = Apply scope and dates | Code | Deterministic | A deliberate variation with a stated scope is never flagged
- a2 = Judge what code can't settle | AI step A2 | Probabilistic | A label from a fixed list, both clauses quoted, and scored against the frozen key
- precedence = Apply precedence | Code | Deterministic | The rules come from the decision records
- spot = Spot where the experts disagree | Code | Deterministic | Label comparison and Cohen's kappa
- settle = Settle a disagreement | People | Human | A decision record that becomes a rule and a test
- a3 = Draft the consolidated section | AI step A3 | Probabilistic | Values only through citations, a gate for untraced values, a diff by code, and a specialist's approval
- a4 = Grade drafts at scale | AI step A4 | Probabilistic | Calibrated against the experts by criterion and never from the drafter's family
- a5 = Answer employees' questions | AI step A5 | Probabilistic | Every value in a cited clause and conflicting sources flagged
- route = Choose each AI step's model | Code | Deterministic | The cheapest model that clears the step's bar within the approved vendors
- mask = Mask account numbers and identifiers before any model call | Code | Deterministic | A test that no recorded prompt holds an unmasked pattern
- publish = Publish approved changes to the assistant's index | Code | Deterministic | Lineage from each change to its finding and its approver

## steps.title
The five AI steps

## steps.may
May

## steps.never
Never

## steps.a1.name
A1 the rule extractor

## steps.a1.may
read a clause code queued and propose the rules it states.

## steps.a1.never
invents a value, a role, or a scope the clause doesn't state, and it never sees the answer key.

## steps.a2.name
A2 the conflict classifier

## steps.a2.may
label a pair code couldn't settle and quote the words that decided it.

## steps.a2.never
makes a finding on its own. Only a conflict label becomes one, and code checks every quote.

## steps.a3.name
A3 the drafter

## steps.a3.may
write one consolidated section for a contradicted rule.

## steps.a3.never
states a value except through a citation, and it can't publish anything.

## steps.a4.name
A4 the judge

## steps.a4.may
grade drafts on the criteria where it agreed with the experts.

## steps.a4.never
grades a draft from its own model family or decides a criterion it wasn't trusted on.

## steps.a5.name
A5 the assistant

## steps.a5.may
answer an employee's question from the retrieved clauses with a citation for every value.

## steps.a5.never
states a value no cited clause holds, and it never hides a disagreement between sources.

## how.res.title
Results

## how.res.text
Every result here is read from a results file the build or a scored run wrote. Each held-out library was scored once after the code and prompts it measures were frozen.

## how.res.col.what
What ran

## how.res.col.caught
Planted problems caught

## how.res.col.alarms
False alarms

## how.res.code_only
Code alone on three held-out libraries

## how.res.code_only_new
Code alone on three new held-out libraries

## how.res.combined
Code with the AI steps on the same three libraries

## how.res.caught
{caught} of {planted}

## how.res.alarms
{n} on {of} deliberate variations and look-alikes

## how.res.alarms_only
{n}

## how.res.pending
The AI steps' held-out scores join this table once the scored round is recorded.

## split.title
What a specialist can do alone

## split.text
This answers which capabilities belong in shared services and which need an engineer.

## split.alone.title
A policy specialist alone

## split.alone
- search = Search the library and compare two sections.
- open = Open a finding and see both sources side by side.
- decide = Record a decision with its reason.
- draft = Edit and approve a consolidated draft.
- ask = Ask the assistant a question.

## split.engineer.title
Needs an engineer

## split.engineer
- format = A new document format.
- rule = A new rule type or comparator.
- precedence = A change to the precedence code.
- key = A new version of the answer key.
- route = Model routing and deployment.

## split.guardrails.title
What keeps self-serve safe

## split.guardrails
- checks = Code checks every AI output before it's used.
- versions = Decisions are versioned and each one has a test.
- approval = A draft publishes only after a specialist approves it.
- gate = The CI gate fails any regression.

## limits.title
Known limits

## limits.list
- formats = Scanned PDFs and tables inside PDFs aren't read. The parser reads Word, web pages, and Markdown.
- multi = Three planted problems span several clauses, and in each one three rules together leave no one able to act. Pairwise comparison can't see them.
- authority = Code can't read every policy statement. When it misses one a weaker document can become the authority until the rule extractor reads the clause.
- wording = The held-out libraries use the same phrasing families as the development ones. The hand-written clauses test new wording, and code alone reads few of them.
- masking = Masking uses patterns. A production deployment would add a dedicated detector for names and addresses.
- judge = The judge's calibration drafts carry clear-cut planted defects. On the 34 real drafts Gemini 3.1 Pro flagged five the specialist had approved, and the routed judge flagged none. The specialist ruled three harmless, one a gap in the source policy, and one real. That's why a person still approves every single draft.
- search = Keyword search often misses a question's clause before reconciliation. Embeddings found some and lost others, and a ten-clause hybrid is next.
- comparison = The model comparison runs each model on one library's 180 extraction clauses and a subset of 69 pairs, 8 drafts, 30 calibration drafts, and 10 questions. On the assistant a single answer separates the route from the rest. The candidates were fixed on 10/28, and a newer model such as Gemini 4 Argon joins with one owner run.
- pricing = Every model is priced at list price without the prompt caching a deployment would add, and each model's thinking counts as output the way its vendor bills it.
- variance = A model's result on the same clauses can move between runs by more than the extraction bar. Close routes need repeated runs or a person's hold.
- conditional = An extractor that reads a conditional approval as a general rule can make the wrong clause a rule's authority. Approval caught it on the demo.
- synthetic = Every bank, person, policy, and number here is synthetic.

## start.title
How I'd start an engagement like this

## start.text
Evaluation comes first so every later step is measured against something the client's own experts agreed on.

## start.w1.title
Week one.

## start.w1
Gather representative documents and real questions with the client's experts, and freeze an answer key before building anything.

## start.w2.title
Week two.

## start.w2
Build a code-only baseline and measure it against the key.

## start.w3.title
Week three.

## start.w3
Add AI only where code can't decide, and score it once on held-out documents.

## start.w4.title
Week four.

## start.w4
Settle the experts' disagreements with decision records and write the readiness report from the results.

## code.title
The code

## code.text
The full source is on GitHub with its tests and CI, and these six files are the best place to start.

## code.feat.gate
The gate

## code.feat.compare
The comparator

## code.feat.routing
The routing rule

## code.feat.validate
The validator

## code.feat.score
The scorer

## code.feat.mask
The masking

## code.note.gate
A draft may state a value only through a citation, and this is the code that holds it to that.

## code.note.compare
Every statement of a rule compared with every other after scope, precedence, and deliberate variations are applied.

## code.note.routing
The cheapest model that clears each step's bar within the approved vendors.

## code.note.validate
Every AI reply checked against its clause before anything uses it.

## code.note.score
Every review scored against the frozen answer key.

## code.note.mask
Customer details masked before any text leaves the machine.

## drafts.approve_demo
Approve as a specialist

## drafts.approved_demo
Approved in this demo

## kit.title
The production kit

## kit.text
Every piece is built, and this table says plainly which ones ran and when.

## kit.gate
The CI gate

## kit.gate.what
Every test, the copy lint, the build with its strip check, the key scan, and the regression thresholds

## kit.audit
The audit log

## kit.audit.what
One line for every model call with its hashes, tokens, cost, time, and validation

## kit.masking
Masking

## kit.masking.what
Account numbers, ID numbers, phone numbers, email addresses, and customer names masked before any call

## kit.secrets
Secrets

## kit.secrets.what
This public copy holds no keys at all, and the key scan proves it

## kit.roles
Roles

## kit.roles.what
A deployment signs people in as a viewer, a policy specialist who approves changes, or an engineer who changes routing and rules, and no one holds both rights

## kit.not_run
Built and not run yet

## kit.ran_ok
Ran and passed on {date}

## kit.ran_failed
Ran and failed on {date}

## kit.audit_n
{n} calls logged, and every one matches its recording

## kit.masked_n
{n} customer details masked so far

## kit.masked_none
Nothing recorded yet

## kit.secrets_state
The key scan finds no key in any file

## kit.roles_state
Designed for a deployment and left out of this demo

## kit.repair
Repair

## kit.audit.title
The audit log

## kit.audit.filter
Step

## kit.audit_none
The audit log fills in once the AI steps are recorded.

## kit.audit.head
- time = Time
- step = Step
- tag = Run
- model = Model
- tokens_in = Tokens in
- tokens_out = Tokens out
- problems = Problems
- repair = Repair

## change.title
Change a rule

## change.text
An engineer changes the {rule} in the {title} from {old} to {new}, and the review reruns only what that change touches.

## change.who
Press Make the change to see exactly what the review reruns.

## change.button
Make the change

## change.result
The review read {sections} of {total} sections again, re-extracted {clauses} clauses, and compared {rules} rule again. It reused the other {reused} findings as they were and took {ms} milliseconds against {full} for a full run.

## change.created
The change created {n} contradictions because every other document still states {old}.

## cost.title
Cost and time at scale

## cost.code
Code runs every deterministic stage on the scale library of {documents} documents and {clauses} clauses in {seconds} seconds.

## cost.head
- step = Step
- items = Items at scale
- model = Model
- tokens = Tokens in and out per item
- estimate = Estimated cost

## cost.waiting
This estimate appears once the step is recorded on the demo library.

## cost.total
The AI steps would cost about ${dollars} for the whole scale library. That's an estimate from the demo library's tokens per item at 10/30/2026 list prices.

## cost.partial
Each estimate multiplies the items at scale by the demo library's measured tokens per item and the model's list prices. The rest appear once their steps are recorded.

## route.title
Model routing

## route.text
Each step runs on the cheapest model that clears its bar among the client's approved vendors, and the rest that clear it become fallbacks. The judge never comes from the drafter's vendor, and a drafter must pass both the judge and the gate. Choose fewer vendors to see what a narrower list costs and where quality drops.

## route.waiting
The routes appear here once every model has run on the comparison set.

## route.vendors
Approved vendors

## route.none
A person

## route.no_fallback
None

## hours.title
Hours and cost

## hours.text
A manual review means someone reads every single document against the rest of the library by hand. The review leaves a specialist only the findings to confirm with both clauses shown side by side.

## hours.minutes_per_document
Minutes per document by hand

## hours.minutes_per_finding
Minutes to confirm one finding

## hours.hourly_rate
Hourly cost in dollars

## hours.manual
By hand it takes about {hours} hours and ${cost}.

## hours.review
With the review it takes about {hours} hours and ${cost} with the AI steps included.

## hours.saved
That saves about {hours} hours and ${cost} on this library.

## hours.note
Every number here is an assumption you can change, and only the review's own time and AI cost are measured.

## cost.sample
A real sample of {n} clauses from the scale library measured {off} against the estimate's tokens per item.

## drafts.waiting_title
The rules waiting for a draft

## drafts.waiting_text
Each of these rules gets its consolidated draft once the drafter is recorded on this machine, and every draft then shows its gate result, its changes, and the judge's grades.

## expert.exception_path.compliance
Staff who follow the procedure will refuse requests the policy allows, and that means the two documents disagree in practice.

## expert.exception_path.operations
The procedure covers the everyday case, and the exception lives in the policy where it belongs.

## expert.unit.compliance
Days and business days can differ by four days, and customers are told the shorter one.

## expert.unit.operations
Everyone in the branches reads this deadline as business days.

## expert.role_generic.compliance
An assistant manager or a head teller could read a general role as permission, and that widens who can approve.

## expert.role_generic.operations
In a branch the manager is the branch manager.

## expert.older_version.compliance
The older version is still published where a branch can follow it today, and that keeps it a live conflict until it's archived.

## expert.older_version.operations
The newer version replaced it, and that makes this a cleanup task.

## route.reason.cheapest
The cheapest approved model that clears the bar

## route.reason.hold
Held on this model after reading its output

## route.reason.none_clears
No approved model clears this step's bar so a person does it

## route.reason.unmeasured
No approved model was measured for this step

## route.reason.same_vendor
Every approved judge comes from the drafter's vendor so a person checks the drafts

## route.why.not_measured
Not measured

## route.why.extract_below
More than one point below the best model on exact readings

## route.why.classify_below
More than two points below the best model's accuracy

## route.why.classify_variation
Called a deliberate variation a conflict

## route.why.draft_unjudged
The judge hasn't read its drafts

## route.why.draft_below
The gate or the judge failed more of its drafts than the best model's

## route.why.judge_untrusted
Not trusted on every criterion against the experts

## route.why.assist_below
More than one question in ten below the best model on the questions search could answer

## drafts.ruling.harmless
Ruled harmless by the specialist.

## drafts.ruling.source_gap
Ruled a gap in the source policy by the specialist.

## drafts.ruling.real
Ruled real by the specialist, and drafted again with that note.

## route.chart.title
Quality against cost for every model

## route.chart.text
There's one chart per step since each step has its own measure. The ringed dot is the route, and the shaded band clears the bar.

## route.chart.x
Cost per 1,000 items at each vendor's list price on a log scale.

## route.chart.aria
{step} with every approved model's quality against its cost

## route.metric.extract
Exact readings

## route.metric.classify
Decision accuracy

## route.metric.draft
Drafts the gate and the judge pass

## route.metric.judge
Lowest agreement on any criterion

## route.metric.assist
Right on questions search could answer

## route.legend.route
The route

## route.legend.clears
Clears the bar

## route.legend.misses
Misses the bar

## route.legend.out
Sits out as the drafter's vendor

## route.legend.bar
The bar and the band that clears it

## route.state.route
The route

## route.state.held
Held as the route after the engineer read its drafts

## route.state.held_short
(held)

## route.state.clears
Clears the bar

## route.state.misses
Misses the bar

## route.state.out
Sits out because it comes from the drafter's vendor

## route.table
Show every measurement as a table

## route.table.head
- step = Step
- model = Model
- measure = Measure
- cost = Cost per 1,000 items
- result = Result

## route.head
- step = Step
- model = Model
- why = Why
- fallbacks = Fallbacks
- cheaper = Cheaper models not chosen
- scale = Cost at scale

## route.unheld
{model} would route without the hold.

## route.per_question
{dollars} per 1,000 questions

## route.blend.less
On these routes a review of the {documents}-document library costs about {pct}% less in model calls than on the models each step started with.

## route.blend.more
On these routes a review of the {documents}-document library costs about {pct}% more in model calls than on the models each step started with.

## route.blend.same
On these routes a review of the {documents}-document library costs about the same in model calls as on the models each step started with.

## route.drops.title
Against every vendor approved

## route.drop
{step} drops from {was} to {now}.

## route.person
{step} goes to a person.

## route.no_drops
Every step keeps the quality it has with every vendor approved.

## route.pricing
Every model is priced on its own tokens at its list price as of 10/30/2026 without the {tokens} tokens of client context each recorded Claude call carries.

## route.caught.title
What the judge caught in the comparison's drafts

## route.caught.text
Every model passed the gate on all eight drafts. The gate proves values and nothing else, and these are the drafts the judge failed.

## route.caught.head
- model = Model
- rule = Rule
- criterion = Criterion
- evidence = The judge's evidence

## route.caught.ruled
The judge also flagged {n} drafts for adding Staff as the subject, and the specialist ruled that harmless.

## embed.title
Do embeddings earn their place?

## embed.text
Embeddings are the usual first answer when a system has to find related text. Here they had to beat what the pipeline already does on held-out libraries with their threshold tuned on development libraries alone, and they're kept only where they win under a rule that was set before the first result came in.

## embed.waiting
The experiment runs once the owner records the vectors.

## embed.pair.title
Pairing two statements of one rule

## embed.pair.head
- arm = How a queued clause gets its rule
- paired = Paraphrased contradictions paired
- wrong = Wrong rules added
- cost = Added cost per library
- time = Added model time per library

## embed.arm.code
Code alone

## embed.arm.embeddings
Code and embeddings

## embed.arm.extractor
Code and the rule extractor

## embed.arm.all
All three

## embed.search.title
Finding the clause a question needs

## embed.search.head
- arm = Search
- gold = The question's clause in what the assistant reads
- both = Its clause and the one that contradicts it

## embed.search.bm25
Top five by keywords

## embed.search.bm25_wide
Top ten by keywords

## embed.search.hybrid
Top five by keywords and embeddings

## embed.choice.pairing.adds
Embeddings pair what the rule extractor leaves unread without adding a wrong rule. They stay in the pipeline beside it.

## embed.choice.pairing.replaces
Embeddings pair as much as the rule extractor with no more wrong rules at a fraction of its cost. They could take its place.

## embed.choice.pairing.no_gain
Embeddings pair nothing the rule extractor misses, and on their own they pair fewer. The pipeline keeps keywords and the extractor.

## embed.choice.search.keep
The hybrid finds more of what each question needs than keywords at either depth and loses no question. The assistant uses it.

## embed.choice.search.no_gain
The hybrid doesn't beat keywords at both depths without losing a question. The assistant keeps keyword search.

## embed.note
Vectors from {model} on masked text. The threshold of {threshold} came from development libraries {dev}, and the results are from {libraries} held-out libraries.

## embed.search.hybrid_wide
Top ten by keywords and embeddings (exploratory)

## embed.explore
A ten-clause hybrid tried after the choice found both clauses for {both} of {q} questions against {base} for keywords at ten and lost {lost}. It's the next test.

## embed.none
none

## route.after
{step} moves to {new} on {date} when {model}'s introductory price ends.
