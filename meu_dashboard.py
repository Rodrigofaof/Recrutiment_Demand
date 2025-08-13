import streamlit as st
import pandas as pd
import os

# --- Configuração da Página ---
st.set_page_config(layout="wide")

st.title("Verificador de Carga de Dados")
st.write("Este painel serve para carregar e exibir as tabelas brutas, garantindo que os arquivos estão acessíveis e sendo lidos corretamente.")

# --- ETAPA 1: Definir os caminhos completos para os arquivos ---
ALLOC_FILE = os.path.join('GeminiCheck.csv')
PROJECTS_FILE = os.path.join('Projects.csv')


# --- ETAPA 2: Função para carregar os dados ---
@st.cache_data
def load_data(file_path):
    """
    Lê um arquivo CSV e o retorna como um DataFrame do pandas.
    Retorna None se o arquivo não for encontrado ou ocorrer um erro.
    """
    if not os.path.exists(file_path):
        st.error(f"ARQUIVO NÃO ENCONTRADO: O arquivo não foi localizado no caminho esperado -> {file_path}")
        return None
    try:
        df = pd.read_csv(file_path)
        return df
    except Exception as e:
        st.error(f"FALHA AO LER ARQUIVO: Ocorreu um erro ao tentar ler o arquivo {file_path}. Detalhes: {e}")
        return None

# --- ETAPA 3: Carregar os dados e exibi-los em abas ---
df_alloc = load_data(ALLOC_FILE)
df_projects = load_data(PROJECTS_FILE)

tab1, tab2 = st.tabs(["Dados de Alocação (GeminiCheck.csv)", "Dados de Cotas (Projects.csv)"])

with tab1:
    st.header("Conteúdo de `GeminiCheck.csv`")
    if df_alloc is not None:
        st.dataframe(df_alloc)
        st.success(f"Arquivo carregado com sucesso. Total de {len(df_alloc)} linhas.")
    else:
        st.warning("Não foi possível carregar o arquivo de dados de alocação.")

with tab2:
    st.header("Conteúdo de `Projects.csv`")
    if df_projects is not None:
        st.dataframe(df_projects)
        st.success(f"Arquivo carregado com sucesso. Total de {len(df_projects)} linhas.")
    else:
        st.warning("Não foi possível carregar o arquivo de dados dos projetos.")
