"""ChatLLM: raw LLM message interface with function calling support.

ChatLLM is designed specifically for the AgentLoop ReAct cycle.
"""

from __future__ import annotations

import html
import json
import os
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from src.providers.content_filter import is_content_filter_triggered
from src.providers.llm import build_llm


def _dedupe_finish_reason(raw: str) -> str:
    """Relays (OpenRouter) emit finish_reason per chunk; AIMessageChunk.__add__
    concatenates into 'stopstop', 'tool_callstool_calls', etc. Return the
    canonical suffix so ReAct equality checks survive.
    """
    return next(
        (m for m in ("tool_calls", "function_call", "content_filter", "length", "stop")
         if raw.endswith(m)),
        raw,
    )


@dataclass
class ToolCallRequest:
    """Tool call request returned by the LLM.

    Attributes:
        id: Tool call ID (used to match tool_result messages).
        name: Tool name.
        arguments: Tool argument dict.
        thought_signature: Gemini thinking-model signature to echo on the next turn.
        extra_content: Provider-specific tool-call metadata that must be
            replayed with the assistant turn, such as Gemini thought signatures.
    """

    id: str
    name: str
    arguments: Dict[str, Any]
    thought_signature: Optional[str] = None
    extra_content: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMResponse:
    """LLM response.

    Attributes:
        content: Text content (final answer or thinking text).
        tool_calls: List of tool call requests.
        reasoning_content: Optional thinking trace surfaced by reasoning models.
        finish_reason: Finish reason string.
        usage_metadata: Real token counts reported by the provider, when
            available. Mirrors LangChain's ``AIMessage.usage_metadata`` —
            ``{"input_tokens": int, "output_tokens": int, "total_tokens": int}``.
            ``None`` if the provider did not return usage information; callers
            should fall back to a heuristic in that case.
        content_filter_triggered: ``True`` when the provider blocked the
            response via content moderation (e.g. DashScope/Qwen content
            moderation filter, ``finish_reason == "content_filter"``).
    """

    content: Optional[str] = None
    tool_calls: List[ToolCallRequest] = field(default_factory=list)
    reasoning_content: Optional[str] = None
    finish_reason: str = "stop"
    usage_metadata: Optional[Dict[str, int]] = None
    content_filter_triggered: bool = False

    @property
    def has_tool_calls(self) -> bool:
        """Return True if the response contains tool calls."""
        return len(self.tool_calls) > 0


class ProviderStreamError(RuntimeError):
    """Raised when provider streaming fails before a complete response."""

    def __init__(self, *, provider: str, model: str, original: Exception) -> None:
        """Initialize a provider-contextual stream error.

        Args:
            provider: Effective provider name.
            model: Effective model name.
            original: Original exception from the stream path.
        """
        self.provider = provider
        self.model = model
        self.original = original
        self.status_code: Optional[int] = getattr(original, "status_code", None)
        safe_message = _redact_provider_error(str(original))
        super().__init__(
            f"provider_stream_error provider={provider} model={model}: "
            f"{type(original).__name__}: {safe_message}"
        )

    @property
    def retryable(self) -> bool:
        """Whether a single retry could plausibly succeed.

        Returns:
            False for deterministic client errors (4xx other than 408/429),
            True for everything else — timeouts, rate limits, 5xx, and
            transport errors that carry no HTTP status.
        """
        if self.status_code is None:
            return True
        if self.status_code in (408, 429):
            return True
        return not 400 <= self.status_code < 500


def _redact_provider_error(message: str) -> str:
    """Redact configured secret/proxy values from provider errors."""
    redacted = message
    sensitive_markers = ("KEY", "TOKEN", "SECRET", "PASSWORD", "PASS", "PROXY")
    for key, value in os.environ.items():
        if not value or len(value) < 8:
            continue
        if any(marker in key.upper() for marker in sensitive_markers):
            redacted = redacted.replace(value, "[redacted]")
    return redacted


