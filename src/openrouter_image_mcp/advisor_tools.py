"""Advisor MCP tools and rejection of unadvertised target/configuration arguments."""

import inspect
import json

from mcp.server.context import CallNext, HandlerResult, ServerRequestContext
from mcp.server.mcpserver import MCPServer
from mcp.types import CallToolResult, TextContent

from .advisor import AdvisorService, SkillPacket
from .advisor_jobs import AdvisorJobs
from .apps import ADVISOR_UI_TOOLS, ADVISOR_UI_URI, APP_ONLY_TOOLS
from .logs import redact
from .preference_tools import PREFERENCE_ARGUMENTS

ADVISOR_ARGUMENTS = {
    "list_chat_models": {"query"},
    "start_advisor_chat": {"model", "title"},
    "send_advisor_message": {"chat_id", "prompt", "skills"},
    "list_advisor_chats": set(),
    "get_advisor_chat": {"chat_id", "limit"},
    "reset_advisor_sandbox": {"chat_id"},
    "delete_advisor_chat": {"chat_id"},
    "retry_advisor_cleanup": {"chat_id"},
    "get_advisor_job": {"job_id"},
    "open_advisor_result": {"job_id"},
    "get_advisor_result": {"job_id"},
    "summarize_advisor_result": {"job_id"},
    "export_advisor_result": {"job_id"},
} | PREFERENCE_ARGUMENTS


async def enforce_advisor_arguments(ctx: ServerRequestContext, call_next: CallNext) -> HandlerResult:
    params = ctx.params or {}
    name = params.get("name")
    if ctx.method == "tools/call" and name in ADVISOR_ARGUMENTS:
        arguments = params.get("arguments") or {}
        if not isinstance(arguments, dict) or set(arguments) - ADVISOR_ARGUMENTS[name]:
            return {"isError": True, "content": [{"type": "text", "text": "Unsupported advisor argument."}]}
        if name in PREFERENCE_ARGUMENTS and "expected_revision" in arguments and type(arguments["expected_revision"]) is not int:
            return {"isError": True, "content": [{"type": "text", "text": "Expected revision must be an integer."}]}
    result = await call_next(ctx)
    if ctx.method == "tools/list" and isinstance(result, dict):
        tools = []
        for tool in result.get("tools", []):
            if tool.get("name") in ADVISOR_ARGUMENTS:
                tool = {**tool, "inputSchema": {**tool["inputSchema"], "additionalProperties": False}}
            tools.append(tool)
        return {**result, "tools": tools}
    return result


