import streamlit as st
import pandas as pd
import os
import plotly.express as px
import ast
from datetime import datetime

st.set_page_config(layout="wide")

st.title("Recruitment Dashboard")

ALLOC_FILE = 'GeminiCheck.csv'
PROJECTS_FILE = 'Projects.csv'

try:
    alloc_mod_time = os.path.getmtime(ALLOC_FILE)
    projects_mod_time = os.path.getmtime(PROJECTS_FILE)
    latest_mod_timestamp = max(alloc_mod_time, projects_mod_time)
    latest_update_dt = datetime.fromtimestamp(latest_mod_timestamp)
    last_update_str = latest_update_dt.strftime("%Y-%m-%d %H:%M:%S")
    st.caption(f"Data last updated on: {last_update_str}")
except FileNotFoundError:
    st.caption("Data files not found, timestamp unavailable.")

@st.cache_data
def load_and_process_data(alloc_path, projects_path):
    if not os.path.exists(alloc_path) or not os.path.exists(projects_path):
        st.error(f"ERROR: One or both files were not found. Please check '{ALLOC_FILE}' and '{PROJECTS_FILE}'.")
        return None, None
    
    df_alloc = pd.read_csv(alloc_path)
    df_projects = pd.read_csv(projects_path)

    if 'quotas' not in df_alloc.columns or 'quota_result' not in df_alloc.columns:
        st.error(f"ERROR: Columns 'quotas' or 'quota_result' not found in {ALLOC_FILE}.")
        return df_alloc, df_projects
        
    def extract_dynamic_data(row):
        try:
            keys = ast.literal_eval(row['quotas'])
            values = ast.literal_eval(row['quota_result'])
            
            if isinstance(keys, (list, tuple)) and isinstance(values, (list, tuple)) and len(keys) == len(values):
                return dict(zip(keys, values))
            else:
                return {}
        except Exception:
            return {}

    dynamic_data = df_alloc.apply(extract_dynamic_data, axis=1)
    dynamic_df = pd.DataFrame(dynamic_data.tolist(), index=df_alloc.index)
    
    df_alloc_processed = pd.concat([df_alloc, dynamic_df], axis=1)
    
    if 'Region' in df_alloc_processed.columns:
        df_alloc_processed['Region'] = df_alloc_processed['Region'].astype(str).replace('0', 'Any Region')
    
    if 'SEL' in df_alloc_processed.columns:
        df_alloc_processed['SEL'] = df_alloc_processed['SEL'].astype(str).replace('0', 'Country without SEL')
    
    df_alloc_processed['project_id'] = df_alloc_processed['project_id'].astype(str)
    df_projects['project_id'] = df_projects['project_id'].astype(str)

    return df_alloc_processed, df_projects

df_alloc_processed, df_projects = load_and_process_data(ALLOC_FILE, PROJECTS_FILE)

if df_alloc_processed is not None:
    st.sidebar.header("Filters")
    
    df_filtered = df_alloc_processed.copy()
    df_projects_filtered = df_projects.copy()

    all_projects = sorted(df_alloc_processed['project_id'].unique())
    selected_projects = st.sidebar.multiselect('1. Project(s)', all_projects)
    
    if selected_projects:
        df_filtered = df_filtered[df_filtered['project_id'].isin(selected_projects)]
        df_projects_filtered = df_projects_filtered[df_projects_filtered['project_id'].isin(selected_projects)]

    all_countries = sorted(df_filtered['country'].dropna().unique())
    selected_countries = st.sidebar.multiselect('2. Country(ies)', all_countries)
    
    if selected_countries:
        df_filtered = df_filtered[df_filtered['country'].isin(selected_countries)]
        if 'country' in df_projects_filtered.columns:
            df_projects_filtered = df_projects_filtered[df_projects_filtered['country'].isin(selected_countries)]
    
    all_regions = sorted(df_filtered['Region'].dropna().unique())
    selected_regions = st.sidebar.multiselect('3. Region(s)', all_regions)

    if selected_regions:
        df_filtered = df_filtered[df_filtered['Region'].isin(selected_regions)]

    all_age_groups = sorted(df_filtered['age_group'].dropna().unique())
    selected_age_groups = st.sidebar.multiselect('4. Age Group', all_age_groups)

    if selected_age_groups:
        df_filtered = df_filtered[df_filtered['age_group'].isin(selected_age_groups)]

    all_genders = sorted(df_filtered['Gender'].dropna().unique())
    selected_genders = st.sidebar.multiselect('5. Gender', all_genders)

    if selected_genders:
        df_filtered = df_filtered[df_filtered['Gender'].isin(selected_genders)]
        
    all_sels = sorted(df_filtered['SEL'].dropna().unique())
    selected_sels = st.sidebar.multiselect('6. Social Class (SEL)', all_sels)

    if selected_sels:
        df_filtered = df_filtered[df_filtered['SEL'].isin(selected_sels)]

