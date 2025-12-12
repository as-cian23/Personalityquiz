import streamlit as st
import pandas as pd
import random
import numpy as np


@st.cache_data
def load_questions(excel_path: str):
    """Load Excel with robust column handling and numeric conversion."""
    # Read ALL columns first to inspect
    df = pd.read_excel(excel_path)
    st.write("**DEBUG: Excel columns found:**", list(df.columns))
    st.write("**DEBUG: First few rows:**")
    st.dataframe(df.head())

    # Handle NO HEADER case (most likely your issue)
    if len(df.columns) >= 15 or df.columns[0] in ['A', 'Unnamed: 0']:
        colnames = ["question", "ans1", "ans2", "ans3", "ans4",
                    "skip1", "work1", "work2", "work3", "work4",
                    "skip2", "pers1", "pers2", "pers3", "pers4"]
        df = pd.read_excel(excel_path, header=None, names=colnames, usecols="A:O")
        st.success("✅ Using NO HEADER mode (columns A-O)")

    # Convert score columns to numeric SAFELY
    score_cols = ['work1', 'work2', 'work3', 'work4', 'pers1', 'pers2', 'pers3', 'pers4']
    for col in score_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')  # NaN for bad values

    questions = []
    for idx, row in df.iterrows():
        if pd.isna(row['question']):  # Skip empty rows
            continue

        options = []
        for i in range(1, 5):
            work_score = row[f'work{i}'] or 0.0
            pers_score = row[f'pers{i}'] or 0.0
            options.append({
                "text": str(row[f'ans{i}'] or f"Option {i}"),
                "work": float(work_score),
                "personality": float(pers_score)
            })

        random.shuffle(options)
        questions.append({
            "question": str(row["question"]),
            "options": options
        })

    random.shuffle(questions)
    return questions


st.title("🧠 Personality & Work Style Quiz")

# File input
uploaded_file = st.file_uploader("📁 Upload quiz.xlsx", type="xlsx")
excel_path = uploaded_file.name if uploaded_file else "quiz.xlsx"

if excel_path and (uploaded_file or excel_path == "quiz.xlsx"):
    try:
        questions = load_questions(uploaded_file if uploaded_file else excel_path)

        if not questions:
            st.error("❌ No valid questions found. Check Excel format.")
            st.stop()

        st.success(f"✅ Loaded {len(questions)} questions!")

        # Session state for answers
        if "responses" not in st.session_state:
            st.session_state.responses = [None] * len(questions)

        # Questions
        for idx, q in enumerate(questions):
            with st.expander(f"Q{idx + 1}: {q['question'][:60]}..."):
                option_texts = [opt["text"] for opt in q["options"]]
                choice = st.radio(
                    "Your answer:",
                    option_texts,
                    index=0 if st.session_state.responses[idx] is None else
                    option_texts.index(st.session_state.responses[idx]),
                    key=f"q_{idx}_{random.randint(1, 10000)}"  # Unique key
                )
                st.session_state.responses[idx] = choice

        if st.button("🚀 Calculate My Scores!", type="primary"):
            total_work = total_pers = 0.0
            valid_answers = 0

            for q, chosen_text in zip(questions, st.session_state.responses):
                if chosen_text:
                    selected = next(opt for opt in q["options"] if opt["text"] == chosen_text)
                    total_work += selected["work"]
                    total_pers += selected["personality"]
                    valid_answers += 1

            col1, col2 = st.columns(2)
            with col1:
                st.metric("💼 Work Score", f"{total_work:.1f}", delta=None)
            with col2:
                st.metric("🧠 Personality Score", f"{total_pers:.1f}", delta=None)

            st.balloons()

    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
        st.info("""
        **Expected Excel format (NO headers needed):**
        ```
        Row1: [Question?] [A] [B] [C] [D] [(empty)] [1.0] [2.0] [0.5] [3.0] [(empty)] [2.0] [1.5] [4.0] [0.0]
        ```
        Columns: A=Question, B-E=Answers, G-J=Work scores, L-O=Personality scores
        """)
else:
    st.info("👈 Upload Excel or place `quiz.xlsx` in folder")
