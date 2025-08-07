import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
from datetime import datetime
from zoneinfo import ZoneInfo

# =============================================================================
# 1. CONFIGURAÇÕES E CONSTANTES
# =============================================================================
st.set_page_config(layout="wide", initial_sidebar_state="expanded")

# --- CORREÇÃO 1: APONTAR PARA O ARQUIVO CORRETO ---
DATA_FILE_PATH = 'Recrutamento_Necessario.csv' 
PROJECTS_FILE_PATH = 'Projetos_Necessarios.csv'
CUSTOM_COLORS = ['#25406e', '#6ba1ff', '#a1f1ff', '#5F9EA0', '#E6E6FA']

# =============================================================================
# 2. CARREGAMENTO E PROCESSAMENTO DE DADOS (COM CACHE)
# =============================================================================

@st.cache_data
def load_recruitment_data(file_path):
    """
    Carrega e processa os dados de recrutamento do novo arquivo final.
    """
    try:
        df = pd.read_csv(file_path)
    except FileNotFoundError:
        return pd.DataFrame()

    # --- CORREÇÃO 2: LÓGICA DE PROCESSAMENTO ATUALIZADA ---
    # O novo arquivo não tem 'resultado_cota', mas sim colunas de perfil.
    # Vamos renomeá-las para nomes mais amigáveis para os gráficos.
    
    rename_map = {
        'country': 'pais',
        'expected_completes': 'allocated_completes', # Ajuste de nome para consistência
        'Pessoas_Para_Recrutar': 'Pessoas_Para_Recrutar' 
        # Adicione aqui os renames das suas colunas de perfil, se necessário
        # Ex: '1': 'age_group', '2': 'Gender', 'profiler186': 'SEL'
    }
    df.rename(columns=rename_map, inplace=True)
    
    # Garantir que as colunas principais existem
    cols_to_use = ['project_id', 'pais', 'age_group', 'SEL', 'Gender', 'Region', 'Pessoas_Para_Recrutar', 'allocated_completes']
    existing_cols = [col for col in cols_to_use if col in df.columns]
    df_clean = df[existing_cols].copy()
    
    # Limpeza e conversão de tipos
    for col in ['Pessoas_Para_Recrutar', 'allocated_completes']:
        if col in df_clean.columns:
            df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce').fillna(0)
            df_clean[col] = df_clean[col].astype(int)

    return df_clean

@st.cache_data
def load_projects_data(file_path):
    """ Carrega os dados dos projetos necessários, também com cache. """
    try:
        return pd.read_csv(file_path)
    except FileNotFoundError:
        return None

def get_last_update_time(file_path):
    """ Retorna a data de modificação do arquivo formatada para o fuso de SP. """
    if not os.path.exists(file_path):
        return "Arquivo de dados não encontrado"
        
    last_update_unix = os.path.getmtime(file_path)
    utc_time = datetime.fromtimestamp(last_update_unix, ZoneInfo("UTC"))
    br_time = utc_time.astimezone(ZoneInfo("America/Sao_Paulo"))
    return br_time.strftime("%d/%m/%Y %H:%M:%S (GMT%z)")

# =============================================================================
# 3. COMPONENTES DO DASHBOARD (Nenhuma mudança necessária aqui)
# =============================================================================

def display_sidebar(df):
    """ Cria e gerencia todos os filtros na barra lateral. """
    st.sidebar.header("Filtros")
    if df.empty:
        st.sidebar.warning("Nenhum dado para filtrar.")
        return df

    # As colunas dos filtros precisam existir no DataFrame carregado
    df_filtered = df.copy()
    
    if 'pais' in df.columns:
        countries = sorted(df['pais'].unique())
        selected_countries = st.sidebar.multiselect('País(es)', countries, default=countries)
        df_filtered = df_filtered[df_filtered['pais'].isin(selected_countries)]

    if 'age_group' in df.columns:
        age_groups = sorted(df_filtered['age_group'].unique())
        selected_age_groups = st.sidebar.multiselect('Grupo de Idade', age_groups, default=age_groups)
        df_filtered = df_filtered[df_filtered['age_group'].isin(selected_age_groups)]

    if 'Gender' in df.columns:
        genders = sorted(df_filtered['Gender'].unique())
        selected_genders = st.sidebar.multiselect('Gênero', genders, default=genders)
        df_filtered = df_filtered[df_filtered['Gender'].isin(selected_genders)]
    
    if 'SEL' in df.columns:
        sels = sorted(df_filtered['SEL'].unique())
        selected_sels = st.sidebar.multiselect('Nível Socioeconômico (SEL)', sels, default=sels)
        df_filtered = df_filtered[df_filtered['SEL'].isin(selected_sels)]

    return df_filtered

def display_kpis(df):
    """ Exibe os principais indicadores (KPIs). """
    completes_needed = df['allocated_completes'].sum()
    panelists_needed = df['Pessoas_Para_Recrutar'].sum()

    kpi1, kpi2 = st.columns(2)
    kpi1.metric(label="Completes Necessárias", value=f"{completes_needed:,}")
    kpi2.metric(label="Painelistas a Recrutar", value=f"{panelists_needed:,}")

