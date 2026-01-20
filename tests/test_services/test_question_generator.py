"""
Tests for question generation service.

Tests all three workflows: document generation, similarity, and refinement.
"""
from unittest.mock import MagicMock, patch

import pytest

from app.models import QuestionType
from app.schemas.questions import (
    GeneratedQuestion,
    GeneratedQuestions,
    MCQOptionSchema,
    QuestionAnalysis,
    RefinedQuestion,
    SimilarityAnalysis,
)
from app.services.question_generator import (
    QuestionGeneratorService,
    get_question_generator,
)


class TestQuestionGeneratorInit:
    """Tests for QuestionGeneratorService initialization."""

    def test_init_with_custom_client(self, mock_llm_client):
        """Test initialization with custom LLM client."""
        service = QuestionGeneratorService(llm_client=mock_llm_client)

        assert service.llm == mock_llm_client

    def test_init_without_client_creates_default(self):
        """Test initialization creates default client when none provided."""
        with patch("app.services.question_generator.get_llm_client") as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            service = QuestionGeneratorService()

            mock_get_client.assert_called_once()
            assert service.llm == mock_client


class TestGenerateFromDocument:
    """Tests for document-based question generation."""

    def test_generate_from_document_basic(
        self,
        mock_llm_client,
        mock_generated_questions: GeneratedQuestions,
        sample_text_content: str,
    ):
        """Test basic document generation."""
        service = QuestionGeneratorService(llm_client=mock_llm_client)

        result = service.generate_from_document(
            content=sample_text_content,
            num_questions=5,
        )

        assert isinstance(result, GeneratedQuestions)
        assert len(result.questions) > 0

    def test_generate_with_mcq_only(
        self,
        mock_llm_client,
        mock_generated_questions: GeneratedQuestions,
        sample_text_content: str,
    ):
        """Test generation with MCQ type only."""
        service = QuestionGeneratorService(llm_client=mock_llm_client)

        result = service.generate_from_document(
            content=sample_text_content,
            num_questions=3,
            question_types=[QuestionType.MCQ],
        )

        # Verify LLM was called
        mock_llm_client.generate_structured.assert_called()

    def test_generate_with_open_ended_only(
        self,
        mock_llm_client,
        mock_generated_questions: GeneratedQuestions,
        sample_text_content: str,
    ):
        """Test generation with open-ended type only."""
        service = QuestionGeneratorService(llm_client=mock_llm_client)

        result = service.generate_from_document(
            content=sample_text_content,
            num_questions=3,
            question_types=[QuestionType.OPEN_ENDED],
        )

        mock_llm_client.generate_structured.assert_called()

    def test_generate_with_mixed_types(
        self,
        mock_llm_client,
        mock_generated_questions: GeneratedQuestions,
        sample_text_content: str,
    ):
        """Test generation with mixed question types."""
        service = QuestionGeneratorService(llm_client=mock_llm_client)

        result = service.generate_from_document(
            content=sample_text_content,
            num_questions=4,
            question_types=[QuestionType.MCQ, QuestionType.OPEN_ENDED],
        )

        mock_llm_client.generate_structured.assert_called()

    def test_generate_with_difficulty_easy(
        self,
        mock_llm_client,
        mock_generated_questions: GeneratedQuestions,
        sample_text_content: str,
    ):
        """Test generation with easy difficulty."""
        service = QuestionGeneratorService(llm_client=mock_llm_client)

        result = service.generate_from_document(
            content=sample_text_content,
            num_questions=3,
            difficulty="easy",
        )

        # Check that the call was made with appropriate prompt
        call_args = mock_llm_client.generate_structured.call_args
        user_prompt = call_args.kwargs.get("user_prompt", "")
        assert "easy" in user_prompt.lower()

    def test_generate_with_topic_focus(
        self,
        mock_llm_client,
        mock_generated_questions: GeneratedQuestions,
        sample_text_content: str,
    ):
        """Test generation with specific topic focus."""
        service = QuestionGeneratorService(llm_client=mock_llm_client)

        result = service.generate_from_document(
            content=sample_text_content,
            num_questions=3,
            topic_focus="Chlorophyll functions",
        )

        call_args = mock_llm_client.generate_structured.call_args
        user_prompt = call_args.kwargs.get("user_prompt", "")
        assert "Chlorophyll functions" in user_prompt


