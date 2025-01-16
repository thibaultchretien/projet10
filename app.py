import streamlit as st
import requests

# Azure Function endpoint
AZURE_FUNCTION_URL = "http://localhost:7071/api/RecommendFunction"

# Sample user IDs for selection
USER_IDS = [1, 5, 10, 20, 40, 100, 123, 150]

def get_recommendations(user_id, top_n=5):
    """Call Azure Function to get recommendations for the selected user ID."""
    try:
        # Prepare the payload
        payload = {"user_id": user_id, "top_n": top_n}
        
        # Send POST request to Azure Function
        response = requests.post(AZURE_FUNCTION_URL, json=payload)
        response.raise_for_status()  # Raise error for bad responses (4xx, 5xx)
        
        # Parse the response
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error calling Azure Function: {e}")
        return None

# Streamlit app
st.title("Système de Recommandation")
st.sidebar.header("Options")
selected_user_id = st.sidebar.selectbox("Choisissez un ID utilisateur", USER_IDS)
top_n = st.sidebar.slider("Nombre de recommandations", 1, 10, 5)

if st.button("Obtenir des recommandations"):
    st.info(f"Appel Azure Function pour l'utilisateur ID {selected_user_id}...")
    result = get_recommendations(selected_user_id, top_n)
    
    if result:
        st.success("Recommandations reçues avec succès !")
        st.write("### Articles Recommandés :")
        st.write(result.get("recommendations", []))
    else:
        st.error("Impossible d'obtenir des recommandations.")
