import json
import re
from typing import Any, Dict, List

from models.candidate_state import CandidateState
from rag.retriever import retrieve
from utils.llm import generate_text


class HRAgent:

    def run(
        self,
        state: CandidateState,
        questions_count: int = 6,
    ) -> CandidateState:

        rag_context = self._get_rag_context()

        prompt = f"""
Create a personalized HR interview for this candidate.

Candidate name:
{state.name}

Target role:
{state.target_role}

Skills:
{", ".join(state.skills)}

Education:
{chr(10).join(state.education)}

Projects:
{chr(10).join(state.projects)}

Experience:
{chr(10).join(state.experience)}

Certifications:
{chr(10).join(state.certifications)}

Technical score:
{state.technical_score}/10

Coding score:
{state.coding_score}/10

Relevant HR interview knowledge from the RAG knowledge base:
{rag_context}

Create exactly {questions_count} HR interview questions.

The questions should cover a mixture of:
- Introduction
- Behavioral
- Projects
- Teamwork
- Leadership
- Strengths and weaknesses
- Career goals
- Situational questions

Requirements:
- Personalize questions using the candidate's actual resume.
- Ask about projects when projects are available.
- Ask about strengths or weaknesses relevant to the candidate.
- Include behavioral and situational questions.
- Do not invent candidate experience.
- Do not provide answers.
- Return ONLY valid JSON.

Required format:

{{
    "questions": [
        "question 1",
        "question 2",
        "question 3",
        "question 4",
        "question 5",
        "question 6"
    ]
}}
"""

        response = generate_text(
            prompt=prompt,
            system_prompt=(
                "You are an experienced HR interviewer. "
                "Create realistic and personalized placement "
                "interview questions using the candidate profile "
                "and the retrieved HR knowledge."
            ),
            temperature=0.4,
        )

        data = self._parse_json(response)

        questions = self._clean_list(
            data.get("questions", [])
        )

        state.hr_questions = questions[:questions_count]
        state.hr_answers = []
        state.hr_score = 0.0

        return state

    def evaluate_answers(
        self,
        state: CandidateState,
    ) -> CandidateState:

        if not state.hr_questions:
            raise ValueError(
                "No HR questions exist. "
                "Generate HR questions first."
            )

        evaluated_answers = []

        total_score = 0.0

        for index, question in enumerate(
            state.hr_questions
        ):

            answer = ""

            if index < len(state.hr_answers):
                answer = state.hr_answers[index]

            rag_context = self._get_rag_context()

            prompt = f"""
Evaluate this candidate's HR interview answer.

Candidate target role:
{state.target_role}

Question:
{question}

Candidate answer:
{answer}

Relevant HR interview knowledge:
{rag_context}

Evaluate the answer on:

1. Relevance
2. Clarity
3. Communication
4. Professionalism
5. Self-awareness
6. Structure
7. Whether the answer actually addresses the question

Give a score from 0 to 10.

Scoring guidance:

0-2 = No meaningful answer
3-4 = Weak or poorly relevant answer
5-6 = Acceptable answer with important weaknesses
7-8 = Good professional answer
9 = Very strong answer
10 = Excellent, clear, relevant and convincing answer

Return ONLY valid JSON:

{{
    "score": 0,
    "feedback": "",
    "strengths": [],
    "improvements": []
}}
"""

            response = generate_text(
                prompt=prompt,
                system_prompt=(
                    "You are a professional HR interview evaluator. "
                    "Evaluate the candidate fairly and provide "
                    "specific actionable feedback."
                ),
                temperature=0.1,
            )

            result = self._parse_json(response)

            score = self._safe_score(
                result.get("score", 0)
            )

            feedback = str(
                result.get("feedback", "")
            ).strip()

            strengths = self._clean_list(
                result.get("strengths", [])
            )

            improvements = self._clean_list(
                result.get("improvements", [])
            )

            evaluated_answers.append({
                "question": question,
                "answer": answer,
                "score": score,
                "feedback": feedback,
                "strengths": strengths,
                "improvements": improvements,
            })

            total_score += score

        state.hr_answers = evaluated_answers

        if evaluated_answers:

            state.hr_score = round(
                total_score / len(evaluated_answers),
                2,
            )

        else:

            state.hr_score = 0.0

        return state

    @staticmethod
    def _get_rag_context() -> str:

        results = retrieve(
            query=(
                "HR interview questions behavioral "
                "projects teamwork leadership strengths "
                "weaknesses career goals situational interview"
            ),
            top_k=6,
        )

        context_parts = []

        for result in results:

            document = result.get(
                "document",
                "",
            )

            metadata = result.get(
                "metadata",
                {},
            )

            source = metadata.get(
                "file",
                "knowledge base",
            )

            section = metadata.get(
                "section",
                "",
            )

            context_parts.append(
                f"Source: {source}\n"
                f"Section: {section}\n"
                f"Content:\n{document}"
            )

        return "\n\n---\n\n".join(
            context_parts
        )

    @staticmethod
    def _parse_json(
        response: str,
    ) -> Dict[str, Any]:

        response = response.strip()

        response = re.sub(
            r"^```(?:json)?\s*",
            "",
            response,
            flags=re.IGNORECASE,
        )

        response = re.sub(
            r"\s*```$",
            "",
            response,
        )

        try:

            data = json.loads(response)

            if not isinstance(data, dict):
                raise ValueError(
                    "LLM response must be a JSON object."
                )

            return data

        except json.JSONDecodeError:

            start = response.find("{")
            end = response.rfind("}")

            if (
                start != -1
                and end != -1
                and end > start
            ):

                json_text = response[
                    start:end + 1
                ]

                try:

                    data = json.loads(
                        json_text
                    )

                    if isinstance(data, dict):
                        return data

                except json.JSONDecodeError:
                    pass

            raise ValueError(
                "HR Agent received invalid JSON "
                "from the LLM."
            )

    @staticmethod
    def _clean_list(
        value: Any,
    ) -> List[str]:

        if not isinstance(value, list):
            return []

        result = []

        for item in value:

            item = str(item).strip()

            if (
                item
                and item not in result
            ):
                result.append(item)

        return result

    @staticmethod
    def _safe_score(
        value: Any,
    ) -> float:

        try:

            score = float(value)

        except (
            TypeError,
            ValueError,
        ):

            return 0.0

        return max(
            0.0,
            min(10.0, score),
        )