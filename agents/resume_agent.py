import json
import re

from models.candidate_state import CandidateState
from utils.llm import generate_text


class ResumeAgent:

    def run(self, resume_text: str, state: CandidateState) -> CandidateState:

        system_prompt = """
You are an expert Resume Analysis Agent for an AI placement preparation system.

Your job is to analyze a candidate's resume and extract structured information.

Return ONLY valid JSON.

The JSON must contain exactly these fields:

{
    "name": "",
    "email": "",
    "phone": "",
    "education": [],
    "skills": [],
    "projects": [],
    "experience": [],
    "certifications": [],
    "target_role": "",
    "technical_topics": []
}

Rules:
- Extract information only from the resume.
- Do not invent information.
- Keep important details from projects, education, and experience.
- Skills should include both technical skills and relevant professional skills when clearly mentioned.
- target_role should be the most reasonable role based on the resume.
- technical_topics should contain technical subjects relevant to the candidate's skills, projects, education, or experience.
- If something is not present, return an empty string or empty list.
- Return valid JSON only.
"""

        prompt = f"""
Analyze the following resume.

RESUME:
{resume_text}
"""

        response = generate_text(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.1,
        )

        data = self._parse_json(response)

        state.name = str(data.get("name", "")).strip()
        state.email = str(data.get("email", "")).strip()
        state.phone = str(data.get("phone", "")).strip()

        state.education = self._clean_list(data.get("education", []))
        state.skills = self._clean_list(data.get("skills", []))
        state.projects = self._clean_list(data.get("projects", []))
        state.experience = self._clean_list(data.get("experience", []))
        state.certifications = self._clean_list(
            data.get("certifications", [])
        )

        state.target_role = str(
            data.get("target_role", "")
        ).strip()

        state.technical_topics = self._clean_list(
            data.get("technical_topics", [])
        )

        return state

    @staticmethod
    def _clean_list(value):

        if not isinstance(value, list):
            return []

        cleaned = []

        for item in value:
            item = str(item).strip()

            if item and item not in cleaned:
                cleaned.append(item)

        return cleaned

    @staticmethod
    def _parse_json(response: str):

        response = response.strip()

        # Remove markdown code fences if the model returns them.
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
            return json.loads(response)

        except json.JSONDecodeError:

            # Try to locate the JSON object inside the response.
            start = response.find("{")
            end = response.rfind("}")

            if start != -1 and end != -1 and end > start:

                json_text = response[start:end + 1]

                try:
                    return json.loads(json_text)

                except json.JSONDecodeError:
                    pass

            raise ValueError(
                "Resume Agent received an invalid JSON response from the LLM."
            )