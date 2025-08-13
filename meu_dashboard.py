import streamlit as st
import pandas as pd
import os
import plotly.express as px
import ast

st.set_page_config(layout="wide", initial_sidebar_state="expanded")

st.title("Painel de Controle de Recrutamento")

# --- ETAPA 1: Definir os caminhos dos arquivos ---
ALLOC_FILE = 'GeminiCheck.csv'
PROJECTS_FILE = 'Projects.csv'

# --- ETAPA 2: Função para carregar e processar os dados (VERSÃO ROBUSTA) ---
@st.cache_data
def load_and_process_data(alloc_path, projects_path):
    # Tenta carregar os arquivos CSV, com mensagens de erro claras se falhar
    if not os.path.exists(alloc_path) or not os.path.exists(projects_path):
        st.error(f"ERRO: Um ou ambos os arquivos não foram encontrados. Verifique a localização de 'GeminiCheck.csv' e 'Projects.csv'.")
        return None, None
    
    df_alloc = pd.read_csv(alloc_path)
    df_projects = pd.read_csv(projects_path)

    if 'cotas' not in df_alloc.columns or 'resultado_cota' not in df_alloc.columns:
        st.error("ERRO: Colunas 'cotas' ou 'resultado_cota' não encontradas em GeminiCheck.csv.")
        return df_alloc, df_projects
        
    def safe_eval(val):
        try:
            return ast.literal_eval(val)
        except (ValueError, SyntaxError):
            return None

    # Processa cada linha para extrair os dados de cota de forma dinâmica e correta
    parsed_data = []
    for index, row in df_alloc.iterrows():
        keys = safe_eval(row['cotas'])
        values = safe_eval(row['resultado_cota'])
        
        row_dict = {}
        if isinstance(keys, (list, tuple)) and isinstance(values, (list, tuple)) and len(keys) == len(values):
            row_dict = dict(zip(keys, values))
        parsed_data.append(row_dict)

    new_cols_df = pd.DataFrame(parsed_data, index=df_alloc.index)
    df_alloc_processed = pd.concat([df_alloc, new_cols_df], axis=1)
    df_alloc_processed.rename(columns={'country': 'pais'}, inplace=True)
    
    # Une com os dados de projetos para criar o QuotaLabel
    df_projects.rename(columns={'index': 'quota_index'}, inplace=True)
    df_alloc_processed['quota_index'] = pd.to_numeric(df_alloc_processed['quota_index'], errors='coerce')
    df_alloc_processed.dropna(subset=['quota_index'], inplace=True)
    df_alloc_processed['quota_index'] = df_alloc_processed['quota_index'].astype(int)

    # Função segura para criar o rótulo da cota
    def create_quota_label(row):
        parts = [f"Q:{row['quota_index']}"]
        # Verifica se as colunas existem antes de usá-las
        if '1' in row and pd.notna(row['1']) and str(row['1']) != '0': 
            parts.append(f"Idade:{row['1']}")
        if '2' in row and pd.notna(row['2']) and str(row['2']) != '0': 
            parts.append(f"Gênero:{row['2']}")
        return " | ".join(parts)

    df_projects['QuotaLabel'] = df_projects.apply(create_quota_label, axis=1)
    df_quotas_unique = df_projects.drop_duplicates(subset=['quota_index'])
    
    df_merged = pd.merge(df_alloc_processed, df_quotas_unique[['quota_index', 'QuotaLabel']], on='quota_index', how='left')
    
    return df_merged, df_projects

# --- ETAPA 3: Carregar os dados ---
df_processed, df_projects = load_and_process_data(ALLOC_FILE, PROJECTS_FILE)

