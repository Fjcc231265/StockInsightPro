# StockInsightPro Architecture

This project is organized so the Streamlit interface can grow into a scalable
analytics and AI platform without mixing UI code with calculation engines.

## Layers

`ui/`
: Streamlit-only presentation layer. Pages and reusable visual components live
here. UI modules should not perform analytics calculations or call raw provider
modules directly.

`services/`
: Stable application facades used by the UI. Today these functions return mock
data. Later they can call APIs, databases, caches, or analytics engines without
requiring UI changes.

`analytics/`
: Framework-free calculation engines. Future modules should live here for
technical indicators, fundamentals scoring, options analytics, volatility
surface logic, gamma exposure, max pain, and risk models.

`ai/`
: AI interpretation and agent orchestration. This layer will convert analytics,
market data, and user context into natural-language summaries and conclusions.

`models/`
: Shared domain models and dataclasses. These should be lightweight and not
depend on Streamlit.

`data/`
: Mock data and future provider/repository adapters. This layer should stay
behind services so UI code remains provider-agnostic.

## Dependency Direction

```text
ui -> services -> analytics / data
ui -> ai -> services / analytics / data
services -> analytics / data / models
analytics -> models
data -> models / raw providers
```

Avoid reverse dependencies. For example, `analytics/` should never import
`streamlit`, and `data/` should not import `ui`.

## Future Growth

- Add provider adapters under `data/` or `services/providers/`.
- Add reusable analytics engines under `analytics/<domain>/`.
- Add AI agents under `ai/agents/` once workflows become more complex.
- Add persistence, caching, and background jobs behind `services/`.
- Add tests at the service and analytics layer before testing UI flows.
