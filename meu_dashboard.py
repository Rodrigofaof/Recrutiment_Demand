import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
from datetime import datetime
from zoneinfo import ZoneInfo
import io

st.set_page_config(layout="wide", initial_sidebar_state="expanded")

@st.cache_data
def load_and_process_data(final_alloc_path, initial_quotas_path):
    try:
        df_alloc = pd.read_csv(final_alloc_path)
        df_quotas = pd.read_csv(initial_quotas_path)
    except FileNotFoundError as e:
        st.error(f"ERRO CRÍTICO: Arquivo não encontrado -> {e}.")
        return None, None

    if df_alloc.empty or df_quotas.empty:
        st.error("ERRO CRÍTICO: Um dos arquivos de dados está vazio.")
        return None, None
    
    def extract_quota_data(row):
        try:
            items = [item.strip() for item in str(row).strip("()").replace("'", "").split(',')]
            while len(items) < 4: items.append(None)
            return items
        except Exception: return [None, None, None, None]

    split_data = df_alloc['resultado_cota'].apply(extract_quota_data).to_list()
    new_cols_df = pd.DataFrame(split_data, index=df_alloc.index, columns=['age_group', 'SEL', 'Gender', 'Region'])
    df_alloc = df_alloc.join(new_cols_df)

    df_alloc['quota_index'] = pd.to_numeric(df_alloc['quota_index'], errors='coerce')
    df_quotas.rename(columns={'index': 'quota_index'}, inplace=True)
    df_quotas['quota_index'] = pd.to_numeric(df_quotas['quota_index'], errors='coerce')

    df_alloc.dropna(subset=['quota_index'], inplace=True)
    df_quotas.dropna(subset=['quota_index'], inplace=True)
    
    df_alloc['quota_index'] = df_alloc['quota_index'].astype(int)
    df_quotas['quota_index'] = df_quotas['quota_index'].astype(int)

    df_alloc.rename(columns={'country': 'pais'}, inplace=True)
    df_clean = df_alloc[['quota_index', 'project_id', 'pais', 'age_group', 'SEL', 'Gender', 'Region', 'Pessoas_Para_Recrutar', 'allocated_completes']].copy()
    df_clean['allocated_completes'] = pd.to_numeric(df_clean['allocated_completes'], errors='coerce').fillna(0).astype(int)
    df_clean['project_id'] = df_clean['project_id'].astype(str)
    df_quotas['project_id'] = df_quotas['project_id'].astype(str)

    def create_quota_label(row):
        parts = [f"Q:{row['quota_index']}"]
        if '1' in row and str(row.get('1', '0')) != '0': parts.append(f"Idade:{row['1']}")
        if '2' in row and str(row.get('2', '0')) != '0': parts.append(f"Gênero:{row['2']}")
        return " | ".join(parts)

    df_quotas['QuotaLabel'] = df_quotas.apply(create_quota_label, axis=1)
    df_merged = pd.merge(df_clean, df_quotas[['quota_index', 'QuotaLabel']], on='quota_index', how='left')
    return df_merged, df_quotas

st.title("Painel de Controle de Recrutamento")
df_processed, df_projects = load_and_process_data('GeminiCheck.csv', 'Projects.csv')

if df_processed is None:
    st.stop()

st.sidebar.header("Filtros")
all_projects = sorted(df_processed['project_id'].unique())
selected_projects = st.sidebar.multiselect('1. Selecione o(s) Projeto(s)', all_projects)

df_temp = df_processed[df_processed['project_id'].isin(selected_projects)] if selected_projects else df_processed
all_labels = sorted(df_temp['QuotaLabel'].dropna().unique())
selected_labels = st.sidebar.multiselect('2. [Opcional] Selecione a(s) Cota(s)', all_labels)

df_filtered = df_processed.copy()
if selected_projects:
    df_filtered = df_filtered[df_filtered['project_id'].isin(selected_projects)]
if selected_labels:
    df_filtered = df_filtered[df_filtered['QuotaLabel'].isin(selected_labels)]

tab1, tab2, tab3 = st.tabs(["Dashboard Geral", "Fluxo Sankey", "Tabelas"])

with tab1:
    st.header("Visão Geral do Recrutamento")
    # Gráficos e KPIs aqui...

with tab2:
    st.header("Fluxo de Distribuição da Cota")
    if not selected_projects:
        st.info("⬅️ Para gerar o gráfico, selecione um ou mais Projetos.")
    elif df_filtered.empty:
        st.warning("Nenhum dado para os filtros.")
    else:
        df_sankey = df_filtered.copy().dropna(subset=['QuotaLabel', 'age_group', 'Gender', 'SEL'])
        # Lógica do Sankey aqui...

with tab3:
    st.header("Tabelas de Dados")
    st.dataframe(df_filtered)
    if not df_projects.empty and not df_filtered.empty:
        st.dataframe(df_projects[df_projects['quota_index'].isin(df_filtered['quota_index'].unique())])
