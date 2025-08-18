import streamlit as st
import pandas as pd
import os
import plotly.express as px
import ast
from datetime import date, timedelta

st.set_page_config(layout="wide")

st.title("Daily Recruitment Dashboard")

ALLOC_FILE = 'GeminiCheck.csv' 
PROJECTS_FILE = 'Projects.csv'

@st.cache_data
def load_and_generate_plan(alloc_path, projects_path):
    if not os.path.exists(alloc_path) or not os.path.exists(projects_path):
        st.error(f"ERROR: Files not found. Check for '{alloc_path}' and '{projects_path}'.")
        return None, None, None

    df_alloc = pd.read_csv(alloc_path)
    df_projects = pd.read_csv(projects_path)

    # --- 1. Generate Daily Plan ---
    today = date.today()
    daily_plan = []
    
    for row in df_alloc.itertuples():
        total_recruits = getattr(row, 'Pessoas_Para_Recrutar', 0)
        days_to_deliver = getattr(row, 'DaystoDeliver', 1.0)

        if total_recruits <= 0:
            continue
        
        if pd.isna(days_to_deliver) or days_to_deliver < 1:
            days_to_deliver = 1
        
        days_to_deliver = int(days_to_deliver)
        base_goal = total_recruits // days_to_deliver
        remainder = total_recruits % days_to_deliver
        
        for i in range(days_to_deliver):
            plan_date = today + timedelta(days=i)
            daily_goal = base_goal + 1 if i < remainder else base_goal
            
            if daily_goal > 0:
                new_row = row._asdict()
                new_row['plan_date'] = plan_date
                new_row['daily_recruitment_goal'] = daily_goal
                del new_row['Index']
                daily_plan.append(new_row)

    if not daily_plan:
        st.warning("Could not generate a daily recruitment plan. Check input data.")
        return df_alloc, df_projects, pd.DataFrame()

    df_daily_plan = pd.DataFrame(daily_plan)
    df_daily_plan['plan_date'] = pd.to_datetime(df_daily_plan['plan_date']).dt.date

    # --- 2. Process for dynamic columns (like original script) ---
    def extract_dynamic_data(row_series):
        try:
            keys = ast.literal_eval(row_series['cotas'])
            values = ast.literal_eval(row_series['resultado_cota'])
            if isinstance(keys, (list, tuple)) and isinstance(values, (list, tuple)) and len(keys) == len(values):
                return dict(zip(keys, values))
        except Exception:
            return {}
        return {}

    dynamic_data = df_daily_plan.apply(extract_dynamic_data, axis=1)
    dynamic_df = pd.DataFrame(dynamic_data.tolist(), index=df_daily_plan.index)
    df_daily_plan_processed = pd.concat([df_daily_plan, dynamic_df], axis=1)

    # --- 3. Final Cleaning ---
    if 'Region' in df_daily_plan_processed.columns:
        df_daily_plan_processed['Region'] = df_daily_plan_processed['Region'].astype(str).replace('0', 'Any Region')
    if 'SEL' in df_daily_plan_processed.columns:
        df_daily_plan_processed['SEL'] = df_daily_plan_processed['SEL'].astype(str).replace('0', 'Country without SEL')
    
    df_daily_plan_processed['project_id'] = df_daily_plan_processed['project_id'].astype(str)
    df_projects['project_id'] = df_projects['project_id'].astype(str)

    return df_alloc, df_projects, df_daily_plan_processed

# --- Load all data ---
df_alloc_original, df_projects_original, df_plan = load_and_generate_plan(ALLOC_FILE, PROJECTS_FILE)

