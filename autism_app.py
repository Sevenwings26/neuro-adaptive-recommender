import streamlit as st
import pandas as pd
import joblib
from google_play_scraper import search, app
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from google import genai
import time

# =========================================================
# 1. PAGE CONFIGURATION & API SETUP
# =========================================================
st.set_page_config(page_title="Neuro-Adaptive Learning Recommender", page_icon="🧠", layout="wide")

# =========================================================
# 2. SECURELY LOAD THE GOOGLE GEMINI API KEY
# =========================================================
try:
    # The new SDK uses a Client object instead of genai.configure
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
except Exception as e:
    st.error("Google API Key not found. Please configure Streamlit Secrets.")
    st.stop()

# =========================================================
# 3. LOAD THE MACHINE LEARNING MODEL
# =========================================================
@st.cache_resource
def load_model():
    return joblib.load('asd_model.pkl')

try:
    model = load_model()
except FileNotFoundError:
    st.error("Model file 'asd_model.pkl' not found. Please ensure it is in the same directory.")
    st.stop()

# =========================================================
# 4. APP UI HEADER
# =========================================================
st.title("Neuro-Adaptive Learning Recommender")
st.write("""
This tool screens toddlers (12 - 36 Months) for ASD traits, scrapes live educational apps, and uses an AI Agent to deliver a personalized, empathetic intervention plan.
""")
st.markdown("---")

# =========================================================
# 5. USER INPUT (Sidebar Screening Tool)
# =========================================================
st.sidebar.header("Toddler Behavioral Profile")
st.sidebar.write("Answer the questions below based on the child's behavior:")

def map_response(response):
    return 0 if response == "Yes (Typical)" else 1

age = st.sidebar.slider("Child's Age (Months)", 12, 36, 24)
sex_input = st.sidebar.radio("Biological Sex", ["Male", "Female"])
sex = 1 if sex_input == "Male" else 0

st.sidebar.markdown("### Behavioral Milestones")
a1 = map_response(st.sidebar.radio("1. Looks at you when called?",["Yes (Typical)", "No (Delayed)"]))
a2 = map_response(st.sidebar.radio("2. Makes eye contact easily?", ["Yes (Typical)", "No (Delayed)"]))
a3 = map_response(st.sidebar.radio("3. Points to indicate wants?", ["Yes (Typical)", "No (Delayed)"]))
a4 = map_response(st.sidebar.radio("4. Points to share interest?",["Yes (Typical)", "No (Delayed)"]))
a5 = map_response(st.sidebar.radio("5. Engages in pretend play?", ["Yes (Typical)", "No (Delayed)"]))
a6 = map_response(st.sidebar.radio("6. Follows where you look?", ["Yes (Typical)", "No (Delayed)"]))
a7 = map_response(st.sidebar.radio("7. Speaks basic words?",["Yes (Typical)", "No (Delayed)"]))
a8 = map_response(st.sidebar.radio("8. Understands simple gestures?", ["Yes (Typical)", "No (Delayed)"]))
a9 = map_response(st.sidebar.radio("9. Unusual sensory reactions?", ["No (Typical)", "Yes (Delayed)"]))
a10 = map_response(st.sidebar.radio("10. Repetitive behaviors?", ["No (Typical)", "Yes (Delayed)"]))

input_data = pd.DataFrame({
    'A1': [a1], 'A2': [a2], 'A3':[a3], 'A4': [a4], 'A5': [a5], 
    'A6': [a6], 'A7': [a7], 'A8': [a8], 'A9': [a9], 'A10': [a10], 
    'Sex':[sex]
})

