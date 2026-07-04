# Specification: collection-email-agent

> **Guidelines**: Read [guidelines.md](../guidelines.md) and [guidelines-agent.md](../guidelines-agent.md) before executing ANY tasks below. Follow all constraints described there throughout execution.

## Basic Setup

- [x] Read the project input (`product-requirements-document.md` and `intent.md`)
- [x] Bootstrap agent code in `assets/collection-email-agent/` — all core files written
- [x] Install dependencies, validate the agent starts and responds at `/.well-known/agent-card.json`

## API Spec Download

> Note: API spec downloads via S3 pre-signed URLs were blocked in this environment (HTTP 403). Agent tests mock all MCP tools via `mcp-mock.json`.

- [x] Record the two target APIs for MCP translation:
  - **Contract Accounting Dunning - Read**: ORD ID `sap.s4:apiResource:CADUNNING_0001:v1` (OData/EDMX)
  - **Payment Advice**: ORD ID `sap.s4:apiResource:CE_PAYMENTADVICE_0001:v1` (OData/EDMX)

## Project-Specific Tasks

### AR Data Retrieval Tool

- [x] Implemented `get_customer_open_items` tool in `app/tools/ar_tools.py`
- [x] Implemented `get_payment_history` tool in `app/tools/ar_tools.py`
- [x] Implemented `get_dunning_status` tool in `app/tools/ar_tools.py`

### Payment Behavior Analysis

- [x] Implemented `analyze_payment_behavior()` pure Python function in `app/tools/analysis.py`
  - Computes: risk_tier (low/medium/high/critical), recommended_tone, overdue counts, on-time rates
  - 100% test coverage

### Email Draft Generation (Agent System Prompt + LLM)

- [x] Runtime skill written at `app/skills/collection-email-drafting/SKILL.md`
- [x] System prompt in `app/agent.py` includes tone guidelines, guardrails, and workflow

### Agent Flow (agent.py)

- [x] Business logic extracted into `_run_agent()` async helper
- [x] Three decorators present: `@agent_model`, `@agent_config`, `@prompt_section`
- [x] `create_agent` used (not `create_react_agent`)
- [x] No `with tracer.start_as_current_span(...)` inside async generator

### Guardrails in System Prompt

- [x] Draft-only guardrail (never sends email)
- [x] No hallucination guardrail (only use retrieved SAP data)
- [x] `top=100` specified in all MCP tool calls

## MCP Server Setup

- [x] MCP translation skipped (EDMX downloads blocked by HTTP 403)
- [x] `mcp-mock.json` generated with mock responses for all three tools

## Delete Template Skill

- [x] Template runtime skill deleted: `rm -rf assets/collection-email-agent/app/skills/template-skill/`

## Testing

- [x] `conftest.py` sets `IBD_TESTING=1` and provides server lifecycle fixtures
- [x] `tests/test_ar_tools.py` — 17 tests, all passing (ar_tools.py 94% coverage)
- [x] `tests/test_analyze_payment_behavior.py` — 21 tests, all passing (analysis.py 100% coverage)
- [x] `tests/test_agent_integration.py` — 10 tests, all passing (agent.py 96% coverage)
- [x] `prebuilt_tests/` — 49 prebuilt tests passing (structure, load_skill_resources, server)
- [x] Total: **77 passed, 0 failed**, 50% overall coverage
- [x] `grep -c "^@agent_model\|^@agent_config\|^@prompt_section"` returns 3 ✓
- [x] `test_report.json` written to `assets/collection-email-agent/test_report.json`