def register_advisor_tools(server: MCPServer, service: AdvisorService, jobs: AdvisorJobs, tool_errors, *, preferences=None):
    def encode(value):
        return redact(json.dumps(value, ensure_ascii=False))

    def status_result(value, *, meta=None):
        return CallToolResult(content=[TextContent(type="text", text=encode(value))],
                              structured_content=value, meta=meta)

    async def list_chat_models(query: str | None = None) -> str:
        """Discover text advisor models with tool support, pricing and context limits.

        Returns up to 100 matching models; use query to narrow the model ID or name.
        Choices use the same six-month catalog-age and approved-family filters
        as setup: Google, OpenAI, GLM, Qwen, Kimi, MiniMax and DeepSeek.
        This does not run inference. Use open_sidecar_settings to select defaults.
        """
        with tool_errors():
            models = (await preferences.view())["models"] if preferences is not None else await service.models()
            if query:
                models = [model for model in models if query.lower() in
                          (str(model.get("id")) + " " + str(model.get("name"))).lower()]
            return encode(models[:100])

    async def start_advisor_chat(model: str | None = None, title: str = "Advisor") -> str:
        """Create a local side-advisor chat for the current Northwestern sign-in.

        Choose an exact model ID or Gemini/ChatGPT/Grok/Open Weight for your saved brand
        default. Omit model to use your saved general advisor default; set these
        through open_sidecar_settings or the preferences tools. An explicit ID
        overrides this chat only. Existing chats keep their chosen model.
        Returns a chat_id for future
        messages. Each chat gets its own server-selected container. This operation
        checks the live model catalog but does not run paid inference.
        """
        with tool_errors():
            resolved = await preferences.resolve(model) if preferences is not None else {"model": model}
            return encode(await service.start(resolved["model"], title))

    async def send_advisor_message(chat_id: str, prompt: str, skills: list[SkillPacket] | None = None) -> CallToolResult:
        """Consult an existing side advisor outside the main Claude context.

        Sends only this deliberate brief, this advisor's saved history, and optional
        shareable skill text to OpenRouter. This costs inference and possibly sandbox
        compute. Skills contain name, content and optional source/version; supply
        supporting instructions as additional named packets. Do not send private
        skill files. Claude selects the skills; a local path alone is not sufficient.
        The sandbox shell has no outbound network and receives no API credentials.
        Starts a background job and returns status and its job_id only. The full
        answer stays local and appears in the advisor MCP App. The user chooses
        what to send to the parent chat. Check get_advisor_job for status or call
        open_advisor_result to reopen the viewer. App shutdown can interrupt work.
        No raw
        container/file selectors, arbitrary HTTP requests, or provider options exist.
        Generated container files can remain for 30 days. No automatic inference retry.
        """
        with tool_errors():
            return status_result(await jobs.start(chat_id, prompt, skills))

    async def list_advisor_chats() -> str:
        """List up to 100 locally saved advisor chats for the active credential/workspace."""
        with tool_errors():
            return encode(service.list())

    async def get_advisor_chat(chat_id: str, limit: int = 20) -> str:
        """Show metadata and message count for an owned local advisor chat.

        Full transcripts are not returned to the parent model. Open an advisor
        result in the MCP App to read it and deliberately select a handoff.
        The limit remains a bounded local-history inspection limit.
        """
        with tool_errors():
            chat = service.get(chat_id, limit)
            return encode({key: value for key, value in chat.items() if key != "messages"}
                          | {"message_count": len(chat["messages"]), "results": jobs.for_chat(chat_id, limit)})

    async def reset_advisor_sandbox(chat_id: str) -> str:
        """Assign a fresh sandbox to an owned chat while preserving its local history.

        Does not delete the old provider sandbox or its saved files; they expire under
        OpenRouter's inactivity policy. Does not make a provider request or run inference.
        """
        with tool_errors():
            return encode(service.reset(chat_id))

    async def delete_advisor_chat(chat_id: str) -> str:
        """Delete the owned chat's local transcript and mapping.

        Does not delete its old provider container files. Refuses while a message is
        active or uploaded skills still need cleanup. Does not run inference.
        """
        with tool_errors():
            return encode(jobs.delete_chat(chat_id))

    async def retry_advisor_cleanup(chat_id: str) -> str:
        """Retry deletion of exact owned skill uploads recorded for this chat.

        No inference charge. Does not list workspace files, inspect other containers,
        or delete generated container files. Pending cleanup blocks new inference.
        """
        with tool_errors():
            return encode(await service.cleanup(chat_id))

    async def get_advisor_job(job_id: str) -> CallToolResult:
        """Check an owned advisor job's status, cost and cleanup without reading its answer.

        Returns no prompt, skill instructions or answer. No paid inference.
        """
        with tool_errors():
            return status_result(jobs.status(job_id))

    async def open_advisor_result(job_id: str) -> CallToolResult:
        """Open the local advisor result viewer without sending its answer into this chat.

        Reading or scrolling in the MCP App does not share the result with the parent
        model. The user can preview and send a selection, full answer or summary.
        """
        with tool_errors():
            return status_result(jobs.status(job_id))

    async def get_advisor_result(job_id: str) -> CallToolResult:
        """App-only: read an owned result for display; never update the parent model context."""
        with tool_errors():
            view = jobs.view(job_id)
            return status_result(jobs.status(job_id), meta={"advisorResult": view})

    async def summarize_advisor_result(job_id: str) -> CallToolResult:
        """App-only: create a paid summary job for review before an explicit parent-chat send.

        Uses this result's owned advisor model; never sends the summary automatically.
        """
        with tool_errors():
            return status_result(await jobs.summarize(job_id))

    async def export_advisor_result(job_id: str) -> CallToolResult:
        """App-only: save an owned completed response as durable local Markdown.

        Uses a server-selected directory on this computer, outside OpenRouter's
        sandbox. No caller-supplied path, provider file fetch, or inference.
        """
        with tool_errors():
            exported = jobs.export(job_id)
            return status_result({"saved": True}, meta={"advisorExport": exported})

    for fn in (list_chat_models, start_advisor_chat, send_advisor_message,
               list_advisor_chats, get_advisor_chat, reset_advisor_sandbox,
               delete_advisor_chat, retry_advisor_cleanup, get_advisor_job,
               open_advisor_result, get_advisor_result, summarize_advisor_result,
               export_advisor_result):
        meta = None
        if fn.__name__ in ADVISOR_UI_TOOLS | APP_ONLY_TOOLS:
            ui = {"resourceUri": ADVISOR_UI_URI}
            if fn.__name__ in APP_ONLY_TOOLS:
                ui["visibility"] = ["app"]
            meta = {"ui": ui}
        server.add_tool(fn, description=inspect.cleandoc(fn.__doc__), structured_output=False, meta=meta)
