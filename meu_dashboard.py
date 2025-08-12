import streamlit as st
import pandas as pd
import os

st.set_page_config(layout="wide")

st.title("Visualizador de Dados Iniciais")
st.write("Esta é a versão inicial do painel, focada em carregar e exibir as tabelas de dados brutos para verificação.")

DATA_PATH = "Recrutiment_Demand/"
ALLOC_FILE = os.path.join(DATA_PATH, 'GeminiCheck.csv')
PROJECTS_FILE = os.path.join(DATA_PATH, 'Projects.csv')


# --- ETAPA 2: FUNÇÃO PARA CARREGAR DADOS ---
@st.cache_data
def load_data(file_path):
    # Função simples para ler um CSV.
    # Retorna o DataFrame ou None se o arquivo não for encontrado.
    if not os.path.exists(file_path):
        st.error(f"ARQUIVO NÃO ENCONTRADO: {file_path}")
        return None
    try:
        df = pd.read_csv(file_path)
        return df
    except Exception as e:
        st.error(f"Falha ao ler o arquivo {file_path}. Erro: {e}")
        return None

# --- ETAPA 3: CARREGAR E EXIBIR AS TABELAS ---
df_alloc = load_data(ALLOC_FILE)
df_projects = load_data(PROJECTS_FILE)

tab1, tab2 = st.tabs(["Dados de Alocação (GeminiCheck.csv)", "Dados dos Projetos (Projects.csv)"])

with tab1:
    st.header("Conteúdo do GeminiCheck.csv")
    if df_alloc is not None:
        st.dataframe(df_alloc)
        st.info(f"Carregadas {len(df_alloc)} linhas.")
    else:
        st.warning("Não foi possível carregar os dados de alocação.")

with tab2:
    st.header("Conteúdo do Projects.csv")
    if df_projects is not None:
        st.dataframe(df_projects)
        st.info(f"Carregadas {len(df_projects)} linhas.")
    else:
        st.warning("Não foi possível carregar os dados dos projetos.")
