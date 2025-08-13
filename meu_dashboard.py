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

# --- ETAPA 2: Função para carregar e processar os dados (VERSÃO CORRIGIDA) ---
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
        
    def safe_eval(val):
        try:
            return ast.literal_eval(val)
        except (ValueError, SyntaxError):
            return None

    # --- INÍCIO DA LÓGICA CORRIGIDA ---
    # Processa cada linha para extrair os dados de cota de forma dinâmica e correta
    parsed_data = []
    for index, row in df_alloc.iterrows():
        keys = safe_eval(row['cotas'])
        values = safe_eval(row['resultado_cota'])
        
        row_dict = {}
        if isinstance(keys, (list, tuple)) and isinstance(values, (list, tuple)) and len(keys) == len(values):
            row_dict = dict(zip(keys, values))
        parsed_data.append(row_dict)

    # Cria um novo DataFrame com os dados demográficos devidamente mapeados
    new_cols_df = pd.DataFrame(parsed_data, index=df_alloc.index)

    # Junta o DataFrame original com as novas colunas demográficas corretas
    df_alloc_processed = pd.concat([df_alloc, new_cols_df], axis=1)
    # --- FIM DA LÓGICA CORRIGIDA ---

    df_alloc_processed.rename(columns={'country': 'pais'}, inplace=True)
    
    return df_alloc_processed, df_projects

# --- ETAPA 3: Carregar os dados ---
df_alloc_processed, df_projects = load_and_process_data(ALLOC_FILE, PROJECTS_FILE)

# --- ETAPA 4: Criar as abas do dashboard ---
if df_alloc_processed is not None and df_projects is not None:
    tab_tabelas, tab_graficos = st.tabs(["Tabelas de Dados", "Gráficos de Cotas"])

    with tab_tabelas:
        st.header("Dados de Alocação Processados (`GeminiCheck.csv`)")
        st.dataframe(df_alloc_processed)
        st.info(f"Carregadas {len(df_alloc_processed)} linhas.")

        st.header("Dados das Cotas Iniciais (`Projects.csv`)")
        st.dataframe(df_projects)
        st.info(f"Carregadas {len(df_projects)} linhas.")

    with tab_graficos:
        st.header("Visão Gráfica da Demanda por Recrutamento")
        
        required_cols = ['Pessoas_Para_Recrutar', 'age_group', 'Gender', 'pais', 'SEL']
        if not all(col in df_alloc_processed.columns for col in required_cols):
            st.warning("Não foi possível gerar os gráficos. Colunas necessárias não encontradas.")
        else:
            custom_colors = ['#25406e', '#6ba1ff', '#a1f1ff', '#5F9EA0', '#E6E6FA']
            
            # Limpa os dados para os gráficos
            df_graficos = df_alloc_processed.copy()
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
