"""
Question Generation Service - Core AI logic for all three workflows.

1. Document-Based Generation: PDF/text -> questions
2. Similarity Generation: Question -> similar questions
3. Interactive Refinement: Question + instruction -> refined question
"""
from app.models import QuestionType
from app.schemas.questions import (
    GeneratedQuestion,
    GeneratedQuestions,
    RefinedQuestion,
    SimilarityAnalysis,
)
from app.services.llm_client import LLMClient, get_llm_client


# =============================================================================
# System Prompts
# =============================================================================

DOCUMENT_GENERATION_SYSTEM_PROMPT = """You are an expert educational content creator specializing in generating high-quality assessment questions.

Your task is to generate questions based on the provided educational content. Follow these guidelines:

1. **Question Quality**:
   - Questions should test understanding, not just memorization
   - Include a mix of difficulty levels as requested
   - Each question must be clear, unambiguous, and self-contained

2. **For MCQ Questions**:
   - Provide exactly 4 options (A, B, C, D)
   - Only ONE option should be correct
   - Distractors (wrong answers) should be plausible but clearly incorrect
   - Avoid "all of the above" or "none of the above" options

3. **For Open-Ended Questions**:
   - Questions should require analytical or explanatory responses
   - Provide a comprehensive model answer

4. **Explanations**:
   - Every question MUST include a detailed explanation
   - Explain WHY the correct answer is correct
   - For MCQ, explain why each distractor is incorrect

5. **Confidence Score**:
   - Rate your confidence in the question quality (0.0 to 1.0)
   - Lower scores for questions that might be ambiguous or edge cases

Generate questions that would be appropriate for academic assessments."""

SIMILARITY_ANALYSIS_SYSTEM_PROMPT = """You are an expert at analyzing educational questions to understand their structure, difficulty, and key characteristics.

Analyze the given question and identify:
1. The main topic and subtopic
2. Key concepts being tested
3. Difficulty level (easy/medium/hard)
4. Question format and style
5. Mathematical operations involved (if any)
6. Suggestions for creating variations

Be precise and detailed in your analysis."""

SIMILARITY_GENERATION_SYSTEM_PROMPT = """You are an expert at creating similar educational questions that maintain the same style, difficulty, and format while varying the specific content.

Based on the analysis of the original question, generate new questions that:
1. Test the SAME concepts and skills
2. Have the SAME difficulty level
3. Follow the SAME format and style
4. Use DIFFERENT values, contexts, or scenarios
5. Are equally clear and well-structured

For math questions: Change numbers but ensure answers remain "clean" (whole numbers, simple fractions) where appropriate.
For conceptual questions: Change the context/scenario while testing the same understanding.

Each generated question must include a complete explanation."""

REFINEMENT_SYSTEM_PROMPT = """You are an expert question editor helping to refine educational assessment questions.

You will receive:
1. The current state of a question
2. A natural language instruction for how to modify it

Apply the requested changes while:
1. Maintaining question quality and clarity
2. Ensuring the question remains valid and answerable
3. Updating the explanation to match any changes
4. Keeping the same format unless instructed otherwise

Common refinement requests include:
- Changing the correct answer
- Making distractors more/less confusing
- Adjusting difficulty
- Changing numerical values
- Modifying wording for clarity

Always describe what changes you made in the 'changes_made' field."""


# =============================================================================
# Question Generation Service
# =============================================================================