_DSML_BAR = r"(?:\|\||｜｜)"
_DSML_TAG = rf"{_DSML_BAR}\s*DSML\s*{_DSML_BAR}"
_DSML_TOOL_CALLS_RE = re.compile(
    rf"<\s*{_DSML_TAG}\s*tool_calls\s*>(?P<body>.*?)"
    rf"</\s*{_DSML_TAG}\s*tool_calls\s*>",
    re.DOTALL,
)
_DSML_INVOKE_RE = re.compile(
    rf"<\s*{_DSML_TAG}\s*invoke\b(?P<attrs>[^>]*)>(?P<body>.*?)"
    rf"</\s*{_DSML_TAG}\s*invoke\s*>",
    re.DOTALL,
)
_DSML_PARAMETER_RE = re.compile(
    rf"<\s*{_DSML_TAG}\s*parameter\b(?P<attrs>[^>]*)>(?P<body>.*?)"
    rf"</\s*{_DSML_TAG}\s*parameter\s*>",
    re.DOTALL,
)
_DSML_ATTR_RE = re.compile(r"""([A-Za-z_][\w:-]*)\s*=\s*(?:"([^"]*)"|'([^']*)')""")


def _parse_dsml_attrs(raw: str) -> dict[str, str]:
    """Parse attributes from a DSML tag."""
    attrs: dict[str, str] = {}
    for match in _DSML_ATTR_RE.finditer(raw):
        attrs[match.group(1)] = html.unescape(match.group(2) or match.group(3) or "")
    return attrs


def _parse_dsml_tool_calls(content: Any) -> list[ToolCallRequest]:
    """Parse DeepSeek-style DSML tool calls embedded as assistant content."""
    if not isinstance(content, str):
        return []

    stripped = content.strip()
    blocks = list(_DSML_TOOL_CALLS_RE.finditer(stripped))
    if not blocks:
        return []

    outside = _DSML_TOOL_CALLS_RE.sub("", stripped).strip()
    if outside not in {"", "/"}:
        return []

    tool_calls: list[ToolCallRequest] = []
    for block in blocks:
        for invoke in _DSML_INVOKE_RE.finditer(block.group("body")):
            invoke_attrs = _parse_dsml_attrs(invoke.group("attrs"))
            name = invoke_attrs.get("name", "").strip()
            if not name:
                continue

            arguments: dict[str, Any] = {}
            for param in _DSML_PARAMETER_RE.finditer(invoke.group("body")):
                param_attrs = _parse_dsml_attrs(param.group("attrs"))
                param_name = param_attrs.get("name", "").strip()
                if param_name:
                    arguments[param_name] = html.unescape(param.group("body")).strip()

            tool_calls.append(
                ToolCallRequest(
                    id=f"dsml_call_{len(tool_calls) + 1}",
                    name=name,
                    arguments=arguments,
                )
            )

    return tool_calls


def _extract_embedded_thinking(
    content: Any,
    existing_reasoning: Optional[str] = None,
) -> tuple[str, Optional[str]]:
    """Extract embedded <think>...</think> or dangling </think> traces from assistant content."""
    if not isinstance(content, str):
        return content if isinstance(content, str) else "", existing_reasoning

    reasoning_parts: list[str] = []
    if existing_reasoning and str(existing_reasoning).strip():
        reasoning_parts.append(str(existing_reasoning).strip())

    # 1. Standard <think>...</think>
    think_pattern = re.compile(r"<\s*think\b[^>]*>(?P<body>.*?)<\s*/\s*think\s*>", re.DOTALL | re.IGNORECASE)
    for m in think_pattern.finditer(content):
        body = m.group("body").strip()
        if body:
            reasoning_parts.append(body)
    cleaned = think_pattern.sub("", content)

    # 2. Dangling </think> (missing opening <think> tag)
    if "</think>" in cleaned.lower():
        parts = re.split(r"<\s*/\s*think\s*>", cleaned, flags=re.IGNORECASE, maxsplit=1)
        dangling_body = parts[0].strip()
        if dangling_body:
            reasoning_parts.append(dangling_body)
        cleaned = parts[1] if len(parts) > 1 else ""

    combined_reasoning = "\n\n".join(p for p in reasoning_parts if p) or None
    return cleaned.strip(), combined_reasoning


_TOOL_CALL_BLOCK_RE = re.compile(
    r"<\s*tool_call\b[^>]*>(?P<body>.*?)<\s*/\s*tool_call\s*>",
    re.DOTALL | re.IGNORECASE,
)
_FUNC_TAG_RE = re.compile(
    r"<\s*function(?P<attrs>[^>]*)>(?P<body>.*?)<\s*/\s*function\s*>",
    re.DOTALL | re.IGNORECASE,
)
_PARAM_TAG_RE = re.compile(
    r"<\s*parameter(?P<attrs>[^>]*)>(?P<body>.*?)<\s*/\s*parameter\s*>",
    re.DOTALL | re.IGNORECASE,
)
_EMBEDDED_PREFIXES = (
    "<||dsml||tool_calls",
    "<｜｜dsml｜｜tool_calls",
    "<tool_call",
    "<function",
    "<think",
    "</think",
)


