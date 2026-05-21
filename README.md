Neuro-Adaptive Learning Recommender (NALR)

Bridging the Diagnostic Gap: Generative AI for Neurodivergent Early Intervention.

The Neuro-Adaptive Learning Recommender is an AI-powered early intervention platform designed for toddlers (12-36 months). It seamlessly connects clinical behavioral screening with advanced Generative AI to provide personalized therapeutic roadmaps.

[ Live Web Application - Click Here to View]((Insert your Streamlit link here))

Project Overview
Early intervention is the most significant predictor of positive outcomes for neurodivergent children. However, many families in underserved regions face "Specialist Bottlenecks." NALR operates in two high-precision phases:
Diagnostic Screening: A machine learning engine predicts the probability of Autism Spectrum Disorder (ASD) traits using the validated Q-CHAT-10 behavioral screening framework.
Generative Intervention (Powered by Google GenAI): For high-risk profiles, the system "injects" specific developmental deficits into the Google Gemini Pro API. The engine generates a tailored therapeutic strategy and recommends globally-rated digital resources (AAC, Speech Therapy, Sensory apps) based on semantic suitability.

Objectives
Democratize Screening: Provide parent-accessible, clinical-grade screening to bridge the gap in specialist-scarce regions.
Precision Pedagogy: Move beyond generic lists to provide "Reasoning-as-a-Service"—explaining why a specific tool helps a child's unique sensory profile.
Scalable Support: Utilizing Generative AI to translate complex behavioral data into actionable, easy-to-understand guidance for caregivers.

Technical Architecture
1. The Diagnostic Engine (XGBoost)
Dataset: Validated on 6,000+ toddler behavioral samples.
Algorithm: Extreme Gradient Boosting (XGBoost) Classifier.
Metrics:
Accuracy: 93.8%
Recall (Class 1): 93.0% (Optimized to minimize false negatives in medical screening).
2. The Generative Recommendation Engine (Google GenAI Injection)
The Shift: Upgraded from static TF-IDF matching to Google Gemini Pro.
The Mechanism: The system builds a dynamic prompt based on the child's failed markers (e.g., "Non-verbal, sensory-seeking, avoids eye contact").
The Output: Gemini acts as a "Virtual Pathologist," analyzing the child's deficit pattern and recommending the best-fitting tools from a curated database of AAC and Speech Therapy resources.

Tech Stack
AI/ML: XGBoost, Scikit-Learn
LLM/GenAI: Google Generative AI (Gemini Pro API)
Data Engineering: Pandas, NumPy
Frontend/Deployment: Streamlit Cloud

Performance & Explainability
This model utilizes SHAP (SHapley Additive exPlanations) to ensure transparency. Caregivers and clinicians can see exactly which behavioral markers (e.g., 'Protodeclarative Pointing' or 'Social Smiling') influenced the AI's risk assessment.

Developed by Taiye Janet Fagbolade and Iyanu Arowosola
