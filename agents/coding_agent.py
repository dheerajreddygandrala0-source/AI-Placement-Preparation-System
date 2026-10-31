import json
import re
from typing import Any, Dict, List

from models.candidate_state import CandidateState
from rag.retriever import retrieve
from utils.llm import generate_text


class CodingAgent:

    def run(self, state: CandidateState) -> CandidateState:

        topic = self._select_topic(state)

        rag_context = self._get_rag_context(topic)

        prompt = f"""
Create one coding interview problem for the candidate.

Candidate target role:
{state.target_role}

Candidate skills:
{", ".join(state.skills)}

Candidate technical topics:
{", ".join(state.technical_topics)}

Coding topic:
{topic}

Relevant knowledge retrieved from the RAG knowledge base:
{rag_context}

Requirements:

- Create a realistic coding interview problem.
- The problem should match the selected coding topic.
- Difficulty must be Easy, Medium, or Hard.
- Prefer Medium or Hard for a technical placement interview.
- Clearly explain the problem.
- Include input format.
- Include output format.
- Include constraints.
- Include exactly two examples.
- Do not provide the solution.
- Do not provide code.
- Return ONLY valid JSON.

Required JSON format:

{{
    "topic": "{topic}",
    "title": "problem title",
    "problem": "complete problem statement",
    "input_format": "input description",
    "output_format": "output description",
    "constraints": [],
    "examples": [
        {{
            "input": "",
            "output": "",
            "explanation": ""
        }},
        {{
            "input": "",
            "output": "",
            "explanation": ""
        }}
    ],
    "difficulty": "Medium"
}}
"""

        response = generate_text(
            prompt=prompt,
            system_prompt=(
                "You are an expert coding interview problem setter. "
                "Create realistic placement coding problems using "
                "the candidate information and retrieved RAG knowledge."
            ),
            temperature=0.4,
        )

        data = self._parse_json(response)

        question = {
            "topic": str(
                data.get("topic", topic)
            ).strip(),

            "title": str(
                data.get("title", "Coding Problem")
            ).strip(),

            "problem": str(
                data.get("problem", "")
            ).strip(),

            "input_format": str(
                data.get("input_format", "")
            ).strip(),

            "output_format": str(
                data.get("output_format", "")
            ).strip(),

            "constraints": self._clean_list(
                data.get("constraints", [])
            ),

            "examples": self._clean_examples(
                data.get("examples", [])
            ),

            "difficulty": str(
                data.get("difficulty", "Medium")
            ).strip(),

            "rag_context": rag_context,
        }

        state.coding_topics = [topic]
        state.coding_questions = [question]
        state.coding_submissions = []
        state.coding_score = 0.0

        return state

    def evaluate_submission(
        self,
        state: CandidateState,
        code: str,
        language: str,
    ) -> CandidateState:

        if not state.coding_questions:

            raise ValueError(
                "No coding question exists. "
                "Generate a coding question first."
            )

        question = state.coding_questions[0]

        topic = question.get(
            "topic",
            "Coding",
        )

        rag_context = question.get(
            "rag_context",
            "",
        )

        prompt = f"""
Evaluate the candidate's coding solution.

Coding topic:
{topic}

Problem:
{question.get("problem", "")}

Input format:
{question.get("input_format", "")}

Output format:
{question.get("output_format", "")}

Constraints:
{question.get("constraints", [])}

Candidate programming language:
{language}

Candidate code:
{code}

Relevant RAG knowledge:
{rag_context}

Evaluate the solution on:

1. Correctness
2. Algorithmic approach
3. Time complexity
4. Space complexity
5. Handling of edge cases
6. Code quality
7. Whether the solution actually solves the given problem

Important:
- Do not assume the code is correct merely because the approach looks reasonable.
- Identify logical errors.
- Check edge cases.
- Explain the expected time and space complexity.
- Give a score from 0 to 10.

Scoring guidance:

0-2 = No meaningful solution or fundamentally incorrect
3-4 = Significant logical problems
5-6 = Partially correct solution with important issues
7-8 = Correct solution with minor issues or room for improvement
9 = Strong and correct solution
10 = Excellent, correct, efficient and well-structured solution

Return ONLY valid JSON:

{{
    "score": 0,
    "correctness": "",
    "feedback": "",
    "time_complexity": "",
    "space_complexity": "",
    "edge_cases": [],
    "improvements": []
}}
"""

        response = generate_text(
            prompt=prompt,
            system_prompt=(
                "You are a strict coding interview evaluator. "
                "Analyze the actual code carefully and evaluate "
                "correctness, complexity and edge cases."
            ),
            temperature=0.1,
        )

        result = self._parse_json(response)

        score = self._safe_score(
            result.get("score", 0)
        )

        submission = {
            "language": language,
            "code": code,
            "score": score,
            "correctness": str(
                result.get("correctness", "")
            ).strip(),
            "feedback": str(
                result.get("feedback", "")
            ).strip(),
            "time_complexity": str(
                result.get("time_complexity", "")
            ).strip(),
            "space_complexity": str(
                result.get("space_complexity", "")
            ).strip(),
            "edge_cases": self._clean_list(
                result.get("edge_cases", [])
            ),
            "improvements": self._clean_list(
                result.get("improvements", [])
            ),
        }

        state.coding_submissions = [submission]
        state.coding_score = score

        return state

    @staticmethod
    def _select_topic(
        state: CandidateState
    ) -> str:

        coding_topics = [
            "Arrays",
            "Strings",
            "Hashing",
            "Two Pointers",
            "Sliding Window",
            "Binary Search",
            "Linked Lists",
            "Stacks",
            "Queues",
            "Trees",
            "Graphs",
            "Heaps",
            "Greedy",
            "Backtracking",
            "Dynamic Programming",
        ]

        # First try to use topics already detected
        # from the candidate's technical profile.
        detected = []

        for topic in state.technical_topics:

            normalized = topic.lower()

            for coding_topic in coding_topics:

                if (
                    coding_topic.lower()
                    in normalized
                    or normalized
                    in coding_topic.lower()
                ):

                    if coding_topic not in detected:
                        detected.append(coding_topic)

        if detected:
            return detected[0]

        # Otherwise use DSA as the default
        # placement coding topic.
        return "Arrays"

    @staticmethod
    def _get_rag_context(
        topic: str
    ) -> str:

        results = retrieve(
            query=(
                f"Coding interview problems, patterns, "
                f"algorithms and important concepts for {topic}"
            ),
            top_k=5,
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
        response: str
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
                "Coding Agent received invalid JSON "
                "from the LLM."
            )

    @staticmethod
    def _clean_list(
        value: Any
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
    def _clean_examples(
        value: Any
    ) -> List[Dict[str, str]]:

        if not isinstance(value, list):
            return []

        examples = []

        for item in value:

            if not isinstance(item, dict):
                continue

            examples.append(
                {
                    "input": str(
                        item.get(
                            "input",
                            "",
                        )
                    ).strip(),

                    "output": str(
                        item.get(
                            "output",
                            "",
                        )
                    ).strip(),

                    "explanation": str(
                        item.get(
                            "explanation",
                            "",
                        )
                    ).strip(),
                }
            )

        return examples[:2]

    @staticmethod
    def _safe_score(
        value: Any
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