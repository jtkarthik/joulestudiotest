"""
Utility functions for MCP tool processing.
Provides helper functions for enhancing MCP tool descriptions and metadata.
"""
import asyncio
import hashlib
import logging
import os
import re
from typing import Any

import httpx
from langchain_core.tools import ToolException

logger = logging.getLogger(__name__)

_MCP_RETRY_ATTEMPTS = 4
_MCP_RETRY_DELAY = 4.0
MCP_MAX_RESPONSE_CHARS = int(os.environ.get("MCP_MAX_RESPONSE_CHARS", 100_000))


def _is_retryable_error(exc: Exception) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code < 400 or exc.response.status_code >= 500
    if isinstance(exc, (ExceptionGroup, BaseExceptionGroup)):
        return True
    return True


def enhance_tool_description(mcp_tool: Any) -> str:
    if mcp_tool is None:
        logger.warning("enhance_tool_description called with None tool")
        return ""
    server_label = getattr(mcp_tool, "fragment_name", mcp_tool.server_name)
    return f"[{server_label}] {mcp_tool.description or ''}".strip()


def enhance_tool_name(mcp_tool: Any) -> str:
    if mcp_tool is None:
        logger.warning("enhance_tool_name called with None tool")
        return ""
    segments = mcp_tool.server_name.split(":")
    remaining = segments[2:] if len(segments) > 2 else segments
    raw = f"{'_'.join(remaining)}__{mcp_tool.name}"
    sanitized = re.sub(r"[^a-zA-Z0-9\-_]", "_", raw)
    if len(sanitized) <= 64:
        return sanitized
    suffix = hashlib.sha256(sanitized.encode()).hexdigest()[:8]
    return f"{sanitized[:55]}_{suffix}"


async def call_mcp_tool_with_retry(agw_client: Any, mcp_tool: Any, user_token: str | None = None, **kwargs: Any) -> str:
    if mcp_tool is None:
        raise ValueError("Tool parameter cannot be None")
    last_exc: Exception | None = None
    for attempt in range(1 + _MCP_RETRY_ATTEMPTS):
        try:
            call_params = {"tool": mcp_tool, **kwargs}
            if user_token is not None:
                call_params["user_token"] = user_token
            _call_result = None
            try:
                _call_result = await agw_client.call_mcp_tool(**call_params)
            except (ExceptionGroup, BaseExceptionGroup) as eg:
                if _call_result is None:
                    raise
            if _call_result is None:
                raise RuntimeError(f"call_mcp_tool returned None for {mcp_tool.name}")
            result = str(_call_result) if _call_result else ""
            if len(result) > MCP_MAX_RESPONSE_CHARS:
                result = result[:MCP_MAX_RESPONSE_CHARS] + "\n...[truncated]"
            return result
        except Exception as e:
            if not _is_retryable_error(e):
                raise
            last_exc = e
            if attempt < _MCP_RETRY_ATTEMPTS:
                await asyncio.sleep(_MCP_RETRY_DELAY)
    raise ToolException(f"Tool '{mcp_tool.name}' failed after {1 + _MCP_RETRY_ATTEMPTS} attempts: {last_exc}") from last_exc