def display_charts(df):
    """ Exibe os gráficos de barra e de pizza. """
    col1, col2 = st.columns(2)
    with col1:
        by_country = df.groupby('pais')['Pessoas_Para_Recrutar'].sum().sort_values(ascending=False).reset_index()
        fig = px.bar(by_country, x='pais', y='Pessoas_Para_Recrutar', title='Demanda por País', labels={'pais': 'País', 'Pessoas_Para_Recrutar': 'Pessoas a Recrutar'}, color_discrete_sequence=CUSTOM_COLORS, template="streamlit")
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        by_gender = df.groupby('Gender')['Pessoas_Para_Recrutar'].sum().reset_index()
        fig = px.pie(by_gender, names='Gender', values='Pessoas_Para_Recrutar', title='Demanda por Gênero', hole=0.3, color_discrete_sequence=CUSTOM_COLORS, template="streamlit")
        st.plotly_chart(fig, use_container_width=True)

    col3, col4 = st.columns(2)
    with col3:
        by_age = df.groupby('age_group')['Pessoas_Para_Recrutar'].sum().sort_values(ascending=False).reset_index()
        fig = px.bar(by_age, x='age_group', y='Pessoas_Para_Recrutar', title='Demanda por Grupo de Idade', labels={'age_group': 'Grupo de Idade', 'Pessoas_Para_Recrutar': 'Pessoas a Recrutar'}, color_discrete_sequence=CUSTOM_COLORS, template="streamlit")
        st.plotly_chart(fig, use_container_width=True)
    with col4:
        by_sel = df.groupby('SEL')['Pessoas_Para_Recrutar'].sum().sort_values(ascending=False).reset_index()
        fig = px.bar(by_sel, x='SEL', y='Pessoas_Para_Recrutar', title='Demanda por Nível Socioeconômico (SEL)', labels={'SEL': 'SEL', 'Pessoas_Para_Recrutar': 'Pessoas a Recrutar'}, color_discrete_sequence=CUSTOM_COLORS, template="streamlit")
        st.plotly_chart(fig, use_container_width=True)

def display_sankey_chart(df, category_column):
    """
    Cria e exibe um gráfico de Sankey para visualizar o fluxo de recrutamento.
    """
    if 'project_id' not in df.columns or category_column not in df.columns:
        st.error(f"As colunas 'project_id' e '{category_column}' são necessárias para este gráfico.")
        return

    df_flow = df.groupby(['project_id', category_column])['Pessoas_Para_Recrutar'].sum().reset_index()
    df_flow = df_flow[df_flow['Pessoas_Para_Recrutar'] > 0]
    
    if df_flow.empty:
        st.warning("Não há dados de fluxo para exibir com os filtros atuais.")
        return

    source_nodes = df_flow['project_id'].astype(str).unique()
    target_nodes = df_flow[category_column].astype(str).unique()
    all_nodes = list(source_nodes) + list(target_nodes)
    
    node_map = {node: i for i, node in enumerate(all_nodes)}
    
    links = {
        'source': df_flow['project_id'].map(node_map),
        'target': df_flow[category_column].map(node_map),
        'value': df_flow['Pessoas_Para_Recrutar']
    }

    fig = go.Figure(data=[go.Sankey(
        node=dict(pad=15, thickness=20, line=dict(color="black", width=0.5), label=all_nodes, color=CUSTOM_COLORS),
        link=dict(
            source=links['source'], target=links['target'], value=links['value'],
            hovertemplate='De %{source.label} para %{target.label}<br>Recrutar: %{value:,}<extra></extra>'
        )
    )])

    fig.update_layout(title_text="Distribuição de Vagas Necessárias por Projeto", font_size=12)
    st.plotly_chart(fig, use_container_width=True)

# =============================================================================
# 4. EXECUÇÃO PRINCIPAL DO DASHBOARD
# =============================================================================

st.title("📊 Dashboard de Recrutamento")
st.caption(f"Última atualização dos dados: {get_last_update_time(DATA_FILE_PATH)}")

df_recruitment = load_recruitment_data(DATA_FILE_PATH)
df_projects = load_projects_data(PROJECTS_FILE_PATH)

if df_recruitment.empty:
    st.error(f"Não foi possível carregar os dados de recrutamento. Verifique se o arquivo '{DATA_FILE_PATH}' existe e não está vazio.")
else:
    df_filtered = display_sidebar(df_recruitment)
    
    tab1, tab2 = st.tabs(["Dashboard de Demanda", "Tabelas de Dados"])

    with tab1:
        st.header("Visão Geral do Recrutamento")
        if df_filtered.empty:
            st.warning("Nenhum dado disponível para os filtros selecionados.")
        else:
            display_kpis(df_filtered)
            st.markdown("---")
            display_charts(df_filtered)
            
            st.markdown("---")
            st.header("Fluxo de Redistribuição de Vagas")
            
            sankey_category = st.selectbox(
                'Visualizar redistribuição por:',
                ('age_group', 'Gender', 'SEL', 'Region'),
                key='sankey_select'
            )
            
            if sankey_category:
                display_sankey_chart(df_filtered, sankey_category)

    with tab2:
        st.header("Dados Detalhados Filtrados")
        if df_filtered.empty:
            st.warning("Nenhum dado disponível para os filtros selecionados.")
        else:
            st.dataframe(df_filtered)
            csv_filtered = df_filtered.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Baixar Dados Filtrados (CSV)",
                data=csv_filtered,
                file_name='dados_filtrados_recrutamento.csv',
                mime='text/csv'
            )

        st.markdown("---")
        st.header("Projetos Necessários")
        
        if df_projects is None:
            st.warning(f"O arquivo '{PROJECTS_FILE_PATH}' não foi encontrado.")
        else:
            st.dataframe(
                df_projects,
                column_config={
                    "project_id": st.column_config.LinkColumn(
                        "Project ID",
                        display_text="🔗 Ver Projeto",
                        help="Clique para ver as estatísticas do projeto",
                        base_url="https://sample.offerwise.com/project/stats/"
                    )
                },
                use_container_width=True
            )
            csv_projects = df_projects.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Baixar Lista de Projetos (CSV)",
                data=csv_projects,
                file_name='projetos_necessarios.csv',
                mime='text/csv'
            )
