import os
import tempfile

import streamlit as st

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from models.candidate_state import CandidateState
from agents.resume_agent import ResumeAgent
from agents.technical_agent import TechnicalAgent
from agents.coding_agent import CodingAgent
from agents.hr_agent import HRAgent
from agents.evaluation_agent import EvaluationAgent
from utils.pdf_parser import extract_text_from_pdf


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="PlacementAI",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =========================================================
# CUSTOM UI
# =========================================================

st.markdown(
    """
    <style>

    .main-title {
        font-size: 42px;
        font-weight: 800;
        margin-bottom: 4px;
    }

    .subtitle {
        font-size: 17px;
        opacity: 0.75;
        margin-bottom: 25px;
    }

    .step-card {
        padding: 14px;
        border-radius: 12px;
        border: 1px solid rgba(128,128,128,0.25);
        text-align: center;
        margin-bottom: 10px;
    }

    .score-box {
        padding: 20px;
        border-radius: 14px;
        border: 1px solid rgba(128,128,128,0.25);
        text-align: center;
        margin-bottom: 10px;
    }

    .score-number {
        font-size: 30px;
        font-weight: 800;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# SESSION STATE
# =========================================================

if "candidate" not in st.session_state:
    st.session_state.candidate = None

candidate = st.session_state.candidate


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def score_card(title, score):
    st.markdown(
        f"""
        <div class="score-box">
            <div>{title}</div>
            <div class="score-number">{score:.1f}/10</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def interview_complete(state):
    return (
        bool(state.technical_answers)
        and bool(state.coding_submissions)
        and bool(state.hr_answers)
        and isinstance(state.hr_answers[0], dict)
    )


# =========================================================
# PDF REPORT GENERATOR
# =========================================================

def create_pdf_report(candidate):

    pdf_path = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".pdf",
    ).name

    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
    )

    styles = getSampleStyleSheet()

    title_style = styles["Title"]
    heading_style = styles["Heading2"]
    body_style = styles["BodyText"]

    story = []

    # -----------------------------------------------------
    # TITLE
    # -----------------------------------------------------

    story.append(
        Paragraph(
            "PlacementAI - Final Placement Report",
            title_style,
        )
    )

    story.append(Spacer(1, 15))

    story.append(
        Paragraph(
            f"<b>Candidate:</b> "
            f"{candidate.name or 'Candidate'}",
            body_style,
        )
    )

    story.append(
        Paragraph(
            f"<b>Email:</b> "
            f"{candidate.email or 'Not available'}",
            body_style,
        )
    )

    story.append(
        Paragraph(
            f"<b>Target Role:</b> "
            f"{candidate.target_role or 'Not specified'}",
            body_style,
        )
    )

    story.append(Spacer(1, 20))

    # -----------------------------------------------------
    # SCORE SUMMARY
    # -----------------------------------------------------

    story.append(
        Paragraph(
            "Performance Summary",
            heading_style,
        )
    )

    score_data = [
        ["Category", "Score"],
        [
            "Overall",
            f"{candidate.overall_score:.1f}/10",
        ],
        [
            "Technical",
            f"{candidate.technical_score:.1f}/10",
        ],
        [
            "Coding",
            f"{candidate.coding_score:.1f}/10",
        ],
        [
            "HR",
            f"{candidate.hr_score:.1f}/10",
        ],
    ]

    table = Table(
        score_data,
        colWidths=[3 * inch, 2 * inch],
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.lightgrey,
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.grey,
                ),
                (
                    "FONTNAME",
                    (0, 0),
                    (-1, 0),
                    "Helvetica-Bold",
                ),
                (
                    "ALIGN",
                    (1, 1),
                    (1, -1),
                    "CENTER",
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    8,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    8,
                ),
            ]
        )
    )

    story.append(table)
    story.append(Spacer(1, 20))

    # -----------------------------------------------------
    # SUMMARY
    # -----------------------------------------------------

    if candidate.evaluation_summary:

        story.append(
            Paragraph(
                "Overall Assessment",
                heading_style,
            )
        )

        story.append(
            Paragraph(
                candidate.evaluation_summary,
                body_style,
            )
        )

        story.append(Spacer(1, 15))

    # -----------------------------------------------------
    # LIST SECTION
    # -----------------------------------------------------

    def add_list_section(title, items):

        story.append(
            Paragraph(
                title,
                heading_style,
            )
        )

        if items:

            for item in items:

                story.append(
                    Paragraph(
                        f"• {item}",
                        body_style,
                    )
                )

        else:

            story.append(
                Paragraph(
                    "No specific items identified.",
                    body_style,
                )
            )

        story.append(Spacer(1, 12))

    add_list_section(
        "Strong Areas",
        candidate.strengths,
    )

    add_list_section(
        "Weak Areas",
        candidate.weaknesses,
    )

    add_list_section(
        "Technical Skill Gaps",
        candidate.technical_gaps,
    )

    add_list_section(
        "Coding Skill Gaps",
        candidate.coding_gaps,
    )

    add_list_section(
        "HR / Communication Improvements",
        candidate.hr_improvements,
    )

    add_list_section(
        "Recommended Topics",
        candidate.recommended_topics,
    )

    add_list_section(
        "Preparation Recommendations",
        candidate.recommendations,
    )

    # -----------------------------------------------------
    # BUILD
    # -----------------------------------------------------

    doc.build(story)

    return pdf_path


# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:

    st.markdown("## 🎯 PlacementAI")

    st.caption(
        "AI-powered placement preparation using "
        "5 specialized agents."
    )

    st.divider()

    st.markdown("### Your Progress")

    if candidate is None:

        st.write("⚪ Resume Analysis")
        st.write("⚪ Technical Interview")
        st.write("⚪ Coding Interview")
        st.write("⚪ HR Interview")
        st.write("⚪ Final Evaluation")

    else:

        st.write("🟢 Resume Analysis")

        st.write(
            "🟢 Technical Interview"
            if candidate.technical_questions
            else "⚪ Technical Interview"
        )

        st.write(
            "🟢 Coding Interview"
            if candidate.coding_questions
            else "⚪ Coding Interview"
        )

        st.write(
            "🟢 HR Interview"
            if candidate.hr_questions
            else "⚪ HR Interview"
        )

        st.write(
            "🟢 Final Evaluation"
            if candidate.overall_score > 0
            else "⚪ Final Evaluation"
        )

    st.divider()

    if candidate:

        st.markdown("### Candidate")

        st.write(
            candidate.name or "Candidate"
        )

        if candidate.target_role:
            st.caption(candidate.target_role)

        st.divider()

        if st.button(
            "🔄 Start New Assessment",
            use_container_width=True,
        ):

            st.session_state.candidate = None

            for key in list(st.session_state.keys()):

                if (
                    key.startswith("technical_answer_")
                    or key.startswith("hr_answer_")
                    or key in [
                        "coding_code",
                        "coding_language",
                    ]
                ):
                    del st.session_state[key]

            st.rerun()


# =========================================================
# HEADER
# =========================================================

st.markdown(
    '<div class="main-title">🎯 PlacementAI</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="subtitle">'
    "Your AI-powered placement preparation platform — "
    "Resume analysis, technical interviews, coding, HR "
    "and final evaluation."
    "</div>",
    unsafe_allow_html=True,
)


# =========================================================
# FIVE STEP OVERVIEW
# =========================================================

step_cols = st.columns(5)

steps = [
    ("1", "📄", "Resume"),
    ("2", "💻", "Technical"),
    ("3", "👨‍💻", "Coding"),
    ("4", "🗣️", "HR"),
    ("5", "🏆", "Evaluation"),
]

for col, (number, icon, name) in zip(
    step_cols,
    steps,
):

    with col:

        st.markdown(
            f"""
            <div class="step-card">
                <div style="font-size:24px">{icon}</div>
                <b>{number}. {name}</b>
            </div>
            """,
            unsafe_allow_html=True,
        )


st.divider()


# =========================================================
# STEP 1 — RESUME
# =========================================================