def _extract_name_from_tag_attrs(attrs_str: str) -> str:
    """Extract tool or parameter name from tag attribute strings."""
    attrs_str = (attrs_str or "").strip()
    if not attrs_str:
        return ""
    if attrs_str.startswith("="):
        val = attrs_str[1:].strip()
        if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
            return val[1:-1].strip()
        return val.split()[0].strip()
    match = re.search(r'\bname\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|([^\s>]+))', attrs_str, re.IGNORECASE)
    if match:
        return (match.group(1) or match.group(2) or match.group(3) or "").strip()
    return ""


def _parse_xml_tool_calls(content: Any) -> tuple[str, list[ToolCallRequest]]:
    """Parse Hermes / Qwen / Ornith XML-style <tool_call> blocks."""
    if not isinstance(content, str):
        return "", []

    stripped = content.strip()
    blocks = list(_TOOL_CALL_BLOCK_RE.finditer(stripped))
    if not blocks:
        return stripped, []

    tool_calls: list[ToolCallRequest] = []
    for block in blocks:
        body = block.group("body").strip()
        funcs = list(_FUNC_TAG_RE.finditer(body))
        if funcs:
            for f in funcs:
                name = _extract_name_from_tag_attrs(f.group("attrs"))
                fbody = f.group("body").strip()
                params = list(_PARAM_TAG_RE.finditer(fbody))
                args: dict[str, Any] = {}
                if params:
                    for p in params:
                        pname = _extract_name_from_tag_attrs(p.group("attrs"))
                        pbody = html.unescape(p.group("body")).strip()
                        if pbody.startswith(("{", "[", '"', "true", "false", "null")) or pbody.isdigit():
                            try:
                                args[pname] = json.loads(pbody)
                            except Exception:
                                args[pname] = pbody
                        else:
                            args[pname] = pbody
                elif fbody.startswith("{") and fbody.endswith("}"):
                    try:
                        args = json.loads(fbody)
                    except Exception:
                        args = {"input": fbody}
                elif fbody:
                    args = {"command": fbody}
                if name:
                    tool_calls.append(
                        ToolCallRequest(
                            id=f"call_{len(tool_calls) + 1}",
                            name=name,
                            arguments=args,
                        )
                    )
        elif body.startswith("{") and body.endswith("}"):
            try:
                data = json.loads(body)
                name = data.get("name") or data.get("function") or ""
                args = data.get("arguments") or data.get("parameters") or data.get("input") or {}
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except Exception:
                        pass
                if name:
                    tool_calls.append(
                        ToolCallRequest(
                            id=f"call_{len(tool_calls) + 1}",
                            name=name,
                            arguments=args if isinstance(args, dict) else {"input": args},
                        )
                    )
            except Exception:
                pass

    cleaned = _TOOL_CALL_BLOCK_RE.sub("", stripped).strip()
    return cleaned, tool_calls


def _parse_embedded_tool_calls(content: Any) -> tuple[str, list[ToolCallRequest]]:
    """Parse both DSML and XML/JSON tool calls embedded in assistant content."""
    if not isinstance(content, str):
        return "", []

    dsml_calls = _parse_dsml_tool_calls(content)
    if dsml_calls:
        return "", dsml_calls

    cleaned_content, xml_calls = _parse_xml_tool_calls(content)
    if xml_calls:
        return cleaned_content, xml_calls

    return content, []


def _is_possible_embedded_tool_call_prefix(content: str) -> bool:
    """Return True while buffered stream text could still be an embedded tool call."""
    compact = re.sub(r"\s+", "", content.lstrip()[:80]).lower()
    if not compact:
        return True
    return any(prefix.startswith(compact) or compact.startswith(prefix) for prefix in _EMBEDDED_PREFIXES)