# --- Sidebar Filters ---
if df_plan is not None and not df_plan.empty:
    st.sidebar.header("Filters")

    # 1. DATE FILTER (PRIMARY)
    min_date = df_plan['plan_date'].min()
    max_date = df_plan['plan_date'].max()
    selected_date = st.sidebar.date_input("1. Select Date", value=date.today(), min_value=min_date, max_value=max_date)

    # Filter by date first
    df_filtered_by_date = df_plan[df_plan['plan_date'] == selected_date].copy()

    # 2. OTHER FILTERS
    all_projects = sorted(df_filtered_by_date['project_id'].unique())
    selected_projects = st.sidebar.multiselect('2. Project(s)', all_projects)
    
    if selected_projects:
        df_filtered_by_date = df_filtered_by_date[df_filtered_by_date['project_id'].isin(selected_projects)]

    all_countries = sorted(df_filtered_by_date['country'].dropna().unique())
    selected_countries = st.sidebar.multiselect('3. Country(ies)', all_countries)
    
    if selected_countries:
        df_filtered_by_date = df_filtered_by_date[df_filtered_by_date['country'].isin(selected_countries)]
    
    # --- The rest of the filters now operate on the date-filtered data ---
    df_filtered = df_filtered_by_date
    
    all_regions = sorted(df_filtered['Region'].dropna().unique())
    selected_regions = st.sidebar.multiselect('4. Region(s)', all_regions)
    if selected_regions:
        df_filtered = df_filtered[df_filtered['Region'].isin(selected_regions)]

    all_age_groups = sorted(df_filtered['age_group'].dropna().unique())
    selected_age_groups = st.sidebar.multiselect('5. Age Group', all_age_groups)
    if selected_age_groups:
        df_filtered = df_filtered[df_filtered['age_group'].isin(selected_age_groups)]

    all_genders = sorted(df_filtered['Gender'].dropna().unique())
    selected_genders = st.sidebar.multiselect('6. Gender', all_genders)
    if selected_genders:
        df_filtered = df_filtered[df_filtered['Gender'].isin(selected_genders)]
        
    all_sels = sorted(df_filtered['SEL'].dropna().unique())
    selected_sels = st.sidebar.multiselect('7. Social Class (SEL)', all_sels)
    if selected_sels:
        df_filtered = df_filtered[df_filtered['SEL'].isin(selected_sels)]

    # --- Dashboard Tabs ---
    tab_charts, tab_tables = st.tabs(["Daily Goal Charts", "Data Tables"])

    with tab_charts:
        st.header(f"Recruitment Demand for: {selected_date.strftime('%Y-%m-%d')}")
        
        if df_filtered.empty:
            st.warning("No recruitment goals found for the selected date and filters.")
        else:
            st.markdown("---")
            total_daily_goal = df_filtered['daily_recruitment_goal'].sum()
            kpi1, kpi2 = st.columns(2)
            kpi1.metric(label="Today's Recruitment Goal", value=f"{int(total_daily_goal):,}")
            kpi2.metric(label="Active Quotas for Today", value=f"{len(df_filtered):,}")
            st.markdown("---")
            
            custom_colors = ['#25406e', '#6ba1ff', '#a1f1ff', '#5F9EA0', '#E6E6FA']
            
            col1, col2 = st.columns(2)
            with col1:
                by_age = df_filtered.groupby('age_group')['daily_recruitment_goal'].sum().sort_values(ascending=False).reset_index()
                fig_age = px.bar(by_age, x='age_group', y='daily_recruitment_goal', title='Demand by Age Group', color_discrete_sequence=custom_colors)
                st.plotly_chart(fig_age, use_container_width=True)
            
            with col2:
                by_gender = df_filtered.groupby('Gender')['daily_recruitment_goal'].sum().reset_index()
                fig_gender = px.pie(by_gender, names='Gender', values='daily_recruitment_goal', title='Demand by Gender', hole=0.3, color_discrete_sequence=custom_colors)
                st.plotly_chart(fig_gender, use_container_width=True)

            col3, col4 = st.columns(2)
            with col3:
                by_country = df_filtered.groupby('country')['daily_recruitment_goal'].sum().sort_values(ascending=False).reset_index()
                fig_country = px.bar(by_country, x='country', y='daily_recruitment_goal', title='Demand by Country', color_discrete_sequence=custom_colors)
                st.plotly_chart(fig_country, use_container_width=True)
                
            with col4:
                by_sel = df_filtered.groupby('SEL')['daily_recruitment_goal'].sum().sort_values(ascending=False).reset_index()
                fig_sel = px.bar(by_sel, x='SEL', y='daily_recruitment_goal', title='Demand by Social Class (SEL)', color_discrete_sequence=custom_colors)
                st.plotly_chart(fig_sel, use_container_width=True)

    with tab_tables:
        st.header(f"Daily Recruitment Plan for {selected_date.strftime('%Y-%m-%d')}")
        display_cols = ['plan_date', 'daily_recruitment_goal', 'project_id', 'country', 'age_group', 'SEL', 'Gender', 'Region', 'Pessoas_Para_Recrutar', 'DaystoDeliver']
        st.dataframe(df_filtered[[col for col in display_cols if col in df_filtered.columns]].reset_index(drop=True))
        st.info(f"Showing {len(df_filtered)} of {len(df_plan)} total planned activities.")

        st.header("Original Projects Data")
        st.dataframe(df_projects_original)
