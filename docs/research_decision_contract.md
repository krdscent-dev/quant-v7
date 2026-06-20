# Research Decision Contract

This document defines the standard output format for the
`ResearchEngine` and the integrated `run_research_pipeline()` flow.

## 1. Purpose

`ResearchDecision` is the structured research output generated from a
normalized `FactorInput`.

It is intended for:

- weekly research review
- event triage
- thematic prioritization
- research workflow automation

It is not a buy/sell recommendation and it does not predict stock prices.

## 2. Input Dependency

The `ResearchEngine` must only depend on `FactorInput`.

It must not depend on:

- `DataProvider`
- `ProviderRouter`
- AkShare APIs
- Tushare APIs

This keeps research decisions decoupled from source selection.

## 3. Standard Fields

`ResearchDecision` must contain:

- `theme_exposure`
- `catalyst_strength`
- `order_confirmation_level`
- `strategic_score`
- `research_conclusion`
- `risk_summary`

## 4. Pipeline Output

The integrated `run_research_pipeline(company_code)` function should
return a dictionary with:

- `company_code`
- `factor_input_summary`
- `factor_scores`
- `strategic_score`
- `theme_exposure`
- `catalyst_strength`
- `order_confirmation_level`
- `risk_summary`
- `research_conclusion`

## 5. Field Definitions

### theme_exposure

A mapping of theme-related factor scores, such as:

- `tau_factor_score`
- `supernode_score`
- `domestic_substitution_score`
- `advanced_packaging_score`
- `advanced_material_score`

### catalyst_strength

A research-side measure of how strong the current catalyst setup is.
This can combine news, guidance, and order-related signals.

### order_confirmation_level

A measure of whether the industrial story has moved into validation:

- orders landing
- revenue recognition
- customer confirmation
- capacity expansion

### strategic_score

The overall medium-term strategic score used for research sorting.

### research_conclusion

A concise textual conclusion for research review.

### risk_summary

A short summary of the main risks that still need validation.

## 6. Design Rules

- use normalized numeric values
- keep the output stable and serializable
- do not embed provider logic
- do not mix reporting language with source logic

## 7. Recommended Usage

The recommended flow is:

`ProviderRouter -> DataMapping -> FactorInput -> Factor Registry -> Strategic Score Engine -> ResearchEngine -> ResearchDecision`

This keeps source governance, factor construction, and research
judgment in separate layers.
