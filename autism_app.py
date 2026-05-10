import streamlit as st
import pandas as pd
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# 1. Page Configuration
st.set_page_config(page_title="Neuro-Adaptive Learning Recommender", page_icon="🧠", layout="centered")

# 2. Load the trained model safely
@st.cache_resource
def load_model():
    return joblib.load('asd_model.pkl')

try:
    model = load_model()
except FileNotFoundError:
    st.error("Model file 'asd_model.pkl' not found. Please ensure it is in the same directory.")
    st.stop()

# 3. Static App Database (The 7 Apps you scraped)
app_data =[
    {'App_Name': 'BASICS: Speech | Autism | ADHD', 'Category': 'Education', 'Rating': 3.94, 'Price': 'Free', 'Installs': '500,000+', 'Description': 'BASICS is an award-winning early learning app trusted by families worldwide. Created by experts to help children with speech delay, autism, and ADHD build foundational communication and cognitive skills.'},
    {'App_Name': 'Language Therapy for Children', 'Category': 'Education', 'Rating': 4.1, 'Price': 'Free', 'Installs': '100,000+', 'Description': 'Designed by speech therapists, this app helps children improve their expressive and receptive language through interactive games and visual aids. Perfect for non-verbal toddlers.'},
    {'App_Name': 'Autism Speech and Language', 'Category': 'Medical', 'Rating': 4.0, 'Price': 'Free', 'Installs': '10,000+', 'Description': 'Focuses on visual learning, routine building, and emotional intelligence. Helps children prone to sensory meltdowns communicate their needs without frustration.'},
    {'App_Name': 'Speech Blubs: Language Therapy', 'Category': 'Parenting', 'Rating': 4.49, 'Price': 'Free', 'Installs': '5,000,000+', 'Description': 'Uses video modeling to encourage children to imitate sounds and words. Highly recommended for kids with delayed speech, articulation issues, and apraxia.'},
    {'App_Name': 'Speech Therapy 3 – Learn Words', 'Category': 'Education', 'Rating': 4.2, 'Price': 'Free', 'Installs': '100,000+', 'Description': 'A gamified approach to vocabulary building. Highly visual, low sensory load, making it perfect for children who struggle with joint attention.'},
    {'App_Name': 'Autism ABC App', 'Category': 'Education', 'Rating': 4.3, 'Price': 'Free', 'Installs': '50,000+', 'Description': 'Teaches the alphabet and basic phonics using calming visuals and predictable routines. Ideal for children with sensory sensitivities.'},
    {'App_Name': 'Speech Therapy: Let Me Talk', 'Category': 'Medical', 'Rating': 3.9, 'Price': 'Free', 'Installs': '50,000+', 'Description': 'Listening to non-speech sounds enhances a child’s ability to analyze, evaluate, and think critically. Great for auditory processing challenges.'}
]
df_apps = pd.DataFrame(app_data)

# 4. App UI - Header
st.title("🧠 Neuro-Adaptive Learning Recommender")
st.write("""
This tool uses **Machine Learning** to screen for early signs of Autism Spectrum Disorder (ASD) in toddlers (12-36 months) and uses **Natural Language Processing (NLP)** to recommend personalized, globally-rated digital learning resources based on the child's specific developmental needs.
""")
st.markdown("---")

# 5. User Input (Q-CHAT-10 Survey Translated for Parents)
st.sidebar.header("Toddler Behavioral Profile")
st.sidebar.write("Please answer the following questions regarding the child's behavior:")

# Helper function to map "Always/Usually" to 0 (Pass) and "Sometimes/Rarely/Never" to 1 (Fail/Trait)
def map_response(response):
    return 0 if response == "Yes (Typical)" else 1

age = st.sidebar.slider("Child's Age (Months)", 12, 36, 24)
sex_input = st.sidebar.radio("Child's Biological Sex", ["Male", "Female"])
sex = 1 if sex_input == "Male" else 0

