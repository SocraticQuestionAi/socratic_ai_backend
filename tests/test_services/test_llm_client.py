"""
Tests for LLM client service.

Tests the LLM client wrapper with mocked API responses.
"""
from unittest.mock import MagicMock, patch

import pytest
from pydantic import BaseModel

from app.services.llm_client import LLMClient, get_llm_client


class SampleResponse(BaseModel):
    """Sample response model for testing."""

    message: str
    score: float


class TestLLMClientInit:
    """Tests for LLM client initialization."""

    @patch("app.services.llm_client.OpenAI")
    @patch("app.services.llm_client.instructor")
    def test_init_with_defaults(self, mock_instructor, mock_openai):
        """Test LLM client initializes with default settings."""
        mock_openai_instance = MagicMock()
        mock_openai.return_value = mock_openai_instance

        client = LLMClient()

        # Should use settings defaults
        assert client.model is not None
        assert client.temperature is not None
        assert client.max_tokens is not None

    @patch("app.services.llm_client.OpenAI")
    @patch("app.services.llm_client.instructor")
    def test_init_with_custom_params(self, mock_instructor, mock_openai):
        """Test LLM client initializes with custom parameters."""
        mock_openai_instance = MagicMock()
        mock_openai.return_value = mock_openai_instance

        client = LLMClient(
            model="custom-model",
            temperature=0.5,
            max_tokens=2000,
        )

        assert client.model == "custom-model"
        assert client.temperature == 0.5
        assert client.max_tokens == 2000


class TestGenerateStructured:
    """Tests for structured output generation."""

    @patch("app.services.llm_client.OpenAI")
    @patch("app.services.llm_client.instructor")
    def test_generate_structured_returns_model(self, mock_instructor, mock_openai):
        """Test generate_structured returns the response model."""
        # Setup mocks
        mock_openai_instance = MagicMock()
        mock_openai.return_value = mock_openai_instance

        mock_client = MagicMock()
        mock_instructor.from_openai.return_value = mock_client

        expected_response = SampleResponse(message="Test response", score=0.95)
        mock_client.chat.completions.create.return_value = expected_response

        # Execute
        client = LLMClient()
        result = client.generate_structured(
            response_model=SampleResponse,
            system_prompt="You are a test assistant.",
            user_prompt="Generate a test response.",
        )

        # Verify
        assert result == expected_response
        assert isinstance(result, SampleResponse)

    @patch("app.services.llm_client.OpenAI")
    @patch("app.services.llm_client.instructor")
    def test_generate_structured_uses_correct_params(self, mock_instructor, mock_openai):
        """Test generate_structured passes correct parameters."""
        mock_openai_instance = MagicMock()
        mock_openai.return_value = mock_openai_instance

        mock_client = MagicMock()
        mock_instructor.from_openai.return_value = mock_client

        mock_client.chat.completions.create.return_value = SampleResponse(
            message="Test", score=0.5
        )

        client = LLMClient(model="test-model", temperature=0.7, max_tokens=1000)
        client.generate_structured(
            response_model=SampleResponse,
            system_prompt="System prompt",
            user_prompt="User prompt",
            temperature=0.3,
            max_retries=5,
        )

        # Verify call arguments
        mock_client.chat.completions.create.assert_called_once()
        call_kwargs = mock_client.chat.completions.create.call_args.kwargs

        assert call_kwargs["model"] == "test-model"
        assert call_kwargs["response_model"] == SampleResponse
        assert call_kwargs["max_retries"] == 5
        assert call_kwargs["temperature"] == 0.3  # Override
        assert call_kwargs["max_tokens"] == 1000
        assert len(call_kwargs["messages"]) == 2


class TestGenerateStructuredWithContext:
    """Tests for structured generation with conversation context."""

    @patch("app.services.llm_client.OpenAI")
    @patch("app.services.llm_client.instructor")
    def test_generate_with_context_includes_history(self, mock_instructor, mock_openai):
        """Test that conversation history is included in messages."""
        mock_openai_instance = MagicMock()
        mock_openai.return_value = mock_openai_instance

        mock_client = MagicMock()
        mock_instructor.from_openai.return_value = mock_client

        mock_client.chat.completions.create.return_value = SampleResponse(
            message="Test", score=0.5
        )

        client = LLMClient()
        history = [
            {"role": "user", "content": "Previous message"},
            {"role": "assistant", "content": "Previous response"},
        ]

        client.generate_structured_with_context(
            response_model=SampleResponse,
            system_prompt="System prompt",
            messages=history,
        )

        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        messages = call_kwargs["messages"]

        # Should have system + history
        assert len(messages) == 3
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "Previous message"


class TestGenerateText:
    """Tests for unstructured text generation."""

    @patch("app.services.llm_client.OpenAI")
    @patch("app.services.llm_client.instructor")
    def test_generate_text_returns_string(self, mock_instructor, mock_openai):
        """Test generate_text returns a string."""
        mock_openai_instance = MagicMock()
        mock_openai.return_value = mock_openai_instance

        # Setup response mock
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Generated text response"
        mock_openai_instance.chat.completions.create.return_value = mock_response

        client = LLMClient()
        result = client.generate_text(
            system_prompt="You are a test assistant.",
            user_prompt="Generate text.",
        )

        assert result == "Generated text response"
        assert isinstance(result, str)

    @patch("app.services.llm_client.OpenAI")
    @patch("app.services.llm_client.instructor")
    def test_generate_text_handles_none_content(self, mock_instructor, mock_openai):
        """Test generate_text handles None content gracefully."""
        mock_openai_instance = MagicMock()
        mock_openai.return_value = mock_openai_instance

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = None
        mock_openai_instance.chat.completions.create.return_value = mock_response

        client = LLMClient()
        result = client.generate_text(
            system_prompt="System",
            user_prompt="User",
        )

        assert result == ""


class TestGetLLMClient:
    """Tests for the factory function."""

    @patch("app.services.llm_client.OpenAI")
    @patch("app.services.llm_client.instructor")
    def test_get_llm_client_returns_instance(self, mock_instructor, mock_openai):
        """Test get_llm_client returns an LLMClient instance."""
        mock_openai.return_value = MagicMock()

        client = get_llm_client()

        assert isinstance(client, LLMClient)

    @patch("app.services.llm_client.OpenAI")
    @patch("app.services.llm_client.instructor")
    def test_get_llm_client_with_params(self, mock_instructor, mock_openai):
        """Test get_llm_client passes parameters correctly."""
        mock_openai.return_value = MagicMock()

        client = get_llm_client(model="custom-model", temperature=0.8)

        assert client.model == "custom-model"
        assert client.temperature == 0.8
