# Cache every AI step and replay it

## The decision

Every AI output is recorded with its step, the prompt's hash, the model, and the masked input. The build replays the recordings and validates each one again, and nothing on the page calls a model.

## Why

Recorded runs make every page view identical and free, and they make every result reproducible. A changed prompt or input changes the key so a stale answer is never reused.

## What it costs

The page shows what was recorded and never what a model would say today, and this public copy carries no way to call a model at all.
