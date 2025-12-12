import streamlit as st
import pandas as pd
import random
import numpy as np

@st.cache_data
def load_questions(excel_path: str):
    """Load quiz Excel with robust column handling."""
    df = pd.read_excel(excel_path)
    st.write("**DEBUG: Quiz Excel columns:**", list(df.columns))
    st.write("**DEBUG: First few rows:**")
    st.dataframe(df.head())

    if len(df.columns) >= 15 or df.columns[0] in ['A', 'Unnamed: 0']:
        colnames = ["question", "ans1", "ans2", "ans3", "ans4",
                   "skip1", "work1", "work2", "work3", "work4",
                   "skip2", "pers1", "pers2", "pers3", "pers4"]
        df = pd.read_excel(excel_path, header=None, names=colnames, usecols="A:O")
        st.success("✅ Quiz: Using NO HEADER mode (columns A-O)")

    score_cols = ['work1', 'work2', 'work3', 'work4', 'pers1', 'pers2', 'pers3', 'pers4']
    for col in score_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    questions = []
    for idx, row in df.iterrows():
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
    """Load results.xlsx: col0=name, col1=description, col2=image_url (9 results in order)"""
    df = pd.read_excel(results_path, header=None, names=['name', 'description', 'image_url'])
    df = df.dropna(subset=['name']).head(9)  # Exactly 9 results
    return df.reset_index(drop=True)

def get_result_category(work_score, pers_score):
    """Map scores to 3x3 grid with correct thresholds"""
    # Work: <20=LOW, 20-40=MID (incl. 20,40), >40=HIGH
    # Pers: <30=LOW, 30-60=MID (incl. 30,60), >60=HIGH
    work_cat = "LOW" if work_score < 10 else "MID" if work_score <= 17 else "HIGH"
    pers_cat = "LOW" if pers_score < 11 else "MID" if pers_score <= 22 else "HIGH"
    
    return work_cat, pers_cat

def find_result(work_score, pers_score, results_df):
    """Find exact result from 9-result matrix - FIXED indexing"""
    work_cat, pers_cat = get_result_category(work_score, pers_score)
    
    # CORRECT 3x3 mapping (column-major: pers x work)
    category_map = {
        ("HIGH", "HIGH"): 0,   # Row 1: maxW_maxP
        ("MID", "HIGH"): 1,    # Row 2: midW_maxP  
        ("LOW", "HIGH"): 2,    # Row 3: lowW_maxP
        ("HIGH", "MID"): 3,    # Row 4: maxW_midP
        ("MID", "MID"): 4,     # Row 5: midW_midP
        ("LOW", "MID"): 5,     # Row 6: lowW_midP  ← YOUR CASE
        ("HIGH", "LOW"): 6,    # Row 7: maxW_lowP
        ("MID", "LOW"): 7,     # Row 8: midW_lowP
        ("LOW", "LOW"): 8      # Row 9: lowW_lowP
    }
    
    key = (work_cat, pers_cat)
    if key in category_map:
        grid_index = category_map[key]
        return results_df.iloc[grid_index]
    return None

st.title("🧠 Personality & Work Style Quiz")

# File inputs
quiz_file = st.file_uploader("📁 Upload quiz.xlsx", type="xlsx")
results_file = st.file_uploader("📁 Upload results.xlsx", type="xlsx")

quiz_path = quiz_file.name if quiz_file else "Personalityquiz/quiz.xlsx"
results_path = results_file.name if results_file else "Personalityquiz/results.xlsx"

if quiz_path:
    try:
        questions = load_questions(quiz_file if quiz_file else quiz_path)
        if not questions:
            st.error("❌ No valid questions found.")
            st.stop()
        
        st.success(f"✅ Loaded {len(questions)} questions!")

        if "responses" not in st.session_state:
            st.session_state.responses = [None] * len(questions)

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

        if st.button("🚀 Calculate My Results!", type="primary"):
            total_work = total_pers = 0.0
            valid_answers = 0

            for q, chosen_text in zip(questions, st.session_state.responses):
                if chosen_text:
                    selected = next(opt for opt in q["options"] if opt["text"] == chosen_text)
                    total_work += selected["work"]
                    total_pers += selected["personality"]
                    valid_answers += 1

            # Load results and find match
            results_df = load_results(results_file if results_file else results_path)
            st.success(f"📊 Raw Scores: Work={total_work:.1f}, Personality={total_pers:.1f}")
            
            result = find_result(total_work, total_pers, results_df)
            
            if result is not None:
                st.markdown("---")
                st.markdown(f"# 🎯 **{result['name']}**")
                st.markdown(f"**{result['description']}**")
                
                if pd.notna(result['image_url']) and result['image_url']:
                    st.image(result['image_url'], use_column_width=True)
                
                st.markdown("---")
            else:
                st.warning("❌ No matching result found. Check scores vs thresholds.")

    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
        st.info("""
**Quiz Excel (NO headers):**
Row1: [Question] [A] [B] [C] [D] [empty] [1.0] [2.0] [0.5] [3.0] [empty] [2.0] [1.5] [4.0] [0.0]

**Results Excel (NO headers, EXACTLY 9 rows in this order):**
Row1: maxW_maxP    [desc]    [image_url]  # HIGH work (>40), HIGH pers (>60)
Row2: midW_maxP    [desc]    [image_url]  # MID work (20-40), HIGH pers (>60)
Row3: lowW_maxP    [desc]    [image_url]  # LOW work (<20), HIGH pers (>60)
Row4: maxW_midP    [desc]    [image_url]  # HIGH work (>40), MID pers (30-60)
Row5: midW_midP    [desc]    [image_url]  # MID work (20-40), MID pers (30-60)
Row6: lowW_midP    [desc]    [image_url]  # LOW work (<20), MID pers (30-60)
Row7: maxW_lowP    [desc]    [image_url]  # HIGH work (>40), LOW pers (<30)
Row8: midW_lowP    [desc]    [image_url]  # MID work (20-40), LOW pers (<30)
Row9: lowW_lowP    [desc]    [image_url]  # LOW work (<20), LOW pers (<30)
        """)
else:
    st.info("👈 Upload both Excel files or place them in folder")
