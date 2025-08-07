import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
from datetime import datetime
from zoneinfo import ZoneInfo

st.set_page_config(layout="wide", initial_sidebar_state="expanded")

@st.cache_data
def load_and_process_data(final_alloc_path, initial_quotas_path):
    df_alloc = pd.read_csv(final_alloc_path)
    df_quotas = pd.read_csv(initial_quotas_path)

    def extract_quota_data(row):
        try:
            items = [item.strip() for item in str(row).strip("()").replace("'", "").split(',')]
            while len(items) < 4:
                items.append(None)
            return items[0], items[1], items[2], items[3]
        except:
            return None, None, None, None

    df_alloc[['age_group', 'SEL', 'Gender', 'Region']] = df_alloc['resultado_cota'].apply(
        lambda x: pd.Series(extract_quota_data(x))
    )
    df_alloc.rename(columns={'country': 'pais'}, inplace=True)
    
    df_clean = df_alloc[['quota_index', 'project_id', 'pais', 'age_group', 'SEL', 'Gender', 'Region', 'Pessoas_Para_Recrutar', 'allocated_completes']].copy()
    df_clean['allocated_completes'] = pd.to_numeric(df_clean['allocated_completes'], errors='coerce').fillna(0).astype(int)
    df_clean['project_id'] = df_clean['project_id'].astype(str)
    
    df_quotas.rename(columns={'index': 'quota_index'}, inplace=True)
    df_quotas['project_id'] = df_quotas['project_id'].astype(str)
    
    def create_quota_label(row):
        parts = [f"Q:{row['quota_index']}"]
        if str(row.get('1', '0')) != '0': parts.append(f"Idade:{row['1']}")
        if str(row.get('2', '0')) != '0': parts.append(f"Gênero:{row['2']}")
        if str(row.get('18', '0')) != '0': parts.append(f"Região:{row['18']}")
        return " | ".join(parts)

    df_quotas['QuotaLabel'] = df_quotas.apply(create_quota_label, axis=1)
    
    df_merged = pd.merge(df_clean, df_quotas[['quota_index', 'QuotaLabel']], on='quota_index', how='left')
    return df_merged, df_quotas

# --- Carregamento dos Dados ---
alloc_file = 'GeminiCheck.csv'
projects_file = 'Projects.csv'
df_processed, df_projects = load_and_process_data(alloc_file, projects_file)

# --- Título e Atualização ---
st.title("Recruitment Dashboard")
last_update_unix = os.path.getmtime(alloc_file)
utc_time = datetime.fromtimestamp(last_update_unix, ZoneInfo("UTC"))
br_timezone = ZoneInfo("America/Sao_Paulo")
br_time = utc_time.astimezone(br_timezone)
formatted_last_update = br_time.strftime("%d/%m/%Y %H:%M:%S (GMT%z)")
st.caption(f"Última atualização dos dados: {formatted_last_update}")

# --- Barra de Filtros (Sidebar) ---
st.sidebar.header("Filtros")
custom_colors = ['#25406e', '#6ba1ff', '#a1f1ff', '#5F9EA0', '#E6E6FA']

# Filtro 1: Projeto (Principal)
all_projects = sorted(df_processed['project_id'].unique())
selected_projects = st.sidebar.multiselect('1. Selecione o(s) Projeto(s)', all_projects, default=None, placeholder="Escolha um projeto")

# Dataframe temporário para popular os outros filtros
if selected_projects:
    df_temp = df_processed[df_processed['project_id'].isin(selected_projects)]
else:
    df_temp = df_processed

# Filtros dinâmicos
all_labels = sorted(df_temp['QuotaLabel'].unique())
selected_labels = st.sidebar.multiselect('2. [Opcional] Selecione a(s) Cota(s)', all_labels, default=None, placeholder="Todas as cotas do projeto")

all_countries = sorted(df_temp['pais'].unique())
selected_countries = st.sidebar.multiselect('País', all_countries, default=all_countries)