class QuestionGeneratorService:
    """Service for generating and refining educational questions."""

    def __init__(self, llm_client: LLMClient | None = None):
        self.llm = llm_client or get_llm_client()

    def generate_from_document(
        self,
        content: str,
        num_questions: int = 5,
        question_types: list[QuestionType] | None = None,
        difficulty: str = "mixed",
        topic_focus: str | None = None,
    ) -> GeneratedQuestions:
        """
        Generate questions from document/text content.

        Args:
            content: Source text content (from PDF or direct input)
            num_questions: Number of questions to generate
            question_types: List of question types to generate (MCQ, open-ended, or both)
            difficulty: "easy", "medium", "hard", or "mixed"
            topic_focus: Optional specific topic to focus on

        Returns:
            GeneratedQuestions with list of questions and summary
        """
        if question_types is None:
            question_types = [QuestionType.MCQ, QuestionType.OPEN_ENDED]

        type_instruction = self._build_type_instruction(question_types)
        difficulty_instruction = self._build_difficulty_instruction(difficulty, num_questions)
        topic_instruction = f"\nFocus specifically on: {topic_focus}" if topic_focus else ""

        user_prompt = f"""Based on the following educational content, generate {num_questions} high-quality questions.

{type_instruction}
{difficulty_instruction}
{topic_instruction}

=== CONTENT ===
{content}
=== END CONTENT ===

Generate {num_questions} questions with complete explanations."""

        result = self.llm.generate_structured(
            response_model=GeneratedQuestions,
            system_prompt=DOCUMENT_GENERATION_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.7,
        )

        return result

    def generate_from_images(
        self,
        images: list[dict],
        num_questions: int = 5,
        question_types: list[QuestionType] | None = None,
        difficulty: str = "mixed",
        topic_focus: str | None = None,
    ) -> GeneratedQuestions:
        """
        Generate questions directly from PDF page images (multimodal).

        This method sends images directly to the LLM for processing,
        which is useful for scanned PDFs or image-based documents.

        Args:
            images: List of image dicts with 'base64' and 'mime_type' keys
            num_questions: Number of questions to generate
            question_types: List of question types to generate
            difficulty: "easy", "medium", "hard", or "mixed"
            topic_focus: Optional specific topic to focus on

        Returns:
            GeneratedQuestions with list of questions and summary
        """
        if question_types is None:
            question_types = [QuestionType.MCQ, QuestionType.OPEN_ENDED]

        type_instruction = self._build_type_instruction(question_types)
        difficulty_instruction = self._build_difficulty_instruction(difficulty, num_questions)
        topic_instruction = f"\nFocus specifically on: {topic_focus}" if topic_focus else ""

        user_prompt = f"""Analyze the provided document images and generate {num_questions} high-quality educational questions based on the content you see.

{type_instruction}
{difficulty_instruction}
{topic_instruction}

Read and understand all the content in the images, then generate {num_questions} questions with complete explanations."""

        result = self.llm.generate_structured_with_images(
            response_model=GeneratedQuestions,
            system_prompt=DOCUMENT_GENERATION_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            images=images,
            temperature=0.7,
        )

        return result

    def analyze_question(self, question_text: str, options: list[dict] | None = None) -> SimilarityAnalysis:
        """
        Analyze a question for similarity generation.

        Args:
            question_text: The question to analyze
            options: MCQ options if applicable

        Returns:
            SimilarityAnalysis with detailed breakdown
        """
        options_text = ""
        if options:
            options_text = "\n\nOptions:\n" + "\n".join(
                f"{opt['label']}. {opt['text']}" for opt in options
            )

        user_prompt = f"""Analyze this question in detail:

{question_text}{options_text}

Provide a comprehensive analysis for generating similar questions."""

        result = self.llm.generate_structured(
            response_model=SimilarityAnalysis,
            system_prompt=SIMILARITY_ANALYSIS_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.3,  # Lower temperature for analysis
        )

        return result

    def generate_similar(
        self,
        original_question: str,
        analysis: SimilarityAnalysis,
        num_questions: int = 3,
        options: list[dict] | None = None,
    ) -> GeneratedQuestions:
        """
        Generate questions similar to the original.

        Args:
            original_question: The source question
            analysis: Analysis of the original question
            num_questions: Number of similar questions to generate
            options: MCQ options if applicable

        Returns:
            GeneratedQuestions with similar questions
        """
        options_text = ""
        if options:
            options_text = "\n\nOriginal Options:\n" + "\n".join(
                f"{opt['label']}. {opt['text']}" for opt in options
            )

        user_prompt = f"""Generate {num_questions} questions similar to the following:

=== ORIGINAL QUESTION ===
{original_question}{options_text}

=== ANALYSIS ===
Topic: {analysis.analysis.topic}
Subtopic: {analysis.analysis.subtopic}
Difficulty: {analysis.analysis.difficulty}
Key Concepts: {', '.join(analysis.analysis.key_concepts)}
Format Style: {analysis.analysis.format_style}
Variation Suggestions: {', '.join(analysis.variation_suggestions)}

Generate {num_questions} new questions that are logically similar but with different values/contexts.
Maintain the same difficulty level and format."""

        result = self.llm.generate_structured(
            response_model=GeneratedQuestions,
            system_prompt=SIMILARITY_GENERATION_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.8,  # Higher temperature for variety
        )

        return result

    def refine_question(
        self,
        question_state: dict,
        instruction: str,
        conversation_history: list[dict] | None = None,
    ) -> RefinedQuestion:
        """
        Refine a question based on natural language instruction (Canvas flow).

        Args:
            question_state: Current state of the question
            instruction: Natural language refinement instruction
            conversation_history: Previous refinement context

        Returns:
            RefinedQuestion with changes applied
        """
        # Format current question state
        state_text = self._format_question_state(question_state)

        messages = []

        # Add conversation history if exists (for context continuity)
        if conversation_history:
            messages.extend(conversation_history)

        # Add current refinement request
        messages.append({
            "role": "user",
            "content": f"""Current question state:

{state_text}

=== REFINEMENT INSTRUCTION ===
{instruction}

Apply the requested changes and provide the updated question."""
        })

        result = self.llm.generate_structured_with_context(
            response_model=RefinedQuestion,
            system_prompt=REFINEMENT_SYSTEM_PROMPT,
            messages=messages,
            temperature=0.5,
        )

        return result

    def _build_type_instruction(self, question_types: list[QuestionType]) -> str:
        if len(question_types) == 2:
            return "Generate a mix of Multiple Choice Questions (MCQ) and Open-Ended questions."
        elif QuestionType.MCQ in question_types:
            return "Generate only Multiple Choice Questions (MCQ) with 4 options each."
        else:
            return "Generate only Open-Ended questions requiring explanatory answers."

    def _build_difficulty_instruction(self, difficulty: str, num_questions: int) -> str:
        if difficulty == "mixed":
            return f"Include a mix of easy, medium, and hard questions across the {num_questions} questions."
        return f"All questions should be {difficulty} difficulty level."

    def _format_question_state(self, state: dict) -> str:
        lines = [f"Question: {state.get('question_text', '')}"]
        lines.append(f"Type: {state.get('question_type', 'mcq')}")
        lines.append(f"Difficulty: {state.get('difficulty', 'medium')}")

        if state.get('options'):
            lines.append("\nOptions:")
            for opt in state['options']:
                marker = " (correct)" if opt.get('is_correct') else ""
                lines.append(f"  {opt['label']}. {opt['text']}{marker}")

        lines.append(f"\nCorrect Answer: {state.get('correct_answer', '')}")
        lines.append(f"\nExplanation: {state.get('explanation', '')}")

        return "\n".join(lines)


# Factory function
def get_question_generator(llm_client: LLMClient | None = None) -> QuestionGeneratorService:
    """Get a question generator service instance."""
    return QuestionGeneratorService(llm_client=llm_client)