st.header("📄 Step 1 — Resume Analysis")

st.write(
    "Upload your resume and let the Resume Agent "
    "extract your candidate profile automatically."
)

uploaded_file = st.file_uploader(
    "Upload Resume PDF",
    type=["pdf"],
    help="Upload a text-based PDF resume.",
)

if uploaded_file is not None:

    st.caption(
        f"Selected: {uploaded_file.name}"
    )

    if st.button(
        "🚀 Analyze Resume",
        type="primary",
        use_container_width=True,
        key="analyze_resume",
    ):

        temp_path = None

        try:

            with tempfile.NamedTemporaryFile(
                delete=False,
                suffix=".pdf",
            ) as temp_file:

                temp_file.write(
                    uploaded_file.getbuffer()
                )

                temp_path = temp_file.name

            with st.spinner(
                "Resume Agent is analyzing your resume..."
            ):

                resume_text = extract_text_from_pdf(
                    temp_path
                )

                state = CandidateState()

                state = ResumeAgent().run(
                    resume_text=resume_text,
                    state=state,
                )

                st.session_state.candidate = state

            st.success(
                "✅ Resume analyzed successfully!"
            )

        except Exception as e:

            st.error(
                f"Resume analysis failed: {e}"
            )

        finally:

            if temp_path and os.path.exists(temp_path):
                os.unlink(temp_path)


# =========================================================
# CANDIDATE PROFILE
# =========================================================

candidate = st.session_state.candidate

