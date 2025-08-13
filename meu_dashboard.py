import streamlit as st
import pandas as pd
import os
import plotly.express as px
import ast

# --- Configuração da Página ---
st.set_page_config(layout="wide", initial_sidebar_state="expanded")

st.title("Painel de Controle de Recrutamento")

# --- ETAPA 1: Definição dos caminhos dos arquivos ---
ALLOC_FILE = 'GeminiCheck.csv'
PROJECTS_FILE = 'Projects.csv'

# --- ETAPA 2: Função de Carregamento e Processamento de Dados (VERSÃO FINAL E ROBUSTA) ---
@st.cache_data
def load_and_process_data(alloc_path, projects_path):
    """
    Função reescrita para ser à prova de falhas, garantindo que os dados
    sejam carregados e processados de forma segura.
    """
    # 2.1: Validação dos Arquivos
    if not os.path.exists(alloc_path) or not os.path.exists(projects_path):
        st.error(f"ERRO CRÍTICO: Um ou ambos os arquivos não foram encontrados. Verifique a localização de '{alloc_path}' e '{projects_path}'.")
        return None, None
    
    df_alloc_raw = pd.read_csv(alloc_path)
    df_projects_raw = pd.read_csv(projects_path)

    # 2.2: Validação das Colunas Essenciais
    required_alloc_cols = ['quota_index', 'project_id', 'country', 'cotas', 'resultado_cota', 'Pessoas_Para_Recrutar', 'allocated_completes']
    if not all(col in df_alloc_raw.columns for col in required_alloc_cols):
        st.error(f"ERRO CRÍTICO: O arquivo 'GeminiCheck.csv' não contém todas as colunas necessárias. Estão faltando: {set(required_alloc_cols) - set(df_alloc_raw.columns)}")
        return None, None

    # 2.3: Processamento Seguro, Linha por Linha
    processed_rows = []
    for index, row in df_alloc_raw.iterrows():
        try:
            # Converte as strings de lista/tupla em objetos Python
            keys = ast.literal_eval(row['cotas'])
            values = ast.literal_eval(row['resultado_cota'])

            # Cria um dicionário base com os dados da linha
            base_data = row.to_dict()
            
            # Adiciona os dados demográficos ao dicionário base
            if isinstance(keys, (list, tuple)) and isinstance(values, (list, tuple)) and len(keys) == len(values):
                demographics = dict(zip(keys, values))
                base_data.update(demographics)
            
            processed_rows.append(base_data)

        except (ValueError, SyntaxError, TypeError):
            # Se uma linha falhar na conversão, ela é ignorada, mas o processo continua
            continue
            
    if not processed_rows:
        st.error("ERRO CRÍTICO: Nenhuma linha do 'GeminiCheck.csv' pôde ser processada. Verifique o formato das colunas 'cotas' e 'resultado_cota'.")
        return None, None

    # 2.4: Criação dos DataFrames Finais
    df_processed = pd.DataFrame(processed_rows)
    df_processed.rename(columns={'country': 'pais'}, inplace=True)

    # Adiciona o QuotaLabel para o filtro, tratando os tipos de dados
    df_projects_raw.rename(columns={'index': 'quota_index'}, inplace=True)
    df_processed['quota_index'] = pd.to_numeric(df_processed['quota_index'], errors='coerce')
    df_processed.dropna(subset=['quota_index'], inplace=True)
    df_processed['quota_index'] = df_processed['quota_index'].astype(int)

    def create_quota_label(row):
        parts = [f"Q:{row['quota_index']}"]
        if '1' in row and pd.notna(row['1']) and str(row['1']) != '0': parts.append(f"Idade:{row['1']}")
        if '2' in row and pd.notna(row['2']) and str(row['2']) != '0': parts.append(f"Gênero:{row['2']}")
        return " | ".join(parts)

    df_projects_raw['QuotaLabel'] = df_projects_raw.apply(create_quota_label, axis=1)
    df_quotas_unique = df_projects_raw.drop_duplicates(subset=['quota_index'])
    
    df_final = pd.merge(df_processed, df_quotas_unique[['quota_index', 'QuotaLabel']], on='quota_index', how='left')

    st.success("Dados carregados e processados com sucesso!")
    return df_final, df_projects_raw

# --- ETAPA 3: Carregar os dados ---
df_processed, df_projects = load_and_process_data(ALLOC_FILE, PROJECTS_FILE)

# --- ETAPA 4: Filtros na barra lateral ---
if df_processed is not None:
    st.sidebar.header("Filtros")
    
    all_projects = sorted(df_processed['project_id'].unique())
    selected_projects = st.sidebar.multiselect('1. Selecione o(s) Projeto(s)', all_projects)

    df_temp = df_processed[df_processed['project_id'].isin(selected_projects)] if selected_projects else df_processed

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
        st.header("Dados de Alocação Processados")
        st.dataframe(df_filtered)

        st.header("Dados das Cotas Iniciais")
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