all_age_groups = sorted(df_temp['age_group'].dropna().unique())
selected_age_groups = st.sidebar.multiselect('Faixa Etária', all_age_groups, default=all_age_groups)

all_genders = sorted(df_temp['Gender'].dropna().unique())
selected_genders = st.sidebar.multiselect('Gênero', all_genders, default=all_genders)

all_sels = sorted(df_temp['SEL'].dropna().unique())
selected_sels = st.sidebar.multiselect('Classe Social (SEL)', all_sels, default=all_sels)

# --- Aplicação Final dos Filtros ---
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

# --- Abas do Dashboard ---
tab1, tab2, tab3 = st.tabs(["Dashboard Geral", "Fluxo Sankey da Cota", "Tabelas de Dados"])

with tab1:
    st.header("Visão Geral do Recrutamento")
    if df_filtered.empty:
        st.warning("Nenhum dado encontrado para os filtros selecionados.")
    else:
        # KPIs
        completes_needed = df_filtered['allocated_completes'].sum()
        panelists_needed = df_filtered['Pessoas_Para_Recrutar'].sum()
        kpi1, kpi2 = st.columns(2)
        kpi1.metric(label="Completes Necessários (Alocados)", value=f"{completes_needed:,}")
        kpi2.metric(label="Painelistas Necessários", value=f"{panelists_needed:,}")
        st.markdown("---")

        # Gráficos (código restaurado)
        col1, col2 = st.columns(2)
        with col1:
            by_age = df_filtered.groupby('age_group')['Pessoas_Para_Recrutar'].sum().sort_values(ascending=False).reset_index()
            fig_age = px.bar(by_age, x='age_group', y='Pessoas_Para_Recrutar', title='Demanda por Faixa Etária', labels={'age_group': 'Faixa Etária', 'Pessoas_Para_Recrutar': 'Pessoas para Recrutar'}, color_discrete_sequence=custom_colors)
            st.plotly_chart(fig_age, use_container_width=True)
        with col2:
            by_gender = df_filtered.groupby('Gender')['Pessoas_Para_Recrutar'].sum().reset_index()
            fig_gender = px.pie(by_gender, names='Gender', values='Pessoas_Para_Recrutar', title='Demanda por Gênero', hole=0.3, color_discrete_sequence=custom_colors)
            st.plotly_chart(fig_gender, use_container_width=True)

        col3, col4 = st.columns(2)
        with col3:
            by_country = df_filtered.groupby('pais')['Pessoas_Para_Recrutar'].sum().sort_values(ascending=False).reset_index()
            fig_country = px.bar(by_country, x='pais', y='Pessoas_Para_Recrutar', title='Demanda por País', labels={'pais': 'País', 'Pessoas_Para_Recrutar': 'Pessoas para Recrutar'}, color_discrete_sequence=custom_colors)
            st.plotly_chart(fig_country, use_container_width=True)
        with col4:
            by_sel = df_filtered.groupby('SEL')['Pessoas_Para_Recrutar'].sum().sort_values(ascending=False).reset_index()
            fig_sel = px.bar(by_sel, x='SEL', y='Pessoas_Para_Recrutar', title='Demanda por Classe Social (SEL)', labels={'SEL': 'Classe Social', 'Pessoas_Para_Recrutar': 'Pessoas para Recrutar'}, color_discrete_sequence=custom_colors)
            st.plotly_chart(fig_sel, use_container_width=True)