st.sidebar.markdown("### Behavioral Milestones")
a1 = map_response(st.sidebar.radio("1. Does the child look at you when you call their name?",["Yes (Typical)", "No (Delayed)"]))
a2 = map_response(st.sidebar.radio("2. Is it easy to get eye contact with the child?", ["Yes (Typical)", "No (Delayed)"]))
a3 = map_response(st.sidebar.radio("3. Does the child point to indicate what they want?", ["Yes (Typical)", "No (Delayed)"]))
a4 = map_response(st.sidebar.radio("4. Does the child point to share interest with you?", ["Yes (Typical)", "No (Delayed)"]))
a5 = map_response(st.sidebar.radio("5. Does the child engage in pretend play?", ["Yes (Typical)", "No (Delayed)"]))
a6 = map_response(st.sidebar.radio("6. Does the child follow where you are looking?",["Yes (Typical)", "No (Delayed)"]))
a7 = map_response(st.sidebar.radio("7. Does the child speak basic words/communicate?", ["Yes (Typical)", "No (Delayed)"]))
a8 = map_response(st.sidebar.radio("8. Does the child understand simple gestures?", ["Yes (Typical)", "No (Delayed)"]))
a9 = map_response(st.sidebar.radio("9. Does the child have unusual sensory reactions (e.g., staring at nothing)?", ["No (Typical)", "Yes (Delayed)"])) # Flipped logic for clarity
a10 = map_response(st.sidebar.radio("10. Does the child exhibit repetitive behaviors (e.g., hand flapping)?",["No (Typical)", "Yes (Delayed)"]))

# Compile inputs in the exact order the XGBoost model expects
input_data = pd.DataFrame({
    'A1': [a1], 'A2': [a2], 'A3':[a3], 'A4': [a4], 'A5': [a5], 
    'A6': [a6], 'A7': [a7], 'A8': [a8], 'A9': [a9], 'A10': [a10], 
    'Sex': [sex]
})

# 6. Run Prediction & Recommendation
if st.button("Analyze Profile & Get Recommendations", type="primary"):
    with st.spinner('Analyzing behavioral markers...'):
        
        # Predict ASD Risk
        risk_prob = model.predict_proba(input_data)[0][1] * 100
        
        st.subheader("Diagnostic Screening Result")
        if risk_prob >= 50:
            st.error(f"⚠️ **High Likelihood of ASD Traits Detected ({risk_prob:.1f}%)**")
            st.write("Based on the behavioral profile, early intervention is highly recommended. Below is a personalized learning plan generated by our AI.")
            
            # NLP Recommendation Engine
            toddler_needs =[]
            if a1 == 1 or a7 == 1:
                toddler_needs.append("speech delay non-verbal communication talk words articulation")
            if a3 == 1 or a4 == 1:
                toddler_needs.append("social interaction play cognitive learning pointing joint attention")
            if a9 == 1 or a10 == 1:
                toddler_needs.append("sensory meltdowns routine calm visual behavior ADHD")
            
            # If they failed other things but not the specific ones above, give a general query
            if len(toddler_needs) == 0:
                toddler_needs.append("autism special education cognitive skills")
                
            toddler_profile_text = " ".join(toddler_needs)
            
            # TF-IDF & Cosine Similarity
            tfidf = TfidfVectorizer(stop_words='english')
            app_descriptions = df_apps['Description'].tolist()
            
            tfidf_matrix = tfidf.fit_transform(app_descriptions)
            toddler_vector = tfidf.transform([toddler_profile_text])
            
            similarity_scores = cosine_similarity(toddler_vector, tfidf_matrix).flatten()
            df_apps['Match_Score'] = (similarity_scores * 100).round(1)
            
            top_apps = df_apps[df_apps['Match_Score'] > 0].sort_values(by='Match_Score', ascending=False).head(3)
            
            st.markdown("---")
            st.subheader("📱 Personalized App Recommendations")
            
            if not top_apps.empty:
                for _, row in top_apps.iterrows():
                    with st.container():
                        st.markdown(f"#### ⭐ {row['App_Name']} (Match: {row['Match_Score']}%)")
                        st.caption(f"**Category:** {row['Category']} | **Rating:** {row['Rating']}⭐ | **Price:** {row['Price']} | **Installs:** {row['Installs']}")
                        st.write(f"*{row['Description']}*")
                        st.markdown("<br>", unsafe_allow_html=True)
            else:
                st.info("No highly specific apps matched this unique profile, but general early intervention apps like 'Otsimo' are recommended.")
                
        else:
            st.success(f"✅ **Low Likelihood of ASD Traits ({risk_prob:.1f}%)**")
            st.write("The child is currently meeting standard developmental milestones. Routine monitoring is recommended.")

st.markdown("---")
st.caption("Developed by Taiye Janet Fagbolade | Models: XGBoost & TF-IDF (NLP)")