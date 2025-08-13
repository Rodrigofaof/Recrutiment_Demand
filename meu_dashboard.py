import streamlit as st
import pandas as pd
import os
import plotly.express as px

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

    if 'resultado_cota' not in df_alloc.columns:
        st.error("ERRO: A coluna 'resultado_cota' não foi encontrada em GeminiCheck.csv, necessária para os gráficos.")
        return df_alloc, df_projects
        
    def extract_quota_data(row):
        try:
            items = [item.strip() for item in str(row).strip("()").replace("'", "").split(',')]
            while len(items) < 4: items.append(None)
            return items
        except Exception: 
            return [None, None, None, None]

    split_data = df_alloc['resultado_cota'].apply(extract_quota_data).to_list()
    new_cols_df = pd.DataFrame(split_data, index=df_alloc.index, columns=['age_group', 'SEL', 'Gender', 'Region'])
    
    df_alloc_processed = df_alloc.join(new_cols_df)
    df_alloc_processed.rename(columns={'country': 'pais'}, inplace=True)
    
    df_alloc_processed['project_id'] = df_alloc_processed['project_id'].astype(str)
    df_projects['project_id'] = df_projects['project_id'].astype(str)

    return df_alloc_processed, df_projects

# --- ETAPA 3: Carregar os dados ---
df_alloc_processed, df_projects = load_and_process_data(ALLOC_FILE, PROJECTS_FILE)

# --- ETAPA 4: Filtros na barra lateral ---
if df_alloc_processed is not None:
    st.sidebar.header("Filtros")
    
    # Adiciona o Modo de Depuração
    debug_mode = st.sidebar.checkbox("Ativar Modo de Depuração")

    # DataFrame que será modificado pelos filtros
    df_filtered = df_alloc_processed.copy()
    df_projects_filtered = df_projects.copy()

    # 1. Filtro de Projeto
    all_projects = sorted(df_alloc_processed['project_id'].unique())
    selected_projects = st.sidebar.multiselect('1. Selecione o(s) Projeto(s)', all_projects)
    
    # Aplica o filtro de projeto imediatamente
    if selected_projects:
        df_filtered = df_filtered[df_filtered['project_id'].isin(selected_projects)]
        df_projects_filtered = df_projects_filtered[df_projects_filtered['project_id'].isin(selected_projects)]

    # 2. Filtro de País (as opções agora dependem do filtro de projeto)
    all_countries = sorted(df_filtered['pais'].unique())
    selected_countries = st.sidebar.multiselect('2. Selecione o(s) País(es)', all_countries)
    
    # Aplica o filtro de país sobre o resultado já filtrado
    if selected_countries:
        df_filtered = df_filtered[df_filtered['pais'].isin(selected_countries)]
        
        if 'pais' in df_projects_filtered.columns:
            df_projects_filtered = df_projects_filtered[df_projects_filtered['pais'].isin(selected_countries)]
        elif 'country' in df_projects_filtered.columns:
            df_projects_filtered = df_projects_filtered[df_projects_filtered['country'].isin(selected_countries)]

# --- ETAPA 5: Seção de Depuração ---
if debug_mode:
    st.warning("--- MODO DE DEPURACÃO ATIVADO ---")
    st.subheader("1. Seleções Atuais nos Filtros")
    st.write(f"**Projetos Selecionados:** `{selected_projects}`")
    st.write(f"**Países Selecionados:** `{selected_countries}`")
    
    st.subheader("2. Estado da Tabela `df_filtered` (usada nos gráficos)")
    st.write(f"A tabela para os gráficos tem **{df_filtered.shape[0]} linhas** e **{df_filtered.shape[1]} colunas**.")
    st.write("Amostra dos dados:")
    st.dataframe(df_filtered.head())
    
    st.subheader("3. Países Únicos na Tabela Filtrada")
    if not df_filtered.empty:
        st.write(df_filtered['pais'].unique())
    st.warning("--- FIM DA DEPURAÇÃO ---")


# --- ETAPA 6: Criar as abas do dashboard ---
if df_alloc_processed is not None and df_projects is not None:
    tab_graficos, tab_tabelas = st.tabs(["Gráficos de Cotas", "Tabelas de Dados"])

    with tab_graficos:
        st.header("Visão Gráfica da Demanda por Recrutamento")
        
        if df_filtered.empty:
            st.warning("Nenhum dado encontrado para a combinação de filtros selecionada.")
        else:
            required_cols = ['Pessoas_Para_Recrutar', 'age_group', 'Gender', 'pais', 'SEL']
            if not all(col in df_filtered.columns for col in required_cols):
                st.warning("Não foi possível gerar os gráficos. Colunas necessárias não encontradas.")
            else:
                custom_colors = ['#25406e', '#6ba1ff', '#a1f1ff', '#5F9EA0', '#E6E6FA']
                
                col1, col2 = st.columns(2)
                with col1:
                    by_age = df_filtered.groupby('age_group')['Pessoas_Para_Recrutar'].sum().sort_values(ascending=False).reset_index()
                    fig_age = px.bar(by_age, x='age_group', y='Pessoas_Para_Recrutar', title='Demanda por Faixa Etária', color_discrete_sequence=custom_colors)
                    st.plotly_chart(fig_age, use_container_width=True)
                
                with col2:
                    by_gender = df_filtered.groupby('Gender')['Pessoas_Para_Recrutar'].sum().reset_index()
                    fig_gender = px.pie(by_gender, names='Gender', values='Pessoas_Para_Recrutar', title='Demanda por Gênero', hole=0.3, color_discrete_sequence=custom_colors)
                    st.plotly_chart(fig_gender, use_container_width=True)

                col3, col4 = st.columns(2)
                with col3:
                    by_country = df_filtered.groupby('pais')['Pessoas_Para_Recrutar'].sum().sort_values(ascending=False).reset_index()
                    fig_country = px.bar(by_country, x='pais', y='Pessoas_Para_Recrutar', title='Demanda por País', color_discrete_sequence=custom_colors)
                    st.plotly_chart(fig_country, use_container_width=True)
                    
                with col4:
                    by_sel = df_filtered.groupby('SEL')['Pessoas_Para_Recrutar'].sum().sort_values(ascending=False).reset_index()
                    fig_sel = px.bar(by_sel, x='SEL', y='Pessoas_Para_Recrutar', title='Demanda por Classe Social (SEL)', color_discrete_sequence=custom_colors)
                    st.plotly_chart(fig_sel, use_container_width=True)

    with tab_tabelas:
        st.header("Dados de Alocação (`GeminiCheck.csv`)")
        st.dataframe(df_filtered)
        st.info(f"Mostrando {len(df_filtered)} de {len(df_alloc_processed)} linhas.")

        st.header("Dados das Cotas Iniciais (`Projects.csv`)")
        st.dataframe(df_projects_filtered)
        st.info(f"Mostrando {len(df_projects_filtered)} de {len(df_projects)} linhas.")
