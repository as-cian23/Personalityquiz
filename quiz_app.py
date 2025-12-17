import streamlit as st
import pandas as pd
import random
import numpy as np
import os  # for file existence checks [web:19]
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
default_quiz_path = BASE_DIR / "quiz.xlsx"
default_results_path = BASE_DIR / "results.xlsx"
results_stats_path = BASE_DIR / "results_stats.xlsx"  # New file for first-time stats


@st.cache_data
def load_questions(excel_path: str):
    """Load quiz Excel with robust column handling."""
    df = pd.read_excel(excel_path)

    if len(df.columns) >= 15 or df.columns[0] in ['A', 'Unnamed: 0']:
        colnames = ["question", "ans1", "ans2", "ans3", "ans4",
                    "skip1", "work1", "work2", "work3", "work4",
                    "skip2", "pers1", "pers2", "pers3", "pers4"]
        df = pd.read_excel(excel_path, header=None, names=colnames, usecols="A:O")

    score_cols = ['work1', 'work2', 'work3', 'work4', 'pers1', 'pers2', 'pers3', 'pers4']
    for col in score_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    questions = []
    for _, row in df.iterrows():
        if pd.isna(row['question']):
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


@st.cache_data
def load_results(results_path: str):
    """Load results.xlsx: col0=name, col1=description, col2=image_url (9 results in order)."""
    df = pd.read_excel(results_path, header=None, names=['name', 'description', 'image_url'])
    df = df.dropna(subset=['name']).head(9)
    return df.reset_index(drop=True)


def ensure_stats_file():
    """Create results_stats.xlsx if it doesn't exist."""
    if not os.path.isfile(results_stats_path):
        stats_df = pd.DataFrame(columns=['plant_name', 'count'])
        stats_df.to_excel(results_stats_path, index=False)


def update_stats(plant_name):
    """Update statistics for first-time takers."""
    ensure_stats_file()
    stats_df = pd.read_excel(results_stats_path)
    
    if plant_name in stats_df['plant_name'].values:
        stats_df.loc[stats_df['plant_name'] == plant_name, 'count'] += 1
    else:
        new_row = pd.DataFrame({'plant_name': [plant_name], 'count': [1]})
        stats_df = pd.concat([stats_df, new_row], ignore_index=True)
    
    stats_df.to_excel(results_stats_path, index=False)


def get_result_category(work_score, pers_score):
    """Map scores to 3x3 grid with correct thresholds."""
    work_cat = "LOW" if work_score <= 10 else "MID" if work_score <= 15 else "HIGH"
    pers_cat = "LOW" if pers_score <= 10 else "MID" if pers_score <= 22 else "HIGH"
    return work_cat, pers_cat


def find_result(work_score, pers_score, results_df):
    """Find exact result from 9-result matrix."""
    work_cat, pers_cat = get_result_category(work_score, pers_score)

    category_map = {
        ("HIGH", "HIGH"): 0,
        ("MID", "HIGH"): 1,
        ("LOW", "HIGH"): 2,
        ("HIGH", "MID"): 3,
        ("MID", "MID"): 4,
        ("LOW", "MID"): 5,
        ("HIGH", "LOW"): 6,
        ("MID", "LOW"): 7,
        ("LOW", "LOW"): 8
    }

    key = (work_cat, pers_cat)
    if key in category_map:
        grid_index = category_map[key]
        return results_df.iloc[grid_index]
    return None


st.title("What sort of office plant are you?")

# Check if default files exist on disk [web:16][web:19]
default_quiz_exists = os.path.isfile(default_quiz_path)
default_results_exists = os.path.isfile(default_results_path)

quiz_file = None
results_file = None

# Only show uploaders if corresponding default file is missing
if not default_quiz_exists:
    quiz_file = st.file_uploader("📁 Upload quiz.xlsx", type="xlsx")
if not default_results_exists:
    results_file = st.file_uploader("📁 Upload results.xlsx", type="xlsx")

# Resolve paths / file-like objects
quiz_source = quiz_file if quiz_file is not None else (
    default_quiz_path if default_quiz_exists else None
)
results_source = results_file if results_file is not None else (
    default_results_path if default_results_exists else None
)

if quiz_source and results_source:
    try:
        questions = load_questions(quiz_source)
        if not questions:
            st.error("❌ No valid questions found.")
            st.stop()

        # Initialize session state
        if "responses" not in st.session_state:
            st.session_state.responses = [None] * len(questions)
        if "first_time" not in st.session_state:
            st.session_state.first_time = None

        # NEW: First-time question (asked before quiz questions)
        if st.session_state.first_time is None:
            st.markdown("### Before we start...")
            st.write("**Is this your first time doing the quiz?**")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Yes", key="first_yes"):
                    st.session_state.first_time = True
                    st.rerun()
            with col2:
                if st.button("❌ No", key="first_no"):
                    st.session_state.first_time = False
                    st.rerun()
            st.stop()

        progress_bar = st.progress(0)

        for idx, q in enumerate(questions):
            st.subheader(f"Q{idx+1}")
            st.write(q["question"])

            option_texts = [opt["text"] for opt in q["options"]]
            choice = st.radio("Your answer:", option_texts, key=f"radio_q{idx}")

            if choice:
                st.session_state.responses[idx] = choice

        answered = sum(1 for r in st.session_state.responses if r is not None)
        progress_bar.progress(answered / len(questions))
        st.caption(f"Answered: {answered}/{len(questions)} questions")

        if st.button("Calculate My Results!", type="primary"):
            total_work = 0.0
            total_pers = 0.0

            for q, chosen_text in zip(questions, st.session_state.responses):
                if chosen_text:
                    selected = next(opt for opt in q["options"] if opt["text"] == chosen_text)
                    total_work += selected["work"]
                    total_pers += selected["personality"]

            results_df = load_results(results_source)
            result = find_result(total_work, total_pers, results_df)

            if result is not None:
                st.markdown("---")
                st.markdown(f"# 🌱 **{result['name']}**")
                st.markdown(f"**{result['description']}**")

                if pd.notna(result['image_url']) and result['image_url']:
                    st.image(result['image_url'], width="content")

                # NEW: Update statistics if first time
                if st.session_state.first_time:
                    update_stats(result['name'])
                    st.success("Thanks for doing the quiz! I hope you enjoyed it, feel free to share it with your friends and colleagues!")

                st.markdown("---")
                
                # Reset for next user
                if st.button("🔄 Take quiz again"):
                    st.session_state.responses = [None] * len(questions)
                    st.session_state.first_time = None
                    st.rerun()
            else:
                st.warning("❌ No matching result found. Check scores vs thresholds.")

    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
else:
    st.info("📁 Waiting for quiz and results Excel files.")
