# Keyword search first

## The decision

The assistant retrieves clauses by BM25 keyword search, and statements of the same rule are paired by the rule vocabulary within each topic. Embeddings join only if they beat that on held-out libraries.

## Why

Keyword search is exact, fast, and explainable, and it returns the same result every time. Embeddings cost a model call per clause and add a second thing to keep in step with the library so they have to earn their place on evidence.

## What it costs

A question in words the library never uses can miss its clause. The embeddings experiment measures how often that happens, and under a rule set before any result embeddings didn't earn a place in pairing or in search.