class ChatLLM:
    """LLM chat client with function calling support.

    Uses build_llm() to obtain a ChatOpenAI instance and bind_tools() to attach tool definitions.

    Attributes:
        model_name: Model name.
    """

    def __init__(self, model_name: Optional[str] = None) -> None:
        """Initialize ChatLLM.

        Args:
            model_name: Model name; defaults to the environment variable value.
        """
        self.model_name = model_name
        self._llm = build_llm(model_name=model_name)

    def chat(self, messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]] = None, timeout: Optional[int] = None) -> LLMResponse:
        """Call the LLM synchronously.

        Args:
            messages: Message list (OpenAI format).
            tools: Tool definition list (OpenAI function calling format).
            timeout: Optional per-call timeout in seconds.

        Returns:
            LLMResponse.
        """
        llm = self._llm.bind_tools(tools) if tools else self._llm
        config = {"timeout": timeout} if timeout else {}
        ai_message = llm.invoke(messages, config=config)
        return self._parse_response(ai_message)

    def stream_chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        on_text_chunk: Optional[Any] = None,
        on_reasoning_chunk: Optional[Any] = None,
        timeout: Optional[int] = None,
        should_cancel: Optional[Callable[[], bool]] = None,
    ) -> LLMResponse:
        """Stream the LLM and optionally forward text deltas (e.g. thinking).

        Iterates AIMessageChunk; text deltas invoke ``on_text_chunk`` and
        reasoning-only deltas invoke ``on_reasoning_chunk``. Aggregates chunks
        into one response. Stream failures are explicit provider errors.

        Args:
            messages: Messages in OpenAI format.
            tools: Tool definitions for function calling.
            on_text_chunk: Optional callback ``(delta: str) -> None``.
            on_reasoning_chunk: Optional callback ``(delta: str) -> None``.
            timeout: Optional per-call timeout in seconds.
            should_cancel: Optional predicate polled per chunk; when it returns
                True the stream stops early and the partial response is returned.
                Lets a caller abort a live stream promptly (cooperative cancel).

        Returns:
            Parsed ``LLMResponse``.
        """
        try:
            llm = self._llm.bind_tools(tools) if tools else self._llm
            config = {"timeout": timeout} if timeout else {}
            accumulated = None
            pending_text = ""
            possible_embedded_text = True
            for chunk in llm.stream(messages, config=config):
                if should_cancel and should_cancel():
                    break
                if chunk.content and on_text_chunk:
                    if possible_embedded_text:
                        pending_text += chunk.content
                        if _is_possible_embedded_tool_call_prefix(pending_text):
                            pass
                        else:
                            possible_embedded_text = False
                            on_text_chunk(pending_text)
                            pending_text = ""
                    else:
                        on_text_chunk(chunk.content)
                reasoning = getattr(chunk, "additional_kwargs", {}).get("reasoning_content")
                if reasoning and not chunk.content and on_reasoning_chunk:
                    on_reasoning_chunk(reasoning)
                accumulated = chunk if accumulated is None else accumulated + chunk
            if accumulated is None:
                return LLMResponse(content="", tool_calls=[], finish_reason="stop")
            response = self._parse_response(accumulated)
            if pending_text and not (response.has_tool_calls and response.content == ""):
                on_text_chunk(pending_text)
            return response
        except Exception as exc:
            provider = os.getenv("LANGCHAIN_PROVIDER", "openai").strip().lower() or "openai"
            model = self.model_name or os.getenv("LANGCHAIN_MODEL_NAME", "").strip() or "(unset)"
            raise ProviderStreamError(provider=provider, model=model, original=exc) from exc

    @staticmethod
    def _tool_call_thought_signature_maps(ai_message: Any) -> tuple[dict[str, str], dict[int, str]]:
        """Return Gemini thought signatures captured by ``ChatOpenAIWithReasoning``."""
        by_id: dict[str, str] = {}
        by_index: dict[int, str] = {}
        additional_kwargs = getattr(ai_message, "additional_kwargs", {})
        entries = additional_kwargs.get("tool_call_thought_signatures", [])

        if isinstance(entries, dict):
            entries = [entries]
        if not isinstance(entries, list):
            return by_id, by_index

        for entry in entries:
            if not isinstance(entry, dict):
                continue
            signature = entry.get("thought_signature")
            if not signature:
                continue
            if entry.get("id"):
                by_id[str(entry["id"])] = signature
            index = entry.get("index")
            if isinstance(index, int):
                by_index[index] = signature
        return by_id, by_index

    @staticmethod
    def _parse_response(ai_message: Any) -> LLMResponse:
        """Convert a LangChain AIMessage (or AIMessageChunk) to ``LLMResponse``.

        Single source for reasoning: ``additional_kwargs["reasoning_content"]``
        combined with any inline ``<think>...</think>`` traces.
        """
        usage = getattr(ai_message, "usage_metadata", None)
        if usage is not None and not isinstance(usage, dict):
            try:
                usage = dict(usage)
            except (TypeError, ValueError):
                usage = None
        additional_kwargs = getattr(ai_message, "additional_kwargs", {}) or {}
        thought_signatures_by_id, thought_signatures_by_index = (
            ChatLLM._tool_call_thought_signature_maps(ai_message)
        )
        raw_tool_calls = additional_kwargs.get("tool_calls") or []
        raw_by_id = {
            raw.get("id"): raw
            for raw in raw_tool_calls
            if isinstance(raw, dict) and raw.get("id")
        }

        # 1. Extract embedded thinking (both <think>...</think> and dangling </think>)
        clean_content, extracted_reasoning = _extract_embedded_thinking(
            ai_message.content, additional_kwargs.get("reasoning_content")
        )

        # 2. Extract native tool calls
        native_tool_calls: list[ToolCallRequest] = []
        for index, tc in enumerate(getattr(ai_message, "tool_calls", []) or []):
            extra_content = _merge_tool_call_extra_content(tc, raw_by_id.get(tc.get("id") if isinstance(tc, dict) else getattr(tc, "id", None)))
            tc_id = tc.get("id") if isinstance(tc, dict) else getattr(tc, "id", "")
            tc_name = tc.get("name") if isinstance(tc, dict) else getattr(tc, "name", "")
            tc_args = tc.get("args") if isinstance(tc, dict) else getattr(tc, "args", {})
            signature = (
                thought_signatures_by_id.get(str(tc_id))
                or thought_signatures_by_index.get(index)
                or extra_content.get("thought_signature")
            )
            if signature:
                extra_content.setdefault("thought_signature", signature)
            native_tool_calls.append(
                ToolCallRequest(
                    id=tc_id,
                    name=tc_name,
                    arguments=tc_args,
                    thought_signature=signature,
                    extra_content=extra_content,
                )
            )

        # 3. Extract embedded tool calls (DSML or XML/JSON) if native_tool_calls is empty
        if native_tool_calls:
            tool_calls = native_tool_calls
            final_content = clean_content
            has_embedded_calls = False
        else:
            final_content, embedded_tool_calls = _parse_embedded_tool_calls(clean_content)
            tool_calls = embedded_tool_calls
            has_embedded_calls = bool(embedded_tool_calls)

        finish_reason = (
            "tool_calls"
            if has_embedded_calls
            else _dedupe_finish_reason(
                ai_message.response_metadata.get("finish_reason", "stop")
            )
        )
        content_filter_triggered = is_content_filter_triggered(
            ai_message.response_metadata.get("finish_reason")
        )

        return LLMResponse(
            content=final_content,
            tool_calls=tool_calls,
            reasoning_content=extracted_reasoning,
            finish_reason=finish_reason,
            usage_metadata=usage,
            content_filter_triggered=content_filter_triggered,
        )


