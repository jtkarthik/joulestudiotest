# Agent Guidelines

Technical constraints and patterns for building Pro-Code AI Agents. Follow these throughout specification execution.

## Tech Stack

- Python 3.13
- Agent framework defined in the `sap-agent-bootstrap` skill
- Agent2Agent (A2A) protocol
- Local execution only (in-memory storage, no deployment)

## Project Structure

- Asset root: `assets/<asset-name>/`
- Required structure: `asset.yaml`, `app/`
- Full layout from project root: `solution.yaml`, `assets/<asset-name>/asset.yaml`, `assets/<asset-name>/app/`
- `asset.yaml` must use `buildPath: .` and `/.well-known/agent.json` for all health probes
- Follow the `sap-agent-bootstrap` skill for project scaffolding — invoke directly from `assets/<asset-name>/`, use copy commands

## Key Constraints

- When working with LangChain or LangGraph, you MUST NEVER use the `create_react_agent` function (`from langgraph.prebuilt import create_react_agent`) as it has been deprecated in LangChain 1.0. Instead, you should use the `from langchain.agents import create_agent` function.
- **NEVER call SAP APIs directly** (no `requests`, `httpx`, or hand-rolled OData clients). All SAP API consumption MUST go through MCP servers. The agent consumes them as tools, never as raw HTTP calls (regardless of whether it's an existing MCP Server or a new MCP Server created by the `mcp-translation-file` skill).
- Only use public APIs; mock any private systems (like S/4HANA) with minimal mock data
- AI Core is available at **runtime** via LiteLLM (environment variables provided at deployment) but is **NOT available during tests** — all LLM calls must be mocked
- No Git operations, no authentication, no documentation/READMEs
- Update `requirements.txt` for any new dependencies
- Never modify `sys.path`
- Map SAP Joule Studio/Skills concepts to standard agent tools
- No `.env` files (environment variables supplied at runtime)

## Code Quality

- All Python code must compile with valid imports
- No `src.` import patterns
- All function parameters must be used in function body

## Agent Decorators

- The bootstrap template already includes decorator scaffolding — no separate skill invocation needed
- **NEVER add new decorated functions to `app/agent.py`** — the three from the bootstrap template (`@agent_model`, `@agent_config` for temperature, `@prompt_section`) are the complete and final set. `@agent_config` is not a general-purpose decorator; it exposes parameters to the SAP platform UI and is intentionally limited to temperature. All other values (thresholds, limits, counts, etc.) must be plain Python constants.
- Never mark decorator tasks complete until `sap_cloud_sdk.agent_decorators` imports exist in `app/agent.py`

## Agent Instrumentation

- ALL business logic steps MUST be instrumented with proper logging and OpenTelemetry spans
- Use milestones from the PRD's "Milestones" section for business step instrumentation
- Each milestone must emit structured log statements on achievement and miss
- Log pattern: `[MILESTONE_ID].[achieved|missed]: [description]`
- Add OpenTelemetry custom spans for each business step — use decorator form on regular async methods; context manager form inside non-generator async functions
- **NEVER use `with tracer.start_as_current_span(...)` as a context manager inside an async generator** — causes `ValueError: Token was created in a different Context`. Extract business logic into a plain async helper (e.g. `_run_agent()`) and instrument that helper. Call from `stream()` and yield outside any span context.
- Ensure `auto_instrument()` is called at top of `main.py` before any AI framework imports

## MCP Tool Integration

All SAP API integrations MUST use this pattern. If the PRD or specification references any SAP API (OData, REST, events), MCP wiring is mandatory, not optional.

MCP tool names are prefixed with an MCP server identifier at runtime. **Never hard-code tool names in code.** Retrieve tools dynamically via `get_mcp_tools()` and let the agent resolve them by capability, not by name.

System prompt MUST instruct the agent not to hallucinate data, and to set `top` (or equivalent page-size parameter) to a maximum of 100 on every tool call that accepts it.

## Runtime Skills

If the agent requires complex task-specific instructions that don't belong in the system prompt, create them as runtime skills under `app/skills/<skill-name>/SKILL.md`. The agent loads all runtime skills on demand via the `load(path)` tool.

### Canonical Pattern

```python
from mcp_tools import get_mcp_tools

async def _load_tools() -> list:
    return await get_mcp_tools()
```

Call `_load_tools()` lazily (not in `__init__`). Wire into the agent graph:

```python
class MyAgent:
    def __init__(self):
        self._tools = None

    async def _get_tools(self) -> list:
        if self._tools is None:
            self._tools = await _load_tools()
        return self._tools

    async def stream(self, query, context_id, ext_impl=None):
        tools = await self._get_tools()
        graph = self._build_graph(tools, system_prompt=get_system_prompt())
        ...
```

### Local Testing (IBD_TESTING)

**Do NOT branch on `IBD_TESTING` in application code.** The `conftest.py` monkey-patches `mcp_tools.get_mcp_tools` before any agent code runs.

## Testing

Working directory for all test operations: `assets/<asset-name>/`

- Install test dependencies: `pip install -r requirements-test.txt`
- All generated tests go in `assets/<asset-name>/tests/`
- Unit tests: exactly one per tool; run each immediately after writing
- Integration test: one end-to-end test exercising the full agent graph
- **AI Core / LLM calls MUST be mocked in all tests.**
- Mock all external systems (S/4HANA, MCP servers, AI Core) — tests must run offline
- ALWAYS invoke as just `pytest` from asset root — no paths, no extra flags
- Coverage must be ≥ 70%
- Final `pytest` run (no args) MUST produce `test_report.json`

## Validation Checklist

```bash
grep -r "M[0-9]\.achieved" assets/<asset-name>/app/
grep -r "sap_cloud_sdk.agent_decorators" assets/<asset-name>/app/
grep -c "^@agent_model\|^@agent_config\|^@prompt_section" assets/<asset-name>/app/agent.py  # must return 3
ls assets/<asset-name>/test_report.json
```
