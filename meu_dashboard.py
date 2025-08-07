import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
from datetime import datetime
from zoneinfo import ZoneInfo

st.set_page_config(layout="wide", initial_sidebar_state="expanded")

def load_and_process_data(file_path):
    df = pd.read_csv(file_path)
    
    def extract_quota_data(row):
        try:
            items = [item.strip() for item in row.strip("()").replace("'", "").split(',')]
            while len(items) < 4:
                items.append(None)
            return items[0], items[1], items[2], items[3]
        except:
            return None, None, None, None

    df[['age_group', 'SEL', 'Gender', 'Region']] = df['resultado_cota'].apply(
        lambda x: pd.Series(extract_quota_data(x))
    )

    df.rename(columns={'country': 'pais'}, inplace=True)
    
    df_clean = df[['project_id', 'pais', 'age_group', 'SEL', 'Gender', 'Region', 'Pessoas_Para_Recrutar', 'allocated_completes']].copy()
    
    df_clean['Pessoas_Para_Recrutar'] = pd.to_numeric(df_clean['Pessoas_Para_Recrutar'], errors='coerce')
    df_clean['allocated_completes'] = pd.to_numeric(df_clean['allocated_completes'], errors='coerce')
    
    df_clean.dropna(subset=['project_id', 'Pessoas_Para_Recrutar', 'allocated_completes', 'age_group', 'SEL', 'Gender'], inplace=True)
    df_clean['Pessoas_Para_Recrutar'] = df_clean['Pessoas_Para_Recrutar'].astype(int)
    df_clean['allocated_completes'] = df_clean['allocated_completes'].astype(int)
    df_clean['project_id'] = df_clean['project_id'].astype(int).astype(str)

    return df_clean

data_file_path = 'GeminiCheck.csv'
df_processed = load_and_process_data(data_file_path)

last_update_unix = os.path.getmtime(data_file_path)
utc_time = datetime.fromtimestamp(last_update_unix, ZoneInfo("UTC"))
br_timezone = ZoneInfo("America/Sao_Paulo")
br_time = utc_time.astimezone(br_timezone)
gmt_offset = br_time.strftime("%z")
formatted_gmt = f"GMT{gmt_offset[:-2]}"
formatted_last_update = br_time.strftime(f"%d/%m/%Y %H:%M:%S ({formatted_gmt})")

st.title("Recruitment Dashboard")
st.caption(f"Last data update: {formatted_last_update}")

st.sidebar.header("Filters")
custom_colors = ['#25406e', '#6ba1ff', '#a1f1ff', '#5F9EA0', '#E6E6FA']
df_filtered = df_processed.copy()

projects = sorted(df_filtered['project_id'].unique())
selected_projects = st.sidebar.multiselect('Select Project(s)', projects, default=None, placeholder="Escolha um ou mais projetos")
if selected_projects:
    df_filtered = df_filtered[df_filtered['project_id'].isin(selected_projects)]

countries = sorted(df_filtered['pais'].unique())
selected_countries = st.sidebar.multiselect('Select Country(s)', countries, default=countries)
if selected_countries:
    df_filtered = df_filtered[df_filtered['pais'].isin(selected_countries)]

age_groups = sorted(df_filtered['age_group'].unique())
if len(age_groups) > 1:
    selected_age_groups = st.sidebar.multiselect('Select Age Group(s)', age_groups, default=age_groups)
    if selected_age_groups:
        df_filtered = df_filtered[df_filtered['age_group'].isin(selected_age_groups)]

genders = sorted(df_filtered['Gender'].unique())
if len(genders) > 1:
    selected_genders = st.sidebar.multiselect('Select Gender(s)', genders, default=genders)
    if selected_genders:
        df_filtered = df_filtered[df_filtered['Gender'].isin(selected_genders)]

sels = sorted(df_filtered['SEL'].unique())
if len(sels) > 1:
    selected_sels = st.sidebar.multiselect('Select SEL(s)', sels, default=sels)
    if selected_sels:
        df_filtered = df_filtered[df_filtered['SEL'].isin(selected_sels)]

tab1, tab2, tab3 = st.tabs(["Dashboard", "Sankey Flow", "Data Tables"])

