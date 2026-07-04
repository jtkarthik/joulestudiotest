import logging
import time
from dataclasses import dataclass
from typing import AsyncGenerator, Literal, Sequence

from langchain.agents import create_agent
from langchain.agents.middleware import SummarizationMiddleware
from langchain_core.messages import HumanMessage
from langchain_core.tools import BaseTool
from langchain_litellm import ChatLiteLLM
from langgraph.checkpoint.memory import InMemorySaver
from sap_cloud_sdk.agent_decorators import agent_config, agent_model, prompt_section

logger = logging.getLogger(__name__)


@agent_model(
    key="config.model",
    label="LLM Model",
    description="The language model powering this agent",
)
def get_model_name() -> str:
    return "sap/anthropic--claude-3-5-sonnet"


@agent_config(
    key="config.temperature",
    label="LLM Temperature",
    description="Controls randomness of responses (0.0 = deterministic, 1.0 = creative)",
)
def get_temperature() -> float:
    return 0.0


@prompt_section(
    key="prompts.system",
    label="System Prompt",
    description="The full system prompt defining the agent's role and behavior",
    validation={"format": "markdown", "max_length": 5000},
)
def get_system_prompt() -> str:
    return """You are the collection-email-agent, an AI assistant that helps Accounts Receivable teams draft personalized collection emails for overdue invoices.

## Your Role
- Read SAP S/4HANA Accounts Receivable data (open items, payment history, dunning status) via the available tools
- Analyze customer payment behavior to understand the context before drafting
- Draft professional, personalized collection emails tailored to each customer's situation
- Present email drafts for human review — NEVER send emails autonomously

## Guardrails
- **DRAFT ONLY**: Always produce email drafts. Never claim to send or schedule emails.
- **No hallucinations**: Only reference invoice numbers, amounts, and dates that you retrieved from SAP tools. Never invent data.
- **Tone calibration**: Adjust tone based on customer history — first-time overdue vs. habitual late payer vs. at-risk account.
- **Data privacy**: Do not log or repeat sensitive financial details outside the email draft itself.
- **Human-in-the-loop**: Always end your response with "Please review and send this draft if it meets your requirements."

## Workflow
1. Call `get_customer_open_items` to retrieve outstanding invoices for the customer
2. Call `get_payment_history` to understand past payment behavior
3. Call `get_dunning_status` to check current dunning level
4. Call `analyze_payment_behavior` to get a structured behavior summary
5. Draft a collection email using the retrieved data
6. Present the draft clearly, with subject line and body separated

## Email Guidelines
- Subject: concise, professional (e.g., "Outstanding Invoice Reminder – [Invoice #]")
- Opening: address the customer by name/company if available
- Body: reference specific invoice numbers, due dates, and amounts from SAP data
- Tone: firm but respectful; escalate firmness based on dunning level
- Closing: clear call-to-action with payment instructions or contact details
- Signature: use a placeholder [Your Name / AR Team]

## Limitations
- You cannot access email systems, send messages, or modify SAP records
- If SAP data is unavailable, inform the user and ask them to check system connectivity
"""


@dataclass
class AgentResponse:
    status: Literal["input_required", "completed", "error"]
    message: str


THREAD_TTL_SECONDS = 3600  # evict threads inactive for 1 hour


class CollectionEmailAgent:
    SUPPORTED_CONTENT_TYPES = ["text", "text/plain"]

    def __init__(self):
        self.llm = ChatLiteLLM(model=get_model_name(), temperature=get_temperature())
        self._checkpointer = InMemorySaver()
        self._last_active: dict[str, float] = {}
        self._summarization_middleware = SummarizationMiddleware(
            model=self.llm,
            trigger=("tokens", 100_000),
            keep=("messages", 4),
        )

    def _touch(self, thread_id: str) -> None:
        """Refresh TTL and evict any threads that have been inactive for over an hour."""
        now = time.monotonic()
        expired = [
            tid
            for tid, ts in list(self._last_active.items())
            if now - ts > THREAD_TTL_SECONDS
        ]
        for tid in expired:
            self._checkpointer.delete_thread(tid)
            del self._last_active[tid]
            logger.info("Evicted inactive thread: %s", tid)
        self._last_active[thread_id] = now

    async def _run_agent(
        self,
        query: str,
        context_id: str,
        tools: Sequence[BaseTool] | None,
    ) -> str:
        """Run the agent graph and return the final response content."""
        system_prompt = get_system_prompt()
        if not tools:
            system_prompt += (
                "\n\nIMPORTANT: No tools are currently available. "
                "Do not attempt to call any tools. "
                "Respond to the user explaining that tools are temporarily unavailable."
            )

        tool_names = [tool.name for tool in tools] if tools else []
        logger.info("Running agent with %d tool(s): %s", len(tool_names), tool_names)

        graph = create_agent(
            self.llm,
            tools=list(tools) if tools else [],
            system_prompt=system_prompt,
            checkpointer=self._checkpointer,
            middleware=[self._summarization_middleware],
        )
        config = {"configurable": {"thread_id": context_id}}
        result = await graph.ainvoke(
            {"messages": [HumanMessage(content=query)]}, config
        )
        self._touch(context_id)
        return result["messages"][-1].content

    async def stream(
        self,
        query: str,
        context_id: str,
        tools: Sequence[BaseTool] | None = None,
    ) -> AsyncGenerator[dict, None]:
        """Stream agent responses.

        Args:
            query: User query to process
            context_id: Context identifier for the conversation
            tools: Optional sequence of LangChain tools. If None or empty, agent runs without tools.

        Yields:
            Status updates and final response with structure:
            - is_task_complete: Whether the task is complete
            - require_user_input: Whether user input is needed
            - content: The response content or status message
        """
        self._touch(context_id)
        yield {
            "is_task_complete": False,
            "require_user_input": False,
            "content": "Processing...",
        }

        try:
            response = await self._run_agent(query, context_id, tools)
            yield {
                "is_task_complete": True,
                "require_user_input": False,
                "content": response,
            }

        except Exception as e:
            logger.exception("Agent stream() failed")
            yield {
                "is_task_complete": True,
                "require_user_input": False,
                "content": f"I encountered an error while processing your request: {str(e)}. Please try again.",
            }

    async def invoke(
        self,
        query: str,
        context_id: str,
        tools: Sequence[BaseTool] | None = None,
    ) -> AgentResponse:
        """Invoke agent and return final response.

        Args:
            query: User query to process
            context_id: Context identifier for the conversation
            tools: Optional sequence of LangChain tools. If None or empty, agent runs without tools.

        Returns:
            AgentResponse with status and message
        """
        last: dict = {}
        async for chunk in self.stream(query, context_id, tools=tools):
            last = chunk
        if last.get("is_task_complete"):
            return AgentResponse(status="completed", message=last["content"])
        if last.get("require_user_input"):
            return AgentResponse(status="input_required", message=last["content"])
        return AgentResponse(
            status="error", message=last.get("content", "Unknown error")
        )
