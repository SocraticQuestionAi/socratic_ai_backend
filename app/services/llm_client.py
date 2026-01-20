"""
LLM Client - Unified interface for OpenRouter and Gemini.

Supports structured outputs via instructor library for JSON Schema enforcement.
"""
import instructor
from openai import OpenAI
from pydantic import BaseModel

from app.core.config import settings


class LLMClient:
    """
    Unified LLM client supporting OpenRouter (multiple models) and direct Gemini.

    Uses instructor library for structured output enforcement via JSON Schema.
    """

    def __init__(
        self,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ):
        self.model = model or settings.DEFAULT_MODEL
        self.temperature = temperature or settings.DEFAULT_TEMPERATURE
        self.max_tokens = max_tokens or settings.DEFAULT_MAX_TOKENS

        # Initialize OpenRouter client (OpenAI-compatible)
        self._openrouter_client = OpenAI(
            api_key=settings.OPENROUTER_API_KEY,
            base_url=settings.OPENROUTER_BASE_URL,
        )

        # Wrap with instructor for structured outputs
        self.client = instructor.from_openai(self._openrouter_client)

    def generate_structured(
        self,
        response_model: type[BaseModel],
        system_prompt: str,
        user_prompt: str,
        temperature: float | None = None,
        max_retries: int = 3,
    ) -> BaseModel:
        """
        Generate a structured response using JSON Schema enforcement.

        Args:
            response_model: Pydantic model defining the expected output structure
            system_prompt: System instructions for the LLM
            user_prompt: User input/query
            temperature: Override default temperature
            max_retries: Number of retries for validation failures

        Returns:
            Instance of response_model with validated data
        """
        response = self.client.chat.completions.create(
            model=self.model,
            response_model=response_model,
            max_retries=max_retries,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature or self.temperature,
            max_tokens=self.max_tokens,
        )
        return response

    def generate_structured_with_context(
        self,
        response_model: type[BaseModel],
        system_prompt: str,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_retries: int = 3,
    ) -> BaseModel:
        """
        Generate structured response with conversation context (for Canvas flow).

        Args:
            response_model: Pydantic model for output structure
            system_prompt: System instructions
            messages: List of conversation messages [{"role": "...", "content": "..."}]
            temperature: Override temperature
            max_retries: Validation retry count

        Returns:
            Instance of response_model
        """
        all_messages = [{"role": "system", "content": system_prompt}] + messages

        response = self.client.chat.completions.create(
            model=self.model,
            response_model=response_model,
            max_retries=max_retries,
            messages=all_messages,
            temperature=temperature or self.temperature,
            max_tokens=self.max_tokens,
        )
        return response

    def generate_text(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float | None = None,
    ) -> str:
        """
        Generate unstructured text response (fallback for simple tasks).

        Args:
            system_prompt: System instructions
            user_prompt: User input
            temperature: Override temperature

        Returns:
            Raw text response
        """
        response = self._openrouter_client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature or self.temperature,
            max_tokens=self.max_tokens,
        )
        return response.choices[0].message.content or ""

    def generate_structured_with_images(
        self,
        response_model: type[BaseModel],
        system_prompt: str,
        user_prompt: str,
        images: list[dict],
        temperature: float | None = None,
        max_retries: int = 3,
    ) -> BaseModel:
        """
        Generate structured response from images (for PDF/image processing).

        Args:
            response_model: Pydantic model defining the expected output structure
            system_prompt: System instructions for the LLM
            user_prompt: User input/query
            images: List of image dicts with 'base64' and 'mime_type' keys
            temperature: Override default temperature
            max_retries: Number of retries for validation failures

        Returns:
            Instance of response_model with validated data
        """
        # Build multimodal content array
        content: list[dict] = []

        # Add images first
        for img in images:
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:{img['mime_type']};base64,{img['base64']}"
                }
            })

        # Add text prompt
        content.append({
            "type": "text",
            "text": user_prompt
        })

        response = self.client.chat.completions.create(
            model=self.model,
            response_model=response_model,
            max_retries=max_retries,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content},
            ],
            temperature=temperature or self.temperature,
            max_tokens=self.max_tokens,
        )
        return response


# Default client instance
def get_llm_client(
    model: str | None = None,
    temperature: float | None = None,
) -> LLMClient:
    """Get an LLM client instance."""
    return LLMClient(model=model, temperature=temperature)
