# Every AI value is a quoted span

## The decision

Every value an AI step returns has to be quoted word for word from its clause, and code reads the quote back to check it holds the same value. A reply that fails gets one repair request and is then held with its reasons.

## Why

A model can state a plausible number that isn't in the document. Requiring the exact words turns that failure into one code can catch every time, and the held items show where the model struggles.

## What it costs

A model that understands a clause but paraphrases it gets held. The repair request recovers most of those, and the rest are listed on the page.