if candidate is not None:

    st.divider()

    st.header("👤 Candidate Profile")

    col1, col2 = st.columns(2)

    with col1:

        st.markdown("### Personal Information")

        st.write(
            f"**Name:** "
            f"{candidate.name or 'Not detected'}"
        )

        st.write(
            f"**Email:** "
            f"{candidate.email or 'Not detected'}"
        )

        st.write(
            f"**Phone:** "
            f"{candidate.phone or 'Not detected'}"
        )

        st.write(
            f"**Target Role:** "
            f"{candidate.target_role or 'Not detected'}"
        )

    with col2:

        st.markdown("### Skills")

        st.write(
            " • ".join(candidate.skills)
            if candidate.skills
            else "No skills detected."
        )

        st.markdown("### Technical Areas")

        st.write(
            " • ".join(candidate.technical_topics)
            if candidate.technical_topics
            else "No technical topics detected."
        )

    with st.expander("🎓 Education"):

        for item in candidate.education:
            st.write(f"• {item}")

        if not candidate.education:
            st.caption("No education information detected.")

    with st.expander("🚀 Projects"):

        for item in candidate.projects:
            st.write(f"• {item}")

        if not candidate.projects:
            st.caption("No projects detected.")

    with st.expander("💼 Experience"):

        for item in candidate.experience:
            st.write(f"• {item}")

        if not candidate.experience:
            st.caption("No experience detected.")

    with st.expander("📜 Certifications"):

        for item in candidate.certifications:
            st.write(f"• {item}")

        if not candidate.certifications:
            st.caption("No certifications detected.")


    # =====================================================
    # STEP 2 — TECHNICAL
    # =====================================================

    st.divider()

    st.header("💻 Step 2 — Technical Interview")

    st.write(
        "The Technical Agent uses your candidate profile "
        "and RAG knowledge base to generate personalized "
        "interview questions."
    )

    technical_agent = TechnicalAgent()

    if st.button(
        "🧠 Generate Technical Questions",
        key="generate_technical",
        use_container_width=True,
    ):

        try:

            with st.spinner(
                "Technical Agent is generating questions..."
            ):

                candidate = technical_agent.run(
                    state=candidate,
                    questions_per_topic=2,
                )

                st.session_state.candidate = candidate

            st.success(
                "✅ Technical questions generated."
            )

        except Exception as e:

            st.error(
                f"Technical question generation failed: {e}"
            )


    candidate = st.session_state.candidate

    if candidate.technical_questions:

        st.subheader("Interview Questions")

        technical_answers = []

        for index, question_data in enumerate(
            candidate.technical_questions
        ):

            question = question_data.get(
                "question",
                "",
            )

            topic = question_data.get(
                "topic",
                "",
            )

            difficulty = question_data.get(
                "difficulty",
                "",
            )

            with st.expander(
                f"Q{index + 1} — {topic}",
                expanded=True,
            ):

                st.markdown(
                    f"**{question}**"
                )

                st.caption(
                    f"Topic: {topic} | "
                    f"Difficulty: {difficulty}"
                )

                answer = st.text_area(
                    "Your answer",
                    key=f"technical_answer_{index}",
                    height=150,
                )

                technical_answers.append(
                    {
                        "question": question,
                        "topic": topic,
                        "answer": answer,
                    }
                )


        if st.button(
            "📊 Evaluate Technical Answers",
            key="evaluate_technical",
            type="primary",
            use_container_width=True,
        ):

            if any(
                item["answer"].strip()
                for item in technical_answers
            ):

                candidate.technical_answers = (
                    technical_answers
                )

                try:

                    with st.spinner(
                        "Technical Agent is evaluating your answers..."
                    ):

                        candidate = (
                            technical_agent.evaluate_answers(
                                state=candidate
                            )
                        )

                        st.session_state.candidate = candidate

                    st.success(
                        "✅ Technical answers evaluated."
                    )

                except Exception as e:

                    st.error(
                        f"Technical evaluation failed: {e}"
                    )

            else:

                st.warning(
                    "Please answer at least one question."
                )


    # =====================================================
    # TECHNICAL RESULTS
    # =====================================================

    candidate = st.session_state.candidate

    if candidate.technical_answers:

        st.subheader("📊 Technical Results")

        col1, col2 = st.columns([1, 3])

        with col1:

            score_card(
                "Technical Score",
                candidate.technical_score,
            )

        with col2:

            st.info(
                "Review the detailed feedback below to "
                "understand which concepts you need to improve."
            )

        for index, result in enumerate(
            candidate.technical_answers
        ):

            if not isinstance(result, dict):
                continue

            with st.expander(
                f"Q{index + 1} — "
                f"{result.get('score', 0)}/10"
            ):

                st.write(
                    f"**Question:** "
                    f"{result.get('question', '')}"
                )

                st.write(
                    f"**Feedback:** "
                    f"{result.get('feedback', '')}"
                )

                correct = result.get(
                    "correct_concepts",
                    [],
                )

                missing = result.get(
                    "missing_concepts",
                    [],
                )

                if correct:

                    st.success(
                        "Correct Concepts: "
                        + ", ".join(correct)
                    )

                if missing:

                    st.warning(
                        "Missing Concepts: "
                        + ", ".join(missing)
                    )


    # =====================================================
    # STEP 3 — CODING
    # =====================================================

    st.divider()

    st.header("👨‍💻 Step 3 — Coding Interview")

    st.write(
        "The Coding Agent generates a coding problem "
        "based on the candidate profile and evaluates "
        "the submitted solution."
    )

    coding_agent = CodingAgent()

    if st.button(
        "🧩 Generate Coding Problem",
        key="generate_coding",
        use_container_width=True,
    ):

        try:

            with st.spinner(
                "Coding Agent is generating a problem..."
            ):

                candidate = coding_agent.run(
                    state=candidate
                )

                st.session_state.candidate = candidate

            st.success(
                "✅ Coding problem generated."
            )

        except Exception as e:

            st.error(
                f"Coding problem generation failed: {e}"
            )


    candidate = st.session_state.candidate

    if candidate.coding_questions:

        coding_problem = candidate.coding_questions[0]

        st.subheader(
            coding_problem.get(
                "title",
                "Coding Problem",
            )
        )

        st.caption(
            f"Difficulty: "
            f"{coding_problem.get('difficulty', '')}"
        )

        st.markdown(
            coding_problem.get(
                "problem",
                "",
            )
        )

        with st.expander(
            "📥 Input / Output / Constraints",
            expanded=True,
        ):

            st.markdown("**Input Format**")

            st.code(
                coding_problem.get(
                    "input_format",
                    "",
                )
            )

            st.markdown("**Output Format**")

            st.code(
                coding_problem.get(
                    "output_format",
                    "",
                )
            )

            st.markdown("**Constraints**")

            st.write(
                coding_problem.get(
                    "constraints",
                    "",
                )
            )

        examples = coding_problem.get(
            "examples",
            [],
        )

        if examples:

            st.markdown("### Examples")

            for index, example in enumerate(examples):

                st.markdown(
                    f"**Example {index + 1}**"
                )

                st.code(str(example))


        st.markdown("### 💻 Your Solution")

        language = st.selectbox(
            "Programming Language",
            [
                "C++",
                "Python",
                "Java",
            ],
            key="coding_language",
        )

        code = st.text_area(
            "Write your solution here",
            height=350,
            key="coding_code",
            placeholder="Write your code...",
        )

        if st.button(
            "📊 Evaluate Code",
            key="evaluate_coding",
            type="primary",
            use_container_width=True,
        ):

            if not code.strip():

                st.warning(
                    "Please enter your code."
                )

            else:

                try:

                    with st.spinner(
                        "Coding Agent is evaluating your solution..."
                    ):

                        candidate = (
                            coding_agent.evaluate_submission(
                                state=candidate,
                                code=code,
                                language=language,
                            )
                        )

                        st.session_state.candidate = candidate

                    st.success(
                        "✅ Code evaluated successfully."
                    )

                except Exception as e:

                    st.error(
                        f"Coding evaluation failed: {e}"
                    )


    # =====================================================
    # CODING RESULTS
    # =====================================================

    candidate = st.session_state.candidate

    if candidate.coding_submissions:

        st.subheader("📊 Coding Results")

        col1, col2 = st.columns([1, 3])

        with col1:

            score_card(
                "Coding Score",
                candidate.coding_score,
            )

        with col2:

            latest_submission = (
                candidate.coding_submissions[-1]
            )

            st.write(
                f"**Language:** "
                f"{latest_submission.get('language', '')}"
            )

            st.write(
                f"**Correctness:** "
                f"{latest_submission.get('correctness', '')}"
            )

        with st.expander(
            "📝 Detailed Coding Feedback",
            expanded=True,
        ):

            st.write(
                "**Feedback:**"
            )

            st.write(
                latest_submission.get(
                    "feedback",
                    "",
                )
            )

            st.write(
                "**Time Complexity:** "
                + latest_submission.get(
                    "time_complexity",
                    "",
                )
            )

            st.write(
                "**Space Complexity:** "
                + latest_submission.get(
                    "space_complexity",
                    "",
                )
            )

            edge_cases = latest_submission.get(
                "edge_cases",
                [],
            )

            if edge_cases:

                st.write("**Edge Cases:**")

                for item in edge_cases:
                    st.write(f"• {item}")

            improvements = latest_submission.get(
                "improvements",
                [],
            )

            if improvements:

                st.write("**Improvements:**")

                for item in improvements:
                    st.write(f"• {item}")


    # =====================================================
    # STEP 4 — HR
    # =====================================================

    st.divider()

    st.header("🗣️ Step 4 — HR Interview")

    st.write(
        "The HR Agent generates personalized behavioral "
        "and HR questions based on your candidate profile "
        "and previous performance."
    )

    hr_agent = HRAgent()

    if st.button(
        "🎤 Generate HR Questions",
        key="generate_hr",
        use_container_width=True,
    ):

        try:

            with st.spinner(
                "HR Agent is generating personalized questions..."
            ):

                candidate = hr_agent.run(
                    state=candidate,
                    questions_count=6,
                )

                st.session_state.candidate = candidate

            st.success(
                "✅ HR questions generated."
            )

        except Exception as e:

            st.error(
                f"HR question generation failed: {e}"
            )


    candidate = st.session_state.candidate

    if candidate.hr_questions:

        st.subheader("HR Questions")

        hr_answers = []

        for index, question in enumerate(
            candidate.hr_questions
        ):

            with st.expander(
                f"Q{index + 1}",
                expanded=True,
            ):

                st.markdown(
                    f"**{question}**"
                )

                answer = st.text_area(
                    "Your answer",
                    key=f"hr_answer_{index}",
                    height=130,
                )

                hr_answers.append(answer)


        if st.button(
            "📊 Evaluate HR Answers",
            key="evaluate_hr",
            type="primary",
            use_container_width=True,
        ):

            if any(
                answer.strip()
                for answer in hr_answers
            ):

                candidate.hr_answers = hr_answers

                try:

                    with st.spinner(
                        "HR Agent is evaluating your answers..."
                    ):

                        candidate = (
                            hr_agent.evaluate_answers(
                                state=candidate
                            )
                        )

                        st.session_state.candidate = candidate

                    st.success(
                        "✅ HR answers evaluated."
                    )

                except Exception as e:

                    st.error(
                        f"HR evaluation failed: {e}"
                    )

            else:

                st.warning(
                    "Please answer at least one HR question."
                )


    # =====================================================
    # HR RESULTS
    # =====================================================

    candidate = st.session_state.candidate

    if (
        candidate.hr_answers
        and isinstance(
            candidate.hr_answers[0],
            dict,
        )
    ):

        st.subheader("📊 HR Results")

        col1, col2 = st.columns([1, 3])

        with col1:

            score_card(
                "HR Score",
                candidate.hr_score,
            )

        with col2:

            st.info(
                "Use the feedback to improve your "
                "communication and interview responses."
            )

        for index, result in enumerate(
            candidate.hr_answers
        ):

            with st.expander(
                f"Q{index + 1} — "
                f"{result.get('score', 0)}/10"
            ):

                st.write(
                    f"**Question:** "
                    f"{result.get('question', '')}"
                )

                st.write(
                    f"**Feedback:** "
                    f"{result.get('feedback', '')}"
                )

                strengths = result.get(
                    "strengths",
                    [],
                )

                improvements = result.get(
                    "improvements",
                    [],
                )

                if strengths:

                    st.success(
                        "Strengths: "
                        + ", ".join(strengths)
                    )

                if improvements:

                    st.warning(
                        "Improvements: "
                        + ", ".join(improvements)
                    )


    # =====================================================
    # STEP 5 — FINAL EVALUATION
    # =====================================================

    st.divider()

    st.header("🏆 Step 5 — Final Placement Evaluation")

    st.write(
        "The Evaluation Agent combines your technical, "
        "coding, and HR performance into a complete "
        "placement preparation report."
    )

    complete_interviews = interview_complete(candidate)

    if not complete_interviews:

        st.info(
            "🔒 Complete the Technical, Coding, and HR "
            "interviews to unlock the final evaluation."
        )

    else:

        st.success(
            "✅ All three interview stages are complete."
        )

        if st.button(
            "🏆 Generate Final Evaluation",
            type="primary",
            key="generate_evaluation",
            use_container_width=True,
        ):

            try:

                with st.spinner(
                    "Evaluation Agent is preparing your final report..."
                ):

                    candidate = EvaluationAgent().run(
                        state=candidate
                    )

                    st.session_state.candidate = candidate

                st.success(
                    "🎉 Final placement evaluation generated!"
                )

            except Exception as e:

                st.error(
                    f"Final evaluation failed: {e}"
                )


    # =====================================================
    # FINAL REPORT
    # =====================================================

    candidate = st.session_state.candidate

    if candidate.overall_score > 0:

        st.divider()

        st.header(
            "🎯 Final Placement Preparation Report"
        )

        st.caption(
            f"Candidate: "
            f"{candidate.name or 'Candidate'}"
            + (
                f" • Target Role: {candidate.target_role}"
                if candidate.target_role
                else ""
            )
        )

        st.markdown("### 📊 Performance Overview")

        score_cols = st.columns(4)

        with score_cols[0]:

            score_card(
                "🏆 Overall",
                candidate.overall_score,
            )

        with score_cols[1]:

            score_card(
                "💻 Technical",
                candidate.technical_score,
            )

        with score_cols[2]:

            score_card(
                "👨‍💻 Coding",
                candidate.coding_score,
            )

        with score_cols[3]:

            score_card(
                "🗣️ HR",
                candidate.hr_score,
            )


        # -------------------------------------------------
        # OVERALL ASSESSMENT
        # -------------------------------------------------

        if candidate.evaluation_summary:

            st.markdown("### 📝 Overall Assessment")

            st.info(
                candidate.evaluation_summary
            )


        # -------------------------------------------------
        # STRENGTHS / WEAKNESSES
        # -------------------------------------------------

        col1, col2 = st.columns(2)

        with col1:

            with st.container(border=True):

                st.subheader("💪 Strong Areas")

                if candidate.strengths:

                    for item in candidate.strengths:
                        st.write(f"✅ {item}")

                else:

                    st.caption(
                        "No specific strengths identified."
                    )

        with col2:

            with st.container(border=True):

                st.subheader("⚠️ Weak Areas")

                if candidate.weaknesses:

                    for item in candidate.weaknesses:
                        st.write(f"🔸 {item}")

                else:

                    st.caption(
                        "No specific weaknesses identified."
                    )


        # -------------------------------------------------
        # SKILL GAPS
        # -------------------------------------------------

        st.markdown("### 🎯 Skill Gap Analysis")

        col1, col2 = st.columns(2)

        with col1:

            with st.container(border=True):

                st.subheader("💻 Technical Gaps")

                if candidate.technical_gaps:

                    for item in candidate.technical_gaps:
                        st.write(f"• {item}")

                else:

                    st.caption(
                        "No major technical gaps identified."
                    )

        with col2:

            with st.container(border=True):

                st.subheader("👨‍💻 Coding Gaps")

                if candidate.coding_gaps:

                    for item in candidate.coding_gaps:
                        st.write(f"• {item}")

                else:

                    st.caption(
                        "No major coding gaps identified."
                    )


        # -------------------------------------------------
        # HR
        # -------------------------------------------------

        with st.container(border=True):

            st.subheader(
                "🗣️ HR / Communication Improvements"
            )

            if candidate.hr_improvements:

                for item in candidate.hr_improvements:
                    st.write(f"• {item}")

            else:

                st.caption(
                    "No major HR improvements identified."
                )


        # -------------------------------------------------
        # RECOMMENDED TOPICS
        # -------------------------------------------------

        with st.container(border=True):

            st.subheader("📚 Recommended Topics")

            if candidate.recommended_topics:

                for item in candidate.recommended_topics:
                    st.write(f"📌 {item}")

            else:

                st.caption(
                    "No specific topics recommended."
                )


        # -------------------------------------------------
        # RECOMMENDATIONS
        # -------------------------------------------------

        with st.container(border=True):

            st.subheader(
                "🚀 Preparation Recommendations"
            )

            if candidate.recommendations:

                for item in candidate.recommendations:
                    st.write(f"👉 {item}")

            else:

                st.caption(
                    "No additional recommendations."
                )


        # -------------------------------------------------
        # PDF DOWNLOAD
        # -------------------------------------------------

        st.markdown("### 📄 Download Report")

        st.write(
            "Save your complete placement assessment "
            "as a PDF."
        )

        try:

            pdf_path = create_pdf_report(candidate)

            with open(
                pdf_path,
                "rb",
            ) as pdf_file:

                st.download_button(
                    label="⬇️ Download Final Placement Report",
                    data=pdf_file.read(),
                    file_name="PlacementAI_Final_Report.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )

            # Clean temporary PDF after the button
            # receives its data.
            if os.path.exists(pdf_path):
                os.unlink(pdf_path)

        except Exception as e:

            st.error(
                f"Could not create PDF report: {e}"
            )


        # -------------------------------------------------
        # COMPLETION MESSAGE
        # -------------------------------------------------

        st.success(
            "🎉 Your placement assessment is complete!"
        )


# =========================================================
# FOOTER
# =========================================================

st.divider()

st.caption(
    "PlacementAI • 5-Agent Architecture • "
    "RAG Knowledge Base • Groq LLM"
)
