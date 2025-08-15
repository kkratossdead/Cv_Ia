# Configuration pour l'analyse de CV avec IA
# Utilise les secrets Streamlit pour la clé API OpenAI

import streamlit as st

try:
    # Récupère la clé API depuis les secrets Streamlit
    OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
except (KeyError, FileNotFoundError):
    # Fallback pour le développement local
    try:
        from config_local import OPENAI_API_KEY
    except ImportError:
        OPENAI_API_KEY = "your_openai_api_key_here"
        st.warning("⚠️ Clé API OpenAI non configurée. Veuillez ajouter OPENAI_API_KEY dans vos secrets Streamlit.")

GPT_MODEL = "gpt-4"  # Utiliser gpt-4 au lieu de gpt-5

OUTPUT_FORMAT = "json"