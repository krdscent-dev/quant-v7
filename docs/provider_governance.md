# Provider Governance

This document describes how the research engine selects between
`MockDataProvider`, `AkShareDataProvider`, and `TushareDataProvider`.

## 1. Provider Priority

The routing priority is defined in `config/provider_priority.yaml`.

Default order:

1. `tushare`
2. `akshare`
3. `mock`

This means the system should prefer the highest-priority enabled source
that can satisfy the requested field or dataset.

## 2. Conflict Handling

When more than one provider can satisfy the same field, the default
strategy is `priority_based`.

Rules:

- use the provider with the best configured priority
- if the preferred provider is disabled, fall back to the next enabled provider
- if no real provider is available, fall back to `mock`

## 3. Degradation Mechanism

If a preferred provider cannot be used because:

- the package is not installed
- the provider is disabled in config
- the provider later fails during integration

the system should degrade to the next available provider instead of
failing the whole research flow.

## 4. Fallback Mechanism

Recommended fallback chain:

1. field-specific preferred provider
2. configured provider priority
3. `MockDataProvider`

This preserves research continuity and keeps the scoring engine working
in offline or partially configured environments.

## 5. Governance Boundary

The provider router is the only place where source selection should be
decided.

It should not:

- compute factors
- apply scoring weights
- infer research conclusions

Those responsibilities remain in the mapping, factor, and scoring layers.

## 6. Operational Recommendation

Use `TushareDataProvider` for structured financial fields, `AkShareDataProvider`
for market and event supplements, and `MockDataProvider` as a safe fallback
for testing, demos, and offline work.

