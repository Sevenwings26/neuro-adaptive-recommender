# Neuro-Adaptive ASD Recommender (NALR)

**Bridging the Diagnostic Gap: AI-Powered Early Intervention for Toddlers**

An intelligent screening and recommendation system that helps parents and caregivers identify Autism Spectrum Disorder (ASD) traits in toddlers (12–36 months) and receive **personalized educational app recommendations + contextual guidance**.

---

## Project Overview

The Neuro-Adaptive ASD Recommender combines machine learning with semantic matching and generative AI to deliver:

- Accurate **ASD risk prediction** using the validated **Q-CHAT-10** screening tool.
- **Personalized app recommendations** based on the child’s specific behavioral profile.
- **Contextual explanations** for parents using Google Gemini to make recommendations more understandable and actionable.

---

## Key Features

- Interactive Q-CHAT-10 behavioral screening
- Real-time ASD risk prediction (XGBoost)
- Semantic app recommendations (TF-IDF + Cosine Similarity)
- **Google Gemini-powered contextual guidance** — explains *why* specific apps are recommended for the child’s unique needs
- Modern, dark-mode-friendly Streamlit interface

---

## How It Works

### 1. Diagnostic Engine (XGBoost)
- Trained on 6,000+ toddler behavioral records
- Predicts probability of ASD traits
- Performance: **Accuracy 93.8%** | **Recall 93.0%**

### 2. Recommendation Engine
- **App Matching**: TF-IDF Vectorization + Cosine Similarity on `app_cache.json`
- **Parent Context Generation**: Google Gemini Pro is used to generate **human-friendly explanations** that relate the recommended apps to the child’s specific behavioral challenges (e.g., speech delay, sensory issues, social interaction).

> **Example Gemini Output**:  
> “Because your child shows signs of speech delay and limited eye contact, we recommend ‘Speech Blubs’ — it uses visual prompts and gamification to encourage verbal communication in a low-pressure way…”

---

## Major Updates & Contributions

- Upgraded to **Python 3.13**
- Refactored modeling notebook for better structure and reproducibility
- Migrated from static book recommendations to dynamic **educational app recommendations**
- Created `app_cache.json` (curated apps from Google Play)
- Added `model_card1.json` for model transparency
- Refactored Streamlit app → `autism_streamlit_app.py`
- Integrated **Google Gemini** to provide contextual, parent-friendly explanations

---

## Tech Stack

- **Language**: Python 3.13
- **ML**: XGBoost, scikit-learn, pandas, numpy
- **Vector Search**: TfidfVectorizer + Cosine Similarity
- **Generative AI**: Google Gemini Pro (for contextual explanations)
- **Frontend**: Streamlit
- **Others**: Joblib, Altair, python-dotenv, google-play-scraper

### Major Libraries
```bash
xgboost==3.2.0
scikit-learn==1.8.0
pandas==3.0.3
numpy==2.4.6
streamlit
google-generativeai
joblib==1.5.3
altair==6.1.0
```

---

## Project Structure

```bash
neuro-adpative-recomendation/
├── autism_streamlit_app.py          # Main Streamlit Application
├── files/
│   ├── asd_model1.pkl
│   ├── model_card1.json
│   └── app_cache.json               # Educational apps database
├── notebooks/
│   └── model_training_refactored.ipynb
├── requirements.txt
└── README.md
```

---

## Installation & Setup

1. Clone the repo
2. Create virtual environment and install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Add your Gemini API key:
   ```bash
   # Create .env file
   GEMINI_API_KEY=your_api_key_here
   ```
4. Run the app:
   ```bash
   streamlit run autism_streamlit_app.py
   ```

---

## Usage

1. Fill in the child’s age, sex, and answer the 10 Q-CHAT questions.
2. Get instant risk assessment.
3. For high-risk profiles, receive **ranked app recommendations** + **Gemini-generated explanations** tailored for parents.

> ⚠️ **Important Disclaimer**: This application is a screening and educational support tool. It is **not** a medical diagnostic instrument. Always consult qualified healthcare professionals for diagnosis and intervention.

---

## Authors

- **Taiye Janet Fagbolade** — Data Scientist & ML Engineer
- **Iyanu Arowosola** — ML Engineer & Full-Stack Developer
