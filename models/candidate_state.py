from dataclasses import dataclass, field
from typing import List, Dict, Any


@dataclass
class CandidateState:

    # =====================================================
    # CANDIDATE PROFILE
    # =====================================================

    name: str = ""
    email: str = ""
    phone: str = ""

    education: List[str] = field(default_factory=list)
    skills: List[str] = field(default_factory=list)
    projects: List[str] = field(default_factory=list)
    experience: List[str] = field(default_factory=list)
    certifications: List[str] = field(default_factory=list)

    target_role: str = ""


    # =====================================================
    # TECHNICAL INTERVIEW
    # =====================================================

    technical_topics: List[str] = field(default_factory=list)

    technical_questions: List[Dict[str, Any]] = field(
        default_factory=list
    )

    technical_answers: List[Dict[str, Any]] = field(
        default_factory=list
    )

    technical_score: float = 0.0


    # =====================================================
    # CODING INTERVIEW
    # =====================================================

    coding_topics: List[str] = field(
        default_factory=list
    )

    coding_questions: List[Dict[str, Any]] = field(
        default_factory=list
    )

    coding_submissions: List[Dict[str, Any]] = field(
        default_factory=list
    )

    coding_score: float = 0.0


    # =====================================================
    # HR INTERVIEW
    # =====================================================

    hr_questions: List[str] = field(
        default_factory=list
    )

    hr_answers: List[Any] = field(
        default_factory=list
    )

    hr_score: float = 0.0


    # =====================================================
    # FINAL EVALUATION
    # =====================================================

    strengths: List[str] = field(
        default_factory=list
    )

    weaknesses: List[str] = field(
        default_factory=list
    )

    recommendations: List[str] = field(
        default_factory=list
    )

    overall_score: float = 0.0

    technical_gaps: List[str] = field(
        default_factory=list
    )

    coding_gaps: List[str] = field(
        default_factory=list
    )

    hr_improvements: List[str] = field(
        default_factory=list
    )

    recommended_topics: List[str] = field(
        default_factory=list
    )

    evaluation_summary: str = ""