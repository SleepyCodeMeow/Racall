"""Chat Completions JSON/SSE state machine; interrupted results fail closed."""

import httpx

from .events import EventDecoder, response_chunks
from .payloads import CONTENT_LIMIT, CompletionProtocolError, content_object, json_object, utf8_size


def _no_tools_or_refusal(message: dict):
    if any(message.get(key) is not None for key in ("tool_calls", "function_call")):
        raise CompletionProtocolError("Tool calls cannot be used as a JSON completion.")
    if message.get("refusal") is not None:
        raise CompletionProtocolError("A refusal cannot be used as a JSON completion.")


def full_response(response: dict) -> dict:
    choices = response.get("choices")
    if "error" in response or not isinstance(choices, list) or len(choices) != 1:
        raise CompletionProtocolError("The provider did not return exactly one completion.")
    choice = choices[0]
    if not isinstance(choice, dict):
        raise CompletionProtocolError("The provider completion choice is invalid.")
    if "index" in choice and (type(choice["index"]) is not int or choice["index"] != 0):
        raise CompletionProtocolError("The provider returned an unexpected choice index.")
    # Some compatible servers ignore stream and omit finish_reason entirely.
    # An explicitly reported interruption must never be accepted.
    if "finish_reason" in choice and choice["finish_reason"] != "stop":
        raise CompletionProtocolError("The provider did not finish the completion normally.")
    message = choice.get("message")
    if not isinstance(message, dict):
        raise CompletionProtocolError("The provider completion message is invalid.")
    _no_tools_or_refusal(message)
    return content_object(message.get("content"))


async def stream_response(response: httpx.Response) -> dict:
    parser = EventDecoder()
    content: list[str] = []
    content_size = 0
    finished = False
    async for chunk in response_chunks(response):
        for event in parser.feed(chunk):
            if event == "[DONE]":
                if not finished:
                    raise CompletionProtocolError("The provider ended before finishing the completion.")
                return content_object("".join(content))
            payload = json_object(event)
            choices = payload.get("choices")
            if "error" in payload or not isinstance(choices, list):
                raise CompletionProtocolError("The provider event has no valid completion choice.")
            if not choices and "usage" in payload:
                continue
            if len(choices) != 1 or not isinstance(choices[0], dict):
                raise CompletionProtocolError("The provider event must contain exactly one choice.")
            choice = choices[0]
            if type(choice.get("index")) is not int or choice["index"] != 0:
                raise CompletionProtocolError("The provider returned an unexpected choice index.")
            if finished:
                raise CompletionProtocolError("The provider sent content after the completed choice.")
            delta = choice.get("delta")
            if not isinstance(delta, dict):
                raise CompletionProtocolError("The provider event delta is invalid.")
            _no_tools_or_refusal(delta)
            value = delta.get("content")
            if value is not None:
                if not isinstance(value, str):
                    raise CompletionProtocolError("The provider content delta is invalid.")
                content_size += utf8_size(value)
                if content_size > CONTENT_LIMIT:
                    raise CompletionProtocolError("The completion content is too large.")
                content.append(value)
            # Reasoning, role and other metadata are deliberately not answer text.
            reason = choice.get("finish_reason")
            if reason is not None:
                if reason != "stop":
                    raise CompletionProtocolError("The provider did not finish the completion normally.")
                finished = True
    raise CompletionProtocolError("The provider stream ended before its completion marker.")
