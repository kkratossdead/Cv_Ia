import streamlit as st
from db import (init_db, insert_analysis, get_all_analyses, 
                save_job_offer, get_analyses_by_job_offer, 
                get_all_job_offers, get_job_offer_stats)
import openai
import json
from datetime import datetime
import base64
from io import BytesIO
from dotenv import load_dotenv
import config
from utils import pdf_to_images_from_bytes

PRICE_INPUT  = 0.00025
PRICE_OUTPUT = 0.00200

api_key = config.OPENAI_API_KEY
load_dotenv()

st.set_page_config(
    page_title="Analyseur de CV avec IA",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

def initialize_openai():
    api_key = config.OPENAI_API_KEY
    if not api_key:
        st.error("⚠️ Clé API OpenAI non configurée.")
        st.stop()
    openai.api_key = api_key
    return openai  

def analyze_cv_with_vision(pdf_bytes, job_offer, client):
    images = pdf_to_images_from_bytes(pdf_bytes)
    if not images:
        return None

    prompt_text = f"""
Vous êtes un expert RH très exigeant. 
Votre mission : analyser le CV en fonction de l’offre d’emploi fournie.

⚠️ Règles strictes :
- Le JSON doit contenir **exactement et uniquement** les champs suivants, sans en ajouter d'autres.
- Les champs numériques doivent rester des nombres (pas de texte).
- Les détails et explications doivent être intégrés **uniquement** dans les champs texte comme "commentaires" ou "experience_pertinente".
- N'utilisez pas de sous-objets ou de champs imbriqués.

Champs attendus dans le JSON final :
{{
  "nom_prenom": "Nom et prénom du candidat (extrait du CV)",
  "score_technique": [nombre sur 40],
  "score_experience": [nombre sur 30],
  "score_formation": [nombre sur 15],
  "score_soft_skills": [nombre sur 15],
  "score_global": [nombre sur 100],
  "points_forts": ["liste des points forts du candidat"],
  "points_faibles": ["liste des points faibles ou manques"],
  "competences_matchees": ["compétences qui correspondent à l'offre"],
  "competences_manquantes": ["compétences requises mais absentes"],
  "experience_pertinente": "description détaillée de l'expérience pertinente",
  "recommandation": "Recommandé / À considérer / Non recommandé",
  "commentaires": "analyse détaillée du profil",
  "pages_analysees": {len(images)},
  "methode_analyse": "GPT-5 "
}}

Critères de notation :
- Compétences techniques requises : 40 points max
- Expérience pertinente : 30 points max
- Formation et qualifications : 15 points max
- Compétences soft skills : 15 points max

Voici l'offre d'emploi à analyser :
{job_offer}
"""

    content_parts = []
    for img in images:
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        img_base64 = base64.b64encode(buffered.getvalue()).decode()
        content_parts.append({
            "type": "input_image",
            "image_url": f"data:image/png;base64,{img_base64}"
        })

    content_parts.append({
        "type": "input_text",
        "text": prompt_text
    })

    try:
        response = client.responses.create(
    model="gpt-5-mini",
    reasoning={"effort": "minimal"},
    input=[
        {
            "role": "user",
            "content": content_parts
        }
    ]
)


        usage = response.usage
        return {
            "content": response.output_text,
            "tokens": {
                "prompt": usage.input_tokens,
                "completion": usage.output_tokens,
                "total": usage.total_tokens
            }
        }

    except Exception as e:
        st.error(f"❌ Erreur GPT-5 Vision : {e}")
        return None

def display_analysis(analysis_text, filename):
    """Affiche l'analyse de manière structurée, avec tous les sous-scores."""
    try:
        clean = analysis_text.strip()
        if clean.startswith("```json"):
            clean = clean[len("```json"):].strip()
        if clean.endswith("```"):
            clean = clean[:-3].strip()
        analysis = json.loads(clean)

        st.header(f"📊 Analyse de {filename}")

        score_global    = analysis.get("score_global", 0)
        score_technique = analysis.get("score_technique", None)
        score_experience= analysis.get("score_experience", None)
        score_formation = analysis.get("score_formation", None)
        score_soft      = analysis.get("score_soft_skills", None)

        st.subheader(f"🎯 Score Global : {score_global}/100")
        if score_global >= 80:
            st.success(f"Excellent candidat ({score_global}/100)")
        elif score_global >= 60:
            st.warning(f"Bon candidat ({score_global}/100)")
        else:
            st.error(f"Candidat à améliorer ({score_global}/100)")
        st.progress(score_global / 100)

        st.subheader("🔢 Détails des sous-scores")
        cols = st.columns(4)
        if score_technique is not None:
            cols[0].metric("Technique", f"{score_technique}/40")
        else:
            cols[0].write("Technique : N/A")
        if score_experience is not None:
            cols[1].metric("Expérience", f"{score_experience}/30")
        else:
            cols[1].write("Expérience : N/A")
        if score_formation is not None:
            cols[2].metric("Formation", f"{score_formation}/15")
        else:
            cols[2].write("Formation : N/A")
        if score_soft is not None:
            cols[3].metric("Soft skills", f"{score_soft}/15")
        else:
            cols[3].write("Soft skills : N/A")

        recommandation = analysis.get("recommandation", "Non spécifiée")
        st.subheader("✅ Recommandation")
        if "Recommandé" in recommandation:
            st.success(f"✅ **{recommandation}**")
        elif "considérer" in recommandation.lower():
            st.warning(f"⚠️ **{recommandation}**")
        else:
            st.error(f"❌ **{recommandation}**")

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("💪 Points Forts")
            for pt in analysis.get("points_forts", []):
                st.write(f"• {pt}")
            st.subheader("✅ Compétences Matchées")
            for comp in analysis.get("competences_matchees", []):
                st.write(f"• {comp}")
        with col2:
            st.subheader("⚠️ Points Faibles")
            for pt in analysis.get("points_faibles", []):
                st.write(f"• {pt}")
            st.subheader("❌ Compétences Manquantes")
            for comp in analysis.get("competences_manquantes", []):
                st.write(f"• {comp}")

        st.subheader("💼 Expérience Pertinente")
        st.write(analysis.get("experience_pertinente", "Non spécifiée"))
        st.subheader("📝 Commentaires Détaillés")
        st.write(analysis.get("commentaires", "Aucun commentaire"))

        st.subheader("📋 Informations Techniques")
        col3, col4, col5 = st.columns(3)
        with col3:
            st.metric("Pages analysées", analysis.get("pages_analysees", "N/A"))
        with col4:
            st.metric("Méthode", analysis.get("methode_analyse", "N/A"))
        with col5:
            st.metric("Date", datetime.now().strftime("%d/%m/%Y %H:%M"))

        return analysis

    except json.JSONDecodeError:
        st.error("❌ Erreur lors du parsing de l'analyse JSON")
        st.text_area("Analyse brute :", analysis_text, height=300)
        return None

def main():
    """Fonction principale de l'application Streamlit"""
    
    # Initialisation de la BDD
    init_db()

    # Menu de navigation
    page = st.sidebar.radio(
        "Navigation",
        ["Analyse de CV", "Gestion des offres", "Historique des analyses"]
    )

    if page == "Analyse de CV":
        st.title("🚀 Analyseur de CV avec GPT-5 Vision")
        st.markdown("---")
        st.markdown("**Analysez des CV par rapport à une offre d'emploi avec une IA de pointe**")

        with st.sidebar:
            st.header("⚙️ Configuration")
            if config.OPENAI_API_KEY and config.OPENAI_API_KEY != "your-openai-api-key-here":
                st.success("✅ Clé API OpenAI configurée")
            else:
                st.error("❌ Clé API OpenAI non configurée")
                st.info("Configurez OPENAI_API_KEY dans vos variables d'environnement")
            st.subheader("🎛️ Paramètres")
            st.markdown("---")
            st.markdown("**💡 Instructions:**")
            st.markdown("1. Ajoutez l'offre d'emploi")
            st.markdown("2. Uploadez un ou plusieurs CV (PDF)")
            st.markdown("3. Cliquez sur 'Analyser'" )
        col_left, col_right = st.columns([1, 1])
        
        with col_left:
            st.subheader("📋 Offre d'emploi")
            job_title = st.text_input(
                "Titre de l'offre d'emploi:",
                placeholder="Ex: Développeur Python Senior - Tech Corp"
            )
            job_offer = st.text_area(
                "Collez l'offre d'emploi ici:",
                height=260,
                placeholder="Poste: Développeur Python\nEntreprise: Tech Corp\nCompétences requises: Python, Django, API REST..."
            )
        
        with col_right:
            st.subheader("📄 Upload de CV")
            uploaded_files = st.file_uploader(
                "Choisissez un ou plusieurs CV (PDF)",
                type=['pdf'],
                accept_multiple_files=True
            )
            if uploaded_files:
                st.success(f"✅ {len(uploaded_files)} fichier(s) sélectionné(s)")
                for file in uploaded_files:
                    st.write(f"• {file.name}")

        if st.button("🔍 Analyser les CV", type="primary", use_container_width=True):
            if not job_offer.strip():
                st.error("⚠️ Veuillez ajouter une offre d'emploi")
                return
            if not job_title.strip():
                st.error("⚠️ Veuillez ajouter un titre pour l'offre d'emploi")
                return
            if not uploaded_files:
                st.error("⚠️ Veuillez uploader au moins un CV")
                return
            
            # Sauvegarder l'offre d'emploi et récupérer son ID
            job_offer_id = save_job_offer(job_title, job_offer)
            st.info(f"💾 Offre d'emploi sauvegardée (ID: {job_offer_id[:8]}...)")
            
            st.markdown("---")
            
            client = initialize_openai()
            st.markdown("---")
            st.header("📊 Résultats de l'analyse")
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            analyses = []
            
            for i, uploaded_file in enumerate(uploaded_files, start=1):
                status_text.text(f"Analyse en cours : {uploaded_file.name} ({i}/{len(uploaded_files)})")
                progress_bar.progress((i - 1) / len(uploaded_files))

                pdf_bytes = uploaded_file.read()

                result = analyze_cv_with_vision(pdf_bytes, job_offer, client)

                if result:  
                    analysis_text = result["content"]        
                    tokens_used   = result["tokens"]         

                    cost_cv = (tokens_used["prompt"]     / 1000) * PRICE_INPUT \
                            + (tokens_used["completion"] / 1000) * PRICE_OUTPUT

                    st.success(f"✅ Analyse terminée pour {uploaded_file.name}")
                    parsed = display_analysis(analysis_text, uploaded_file.name)

                    # Enregistrement dans la BDD si le parsing a réussi
                    if parsed:
                        insert_analysis(uploaded_file.name, parsed, job_offer_id)

                    st.info(
                        f"🧮 **Tokens** : {tokens_used['total']}  "
                        f"(prompt {tokens_used['prompt']} / completion {tokens_used['completion']})  "
                        f"— **Coût estimé : ${cost_cv:.4f}**"
                    )

                    analyses.append({
                        "filename": uploaded_file.name,
                        "analysis": parsed if parsed else analysis_text,
                        "tokens":   tokens_used,
                        "cost_usd": cost_cv
                    })
                    st.markdown("---")

                else:  
                    st.error(f"❌ Échec de l'analyse pour {uploaded_file.name}")
            
            progress_bar.progress(1.0)
            status_text.text("✅ Analyse terminée !")
            
            if analyses:
                st.success(f"🎉 {len(analyses)}/{len(uploaded_files)} CV(s) analysé(s) avec succès")
                if st.button("💾 Télécharger les résultats (JSON)"):
                    results_json = {
                        "metadata": {
                            "date": datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
                            "nombre_cv_analyses": len(analyses),
                            "modele_utilise": "gpt-5-mini",
                        },
                        "job_offer": job_offer,
                        "analyses": analyses
                    }
                    st.download_button(
                        label="📥 Télécharger JSON",
                        data=json.dumps(results_json, ensure_ascii=False, indent=2),
                        file_name=f"analyse_cv_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json"
                    )

    elif page == "Gestion des offres":
        st.title("📋 Gestion des offres d'emploi")
        st.markdown("---")
        
        # Onglets pour organiser les fonctionnalités
        tab1, tab2 = st.tabs(["📊 Vue d'ensemble", "🔍 Détails par offre"])
        
        with tab1:
            st.subheader("📈 Statistiques des offres d'emploi")
            
            job_offers = get_all_job_offers()
            if job_offers:
                # Affichage sous forme de tableau
                import pandas as pd
                
                df = pd.DataFrame(job_offers, columns=["ID", "Titre", "Date de création", "Nb CV analysés"])
                df["ID court"] = df["ID"].apply(lambda x: x[:8] + "...")
                df_display = df[["ID court", "Titre", "Date de création", "Nb CV analysés"]]
                
                st.dataframe(df_display, use_container_width=True)
                
                # Métriques globales
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Total offres", len(job_offers))
                
                with col2:
                    total_cv = sum([job[3] for job in job_offers])
                    st.metric("Total CV analysés", total_cv)
                
                with col3:
                    if total_cv > 0:
                        avg_cv_per_job = total_cv / len(job_offers)
                        st.metric("Moyenne CV/offre", f"{avg_cv_per_job:.1f}")
                
            else:
                st.info("Aucune offre d'emploi trouvée. Analysez des CV pour commencer !")
        
        with tab2:
            st.subheader("🔍 Analyses par offre d'emploi")
            
            job_offers = get_all_job_offers()
            if job_offers:
                # Sélecteur d'offre
                job_titles = {f"{job[1]} ({job[0][:8]}...)": job[0] for job in job_offers}
                selected_job_title = st.selectbox(
                    "Choisissez une offre d'emploi:",
                    options=list(job_titles.keys())
                )
                
                if selected_job_title:
                    job_offer_id = job_titles[selected_job_title]
                    
                    # Statistiques de l'offre sélectionnée
                    stats = get_job_offer_stats(job_offer_id)
                    if stats and stats[0] > 0:
                        col1, col2, col3, col4 = st.columns(4)
                        
                        with col1:
                            st.metric("CV analysés", int(stats[0]))
                        with col2:
                            st.metric("Score moyen", f"{stats[1]:.1f}/100")
                        with col3:
                            st.metric("Meilleur score", f"{stats[2]}/100")
                        with col4:
                            st.metric("Score minimum", f"{stats[3]}/100")
                        
                        st.markdown("---")
                        
                        # Liste des analyses pour cette offre
                        analyses = get_analyses_by_job_offer(job_offer_id)
                        
                        st.subheader("📄 CV analysés pour cette offre")
                        
                        for i, analysis in enumerate(analyses):
                            with st.expander(f"🏆 {analysis[0]} - Score: {analysis[1]}/100 ({analysis[8]})", expanded=(i==0)):
                                col1, col2 = st.columns([2, 1])
                                
                                with col1:
                                    st.write("**Commentaire:**")
                                    st.write(analysis[6])
                                
                                with col2:
                                    st.write("**Scores détaillés:**")
                                    st.write(f"🎯 Global: {analysis[1]}/100")
                                    st.write(f"⚙️ Technique: {analysis[2]}/40")
                                    st.write(f"📈 Expérience: {analysis[3]}/30")
                                    st.write(f"🎓 Formation: {analysis[4]}/15")
                                    st.write(f"🤝 Soft Skills: {analysis[5]}/15")
                                    st.write(f"📅 Date: {analysis[7]}")
                    else:
                        st.info("Aucune analyse trouvée pour cette offre d'emploi.")
            else:
                st.info("Aucune offre d'emploi trouvée.")
    
    elif page == "Historique des analyses":
        st.title("📑 Historique des analyses (BDD)")
        st.markdown("---")
        rows = get_all_analyses()
        if rows:
            # Filtre par offre d'emploi
            job_offers = get_all_job_offers()
            if job_offers and len(job_offers) > 1:
                job_filter_options = ["Toutes les offres"] + [f"{job[1]} ({job[0][:8]}...)" for job in job_offers]
                selected_filter = st.selectbox("Filtrer par offre d'emploi:", job_filter_options)
                
                if selected_filter != "Toutes les offres":
                    # Extraire l'ID de l'offre sélectionnée
                    selected_job_id = None
                    for job in job_offers:
                        if f"{job[1]} ({job[0][:8]}...)" == selected_filter:
                            selected_job_id = job[0]
                            break
                    
                    # Filtrer les analyses
                    rows = [r for r in rows if r[9] == selected_job_id]
            
            if rows:
                st.dataframe(
                    [{
                        "Nom/Prénom": r[0],
                        "Score global /100": r[1],
                        "Technique /40": r[2],
                        "Expérience /30": r[3],
                        "Formation /15": r[4],
                        "Soft skills /15": r[5],
                        "Offre d'emploi": r[8] if r[8] else "Non spécifiée",
                        "Commentaire": r[6][:100] + "..." if len(str(r[6])) > 100 else r[6],
                        "Date": r[7]
                    } for r in rows],
                    use_container_width=True
                )
                
                # Statistiques rapides
                col1, col2, col3 = st.columns(3)
                scores = [r[1] for r in rows if r[1] is not None]
                if scores:
                    with col1:
                        st.metric("Analyses totales", len(rows))
                    with col2:
                        st.metric("Score moyen", f"{sum(scores)/len(scores):.1f}/100")
                    with col3:
                        st.metric("Meilleur score", f"{max(scores)}/100")
            else:
                st.info("Aucune analyse trouvée pour le filtre sélectionné.")
        else:
            st.info("Aucune analyse enregistrée dans la base de données.")


if __name__ == "__main__":
    main()
