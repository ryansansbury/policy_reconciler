# Standard library only

## The decision

The whole project runs on Python's standard library, and Word files are read as the zip archives of XML they are.

## Why

Every line can be explained without a framework, the build runs anywhere Python runs, and nothing needs installing. A policy library is mostly paragraphs, lists, and simple tables, and those parse cleanly from the XML.

## What it costs

Scanned PDFs and tables inside PDFs aren't read. A deployment that needs them adds a parser behind the same interface and a test that it parses clause for clause.