with tab2:
    st.header("Fluxo de Distribuição da Cota")
    # Lógica corrigida: o gráfico é ativado pela seleção do PROJETO
    if not selected_projects:
        st.info("⬅️ Para gerar o gráfico de fluxo, por favor, selecione um ou mais Projetos na barra lateral.")
    elif df_filtered.empty:
        st.warning("Não há dados para a combinação de filtros selecionada.")
    else:
        df_sankey = df_filtered.copy()
        df_sankey.dropna(subset=['QuotaLabel', 'age_group', 'Gender', 'SEL'], inplace=True)
        df_sankey['source_project'] = 'Projeto: ' + df_sankey['project_id']

        all_nodes = list(pd.unique(df_sankey[['source_project', 'QuotaLabel', 'age_group', 'Gender', 'SEL']].values.ravel('K')))
        node_map = {node: i for i, node in enumerate(all_nodes)}
        
        source, target, value = [], [], []
        
        flow0 = df_sankey.groupby(['source_project', 'QuotaLabel'])['allocated_completes'].sum().reset_index()
        source.extend(flow0['source_project'].map(node_map))
        target.extend(flow0['QuotaLabel'].map(node_map))
        value.extend(flow0['allocated_completes'])

        flow1 = df_sankey.groupby(['QuotaLabel', 'age_group'])['allocated_completes'].sum().reset_index()
        source.extend(flow1['QuotaLabel'].map(node_map))
        target.extend(flow1['age_group'].map(node_map))
        value.extend(flow1['allocated_completes'])

        flow2 = df_sankey.groupby(['age_group', 'Gender'])['allocated_completes'].sum().reset_index()
        source.extend(flow2['age_group'].map(node_map))
        target.extend(flow2['Gender'].map(node_map))
        value.extend(flow2['allocated_completes'])
        
        flow3 = df_sankey.groupby(['Gender', 'SEL'])['allocated_completes'].sum().reset_index()
        source.extend(flow3['Gender'].map(node_map))
        target.extend(flow3['SEL'].map(node_map))
        value.extend(flow3['allocated_completes'])

        fig_sankey = go.Figure(data=[go.Sankey(
            node = dict(pad=15, thickness=20, line=dict(color="black", width=0.5), label=all_nodes, color="#25406e"),
            link = dict(source=source, target=target, value=value)
        )])
        fig_sankey.update_layout(title_text="Fluxo do Projeto e Cota para os Perfis Demográficos", font_size=12, height=600)
        st.plotly_chart(fig_sankey, use_container_width=True)

with tab3:
    st.header("Dados Detalhados Filtrados")
    st.dataframe(df_filtered)

    st.markdown("---")
    st.header("Definição das Cotas Iniciais (Projetos)")
    st.dataframe(df_projects[df_projects['quota_index'].isin(df_filtered['quota_index'].unique())])def load_and_process_data(final_alloc_path, initial_quotas_path):
    try:
        df_alloc = pd.read_csv(final_alloc_path)
        df_quotas = pd.read_csv(initial_quotas_path)
    except FileNotFoundError as e:
        st.error(f"Erro: Arquivo não encontrado - {e}. Verifique se os arquivos '{final_alloc_path}' e '{initial_quotas_path}' estão no lugar certo.")
        return pd.DataFrame(), pd.DataFrame()

    # --- CORREÇÃO CRÍTICA: Garantir tipos de dados consistentes para a chave ---
    # Força a coluna 'quota_index' a ser numérica em ambos os dataframes, ignorando erros.
    df_alloc['quota_index'] = pd.to_numeric(df_alloc['quota_index'], errors='coerce')
    df_quotas.rename(columns={'index': 'quota_index'}, inplace=True)
    df_quotas['quota_index'] = pd.to_numeric(df_quotas['quota_index'], errors='coerce')

    # Remove linhas onde a chave se tornou nula (porque não era um número válido)
    df_alloc.dropna(subset=['quota_index'], inplace=True)
    df_quotas.dropna(subset=['quota_index'], inplace=True)

    # Converte a chave para inteiro para garantir a correspondência exata.
    df_alloc['quota_index'] = df_alloc['quota_index'].astype(int)
    df_quotas['quota_index'] = df_quotas['quota_index'].astype(int)
    # --- FIM DA CORREÇÃO ---
