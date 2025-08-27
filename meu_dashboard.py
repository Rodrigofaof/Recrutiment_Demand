import streamlit as st
import pandas as pd
import os
import plotly.express as px
import ast
from datetime import date, timedelta
import json
import streamlit.components.v1 as components

st.set_page_config(layout="wide")

st.title("Dynamic Recruitment Dashboard")

ALLOC_FILE = 'GeminiCheck.csv'
PROJECTS_FILE = 'Projects.csv'
REPORT_FILE = 'Report.xlsx'

# --- Gemini API Call Function ---
def call_gemini_api(messages, report_data):
    system_prompt = f"""
    You are a specialized data analyst assistant. Your task is to answer questions based ONLY on the data provided from the 'Report.xlsx' file.
    Do not make assumptions or use external knowledge. If the answer cannot be found in the provided data, state that clearly.
    Here is the report data in markdown format:
    ---
    {report_data}
    ---
    """
    
    # We only need the last user message for the API call content
    user_query = ""
    if messages and messages[-1]['role'] == 'user':
        user_query = messages[-1]['content']

    payload = {
        "contents": [{"parts": [{"text": user_query}]}],
        "systemInstruction": {
            "parts": [{"text": system_prompt}]
        },
    }

    # This component will run the JavaScript to call the API
    # and will use a callback to return the result to Streamlit
    components.html(
        f"""
        <script>
        async function callApi() {{
            const apiKey = ""; 
            const url = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-05-20:generateContent?key=${apiKey}`;
            
            const payload = {json.dumps(payload)};

            try {{
                const response = await fetch(url, {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify(payload)
                }});
                const result = await response.json();
                
                let text = "Sorry, I could not process the response.";
                if (result.candidates && result.candidates[0].content && result.candidates[0].content.parts[0].text) {{
                   text = result.candidates[0].content.parts[0].text;
                }}
                
                window.parent.postMessage({{
                    'type': 'streamlit:setComponentValue',
                    'value': {{'type': 'ai_response', 'text': text}}
                }}, '*');

            }} catch (error) {{
                console.error('Error calling Gemini API:', error);
                window.parent.postMessage({{
                    'type': 'streamlit:setComponentValue',
                    'value': {{'type': 'ai_response', 'text': 'An error occurred while contacting the AI model.'}}
                }}, '*');
            }}
        }}
        callApi();
        </script>
        """,
        height=0,
        width=0,
    )


@st.cache_data
def load_data(alloc_path, projects_path, report_path):
    if not os.path.exists(alloc_path) or not os.path.exists(projects_path) or not os.path.exists(report_path):
        st.error(f"ERROR: Files not found. Check for '{alloc_path}', '{projects_path}', and '{report_path}'.")
        return None, None, None, None

    df_alloc = pd.read_csv(alloc_path)
    df_projects = pd.read_csv(projects_path)
    df_report = pd.read_excel(report_path)
    return df_alloc, df_projects, df_report

@st.cache_data
def generate_plan(df_alloc):
    today = date.today()
    daily_plan = []
    
    for row in df_alloc.itertuples():
        total_recruits = getattr(row, 'Pessoas_Para_Recrutar', 0)
        total_allocated = getattr(row, 'allocated_completes', 0)
        days_to_deliver = getattr(row, 'DaystoDeliver', 1.0)

        if pd.isna(days_to_deliver) or days_to_deliver < 1:
            days_to_deliver = 1
        
        days_to_deliver = int(days_to_deliver)

        base_goal = total_recruits // days_to_deliver
        remainder = total_recruits % days_to_deliver
        
        base_allocated = total_allocated // days_to_deliver
        remainder_allocated = total_allocated % days_to_deliver
        
        for i in range(days_to_deliver):
            plan_date = today + timedelta(days=i)
            daily_goal = base_goal + 1 if i < remainder else base_goal
            daily_allocated_goal = base_allocated + 1 if i < remainder_allocated else base_allocated

            if daily_goal > 0 or daily_allocated_goal > 0:
                new_row = row._asdict()
                new_row['plan_date'] = plan_date
                new_row['daily_recruitment_goal'] = daily_goal
                new_row['daily_allocated_goal'] = daily_allocated_goal
                new_row['original_quota_index'] = row.Index
                del new_row['Index']
                daily_plan.append(new_row)

    if not daily_plan:
        return pd.DataFrame()

    df_daily_plan = pd.DataFrame(daily_plan)
    df_daily_plan['plan_date'] = pd.to_datetime(df_daily_plan['plan_date']).dt.date

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

    if 'Region' in df_daily_plan_processed.columns:
        df_daily_plan_processed['Region'] = df_daily_plan_processed['Region'].astype(str).replace('0', 'Any Region')
    if 'SEL' in df_daily_plan_processed.columns:
        df_daily_plan_processed['SEL'] = df_daily_plan_processed['SEL'].astype(str).replace('0', 'Country without SEL')
    
    df_daily_plan_processed['project_id'] = df_daily_plan_processed['project_id'].astype(str)
    
    return df_daily_plan_processed