class TestAnalyzeQuestion:
    """Tests for question analysis (similarity workflow step 1)."""

    def test_analyze_question_basic(
        self,
        mock_llm_client,
        mock_similarity_analysis: SimilarityAnalysis,
    ):
        """Test basic question analysis."""
        service = QuestionGeneratorService(llm_client=mock_llm_client)

        result = service.analyze_question(
            question_text="What is 2 + 2?"
        )

        assert isinstance(result, SimilarityAnalysis)
        assert result.analysis is not None
        assert result.variation_suggestions is not None

    def test_analyze_question_with_options(
        self,
        mock_llm_client,
        mock_similarity_analysis: SimilarityAnalysis,
    ):
        """Test analysis with MCQ options."""
        service = QuestionGeneratorService(llm_client=mock_llm_client)

        options = [
            {"label": "A", "text": "3", "is_correct": False},
            {"label": "B", "text": "4", "is_correct": True},
            {"label": "C", "text": "5", "is_correct": False},
            {"label": "D", "text": "6", "is_correct": False},
        ]

        result = service.analyze_question(
            question_text="What is 2 + 2?",
            options=options,
        )

        # Verify options were included in the prompt
        call_args = mock_llm_client.generate_structured.call_args
        user_prompt = call_args.kwargs.get("user_prompt", "")
        assert "Options:" in user_prompt


class TestGenerateSimilar:
    """Tests for similarity-based question generation."""

    def test_generate_similar_basic(
        self,
        mock_llm_client,
        mock_similarity_analysis: SimilarityAnalysis,
        mock_generated_questions: GeneratedQuestions,
    ):
        """Test basic similar question generation."""
        service = QuestionGeneratorService(llm_client=mock_llm_client)

        result = service.generate_similar(
            original_question="What is 2 + 2?",
            analysis=mock_similarity_analysis,
            num_questions=3,
        )

        assert isinstance(result, GeneratedQuestions)

    def test_generate_similar_with_options(
        self,
        mock_llm_client,
        mock_similarity_analysis: SimilarityAnalysis,
        mock_generated_questions: GeneratedQuestions,
    ):
        """Test similar generation with original MCQ options."""
        service = QuestionGeneratorService(llm_client=mock_llm_client)

        options = [
            {"label": "A", "text": "3", "is_correct": False},
            {"label": "B", "text": "4", "is_correct": True},
        ]

        result = service.generate_similar(
            original_question="What is 2 + 2?",
            analysis=mock_similarity_analysis,
            num_questions=2,
            options=options,
        )

        # Verify original options were included
        call_args = mock_llm_client.generate_structured.call_args
        user_prompt = call_args.kwargs.get("user_prompt", "")
        assert "Original Options" in user_prompt


class TestRefineQuestion:
    """Tests for question refinement (Canvas flow)."""

    def test_refine_question_basic(
        self,
        mock_llm_client,
        mock_refined_question: RefinedQuestion,
    ):
        """Test basic question refinement."""
        service = QuestionGeneratorService(llm_client=mock_llm_client)

        question_state = {
            "question_text": "What is photosynthesis?",
            "question_type": "mcq",
            "difficulty": "medium",
            "options": [
                {"label": "A", "text": "Process of breathing", "is_correct": False},
                {"label": "B", "text": "Process of making food", "is_correct": True},
            ],
            "correct_answer": "B",
            "explanation": "Photosynthesis is how plants make food.",
        }

        result = service.refine_question(
            question_state=question_state,
            instruction="Make the question easier",
        )

        assert isinstance(result, RefinedQuestion)
        assert result.changes_made is not None

    def test_refine_question_with_history(
        self,
        mock_llm_client,
        mock_refined_question: RefinedQuestion,
    ):
        """Test refinement with conversation history."""
        service = QuestionGeneratorService(llm_client=mock_llm_client)

        question_state = {
            "question_text": "Test question?",
            "question_type": "mcq",
            "difficulty": "medium",
            "correct_answer": "A",
            "explanation": "Test explanation.",
        }

        history = [
            {"role": "user", "content": "Previous refinement request"},
            {"role": "assistant", "content": "Previous refinement response"},
        ]

        result = service.refine_question(
            question_state=question_state,
            instruction="Now make it harder",
            conversation_history=history,
        )

        # Verify history was passed to LLM
        call_args = mock_llm_client.generate_structured_with_context.call_args
        messages = call_args.kwargs.get("messages", [])
        assert len(messages) >= 3  # history + new message