# --- ETAPA 4: Filtros na barra lateral (LÓGICA CORRIGIDA) ---
if df_processed is not None:
    st.sidebar.header("Filtros")
    
    all_projects = sorted(df_processed['project_id'].unique())
    selected_projects = st.sidebar.multiselect('1. Selecione o(s) Projeto(s)', all_projects)

    # DataFrame temporário com base na seleção de projetos para popular outros filtros
    df_temp = df_processed[df_processed['project_id'].isin(selected_projects)] if selected_projects else df_processed

    # Filtros secundários SEM seleção padrão para evitar conflitos
    all_labels = sorted(df_temp['QuotaLabel'].dropna().unique())
    selected_labels = st.sidebar.multiselect('2. [Opcional] Selecione a(s) Cota(s)', all_labels)
    
    all_countries = sorted(df_temp['pais'].dropna().unique())
    selected_countries = st.sidebar.multiselect('País', all_countries)

    all_age_groups = sorted(df_temp['age_group'].dropna().unique())
    selected_age_groups = st.sidebar.multiselect('Faixa Etária', all_age_groups)

    all_genders = sorted(df_temp['Gender'].dropna().unique())
    selected_genders = st.sidebar.multiselect('Gênero', all_genders)

    all_sels = sorted(df_temp['SEL'].dropna().unique())
    selected_sels = st.sidebar.multiselect('Classe Social (SEL)', all_sels)

    # Aplicação dos filtros que foram de fato selecionados pelo usuário
    df_filtered = df_processed.copy()
    if selected_projects:
        df_filtered = df_filtered[df_filtered['project_id'].isin(selected_projects)]
    if selected_labels:
        df_filtered = df_filtered[df_filtered['QuotaLabel'].isin(selected_labels)]
    if selected_countries:
        df_filtered = df_filtered[df_filtered['pais'].isin(selected_countries)]
    if selected_age_groups:
        df_filtered = df_filtered[df_filtered['age_group'].isin(selected_age_groups)]
    if selected_genders:
        df_filtered = df_filtered[df_filtered['Gender'].isin(selected_genders)]
    if selected_sels:
        df_filtered = df_filtered[df_filtered['SEL'].isin(selected_sels)]

# --- ETAPA 5: Criar as abas do dashboard ---
if df_processed is not None and df_projects is not None:
    tab_tabelas, tab_graficos = st.tabs(["Tabelas de Dados", "Gráficos de Cotas"])

    with tab_tabelas:
        st.header("Dados de Alocação Processados (`GeminiCheck.csv`)")
        st.dataframe(df_filtered)

        st.header("Dados das Cotas Iniciais (`Projects.csv`)")
        if not df_filtered.empty:
            st.dataframe(df_projects[df_projects['quota_index'].isin(df_filtered['quota_index'].unique())])
        else:
            st.dataframe(df_projects)

    with tab_graficos:
        st.header("Visão Gráfica da Demanda por Recrutamento")
        
        if df_filtered.empty:
            st.warning("Nenhum dado encontrado para os filtros selecionados. Selecione um projeto para começar.")
        else:
            custom_colors = ['#25406e', '#6ba1ff', '#a1f1ff', '#5F9EA0', '#E6E6FA']
            
            df_graficos = df_filtered.copy()
            for col in ['Gender', 'SEL', 'age_group', 'pais']:
                if col in df_graficos.columns:
                    df_graficos[col] = df_graficos[col].replace(['0', 0, 'No_Age_Group'], None)

            col1, col2 = st.columns(2)
            with col1:
                by_age = df_graficos.groupby('age_group')['Pessoas_Para_Recrutar'].sum().sort_values(ascending=False).reset_index()
                fig_age = px.bar(by_age, x='age_group', y='Pessoas_Para_Recrutar', title='Demanda por Faixa Etária', color_discrete_sequence=custom_colors)
                st.plotly_chart(fig_age, use_container_width=True)
            
            with col2:
                by_gender = df_graficos.groupby('Gender')['Pessoas_Para_Recrutar'].sum().reset_index()
                fig_gender = px.pie(by_gender, names='Gender', values='Pessoas_Para_Recrutar', title='Demanda por Gênero', hole=0.3, color_discrete_sequence=custom_colors)
                st.plotly_chart(fig_gender, use_container_width=True)

            col3, col4 = st.columns(2)
            with col3:
                by_country = df_graficos.groupby('pais')['Pessoas_Para_Recrutar'].sum().sort_values(ascending=False).reset_index()
                fig_country = px.bar(by_country, x='pais', y='Pessoas_Para_Recrutar', title='Demanda por País', color_discrete_sequence=custom_colors)
                st.plotly_chart(fig_country, use_container_width=True)
                
            with col4:
                by_sel = df_graficos.groupby('SEL')['Pessoas_Para_Recrutar'].sum().sort_values(ascending=False).reset_index()
                fig_sel = px.bar(by_sel, x='SEL', y='Pessoas_Para_Recrutar', title='Demanda por Classe Social (SEL)', color_discrete_sequence=custom_colors)
                st.plotly_chart(fig_sel, use_container_width=True)
