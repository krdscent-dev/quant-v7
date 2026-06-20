# Strategic Score Methodology

## 1. Purpose

Strategic Score is a research ranking tool designed to measure
medium-term industrial trend strength over the next 12-24 months.

It is not a direct buy/sell recommendation and should not be used as a
standalone trading signal.

## 2. New V8 Weights

- `tau_factor_score` 20%
- `supernode_score` 20%
- `domestic_substitution_score` 20%
- `advanced_packaging_score` 15%
- `order_confirmation_score` 15%
- `advanced_material_score` 10%

The total score is normalized to a 0-100 range.

## 3. Why Reduce τ Factor Weight

The τ factor remains important, but in V8 it should not dominate the
ranking:

- τ-based signals are useful for structure and timing
- however, they can drift faster than industrial fundamentals
- for medium-term research, the underlying industrial thesis matters more

As a result, τ factor weight is reduced to 20% so that it supports
ranking without dominating it.

## 4. Why Increase Domestic Substitution, Advanced Packaging, and Order Confirmation

### Domestic Substitution

Domestic substitution captures supply-chain security, localization, and
platform independence. These themes tend to have longer research tails
and broader policy support.

### Advanced Packaging

Advanced packaging is increasingly central to high-performance compute,
AI hardware, and next-generation integration. It often determines
practical performance and commercial scalability.

### Order Confirmation

Order confirmation is a bridge from story to earnings:

- orders landing
- revenue beginning to confirm
- customer validation becoming explicit
- the narrative entering earnings verification

This makes it a critical medium-term research signal.

## 5. What the Engine Measures

Strategic Score is intended to reflect whether a company or theme is
moving from:

- concept
- into validation
- and then into industrialized earnings confirmation

## 6. Scope

- Research sorting tool only
- Not a price prediction model
- Not a trading recommendation
- Intended for 12-24 month industrial trend assessment

## 7. Usage Notes

- Inputs may be analyst-assigned research placeholders
- No external API is required for the current framework
- The engine is designed to be extended later with real factor feeds