class TestBuildTypeInstruction:
    """Tests for type instruction builder."""

    def test_build_type_instruction_both(self, mock_llm_client):
        """Test instruction for both types."""
        service = QuestionGeneratorService(llm_client=mock_llm_client)

        result = service._build_type_instruction([QuestionType.MCQ, QuestionType.OPEN_ENDED])

        assert "mix" in result.lower()
        assert "MCQ" in result or "Multiple Choice" in result

    def test_build_type_instruction_mcq_only(self, mock_llm_client):
        """Test instruction for MCQ only."""
        service = QuestionGeneratorService(llm_client=mock_llm_client)

        result = service._build_type_instruction([QuestionType.MCQ])

        assert "MCQ" in result or "Multiple Choice" in result
        assert "4 options" in result

    def test_build_type_instruction_open_ended_only(self, mock_llm_client):
        """Test instruction for open-ended only."""
        service = QuestionGeneratorService(llm_client=mock_llm_client)

        result = service._build_type_instruction([QuestionType.OPEN_ENDED])

        assert "Open-Ended" in result


class TestBuildDifficultyInstruction:
    """Tests for difficulty instruction builder."""

    def test_build_difficulty_instruction_mixed(self, mock_llm_client):
        """Test instruction for mixed difficulty."""
        service = QuestionGeneratorService(llm_client=mock_llm_client)

        result = service._build_difficulty_instruction("mixed", 5)

        assert "mix" in result.lower()
        assert "5" in result

    def test_build_difficulty_instruction_specific(self, mock_llm_client):
        """Test instruction for specific difficulty."""
        service = QuestionGeneratorService(llm_client=mock_llm_client)

        result = service._build_difficulty_instruction("hard", 3)

        assert "hard" in result.lower()


class TestFormatQuestionState:
    """Tests for question state formatter."""

    def test_format_question_state_mcq(self, mock_llm_client):
        """Test formatting MCQ question state."""
        service = QuestionGeneratorService(llm_client=mock_llm_client)

        state = {
            "question_text": "Test question?",
            "question_type": "mcq",
            "difficulty": "easy",
            "options": [
                {"label": "A", "text": "Option A", "is_correct": True},
                {"label": "B", "text": "Option B", "is_correct": False},
            ],
            "correct_answer": "A",
            "explanation": "Because A is correct.",
        }

        result = service._format_question_state(state)

        assert "Test question?" in result
        assert "mcq" in result
        assert "Option A" in result
        assert "(correct)" in result
        assert "Explanation:" in result

    def test_format_question_state_open_ended(self, mock_llm_client):
        """Test formatting open-ended question state."""
        service = QuestionGeneratorService(llm_client=mock_llm_client)

        state = {
            "question_text": "Explain something.",
            "question_type": "open_ended",
            "difficulty": "hard",
            "correct_answer": "A detailed answer.",
            "explanation": "Because it requires analysis.",
        }

        result = service._format_question_state(state)

        assert "Explain something." in result
        assert "open_ended" in result
        assert "Options:" not in result  # No options for open-ended


class TestGetQuestionGenerator:
    """Tests for the factory function."""

    def test_get_question_generator_with_client(self, mock_llm_client):
        """Test factory with provided client."""
        service = get_question_generator(llm_client=mock_llm_client)

        assert isinstance(service, QuestionGeneratorService)
        assert service.llm == mock_llm_client

    def test_get_question_generator_without_client(self):
        """Test factory without client uses default LLM client."""
        with patch("app.services.question_generator.get_llm_client") as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            service = get_question_generator()

            assert isinstance(service, QuestionGeneratorService)
            mock_get_client.assert_called_once()
