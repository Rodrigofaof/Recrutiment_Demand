import streamlit as st
import pandas as pd
import os
import plotly.express as px
import ast
from datetime import date, timedelta
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_experimental.agents.agent_toolkits import create_pandas_dataframe_agent
from langchain.agents.agent_types import AgentType

st.set_page_config(layout="wide")

st.title("Dynamic Recruitment Dashboard")

ALLOC_FILE = 'GeminiCheck.csv'
PROJECTS_FILE = 'Projects.csv'
REPORT_FILE = 'Report.xlsx'

google_api_key = st.secrets["GOOGLE_API_KEY"] if "GOOGLE_API_KEY" in st.secrets else None

@st.cache_data
def load_data(alloc_path, projects_path, report_path):
    if not all(os.path.exists(p) for p in [alloc_path, projects_path, report_path]):
        st.error("Um ou mais arquivos de dados não foram encontrados. Verifique os caminhos.")
        return None, None, None
    df_alloc = pd.read_csv(alloc_path)
    df_projects = pd.read_csv(projects_path)
    df_report = pd.read_excel(report_path)
    return df_alloc, df_projects, df_report

@st.cache_data
def generate_plan(_df_alloc):
    today = date.today()
    daily_plan = []
    for row in _df_alloc.itertuples():
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
                new_row.update({
                    'plan_date': plan_date,
                    'daily_recruitment_goal': daily_goal,
                    'daily_allocated_goal': daily_allocated_goal,
                    'original_quota_index': row.Index
                })
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
            if isinstance(keys, (list, tuple)) and len(keys) == len(values):
                return dict(zip(keys, values))
        except Exception:
            return {}
        return {}
    dynamic_data = df_daily_plan.apply(extract_dynamic_data, axis=1)
    dynamic_df = pd.DataFrame(dynamic_data.tolist(), index=df_daily_plan.index)
    df_daily_plan_processed = pd.concat([df_daily_plan, dynamic_df], axis=1)
    for col, replacement in {'Region': 'Any Region', 'SEL': 'Country without SEL'}.items():
        if col in df_daily_plan_processed.columns:
            df_daily_plan_processed[col] = df_daily_plan_processed[col].astype(str).replace('0', replacement)
    df_daily_plan_processed['project_id'] = df_daily_plan_processed['project_id'].astype(str)
    return df_daily_plan_processed

@st.cache_resource
def get_pandas_agent(_df_report, api_key):
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=api_key, temperature=0)
    
    # Pega a data de hoje e formata
    today_date_str = date.today().strftime('%Y-%m-%d')

    agent = create_pandas_dataframe_agent(
        llm,
        _df_report,
        agent_type=AgentType.OPENAI_FUNCTIONS,
        verbose=True,
        agent_executor_kwargs={"handle_parsing_errors": True},
        allow_dangerous_code=True,
        # O prefixo agora é uma f-string que inclui a data
        prefix=f"""
        Você é um assistente de análise de dados especialista em pandas. Sua tarefa é ajudar os usuários a responder perguntas sobre um DataFrame.
        - Antes de responder, SEMPRE pense passo a passo no seu plano de ação.
        - Verifique cuidadosamente os nomes das colunas no DataFrame antes de escrever qualquer código. Os nomes são sensíveis a maiúsculas e minúsculas.
        - Se precisar fazer um cálculo, escreva o código pandas para isso.
        - Ao dar a resposta final, explique brevemente como você chegou a ela.
        - Se a pergunta for ambígua, peça esclarecimentos.
        - Na coluna Age temos uma string, o primeiro número é referente a idade inicial do Range e o segundo a idade final do Range
        - Na coluna Expected Date você deve interpretar a data como yyyy-mm-dd
        - Quando for perguntado sobre hoje, sempre some tudo que está para trás
        - Hoje é {today_date_str}
        """
    )
    return agent

df_alloc_original, df_projects_original, df_report = load_data(ALLOC_FILE, PROJECTS_FILE, REPORT_FILE)

df_plan = pd.DataFrame()
if df_alloc_original is not None:
    df_plan = generate_plan(df_alloc_original)
    if df_projects_original is not None:
        df_projects_original['project_id'] = df_projects_original['project_id'].astype(str)

tab_ia, tab_charts, tab_tables = st.tabs(["AI Assistant", "Demand Charts", "Data Tables"])

with tab_ia:
    st.header("Ask about the recruitment Data")
    if not google_api_key:
        st.error("Chave da API do Google não encontrada. Adicione a variável GOOGLE_API_KEY aos seus secrets do Streamlit.")
    elif df_report is not None:
        agent = get_pandas_agent(df_report, google_api_key)
        
        if "messages" not in st.session_state:
            st.session_state.messages = [{"role": "assistant", "content": "How can I help you analyze the recruitment report?"}]

        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        if prompt := st.chat_input("What would you like to know?"):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                with st.spinner("Analyzing data..."):
                    try:
                        response = agent.invoke(prompt)
                        answer = response.get("output", "Não consegui processar a resposta.")
                    except Exception as e:
                        answer = f"Ocorreu um erro: {e}"
                    st.markdown(answer)
            st.session_state.messages.append({"role": "assistant", "content": answer})
    else:
        st.warning("Não foi possível carregar o arquivo de relatório para alimentar o assistente de IA.")