# --- Main App ---
df_alloc_original, df_projects_original, df_report = load_data(ALLOC_FILE, PROJECTS_FILE, REPORT_FILE)

if df_alloc_original is not None:
    df_plan = generate_plan(df_alloc_original)
    if df_projects_original is not None:
        df_projects_original['project_id'] = df_projects_original['project_id'].astype(str)
else:
    df_plan = pd.DataFrame()

# --- TABS ---
tab_ia, tab_charts, tab_tables = st.tabs(["AI Assistant", "Demand Charts", "Data Tables"])

# --- AI Assistant Tab ---
with tab_ia:
    st.header("Ask About the Recruitment Report")
    
    if df_report is not None:
        report_markdown = df_report.to_markdown(index=False)

        if "messages" not in st.session_state:
            st.session_state.messages = []

        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        if prompt := st.chat_input("What would you like to know about the report?"):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    # The call_gemini_api function will render an HTML component
                    # that calls the API and sets the result in st.session_state
                    # via a component value callback.
                    component_value = call_gemini_api(st.session_state.messages, report_markdown)
                    
                    # We don't have a direct return, so we rely on the component to set a value
                    # and then we can check for it. This part is tricky with st.components.v1.html
                    # A more robust solution might use a custom component or a different architecture,
                    # but this is a workaround. For now, we'll just show the spinner and the user
                    # will see the response appear after the API call finishes.

    else:
        st.warning("Could not load the report file to power the AI assistant.")