if df_alloc_processed is not None and df_projects is not None:
    tab_charts, tab_tables = st.tabs(["Quota Charts", "Data Tables"])

    with tab_charts:
        st.header("Graphical View of Recruitment Demand")
        
        if df_filtered.empty:
            st.warning("No data found for the selected filter combination.")
        else:
            st.markdown("---")
            total_to_recruit = df_filtered['People_To_Recruit'].sum()
            total_allocated = df_filtered['allocated_completes'].sum()
            kpi1, kpi2 = st.columns(2)
            kpi1.metric(label="Panelists Needed", value=f"{total_to_recruit:,}")
            kpi2.metric(label="Completes Needed (Allocated)", value=f"{total_allocated:,}")
            st.markdown("---")
            
            required_cols = ['People_To_Recruit', 'age_group', 'Gender', 'country', 'SEL']
            if not all(col in df_filtered.columns for col in required_cols):
                st.warning("Could not generate charts. Required columns not found.")
            else:
                custom_colors = ['#25406e', '#6ba1ff', '#a1f1ff', '#5F9EA0', '#E6E6FA']
                
                col1, col2 = st.columns(2)
                with col1:
                    by_age = df_filtered.groupby('age_group')['People_To_Recruit'].sum().sort_values(ascending=False).reset_index()
                    fig_age = px.bar(by_age, x='age_group', y='People_To_Recruit', title='Demand by Age Group', color_discrete_sequence=custom_colors)
                    st.plotly_chart(fig_age, use_container_width=True)
                
                with col2:
                    by_gender = df_filtered.groupby('Gender')['People_To_Recruit'].sum().reset_index()
                    fig_gender = px.pie(by_gender, names='Gender', values='People_To_Recruit', title='Demand by Gender', hole=0.3, color_discrete_sequence=custom_colors)
                    st.plotly_chart(fig_gender, use_container_width=True)

                col3, col4 = st.columns(2)
                with col3:
                    by_country = df_filtered.groupby('country')['People_To_Recruit'].sum().sort_values(ascending=False).reset_index()
                    fig_country = px.bar(by_country, x='country', y='People_To_Recruit', title='Demand by Country', color_discrete_sequence=custom_colors)
                    st.plotly_chart(fig_country, use_container_width=True)
                    
                with col4:
                    by_sel = df_filtered.groupby('SEL')['People_To_Recruit'].sum().sort_values(ascending=False).reset_index()
                    fig_sel = px.bar(by_sel, x='SEL', y='People_To_Recruit', title='Demand by Social Class (SEL)', color_discrete_sequence=custom_colors)
                    st.plotly_chart(fig_sel, use_container_width=True)

    with tab_tables:
        st.header("Initial Quota Data")
        st.dataframe(df_projects_filtered.reset_index(drop=True))
        st.info(f"Showing {len(df_projects_filtered)} of {len(df_projects)} rows.")
        
        st.header("Allocation Data")
        st.dataframe(df_filtered[['project_id','country','allocated_completes','CR_filled','People_To_Recruit','Start Date','days_in_field','Expected Date','DaystoDeliver','age_group','SEL','Gender','Region']].reset_index(drop=True))
        st.info(f"Showing {len(df_filtered)} of {len(df_alloc_processed)} rows.")
