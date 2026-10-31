import json
import re
from typing import Any, Dict, List

from models.candidate_state import CandidateState
from rag.retriever import retrieve
from utils.llm import generate_text


class EvaluationAgent:

    def run(self, state: CandidateState) -> CandidateState:

        rag_context = self._get_rag_context(
            state.target_role
        )

        technical_summary = (
            self._format_technical_results(state)
        )

        coding_summary = (
            self._format_coding_results(state)
        )

        hr_summary = (
            self._format_hr_results(state)
        )

        prompt = f"""
You are the final Evaluation Agent of an AI Placement
Preparation System.

Analyze the candidate's performance across:
1. Technical Interview
2. Coding Interview
3. HR Interview

Create a concise and useful final placement
preparation report.

==============================
CANDIDATE PROFILE
==============================

Name: {state.name}
Target Role: {state.target_role}

Skills:
{", ".join(state.skills[:15])}

Education:
{chr(10).join(state.education[:3])}

Projects:
{chr(10).join(state.projects[:3])}

Experience:
{chr(10).join(state.experience[:3])}

Certifications:
{chr(10).join(state.certifications[:3])}

==============================
TECHNICAL INTERVIEW
==============================

Technical Score: {state.technical_score}/10

{technical_summary}

==============================
CODING INTERVIEW
==============================

Coding Score: {state.coding_score}/10

{coding_summary}

==============================
HR INTERVIEW
==============================

HR Score: {state.hr_score}/10

{hr_summary}

==============================
PLACEMENT KNOWLEDGE
==============================

{rag_context}

==============================
SCORING
==============================

Technical = 40%
Coding = 40%
HR = 20%

Overall Score =
(Technical × 0.40)
+
(Coding × 0.40)
+
(HR × 0.20)

==============================
TASK
==============================

Identify:

1. Strong areas
2. Weak areas
3. Technical skill gaps
4. Coding skill gaps
5. HR/communication improvements
6. Recommended topics
7. Practical preparation recommendations
8. Overall summary

Use only information available in the
candidate profile and interview results.

Do not invent candidate information.

Keep each list concise and practical.

Return ONLY valid JSON.

Required format:

{{
    "overall_score": 0,
    "strengths": [],
    "weaknesses": [],
    "technical_gaps": [],
    "coding_gaps": [],
    "hr_improvements": [],
    "recommended_topics": [],
    "recommendations": [],
    "summary": ""
}}
"""

        response = generate_text(
            prompt=prompt,
            system_prompt=(
                "You are an expert placement evaluation "
                "specialist. Analyze candidate performance "
                "objectively and provide concise, "
                "evidence-based and actionable feedback. "
                "Return valid JSON only."
            ),
            temperature=0.2,
        )

        data = self._parse_json(response)

        state.overall_score = self._safe_score(
            data.get("overall_score", 0)
        )

        state.strengths = self._clean_list(
            data.get("strengths", [])
        )

        state.weaknesses = self._clean_list(
            data.get("weaknesses", [])
        )

        state.recommendations = self._clean_list(
            data.get("recommendations", [])
        )

        state.technical_gaps = self._clean_list(
            data.get("technical_gaps", [])
        )

        state.coding_gaps = self._clean_list(
            data.get("coding_gaps", [])
        )

        state.hr_improvements = self._clean_list(
            data.get("hr_improvements", [])
        )

        state.recommended_topics = self._clean_list(
            data.get("recommended_topics", [])
        )

        state.evaluation_summary = str(
            data.get("summary", "")
        ).strip()

        return state


    # =====================================================
    # RAG CONTEXT
    # =====================================================

    @staticmethod
    def _get_rag_context(
        target_role: str
    ) -> str:

        query = (
            f"placement preparation evaluation "
            f"skills interview readiness "
            f"recommendations for {target_role}"
        )

        # Only one RAG result to keep the prompt small.
        results = retrieve(
            query=query,
            top_k=1
        )

        if not results:
            return "No additional placement knowledge retrieved."

        result = results[0]

        document = str(
            result.get("document", "")
        )[:600]

        metadata = result.get(
            "metadata",
            {}
        )

        source = metadata.get(
            "file",
            "knowledge base"
        )

        section = metadata.get(
            "section",
            ""
        )

        return (
            f"Source: {source}\n"
            f"Section: {section}\n"
            f"Content:\n{document}"
        )


    # =====================================================
    # TECHNICAL RESULTS
    # =====================================================

    @staticmethod
    def _format_technical_results(
        state: CandidateState
    ) -> str:

        if not state.technical_answers:
            return "No technical interview results."

        results = []

        for item in state.technical_answers:

            question = str(
                item.get("question", "")
            )[:300]

            answer = str(
                item.get("answer", "")
            )[:300]

            feedback = str(
                item.get("feedback", "")
            )[:250]

            topic = str(
                item.get("topic", "")
            )[:80]

            score = item.get(
                "score",
                0
            )

            correct = item.get(
                "correct_concepts",
                []
            )

            missing = item.get(
                "missing_concepts",
                []
            )

            results.append(
                f"""
Q: {question}
Topic: {topic}
Answer: {answer}
Score: {score}/10
Feedback: {feedback}
Correct: {correct}
Missing: {missing}
"""
            )

        return "\n".join(results)


    # =====================================================
    # CODING RESULTS
    # =====================================================

    @staticmethod
    def _format_coding_results(
        state: CandidateState
    ) -> str:

        if not state.coding_submissions:
            return "No coding submission."

        results = []

        for item in state.coding_submissions:

            language = str(
                item.get("language", "")
            )[:30]

            code = str(
                item.get("code", "")
            )[:800]

            correctness = str(
                item.get("correctness", "")
            )[:250]

            feedback = str(
                item.get("feedback", "")
            )[:250]

            time_complexity = str(
                item.get("time_complexity", "")
            )[:100]

            space_complexity = str(
                item.get("space_complexity", "")
            )[:100]

            edge_cases = item.get(
                "edge_cases",
                []
            )

            improvements = item.get(
                "improvements",
                []
            )

            score = item.get(
                "score",
                0
            )

            results.append(
                f"""
Language: {language}
Code:
{code}

Score: {score}/10
Correctness: {correctness}
Feedback: {feedback}
Time: {time_complexity}
Space: {space_complexity}
Edge Cases: {edge_cases}
Improvements: {improvements}
"""
            )

        return "\n".join(results)


    # =====================================================
    # HR RESULTS
    # =====================================================

    @staticmethod
    def _format_hr_results(
        state: CandidateState
    ) -> str:

        if not state.hr_answers:
            return "No HR interview results."

        results = []

        for item in state.hr_answers:

            if not isinstance(
                item,
                dict
            ):
                continue

            question = str(
                item.get("question", "")
            )[:300]

            answer = str(
                item.get("answer", "")
            )[:300]

            feedback = str(
                item.get("feedback", "")
            )[:250]

            score = item.get(
                "score",
                0
            )

            strengths = item.get(
                "strengths",
                []
            )

            improvements = item.get(
                "improvements",
                []
            )

            results.append(
                f"""
Q: {question}
Answer: {answer}
Score: {score}/10
Feedback: {feedback}
Strengths: {strengths}
Improvements: {improvements}
"""
            )

        if not results:
            return "No evaluated HR results."

        return "\n".join(results)


    # =====================================================
    # JSON PARSER
    # =====================================================

    @staticmethod
    def _parse_json(
        response: str
    ) -> Dict[str, Any]:

        response = response.strip()

        response = re.sub(
            r"^```(?:json)?\s*",
            "",
            response,
            flags=re.IGNORECASE
        )

        response = re.sub(
            r"\s*```$",
            "",
            response
        )

        try:

            data = json.loads(response)

            if not isinstance(
                data,
                dict
            ):
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

                    if isinstance(
                        data,
                        dict
                    ):
                        return data

                except json.JSONDecodeError:
                    pass

            raise ValueError(
                "Evaluation Agent received "
                "invalid JSON from the LLM."
            )


    # =====================================================
    # CLEAN LIST
    # =====================================================

    @staticmethod
    def _clean_list(
        value: Any
    ) -> List[str]:

        if not isinstance(
            value,
            list
        ):
            return []

        result = []

        for item in value:

            item = str(
                item
            ).strip()

            if (
                item
                and item not in result
            ):
                result.append(item)

        return result


    # =====================================================
    # SAFE SCORE
    # =====================================================

    @staticmethod
    def _safe_score(
        value: Any
    ) -> float:

        try:

            score = float(value)

        except (
            TypeError,
            ValueError
        ):

            return 0.0

        return max(
            0.0,
            min(
                10.0,
                score
            )
        )