# --- Dashboard Filters and Content (Charts and Tables) ---
if df_plan is not None and not df_plan.empty:
    st.sidebar.header("Filters")

    use_date_filter = st.sidebar.checkbox("Filter by date range")
    
    df_filtered_by_date = df_plan.copy()
    header_title = "Overall Recruitment Demand"

    if use_date_filter:
        min_date = df_plan['plan_date'].min()
        max_date = df_plan['plan_date'].max()
        
        selected_range = st.sidebar.date_input(
            "1. Select Date Range", 
            value=(min_date, min_date + timedelta(days=7)),
            min_value=min_date, 
            max_value=max_date
        )
        
        if len(selected_range) == 2:
            start_date, end_date = selected_range
            df_filtered_by_date = df_plan[
                (df_plan['plan_date'] >= start_date) & (df_plan['plan_date'] <= end_date)
            ]
            header_title = f"Recruitment Demand for: {start_date.strftime('%d/%m/%Y')} to {end_date.strftime('%d/%m/%Y')}"

    df_filtered = df_filtered_by_date
    df_projects_filtered = df_projects_original.copy() if df_projects_original is not None else pd.DataFrame()

    all_projects = sorted(df_filtered['project_id'].unique())
    selected_projects = st.sidebar.multiselect('2. Project(s)', all_projects)
    if selected_projects:
        df_filtered = df_filtered[df_filtered['project_id'].isin(selected_projects)]
        if not df_projects_filtered.empty:
            df_projects_filtered = df_projects_filtered[df_projects_filtered['project_id'].isin(selected_projects)]

    all_countries = sorted(df_filtered['country'].dropna().unique())
    selected_countries = st.sidebar.multiselect('3. Country(ies)', all_countries)
    if selected_countries:
        df_filtered = df_filtered[df_filtered['country'].isin(selected_countries)]
        if not df_projects_filtered.empty and 'country' in df_projects_filtered.columns:
             df_projects_filtered = df_projects_filtered[df_projects_filtered['country'].isin(selected_countries)]

    if 'Recruitment' in df_filtered.columns:
        all_recruitment_options = sorted(df_filtered['Recruitment'].dropna().unique())
        selected_recruitment = st.sidebar.multiselect('4. Recruitment', all_recruitment_options)
        if selected_recruitment:
            df_filtered = df_filtered[df_filtered['Recruitment'].isin(selected_recruitment)]
            if not df_projects_filtered.empty and 'Recruitment' in df_projects_filtered.columns:
                df_projects_filtered = df_projects_filtered[df_projects_filtered['Recruitment'].isin(selected_recruitment)]

    all_regions = sorted(df_filtered['Region'].dropna().unique())
    selected_regions = st.sidebar.multiselect('5. Region(s)', all_regions)
    if selected_regions:
        df_filtered = df_filtered[df_filtered['Region'].isin(selected_regions)]

    all_age_groups = sorted(df_filtered['age_group'].dropna().unique())
    selected_age_groups = st.sidebar.multiselect('6. Age Group', all_age_groups)
    if selected_age_groups:
        df_filtered = df_filtered[df_filtered['age_group'].isin(selected_age_groups)]

    all_genders = sorted(df_filtered['Gender'].dropna().unique())
    selected_genders = st.sidebar.multiselect('7. Gender', all_genders)
    if selected_genders:
        df_filtered = df_filtered[df_filtered['Gender'].isin(selected_genders)]
        
    all_sels = sorted(df_filtered['SEL'].dropna().unique())
    selected_sels = st.sidebar.multiselect('8. Social Class (SEL)', all_sels)
    if selected_sels:
        df_filtered = df_filtered[df_filtered['SEL'].isin(selected_sels)]

    with tab_charts:
        st.header(header_title)
        
        if df_filtered.empty:
            st.warning("No recruitment goals found for the selected filters.")
        else:
            st.markdown("---")
            recruitment_goal = df_filtered['daily_recruitment_goal'].sum()
            allocated_goal = df_filtered['daily_allocated_goal'].sum()
            
            unique_quota_indices = df_filtered['original_quota_index'].unique()
            total_completes_needed = df_alloc_original.loc[unique_quota_indices, 'allocated_completes'].sum()

            kpi1, kpi2, kpi3 = st.columns(3)
            kpi1.metric(label="Recruitment Needed (Date Range)", value=f"{int(recruitment_goal):,}")
            kpi2.metric(label="Completes Needed (Date Range)", value=f"{int(allocated_goal):,}")
            kpi3.metric(label="Completes Needed (Total)", value=f"{int(total_completes_needed):,}")

            st.markdown("---")
            
            custom_colors = ['#25406e', '#6ba1ff', '#a1f1ff', '#5F9EA0', '#E6E6FA']
            
            st.subheader("Recruitment Goal Breakdown")
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
        if df_report is not None:
            st.header("Recruitment Report Data")
            st.dataframe(df_report)
        
        st.header("Detailed Recruitment Plan")
        display_cols = ['plan_date', 'daily_recruitment_goal', 'daily_allocated_goal', 'project_id', 'country', 'Recruitment', 'age_group', 'SEL', 'Gender', 'Region', 'Pessoas_Para_Recrutar', 'allocated_completes', 'DaystoDeliver']
        st.dataframe(df_filtered[[col for col in display_cols if col in df_filtered.columns]].reset_index(drop=True))
        st.info(f"Showing {len(df_filtered)} of {len(df_plan)} total planned activities.")

        if not df_projects_filtered.empty:
            st.header("Original Projects Data")
            st.dataframe(df_projects_filtered)
            st.info(f"Showing {len(df_projects_filtered)} of {len(df_projects_original)} projects.")
