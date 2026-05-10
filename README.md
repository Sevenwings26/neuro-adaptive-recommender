# Neuro-Adaptive Learning Recommender

## Project Overview
The **Neuro-Adaptive Learning Recommender** is an AI-powered early intervention web application designed to support neurodivergent toddlers (12-36 months). 

The system operates in two phases:
1.  **Diagnostic Screening:** It utilizes a machine learning classifier to predict the probability of Autism Spectrum Disorder (ASD) traits based on the Q-CHAT-10 behavioral screening tool.
2.  **Personalized Intervention:** If high-risk traits are detected, it deploys a Natural Language Processing (NLP) engine to translate the child's specific developmental deficits into personalized recommendations for globally-rated digital learning resources.

**[Live Web Application - Click Here to View]((Insert your Streamlit link here))**

## Objectives
*   **Early Detection:** Provide an accessible, highly accurate screening tool for parents in underserved regions lacking immediate access to pediatric specialists.
*   **Precision Education:** Move beyond "one-size-fits-all" special education by recommending learning tools tailored to a child's specific sensory and communication needs.
*   **Bridge the Gap:** Seamlessly connect clinical diagnostic markers directly to actionable therapeutic and educational interventions.

## Data & Methodology

### 1. The Diagnostic Engine (XGBoost)
*   **Dataset:** Trained on a widely validated dataset of 6,000+ toddlers using the Q-CHAT-10 screening criteria.
*   **Algorithm:** Extreme Gradient Boosting (`XGBoost`) Classifier.
*   **Performance:** 
    *   **Accuracy:** 93.8%
    *   **Recall (Class 1):** 93% (Ensuring critical early detection by minimizing false negatives).

### 2. The Recommendation Engine (NLP)
*   **Data Source:** A curated database of top-rated special education, AAC (Augmentative and Alternative Communication), and speech therapy apps scraped from digital storefronts.
*   **Feature Engineering:** The system translates failed behavioral markers (e.g., lack of eye contact, speech delay) into a targeted natural language query (e.g., *"speech delay non-verbal visual communication"*).
*   **Algorithm:** Uses **TF-IDF (Term Frequency-Inverse Document Frequency)** and **Cosine Similarity** to mathematically rank and recommend the best-fitting digital resources for the child's unique profile.

## Tools & Technologies
*   **Language:** Python
*   **Data Processing:** Pandas, NumPy
*   **Machine Learning:** Scikit-Learn, XGBoost
*   **NLP:** Scikit-Learn (TF-IDF Vectorizer, Cosine Similarity)
*   **Deployment:** Streamlit Community Cloud

## Contributing
Contributions, issues, and feature requests are welcome! If you are a speech therapist, special educator, or developer interested in expanding the app database, please reach out.

## License
This project is open-source and intended for educational and developmental research purposes. It does not replace professional medical diagnosis.

---
*Developed by Taiye Janet Fagbolade*
