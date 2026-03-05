import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Callable, Awaitable

from openai import AsyncOpenAI
from app.config import get_settings

logger = logging.getLogger(__name__)

ToolHandler = Callable[..., Awaitable[str]]


class LLMProvider(ABC):
    """Abstract base for LLM providers."""

    @abstractmethod
    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        pass

    @abstractmethod
    async def generate_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
        tool_handlers: dict[str, ToolHandler],
        max_iterations: int = 15,
        on_text: Callable[[str], None] | None = None,
    ) -> list[dict]:
        """Run a tool-calling loop. Returns the full message history.

        Args:
            on_text: Optional callback invoked when the LLM produces text content.
                     Used for streaming 'thinking' events to the frontend.
        """
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        pass


class OpenAICompatibleProvider(LLMProvider):
    """Provider for any OpenAI-compatible API (Ollama, Groq, Together, HuggingFace)."""

    def __init__(self, base_url: str, api_key: str, model: str):
        self.client = AsyncOpenAI(base_url=base_url, api_key=api_key)
        self.model = model

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
        )
        return response.choices[0].message.content or ""

    async def generate_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
        tool_handlers: dict[str, ToolHandler],
        max_iterations: int = 15,
        on_text: Callable[[str], None] | None = None,
    ) -> list[dict]:
        """Run a tool-calling loop until the LLM stops calling tools or we hit max_iterations."""
        messages = list(messages)  # don't mutate caller's list
        consecutive_text_only = 0

        for iteration in range(max_iterations):
            logger.info(f"Tool-calling iteration {iteration + 1}/{max_iterations}")

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools,
                temperature=0.3,
            )

            choice = response.choices[0]
            assistant_msg: dict[str, Any] = {"role": "assistant"}

            if choice.message.content:
                assistant_msg["content"] = choice.message.content
                if on_text:
                    on_text(choice.message.content)

            if choice.message.tool_calls:
                assistant_msg["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in choice.message.tool_calls
                ]

            messages.append(assistant_msg)

            # No tool calls — the LLM may be thinking or genuinely done.
            # Allow up to 2 consecutive text-only responses before stopping,
            # because models often emit analysis text between tool calls.
            if not choice.message.tool_calls:
                consecutive_text_only += 1
                if consecutive_text_only >= 2:
                    logger.info("LLM finished (2 consecutive text-only responses)")
                    break
                logger.info("Text-only response, continuing loop (attempt %d/2)", consecutive_text_only)
                # Nudge the model to continue using tools
                messages.append({
                    "role": "user",
                    "content": "Continue — use the tools to search for and add mods.",
                })
                continue

            consecutive_text_only = 0

            # Execute each tool call
            for tc in choice.message.tool_calls:
                fn_name = tc.function.name
                try:
                    args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    args = {}

                handler = tool_handlers.get(fn_name)
                if handler:
                    try:
                        result = await handler(**args)
                    except Exception as e:
                        logger.error(f"Tool {fn_name} failed: {e}")
                        result = json.dumps({"error": str(e)})
                else:
                    result = json.dumps({"error": f"Unknown tool: {fn_name}"})

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                })
        else:
            logger.warning(f"Hit max iterations ({max_iterations})")

        return messages

    def get_model_name(self) -> str:
        return self.model


