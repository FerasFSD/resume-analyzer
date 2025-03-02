import streamlit as st
import spacy
import pdfplumber
from docx import Document
import json
from collections import defaultdict

# Konfiguration: Lade das NLP-Modell und Skills-Daten
nlp = spacy.load("en_core_web_sm")
with open("utils/skills.json") as f:
    SKILLS_DATA = json.load(f)

@st.cache_data
def extract_text(file):
    if file.name.endswith(".pdf"):
        with pdfplumber.open(file) as pdf:
            return " ".join(page.extract_text() for page in pdf.pages)
    elif file.name.endswith(".docx"):
        doc = Document(file)
        return " ".join(para.text for para in doc.paragraphs)
    return ""

@st.cache_data
def analyze_text(text):
    doc = nlp(text.lower())
    results = {"tech_skills": defaultdict(list), "job_keywords": []}
    
    # Finde Tech-Skills
    for category, skills in SKILLS_DATA["tech_skills"].items():
        for skill in skills:
            if skill.lower() in text.lower():
                results["tech_skills"][category].append(skill)
    
    # Finde Job-Keywords
    results["job_keywords"] = [
        kw for kw in SKILLS_DATA["job_keywords"]
        if kw.lower() in text.lower()
    ]
    
    return results

def calculate_match(resume_data, job_data):
    total_required = sum(len(skills) for skills in job_data["tech_skills"].values()) + len(job_data["job_keywords"])
    matched = 0
    
    # Abgleich der Tech-Skills
    for category, jd_skills in job_data["tech_skills"].items():
        resume_skills = resume_data["tech_skills"].get(category, [])
        matched += len(set(resume_skills) & set(jd_skills))
    
    # Abgleich der Keywords
    matched += len(set(resume_data["job_keywords"]) & set(job_data["job_keywords"]))
    
    return (matched / total_required * 100) if total_required > 0 else 0

# ----------------- Frontend -----------------
st.set_page_config(page_title="AI Powered Tech-Roles-Matching Tool", layout="wide")
st.title("AAI Powered Tech-Roles-Matching Tool 💼")

# Wir verwenden einen dynamischen Reset-Zähler, der als Teil der Keys genutzt wird
if "reset_count" not in st.session_state:
    st.session_state.reset_count = 0

# Button zum kompletten Zurücksetzen der App (erhöht den Reset-Zähler)
if st.button("Neues Matching starten"):
    st.session_state.reset_count += 1
    st.experimental_rerun()

# Sidebar: Eingaben für die Jobbeschreibung mit dynamischen Keys
with st.sidebar:
    st.header("Job Description Eingabe")
    st.markdown("Füge hier den Text der Jobbeschreibung ein oder lade die Datei hoch.")
    job_desc_text = st.text_area("Jobbeschreibung Text", key=f"job_desc_text_{st.session_state.reset_count}")
    job_desc_file = st.file_uploader("Jobbeschreibung hochladen (PDF/DOCX)", type=["pdf", "docx"], key=f"job_desc_file_{st.session_state.reset_count}")

# Hauptbereich: Lebenslauf Upload mit dynamischem Key
st.header("Dein Lebenslauf Upload")
st.markdown("Bitte lade deinen Lebenslauf als PDF oder DOCX hoch.")
resume_file = st.file_uploader("Lebenslauf hochladen (PDF/DOCX)", type=["pdf", "docx"], key=f"resume_file_{st.session_state.reset_count}")

# Button zum Starten des Matching-Prozesses
if st.button("Matching starten"):
    if resume_file and (job_desc_text or job_desc_file):
        with st.spinner("Analysiere Dokumente..."):
            # Analyse des Lebenslaufs
            resume_text = extract_text(resume_file)
            resume_skills = analyze_text(resume_text)
            
            # Analyse der Jobbeschreibung
            if job_desc_file:
                job_desc_text = extract_text(job_desc_file)
            job_desc_skills = analyze_text(job_desc_text)
            
            # Berechne den Matching Score
            try:
                match_score = calculate_match(resume_skills, job_desc_skills)
            except Exception as e:
                st.error(f"⚠️ Fehler beim Berechnen des Scores: {str(e)}")
                match_score = 0

        # Ergebnisse anzeigen
        st.subheader("🔧 Gefundene Tech-Skills (Lebenslauf)")
        for category, skills in resume_skills["tech_skills"].items():
            if skills:
                st.markdown(f"**{category.upper()}**: {', '.join(skills)}")
        st.markdown(f"**Keywords:** {', '.join(resume_skills['job_keywords'])}")

        st.subheader("🎯 Geforderte Skills (Jobbeschreibung)")
        for category, skills in job_desc_skills["tech_skills"].items():
            if skills:
                st.markdown(f"**{category.upper()}**: {', '.join(skills)}")
        st.markdown(f"**Keywords:** {', '.join(job_desc_skills['job_keywords'])}")
        
        # Fehlende Skills ermitteln
        missing_skills = {}
        for category, jd_skills in job_desc_skills["tech_skills"].items():
            resume_list = resume_skills["tech_skills"].get(category, [])
            missing = list(set(jd_skills) - set(resume_list))
            if missing:
                missing_skills[category] = missing

        if missing_skills:
            st.subheader("❌ Fehlende Skills")
            for category, skills in missing_skills.items():
                st.markdown(f"**{category.upper()}**: {', '.join(skills)}")
        
        # Gesamt-Match-Score anzeigen
        st.metric("Overall Match Score", f"{match_score:.1f}%")
    else:
        st.info("Bitte lade sowohl deinen Lebenslauf als auch die Jobbeschreibung hoch.")
