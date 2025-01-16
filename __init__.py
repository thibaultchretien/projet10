import azure.functions as func
from azure.storage.blob import BlobServiceClient
import pandas as pd
import pickle
import json
import logging
from io import BytesIO

# Configuration du logging
logging.basicConfig(level=logging.INFO)

def load_model(connect_str, container_name, blob_name):
    """Charge le modèle à partir d'Azure Blob Storage."""
    try:
        logging.info("Connecting to Azure Blob Storage...")
        blob_service_client = BlobServiceClient.from_connection_string(connect_str)
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)

        logging.info("Downloading model...")
        stream = BytesIO()
        blob_data = blob_client.download_blob()
        blob_data.readinto(stream)
        stream.seek(0)

        logging.info("Loading model into memory...")
        model = pickle.load(stream)
        logging.info("Model loaded successfully.")
        return model
    except Exception as e:
        logging.error(f"Failed to load model: {e}")
        raise RuntimeError(f"Error loading model: {e}")

def recommend_collaborative_filtering(user_id, user_item_matrix, user_similarity_df, top_n=5):
    """Recommande des articles basés sur la similarité entre utilisateurs."""
    logging.info(f"Generating recommendations for user {user_id}...")
    if user_id not in user_item_matrix.index:
        logging.warning(f"User {user_id} not found in the user-item matrix.")
        return []

    similar_users = user_similarity_df[user_id].sort_values(ascending=False)[1:]
    similar_users_ids = similar_users.index[:top_n]

    recommended_articles = set()
    for similar_user_id in similar_users_ids:
        similar_user_clicks = user_item_matrix.loc[similar_user_id]
        recommended_articles.update(similar_user_clicks[similar_user_clicks > 0].index)

    user_clicks = user_item_matrix.loc[user_id]
    final_recommendations = [
        int(article_id) for article_id in recommended_articles
        if article_id not in user_clicks[user_clicks > 0].index
    ]

    logging.info(f"Recommendations for user {user_id}: {final_recommendations[:top_n]}")
    return final_recommendations[:top_n]

def main(req: func.HttpRequest) -> func.HttpResponse:
    connect_str = "DefaultEndpointsProtocol=https;AccountName=modelsimilarity;AccountKey=XedEJjSMXyuS+R9CRe6aUxSNugSBkk7cvWZsndZnnZ/JVOsHFdxaZauWGgQDft1/T0lwMZQEVC2n+ASt1ycjHQ==;EndpointSuffix=core.windows.net"
    container_name_model = "model"
    blob_name_model = "user_similarity_model.pkl"

    try:
        # Charger le modèle
        model_data = load_model(connect_str, container_name_model, blob_name_model)
        user_item_matrix = model_data['user_item_matrix']
        user_similarity_df = model_data['user_similarity_df']
    except Exception as e:
        logging.error(f"Error during model initialization: {e}")
        return func.HttpResponse(
            json.dumps({"error": f"Error during model initialization: {e}"}),
            mimetype="application/json",
            status_code=500
        )

    try:
        # Parse JSON depuis la requête
        req_body = req.get_json()
        logging.info(f"Received request body: {req_body}")

        # Validation des champs requis
        if "user_id" not in req_body:
            return func.HttpResponse(
                json.dumps({"error": "Missing 'user_id' in the request body."}),
                mimetype="application/json",
                status_code=400
            )

        user_id = req_body.get("user_id")
        if not isinstance(user_id, int) or user_id <= 0:
            return func.HttpResponse(
                json.dumps({"error": "'user_id' must be a positive integer."}),
                mimetype="application/json",
                status_code=400
            )

        top_n = req_body.get("top_n", 5)
        if not isinstance(top_n, int) or top_n <= 0:
            return func.HttpResponse(
                json.dumps({"error": "'top_n' must be a positive integer."}),
                mimetype="application/json",
                status_code=400
            )

        # Obtenir des recommandations
        recommendations = recommend_collaborative_filtering(
            user_id, user_item_matrix, user_similarity_df, top_n
        )

        response_data = {
            "user_id": user_id,
            "top_n": top_n,
            "recommendations": recommendations
        }

        return func.HttpResponse(
            json.dumps(response_data),
            mimetype="application/json",
            status_code=200
        )

    except json.JSONDecodeError as e:
        logging.error(f"Invalid JSON: {e}")
        return func.HttpResponse(
            json.dumps({"error": "Invalid JSON input."}),
            mimetype="application/json",
            status_code=400
        )
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return func.HttpResponse(
            json.dumps({"error": f"Unexpected error: {str(e)}"}),
            mimetype="application/json",
            status_code=500
        )