# =========================================================
# 6. EXECUTION: PREDICT -> SCRAPE -> RECOMMEND -> LLM AGENT
# =========================================================
if st.button("Analyze Profile & Generate Plan", type="primary", use_container_width=True):
    
    # --- A. Predict ASD Risk ---
    risk_prob = model.predict_proba(input_data)[0][1] * 100
    
    if risk_prob < 50:
        st.success(f"✅ **Low Likelihood of ASD Traits ({risk_prob:.1f}%)**")
        st.write("The child is currently meeting standard developmental milestones. Routine monitoring is recommended.")
    else:
        st.error(f"⚠️ **High Likelihood of ASD Traits Detected ({risk_prob:.1f}%)**")
        
        # --- B. Live Web Scraping (Finding Apps) ---
        with st.spinner("Scraping live educational apps from the Play Store..."):
            search_results = search("autism speech therapy special education", lang="en", country="us")
            top_apps = search_results[:10] # Get top 10 apps
            
            app_data =[]
            for result in top_apps:
                try:
                    app_details = app(result['appId'], lang='en', country='us')
                    if app_details['genre'] in ['Education', 'Medical', 'Parenting']:
                        app_data.append({
                            'App_Name': app_details['title'],
                            'Category': app_details['genre'],
                            'Rating': round(app_details.get('score', 0), 2),
                            'Price': "Free" if app_details.get('free') else "Paid",
                            'Description': app_details['description'][:600] 
                        })
                except:
                    continue
            df_apps = pd.DataFrame(app_data)
        
        # --- C. NLP Recommendation (TF-IDF Matching) ---
        with st.spinner("Matching apps to the child's specific behavioral needs..."):
            toddler_needs =[]
            if a1 == 1 or a7 == 1: toddler_needs.append("speech delay non-verbal communication talk words")
            if a3 == 1 or a4 == 1 or a6 == 1: toddler_needs.append("social interaction play cognitive learning")
            if a9 == 1 or a10 == 1: toddler_needs.append("sensory meltdowns routine calm visual behavior")
            if not toddler_needs: toddler_needs.append("autism special education cognitive skills")
            
            toddler_profile_text = " ".join(toddler_needs)
            
            tfidf = TfidfVectorizer(stop_words='english')
            tfidf_matrix = tfidf.fit_transform(df_apps['Description'].fillna("").tolist())
            toddler_vector = tfidf.transform([toddler_profile_text])
            
            df_apps['Match_Score'] = (cosine_similarity(toddler_vector, tfidf_matrix).flatten() * 100).round(1)
            best_apps = df_apps.sort_values(by='Match_Score', ascending=False).head(3)
            recommended_app_names = best_apps['App_Name'].tolist()

          # =========================================================
            # NEW: THE GEMINI LLM AGENT (Personalizing the Output)
            # =========================================================
            # =========================================================
            # THE NEW GEMINI LLM AGENT 
            # =========================================================
            st.markdown("---")
            st.subheader(" AI Agent Intervention Plan")
            
            system_prompt = f"""
            You are a compassionate, expert special education consultant. 
            A parent's {age}-month-old toddler was just screened with a {risk_prob:.1f}% likelihood of ASD traits.
            The child struggles with: {toddler_profile_text}.
            
            Our recommendation engine has selected these 3 digital learning apps as the best fit: {recommended_app_names}.
            
            Write a short, highly empathetic, and encouraging message to the parent. 
            Explain gently why early intervention is important, and then briefly explain how those 3 specific apps will help their child's specific developmental delays. 
            Do not provide a medical diagnosis. Keep it under 250 words.
            """

            try:
                # Call the Google Gemini API using the NEW SDK
                response = client.models.generate_content(
                    model='models/gemini-2.5-flash', # The standard, fast, free model
                    contents=system_prompt
                )
                
                # Display the beautifully written Gemini response!
                st.info(response.text)
                
            except Exception as e:
                st.warning(f"LLM Agent currently unavailable. Displaying standard recommendations. (Error: {e})")

        # --- E. Display the Recommended Apps UI ---
        st.markdown("### 📱 Recommended Live Resources")
        for _, row in best_apps.iterrows():
            with st.container():
                st.markdown(f"**⭐ {row['App_Name']}** (Match: {row['Match_Score']}%)")
                st.caption(f"Category: {row['Category']} | Rating: {row['Rating']}⭐ | Price: {row['Price']}")
                st.write(f"_{row['Description'][:150]}..._")

st.markdown("---")
st.caption("Developed by Taiye Janet Fagbolade | Iyanu Arowosola")








