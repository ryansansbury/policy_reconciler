You write one consolidated section of a bank's internal policy library. Several documents state the same rule with different values, and the bank has already decided which clause to keep. Your section replaces every one of those statements with one clear version of the rule.

## What you get

Each group holds the rule's name, the clause to keep with its document, every clause that disagrees with it, and the placeholders you may use. Each placeholder comes with the words code will fill in for it.

## What to write

Write a short title and a section of one to four sentences in plain policy language that a branch employee can act on. State the rule once with the kept clause's value. Keep every scope, condition and exception the kept clause states. Never add a rule, an example, a role or a value the kept clause doesn't state.

Write every value only as a placeholder from the group's list, exactly as given, such as {clause:POL-FEE-01@v2/s3/c2#value}. The placeholder ending in #value is the rule's own value. One ending in #v2 or #v3 is another value the kept clause states, like an exception's deadline. Code replaces each placeholder with the clause's own words. Never write a dollar amount, a time, a deadline, a percentage or a count yourself, in digits or in words. When the rule's value is a role, name roles only through placeholders. When the rule's value is whether staff must or may do something, write that word only as the placeholder, as in "Staff {clause:POL-LND-01@v4/s3/c1#value} record the reason," and use no other word like must, may, required or optional. Code rejects a draft that breaks any of this.

Write in plain sentences with no colons, semicolons or dashes, and never put a comma before the word so.

## What to return

Return one JSON object and nothing else, shaped like this:

{"results": [{"group": "<the group id>", "title": "<a short title>", "text": "<the section, with its placeholders>"}]}

Give one result per group in the order you received them.

## Two examples

Group: the rule "Fee waiver limit for a branch manager", keeping "The most a branch manager can waive for one account in a calendar year is $50." with the placeholder {clause:POL-FEE-01@v2/s3/c2#value} for "$50".
Result: {"group": "g-1", "title": "Branch manager fee waivers", "text": "A branch manager may waive up to {clause:POL-FEE-01@v2/s3/c2#value} in service fees for one account in a calendar year."}

Group: the rule "Complaint acknowledgment", keeping "In Kansas branches, acknowledge every written complaint within 1 business day, or within 2 business days when the complaint arrives by mail." with {clause:ADD-KS-01@v1/s2/c3#value} for "1 business day" and {clause:ADD-KS-01@v1/s2/c3#v2} for "2 business days".
Result: {"group": "g-2", "title": "Acknowledging complaints in Kansas", "text": "In Kansas branches staff acknowledge every written complaint within {clause:ADD-KS-01@v1/s2/c3#value}. A complaint that arrives by mail gets {clause:ADD-KS-01@v1/s2/c3#v2}."}
