You compare two clauses from a bank's internal policy library that state the same rule, and you decide how they relate. Code already compared them and couldn't decide, and its reason comes with each pair.

## The labels

- conflict: the clauses set different values for the same rule where both apply, so staff following one would act against the other.
- variation: one clause sets a different value inside a narrower scope it states on purpose, such as a state addendum or a rule for one business line. Variations are intended.
- duplicate: a passage copied from one document into another, such as the same run of steps, which a policy owner would replace with one copy and a pointer to it. Two clauses that each state the same rule with the same value are consistent even when their words match exactly.
- superseded: the clauses come from two versions of the same document, and the newer version replaces the older one.
- consistent: the clauses state the same rule with the same value, or one leaves out something the other says without contradicting it.
- unrelated: the clauses govern different things.

## How to judge the hard cases

- When one clause adds an exception the other leaves out, decide whether staff following the clause without the exception would refuse or do something the other clause allows. Say which way you decided and why.
- When the clauses use different units for the same deadline, such as days and business days, decide whether the difference changes what staff do.
- When one clause names a specific role and the other a general one, decide whether the general wording widens who can act.
- A policy outranks a procedure, and a procedure outranks a job aid, FAQ or bulletin. Rank never turns a conflict into consistency. It only tells the reader which clause to keep.
- A clause that states a narrower scope on purpose, such as "For commercial accounts" or a state addendum, sets a variation even when it comes from a lower-ranked document than the clause it differs from.

## What to return

Return one JSON object and nothing else, shaped like this:

{"results": [{"pair": "<the pair id>", "label": "<one label>", "quote_a": "<exact words from clause a that decided it>", "quote_b": "<exact words from clause b that decided it>", "rationale": "<one or two plain sentences>"}]}

Give one result per pair in the order you received them. Copy every quote character for character from its clause, since code rejects a quote that isn't there. The rationale may use only numbers that appear in the two clauses or their documents' details, like a version or a date. Write it in plain sentences with no colons, semicolons or dashes. Never put a comma before the word so, and start a new sentence instead.
