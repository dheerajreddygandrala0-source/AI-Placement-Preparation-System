import json
import re
from typing import Any, Dict, List

from models.candidate_state import CandidateState
from rag.retriever import retrieve
from utils.llm import generate_text


class TechnicalAgent:

    def run(
        self,
        state: CandidateState,
        questions_per_topic: int = 2
    ) -> CandidateState:

        topics = self._select_topics(state)

        if not topics:
            topics = ["DSA", "OOP", "SQL", "Python", "Computer Networks"]

        questions = []

        for topic in topics:
            rag_context = self._get_rag_context(topic)

            prompt = f"""
Create {questions_per_topic} technical interview questions
for the candidate described below.

Candidate target role:
{state.target_role}

Candidate skills:
{", ".join(state.skills)}

Candidate technical topics:
{", ".join(state.technical_topics)}

Focus topic:
{topic}

Relevant knowledge retrieved from the RAG knowledge base:
{rag_context}

Requirements:
- Questions must be relevant to the candidate and the topic.
- Questions should test understanding, not just memorization.
- Use the retrieved knowledge as the grounding source.
- Do not ask questions unrelated to the retrieved material.
- Include a mixture of conceptual and practical questions.
- Difficulty should be Easy, Medium, or Hard.
- Return exactly {questions_per_topic} questions.
- Return ONLY valid JSON.

Required format:
{{
    "questions": [
        {{
            "topic": "{topic}",
            "question": "question text",
            "difficulty": "Easy/Medium/Hard"
        }}
    ]
}}
"""

            response = generate_text(
                prompt=prompt,
                system_prompt=(
                    "You are an expert technical interviewer. "
                    "Generate grounded, personalized interview questions "
                    "using the candidate information and retrieved RAG context."
                ),
                temperature=0.3,
            )

            data = self._parse_json(response)

            topic_questions = data.get("questions", [])

            if isinstance(topic_questions, list):
                for question in topic_questions:
                    if not isinstance(question, dict):
                        continue

                    question_text = str(
                        question.get("question", "")
                    ).strip()

                    if not question_text:
                        continue

                    questions.append({
                        "topic": str(
                            question.get("topic", topic)
                        ).strip(),

                        "question": question_text,

                        "difficulty": str(
                            question.get("difficulty", "Medium")
                        ).strip(),

                        "rag_context": rag_context,
                    })

        state.technical_questions = questions

        return state

    def evaluate_answers(
        self,
        state: CandidateState
    ) -> CandidateState:

        evaluated_answers = []

        total_score = 0.0

        for answer_data in state.technical_answers:

            question = answer_data.get("question", "")
            topic = answer_data.get("topic", "")
            answer = answer_data.get("answer", "")

            rag_context = self._get_rag_context(topic)

            prompt = f"""
Evaluate the candidate's answer to a technical interview question.

Topic:
{topic}

Question:
{question}

Candidate answer:
{answer}

Relevant knowledge from the RAG knowledge base:
{rag_context}

Evaluate the answer based on:
1. Technical correctness
2. Understanding of the concept
3. Completeness
4. Accuracy
5. Relevance

Give a score from 0 to 10.

Scoring guidance:
0-2 = Incorrect or no meaningful understanding
3-4 = Major gaps or partially incorrect
5-6 = Basic understanding but important gaps
7-8 = Good and mostly correct understanding
9 = Very strong answer
10 = Excellent, complete and technically accurate answer

Return ONLY valid JSON:

{{
    "score": 0,
    "feedback": "",
    "correct_concepts": [],
    "missing_concepts": []
}}
"""

            response = generate_text(
                prompt=prompt,
                system_prompt=(
                    "You are a strict but fair technical interview evaluator. "
                    "Evaluate answers using the question and RAG knowledge. "
                    "Do not give a high score merely because the answer is long."
                ),
                temperature=0.1,
            )

            result = self._parse_json(response)

            score = self._safe_score(result.get("score", 0))

            feedback = str(
                result.get("feedback", "")
            ).strip()

            correct_concepts = self._clean_list(
                result.get("correct_concepts", [])
            )

            missing_concepts = self._clean_list(
                result.get("missing_concepts", [])
            )

            evaluated_answers.append({
                "question": question,
                "topic": topic,
                "answer": answer,
                "score": score,
                "feedback": feedback,
                "correct_concepts": correct_concepts,
                "missing_concepts": missing_concepts,
            })

            total_score += score

        state.technical_answers = evaluated_answers

        if evaluated_answers:
            state.technical_score = round(
                total_score / len(evaluated_answers),
                2
            )
        else:
            state.technical_score = 0.0

        return state

    def _select_topics(
        self,
        state: CandidateState
    ) -> List[str]:

        topics = []

        for topic in state.technical_topics:
            if topic not in topics:
                topics.append(topic)

        if len(topics) < 5:

            for skill in state.skills:

                normalized = skill.lower()

                known_topics = {
                    "python": "Python",
                    "c++": "C++",
                    "java": "Java",
                    "sql": "SQL",
                    "dsa": "DSA",
                    "data structures": "DSA",
                    "algorithms": "DSA",
                    "oop": "OOP",
                    "dbms": "DBMS",
                    "operating systems": "Operating Systems",
                    "os": "Operating Systems",
                    "computer networks": "Computer Networks",
                    "networks": "Computer Networks",
                    "machine learning": "Machine Learning",
                    "deep learning": "Deep Learning",
                    "artificial intelligence": "Artificial Intelligence",
                    "cloud": "Cloud Computing",
                    "git": "Git & GitHub",
                    "system design": "System Design",
                }

                for key, topic in known_topics.items():

                    if key in normalized and topic not in topics:
                        topics.append(topic)

        return topics[:5]

    @staticmethod
    def _get_rag_context(topic: str) -> str:

        results = retrieve(
            query=f"Important interview concepts and questions about {topic}",
            top_k=4,
        )

        context_parts = []

        for result in results:

            document = result.get("document", "")

            metadata = result.get("metadata", {})

            source = metadata.get("file", "knowledge base")

            section = metadata.get("section", "")

            context_parts.append(
                f"Source: {source}\n"
                f"Section: {section}\n"
                f"Content:\n{document}"
            )

        return "\n\n---\n\n".join(context_parts)

    @staticmethod
    def _parse_json(response: str) -> Dict[str, Any]:

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
                    "LLM response JSON must be an object."
                )

            return data

        except json.JSONDecodeError:

            start = response.find("{")
            end = response.rfind("}")

            if start != -1 and end != -1 and end > start:

                json_text = response[start:end + 1]

                try:
                    data = json.loads(json_text)

                    if isinstance(data, dict):
                        return data

                except json.JSONDecodeError:
                    pass

            raise ValueError(
                "Technical Agent received invalid JSON from the LLM."
            )

    @staticmethod
    def _clean_list(value: Any) -> List[str]:

        if not isinstance(value, list):
            return []

        result = []

        for item in value:

            item = str(item).strip()

            if item and item not in result:
                result.append(item)

        return result

    @staticmethod
    def _safe_score(value: Any) -> float:

        try:
            score = float(value)
        except (TypeError, ValueError):
            return 0.0

        return max(0.0, min(10.0, score))