import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
from datetime import datetime
from zoneinfo import ZoneInfo

st.set_page_config(layout="wide", initial_sidebar_state="expanded")

def load_and_process_data(final_alloc_path, initial_quotas_path):
    df_alloc = pd.read_csv(final_alloc_path)
    df_quotas = pd.read_csv(initial_quotas_path)

    def extract_quota_data(row):
        try:
            items = [item.strip() for item in row.strip("()").replace("'", "").split(',')]
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
    
    df_quotas.rename(columns={'index': 'quota_index'}, inplace=True)
    
    def create_quota_label(row):
        parts = [f"P:{row['project_id']}", f"Q:{row['quota_index']}"]
        if str(row.get('1', '0')) != '0': parts.append(f"Idade:{row['1']}")
        if str(row.get('2', '0')) != '0': parts.append(f"Gênero:{row['2']}")
        if str(row.get('18', '0')) != '0': parts.append(f"Região:{row['18']}")
        return " | ".join(parts)

    df_quotas['QuotaLabel'] = df_quotas.apply(create_quota_label, axis=1)
    
    df_merged = pd.merge(df_clean, df_quotas[['quota_index', 'QuotaLabel']], on='quota_index', how='left')
    return df_merged, df_quotas

alloc_file = 'GeminiCheck.csv'
projects_file = 'Projects.csv'
df_processed, df_projects = load_and_process_data(alloc_file, projects_file)

last_update_unix = os.path.getmtime(alloc_file)
utc_time = datetime.fromtimestamp(last_update_unix, ZoneInfo("UTC"))
br_timezone = ZoneInfo("America/Sao_Paulo")
br_time = utc_time.astimezone(br_timezone)
formatted_last_update = br_time.strftime("%d/%m/%Y %H:%M:%S (GMT%z)")

st.title("Recruitment Dashboard")
st.caption(f"Last data update: {formatted_last_update}")

st.sidebar.header("Filters")
df_filtered = df_processed.copy()

quota_labels = sorted(df_filtered['QuotaLabel'].unique())
selected_labels = st.sidebar.multiselect('Selecione a Cota Inicial', quota_labels, default=None, placeholder="Escolha uma ou mais cotas")

if selected_labels:
    df_filtered = df_filtered[df_filtered['QuotaLabel'].isin(selected_labels)]

tab1, tab2, tab3 = st.tabs(["Dashboard", "Sankey Flow", "Data Tables"])

with tab1:
    st.header("Recruitment Overview")
    df_display = df_processed if not selected_labels else df_filtered
    
    completes_needed = df_display['allocated_completes'].sum()
    panelists_needed = df_display['Pessoas_Para_Recrutar'].sum()
    kpi1, kpi2 = st.columns(2)
    kpi1.metric(label="Completes Necessários (Alocados)", value=f"{completes_needed:,}")
    kpi2.metric(label="Painelistas Necessários", value=f"{panelists_needed:,}")

with tab2:
    st.header("Fluxo de Distribuição da Cota")
    if not selected_labels:
        st.info("⬅️ Para gerar o gráfico, selecione uma ou mais cotas no filtro da barra lateral.")
    elif df_filtered.empty:
        st.warning("Não há dados para a cota selecionada.")
    else:
        df_sankey = df_filtered.copy()
        df_sankey.dropna(subset=['age_group', 'Gender', 'SEL'], inplace=True)

        all_nodes = list(pd.unique(df_sankey[['QuotaLabel', 'age_group', 'Gender', 'SEL']].values.ravel('K')))
        node_map = {node: i for i, node in enumerate(all_nodes)}
        
        source, target, value = [], [], []
        
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
        fig_sankey.update_layout(title_text="Fluxo da Cota para os Perfis Demográficos", font_size=12, height=600)
        st.plotly_chart(fig_sankey, use_container_width=True)

with tab3:
    st.header("Dados Detalhados")
    st.dataframe(df_filtered)

    st.markdown("---")
    st.header("Cotas Iniciais (Projetos)")
    df_display_projects = df_projects
    if selected_labels:
        selected_indices = df_processed[df_processed['QuotaLabel'].isin(selected_labels)]['quota_index'].unique()
        df_display_projects = df_projects[df_projects['quota_index'].isin(selected_indices)]
    
    st.dataframe(df_display_projects)