def _extract_tool_call_extra_content(raw_tool_call: Any) -> Dict[str, Any]:
    """Extract provider-specific tool-call metadata LangChain would drop."""
    if not isinstance(raw_tool_call, dict):
        return {}

    extra_content: Dict[str, Any] = {}
    raw_extra = raw_tool_call.get("extra_content")
    if isinstance(raw_extra, dict):
        extra_content.update(raw_extra)
        google_extra = raw_extra.get("google")
        if isinstance(google_extra, dict):
            signature = google_extra.get("thought_signature") or google_extra.get(
                "thoughtSignature"
            )
            if signature:
                extra_content["thought_signature"] = signature

    function = raw_tool_call.get("function")
    if isinstance(function, dict):
        function_extra = function.get("extra_content")
        if isinstance(function_extra, dict):
            extra_content.update(function_extra)
        if function.get("thought_signature"):
            extra_content["thought_signature"] = function["thought_signature"]

    if raw_tool_call.get("thought_signature"):
        extra_content["thought_signature"] = raw_tool_call["thought_signature"]

    return extra_content


def _merge_tool_call_extra_content(*raw_tool_calls: Any) -> Dict[str, Any]:
    """Merge provider metadata from standardized and raw tool-call shapes."""
    extra_content: Dict[str, Any] = {}
    for raw_tool_call in raw_tool_calls:
        extra_content.update(_extract_tool_call_extra_content(raw_tool_call))
    return extra_content