class AnthropicProvider(LLMProvider):
    """Provider for Anthropic's Claude API (native Messages API)."""

    def __init__(self, api_key: str, model: str):
        from anthropic import AsyncAnthropic
        self.client = AsyncAnthropic(api_key=api_key)
        self.model = model

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
            temperature=0.3,
        )
        return response.content[0].text

    async def generate_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
        tool_handlers: dict[str, ToolHandler],
        max_iterations: int = 15,
        on_text: Callable[[str], None] | None = None,
    ) -> list[dict]:
        # Extract system prompt and convert messages
        system = ""
        anthropic_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system = msg["content"]
            else:
                anthropic_messages.append({"role": msg["role"], "content": msg["content"]})

        # Convert OpenAI tool format to Anthropic format
        anthropic_tools = []
        for tool in tools:
            fn = tool["function"]
            anthropic_tools.append({
                "name": fn["name"],
                "description": fn.get("description", ""),
                "input_schema": fn.get("parameters", {"type": "object", "properties": {}}),
            })

        msgs = list(anthropic_messages)
        consecutive_text_only = 0
        for iteration in range(max_iterations):
            logger.info(f"[Anthropic] Tool-calling iteration {iteration + 1}/{max_iterations}")

            response = await self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=system,
                messages=msgs,
                tools=anthropic_tools,
                temperature=0.3,
            )

            # Convert response content blocks to serializable dicts
            assistant_content = []
            for block in response.content:
                if block.type == "text":
                    assistant_content.append({"type": "text", "text": block.text})
                    if on_text:
                        on_text(block.text)
                elif block.type == "tool_use":
                    assistant_content.append({
                        "type": "tool_use",
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
                    })
            msgs.append({"role": "assistant", "content": assistant_content})

            # Extract tool use blocks
            tool_uses = [b for b in response.content if b.type == "tool_use"]
            if not tool_uses:
                consecutive_text_only += 1
                if consecutive_text_only >= 2:
                    logger.info("[Anthropic] LLM finished (2 consecutive text-only responses)")
                    break
                logger.info("[Anthropic] Text-only response, continuing loop (attempt %d/2)", consecutive_text_only)
                # Nudge the model to continue using tools (also satisfies
                # Anthropic's requirement that messages alternate user/assistant)
                msgs.append({
                    "role": "user",
                    "content": "Continue — use the tools to search for and add mods.",
                })
                continue

            consecutive_text_only = 0

            # Execute tools and build Anthropic-format tool results
            tool_results = []
            for tu in tool_uses:
                handler = tool_handlers.get(tu.name)
                if handler:
                    try:
                        result = await handler(**tu.input)
                    except Exception as e:
                        logger.error(f"Tool {tu.name} failed: {e}")
                        result = json.dumps({"error": str(e)})
                else:
                    result = json.dumps({"error": f"Unknown tool: {tu.name}"})

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tu.id,
                    "content": result,
                })

            # Anthropic expects all tool results in a single user message
            msgs.append({"role": "user", "content": tool_results})
        else:
            logger.warning(f"[Anthropic] Hit max iterations ({max_iterations})")

        return msgs

    def get_model_name(self) -> str:
        return self.model


class LLMProviderFactory:
    """Factory to create LLM providers based on configuration or registry."""

    @staticmethod
    def create(provider_name: str | None = None) -> LLMProvider:
        """Create provider using server-side env-var credentials."""
        from app.llm.registry import get_provider

        settings = get_settings()
        name = provider_name or settings.llm_provider

        # Ollama is a special local-only case not in the public registry
        if name == "ollama":
            return OpenAICompatibleProvider(
                base_url=settings.ollama_base_url,
                api_key="ollama",
                model=settings.ollama_model,
            )

        # Try registry lookup — gets base_url and type
        entry = get_provider(name)
        if entry:
            # Read API key from env-var settings (e.g. settings.groq_api_key)
            key_attr = f"{name}_api_key"
            api_key = getattr(settings, key_attr, "")
            model_attr = f"{name}_model"
            model = getattr(settings, model_attr, entry["model"])

            if entry["type"] == "anthropic":
                return AnthropicProvider(api_key=api_key, model=model)
            return OpenAICompatibleProvider(
                base_url=entry["base_url"], api_key=api_key, model=model,
            )

        # Legacy: huggingface (in settings but not public registry)
        if name == "huggingface":
            return OpenAICompatibleProvider(
                base_url="https://router.huggingface.co/v1",
                api_key=settings.huggingface_api_key,
                model=settings.huggingface_model,
            )

        raise ValueError(f"Unknown LLM provider: {name}")

    @staticmethod
    def create_from_request(
        provider_id: str,
        api_key: str,
        base_url: str | None = None,
        model: str | None = None,
    ) -> LLMProvider:
        """Create a provider using per-request user-supplied credentials.

        For known providers, only provider_id + api_key are needed.
        For custom providers, base_url (and optionally model) must be supplied.
        """
        from app.llm.registry import get_provider

        entry = get_provider(provider_id)

        if entry:
            actual_model = model or entry["model"]
            if entry["type"] == "anthropic":
                return AnthropicProvider(api_key=api_key, model=actual_model)
            return OpenAICompatibleProvider(
                base_url=base_url or entry["base_url"],
                api_key=api_key,
                model=actual_model,
            )

        # Custom / unknown provider — requires base_url
        if base_url:
            return OpenAICompatibleProvider(
                base_url=base_url,
                api_key=api_key,
                model=model or "default",
            )

        raise ValueError(f"Unknown provider '{provider_id}' and no base_url supplied")
