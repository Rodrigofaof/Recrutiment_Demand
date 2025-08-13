import streamlit as st
import pandas as pd
import os
import plotly.express as px
import ast

st.set_page_config(layout="wide")

st.title("Painel de Controle de Recrutamento")

# --- ETAPA 1: Definir os caminhos dos arquivos ---
ALLOC_FILE = 'GeminiCheck.csv'
PROJECTS_FILE = 'Projects.csv'

# --- ETAPA 2: Função para carregar e processar os dados ---
@st.cache_data
def load_and_process_data(alloc_path, projects_path):
    if not os.path.exists(alloc_path) or not os.path.exists(projects_path):
        st.error(f"ERRO: Um ou ambos os arquivos não foram encontrados. Verifique 'GeminiCheck.csv' e 'Projects.csv'.")
        return None, None
    
    df_alloc = pd.read_csv(alloc_path)
    df_projects = pd.read_csv(projects_path)

    if 'cotas' not in df_alloc.columns or 'resultado_cota' not in df_alloc.columns:
        st.error("ERRO: Colunas 'cotas' ou 'resultado_cota' não encontradas em GeminiCheck.csv.")
        return df_alloc, df_projects
        
    def extract_dynamic_data(row):
        try:
            keys = ast.literal_eval(row['cotas'])
            values = ast.literal_eval(row['resultado_cota'])
            
            if isinstance(keys, (list, tuple)) and isinstance(values, (list, tuple)) and len(keys) == len(values):
                return dict(zip(keys, values))
            else:
                return {}
        except Exception:
            return {}

    dynamic_data = df_alloc.apply(extract_dynamic_data, axis=1)
    dynamic_df = pd.DataFrame(dynamic_data.tolist(), index=df_alloc.index)
    
    df_alloc_processed = pd.concat([df_alloc, dynamic_df], axis=1)
    df_alloc_processed.rename(columns={'country': 'pais'}, inplace=True)
    
    # --- INÍCIO DAS NOVAS SUBSTITUIÇÕES ---
    # Substitui os valores '0' por textos descritivos
    if 'Region' in df_alloc_processed.columns:
        # Usamos .astype(str) para garantir que a comparação com '0' funcione
        df_alloc_processed['Region'] = df_alloc_processed['Region'].astype(str).replace('0', 'Qualquer Região')
    
    if 'SEL' in df_alloc_processed.columns:
        df_alloc_processed['SEL'] = df_alloc_processed['SEL'].astype(str).replace('0', 'País sem SEL')
    # --- FIM DAS NOVAS SUBSTITUIÇÕES ---
    
    df_alloc_processed['project_id'] = df_alloc_processed['project_id'].astype(str)
    df_projects['project_id'] = df_projects['project_id'].astype(str)

    return df_alloc_processed, df_projects

# --- ETAPA 3: Carregar os dados ---
df_alloc_processed, df_projects = load_and_process_data(ALLOC_FILE, PROJECTS_FILE)

# --- ETAPA 4: Filtros na barra lateral ---
if df_alloc_processed is not None:
    st.sidebar.header("Filtros")
    
    df_filtered = df_alloc_processed.copy()
    df_projects_filtered = df_projects.copy()

    all_projects = sorted(df_alloc_processed['project_id'].unique())
    selected_projects = st.sidebar.multiselect('1. Projeto(s)', all_projects)
    
    if selected_projects:
        df_filtered = df_filtered[df_filtered['project_id'].isin(selected_projects)]
        df_projects_filtered = df_projects_filtered[df_projects_filtered['project_id'].isin(selected_projects)]

    all_countries = sorted(df_filtered['pais'].dropna().unique())
    selected_countries = st.sidebar.multiselect('2. País(es)', all_countries)
    
    if selected_countries:
        df_filtered = df_filtered[df_filtered['pais'].isin(selected_countries)]
        if 'pais' in df_projects_filtered.columns:
            df_projects_filtered = df_projects_filtered[df_projects_filtered['pais'].isin(selected_countries)]
        elif 'country' in df_projects_filtered.columns:
            df_projects_filtered = df_projects_filtered[df_projects_filtered['country'].isin(selected_countries)]
    
    all_regions = sorted(df_filtered['Region'].dropna().
