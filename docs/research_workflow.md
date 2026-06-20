# Research Workflow

This document defines the standard research workflow for the V8 engine.

## Weekly Pipeline

The weekly pipeline is the default operating loop for research review.

Flow:

`Universe -> Research Pipeline -> ResearchDecision -> Weekly Report`

Steps:

1. load the core universe
2. run the integrated research pipeline for each company
3. collect `ResearchDecision` outputs
4. rank by `Strategic Score`
5. generate the weekly markdown report

Weekly outputs focus on:

- this week's key themes
- Strategic Score Top10
- catalyst changes
- order confirmation changes
- risk alerts
- watchlist changes
- research conclusions

## Monthly Review

Monthly review should compare theme strength, factor stability, and
watchlist rotation across the month.

## Quarterly Review

Quarterly review should validate whether the theme thesis still holds,
whether orders are converting, and whether strategic scores need to be
reweighted.

## Operating Principle

`ResearchDecision` is the only input used by reporting layers.
Reports must not depend directly on providers.

## Output Rules

- YAML theme files stay in `data/watchlists/`
- report artifacts stay in `reports/`
- workflow documentation stays in `docs/`

## Encoding Rules

- YAML uses `utf-8`
- Markdown uses `utf-8`
- CSV outputs continue to use `utf-8-sig`