with tab1:
    st.header("Recruitment Overview")
    if df_filtered.empty:
        st.warning("No data available for the selected filters.")
    else:
        completes_needed = df_filtered['allocated_completes'].sum()
        panelists_needed = df_filtered['Pessoas_Para_Recrutar'].sum()

        kpi1, kpi2 = st.columns(2)
        kpi1.metric(label="Completes Needed", value=f"{completes_needed:,}")
        kpi2.metric(label="Panelists Needed", value=f"{panelists_needed:,}")
        
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            by_age = df_filtered.groupby('age_group')['Pessoas_Para_Recrutar'].sum().sort_values(ascending=False).reset_index()
            fig_age = px.bar(by_age, x='age_group', y='Pessoas_Para_Recrutar', title='Demand by Age Group', labels={'age_group': 'Age Group', 'Pessoas_Para_Recrutar': 'People to Recruit'}, color_discrete_sequence=custom_colors)
            fig_age.update_layout(template="streamlit")
            st.plotly_chart(fig_age, use_container_width=True)
        with col2:
            by_gender = df_filtered.groupby('Gender')['Pessoas_Para_Recrutar'].sum().reset_index()
            fig_gender = px.pie(by_gender, names='Gender', values='Pessoas_Para_Recrutar', title='Demand by Gender', hole=0.3, color_discrete_sequence=custom_colors)
            fig_gender.update_layout(template="streamlit")
            st.plotly_chart(fig_gender, use_container_width=True)

        col3, col4 = st.columns(2)
        with col3:
            by_country = df_filtered.groupby('pais')['Pessoas_Para_Recrutar'].sum().sort_values(ascending=False).reset_index()
            fig_country = px.bar(by_country, x='pais', y='Pessoas_Para_Recrutar', title='Demand by Country', labels={'pais': 'Country', 'Pessoas_Para_Recrutar': 'People to Recruit'}, color_discrete_sequence=custom_colors)
            fig_country.update_layout(template="streamlit")
            st.plotly_chart(fig_country, use_container_width=True)
        with col4:
            by_sel = df_filtered.groupby('SEL')['Pessoas_Para_Recrutar'].sum().sort_values(ascending=False).reset_index()
            fig_sel = px.bar(by_sel, x='SEL', y='Pessoas_Para_Recrutar', title='Demand by Socioeconomic Level (SEL)', labels={'SEL': 'Socioeconomic Level', 'Pessoas_Para_Recrutar': 'People to Recruit'}, color_discrete_sequence=custom_colors)
            fig_sel.update_layout(template="streamlit")
            st.plotly_chart(fig_sel, use_container_width=True)

with tab2:
    st.header("Completes Allocation Flow")

    if not selected_projects:
        st.info("⬅️ Para gerar o gráfico, por favor, selecione um ou mais projetos no filtro da barra lateral.")
    elif df_filtered.empty:
        st.warning("Não há dados para a combinação de filtros selecionada.")
    else:
        df_sankey = df_filtered.copy()
        
        all_nodes = list(pd.unique(df_sankey[['project_id', 'age_group', 'Gender', 'SEL']].values.ravel('K')))
        node_map = {node: i for i, node in enumerate(all_nodes)}
        
        source = []
        target = []
        value = []
        
        flow1 = df_sankey.groupby(['project_id', 'age_group'])['allocated_completes'].sum().reset_index()
        source.extend(flow1['project_id'].map(node_map))
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
            node = dict(
              pad = 15,
              thickness = 20,
              line = dict(color = "black", width = 0.5),
              label = all_nodes,
              color = "#25406e"
            ),
            link = dict(
              source = source,
              target = target,
              value = value
          ))])

        fig_sankey.update_layout(title_text="Fluxo de Alocação dos Projetos Selecionados", font_size=12, height=600)
        st.plotly_chart(fig_sankey, use_container_width=True)

with tab3:
    st.header("Detailed Filtered Data")
    if df_filtered.empty:
        st.warning("No data available for the selected filters.")
    else:
        st.dataframe(df_filtered)
        csv_filtered = df_filtered.to_csv(index=False).encode('utf-8')
        st.download_button(label="Download Filtered Data as CSV", data=csv_filtered, file_name='filtered_recruitment_data.csv', mime='text/csv')

    st.markdown("---")
    st.header("Necessary Projects")
    try:
        ProjetosNecessarios = pd.read_csv("Projects.csv")
        ProjetosNecessarios = ProjetosNecessarios.sort_values(by='expectedcompletes', ascending=False)

        def make_clickable(project_id):
            return f'<a target="_blank" href="https://sample.offerwise.com/project/stats/{project_id}">{project_id}</a>'

        ProjetosNecessarios['project_id'] = ProjetosNecessarios['project_id'].apply(make_clickable)
        
        html = ProjetosNecessarios.to_html(escape=False, index=False)
        
        st.write(html, unsafe_allow_html=True)
        st.download_button(label="Download Projects as CSV", data=ProjetosNecessarios.to_csv(index=False).encode('utf-8'), file_name='Necessary_Projects.csv', mime='text/csv')
    except FileNotFoundError:
        st.error("File 'Projects.csv' not found.")