if df_plan is not None and not df_plan.empty:
    st.sidebar.header("Filtros")
    use_date_filter = st.sidebar.checkbox("Filtrar por período")
    df_filtered_by_date = df_plan.copy()
    header_title = "Demanda Geral de Recrutamento"
    if use_date_filter:
        min_date, max_date = df_plan['plan_date'].min(), df_plan['plan_date'].max()
        selected_range = st.sidebar.date_input(
            "1. Selecione o Período",
            value=(min_date, min_date + timedelta(days=7)),
            min_value=min_date, max_value=max_date
        )
        if len(selected_range) == 2:
            start_date, end_date = selected_range
            df_filtered_by_date = df_plan[df_plan['plan_date'].between(start_date, end_date)]
            header_title = f"Demanda de Recrutamento de: {start_date:%d/%m/%Y} a {end_date:%d/%m/%Y}"
    
    df_filtered = df_filtered_by_date
    df_projects_filtered = df_projects_original.copy() if df_projects_original is not None else pd.DataFrame()

    filter_options = {
        '2. Projeto(s)': 'project_id', '3. País(es)': 'country', '4. Recrutamento': 'Recruitment',
        '5. Região(ões)': 'Region', '6. Faixa Etária': 'age_group', '7. Gênero': 'Gender',
        '8. Classe Social (SEL)': 'SEL'
    }
    for label, col in filter_options.items():
        if col in df_filtered.columns:
            options = sorted(df_filtered[col].dropna().unique())
            if options:
                if col == 'Recruitment':
                    default_value = ['Yes'] if 'Yes' in options else []
                    selected = st.sidebar.multiselect(label, options, default=default_value)
                else:
                    selected = st.sidebar.multiselect(label, options)

                if selected:
                    df_filtered = df_filtered[df_filtered[col].isin(selected)]
                    if not df_projects_filtered.empty and col in df_projects_filtered.columns:
                        df_projects_filtered = df_projects_filtered[df_projects_filtered[col].isin(selected)]
    
    with tab_charts:
        st.header(header_title)
        if df_filtered.empty:
            st.warning("Nenhuma meta de recrutamento encontrada para os filtros selecionados.")
        else:
            st.markdown("---")
            recruitment_goal = df_filtered['daily_recruitment_goal'].sum()
            allocated_goal = df_filtered['daily_allocated_goal'].sum()
            unique_quota_indices = df_filtered['original_quota_index'].unique()
            total_completes_needed = df_alloc_original.loc[unique_quota_indices, 'allocated_completes'].sum()

            kpi1, kpi2, kpi3 = st.columns(3)
            kpi1.metric(label="Recrutamento Necessário (Período)", value=f"{int(recruitment_goal):,}")
            kpi2.metric(label="Completes Necessários (Período)", value=f"{int(allocated_goal):,}")
            kpi3.metric(label="Completes Necessários (Total)", value=f"{int(total_completes_needed):,}")

            st.markdown("---")
            custom_colors = ['#25406e', '#6ba1ff', '#a1f1ff', '#5F9EA0', '#E6E6FA']
            st.subheader("Detalhamento da Meta de Recrutamento")
            
            charts_to_display = {
                'age_group': 'Demanda por Faixa Etária', 'Gender': 'Demanda por Gênero',
                'country': 'Demanda por País', 'SEL': 'Demanda por Classe Social (SEL)'
            }
            
            col1, col2 = st.columns(2)
            cols = [col1, col2, col1, col2] 
            
            chart_idx = 0
            for col_name, title in charts_to_display.items():
                if col_name in df_filtered.columns:
                    with cols[chart_idx % 4]:
                        grouped_data = df_filtered.groupby(col_name)['daily_recruitment_goal'].sum().sort_values(ascending=False).reset_index()
                        if col_name == 'Gender':
                            fig = px.pie(grouped_data, names=col_name, values='daily_recruitment_goal', title=title, hole=0.3, color_discrete_sequence=custom_colors)
                        else:
                            fig = px.bar(grouped_data, x=col_name, y='daily_recruitment_goal', title=title, color_discrete_sequence=custom_colors)
                        st.plotly_chart(fig, use_container_width=True)
                        chart_idx += 1

    with tab_tables:
        if df_report is not None:
            st.header("Dados do Relatório de Recrutamento")
            st.dataframe(df_report)
        
        st.header("Plano de Recrutamento Detalhado")
        display_cols = ['plan_date', 'daily_recruitment_goal', 'daily_allocated_goal', 'project_id', 'country', 'Recruitment', 'age_group', 'SEL', 'Gender', 'Region', 'Pessoas_Para_Recrutar', 'allocated_completes', 'DaystoDeliver']
        st.dataframe(df_filtered[[col for col in display_cols if col in df_filtered.columns]].reset_index(drop=True))
        st.info(f"Mostrando {len(df_filtered)} de {len(df_plan)} atividades planejadas.")

        if not df_projects_filtered.empty:
            st.header("Dados Originais dos Projetos")
            st.dataframe(df_projects_filtered)
            st.info(f"Mostrando {len(df_projects_filtered)} de {len(df_projects_original)} projetos.")
