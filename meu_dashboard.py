import streamlit as st
import pandas as pd
import os
import plotly.express as px
import ast

st.set_page_config(layout="wide")

st.title("Painel de Controle de Recrutamento")

ALLOC_FILE = 'GeminiCheck.csv'
PROJECTS_FILE = 'Projects.csv'

@st.cache_data
def load_and_process_data(alloc_path, projects_path):
    if not os.path.exists(alloc_path) or not os.path.exists(projects_path):
        st.error(f"ERRO: Um ou ambos os arquivos não foram encontrados. Verifique 'Completes.csv' e 'Projects.csv'.")
        return None, None
    
    df_alloc = pd.read_csv(alloc_path)
    df_projects = pd.read_csv(projects_path)

    if 'cotas' not in df_alloc.columns or 'resultado_cota' not in df_alloc.columns:
        st.error("ERRO: Colunas 'cotas' ou 'resultado_cota' não encontradas em Completes.csv.")
        return df_alloc, df_projects
        
    def extract_dynamic_data(row):
        try:
            keys = ast.literal_eval(row['cotas'])
            values = ast.literal_eval(row['resultado_cota'])
            
            if isinstance(keys, (list, tuple)) and isinstance(values, (list, tuple)) and len(keys) == len(values):
                return dict(zip(keys, values))
            else:
                return {}
        except Exception:
            return {}

    dynamic_data = df_alloc.apply(extract_dynamic_data, axis=1)
    dynamic_df = pd.DataFrame(dynamic_data.tolist(), index=df_alloc.index)
    
    df_alloc_processed = pd.concat([df_alloc, dynamic_df], axis=1)
    df_alloc_processed.rename(columns={'country': 'pais'}, inplace=True)
    
    if 'Region' in df_alloc_processed.columns:
        # Usamos .astype(str) para garantir que a comparação com '0' funcione
        df_alloc_processed['Region'] = df_alloc_processed['Region'].astype(str).replace('0', 'Qualquer Região')
    
    if 'SEL' in df_alloc_processed.columns:
        df_alloc_processed['SEL'] = df_alloc_processed['SEL'].astype(str).replace('0', 'País sem SEL')
    # --- FIM DAS NOVAS SUBSTITUIÇÕES ---
    
    df_alloc_processed['project_id'] = df_alloc_processed['project_id'].astype(str)
    df_projects['project_id'] = df_projects['project_id'].astype(str)

    return df_alloc_processed, df_projects

# --- ETAPA 3: Carregar os dados ---
df_alloc_processed, df_projects = load_and_process_data(ALLOC_FILE, PROJECTS_FILE)

# --- ETAPA 4: Filtros na barra lateral ---
if df_alloc_processed is not None:
    st.sidebar.header("Filtros")
    
    df_filtered = df_alloc_processed.copy()
    df_projects_filtered = df_projects.copy()

    all_projects = sorted(df_alloc_processed['project_id'].unique())
    selected_projects = st.sidebar.multiselect('1. Projeto(s)', all_projects)
    
    if selected_projects:
        df_filtered = df_filtered[df_filtered['project_id'].isin(selected_projects)]
        df_projects_filtered = df_projects_filtered[df_projects_filtered['project_id'].isin(selected_projects)]

    all_countries = sorted(df_filtered['pais'].dropna().unique())
    selected_countries = st.sidebar.multiselect('2. País(es)', all_countries)
    
    if selected_countries:
        df_filtered = df_filtered[df_filtered['pais'].isin(selected_countries)]
        if 'pais' in df_projects_filtered.columns:
            df_projects_filtered = df_projects_filtered[df_projects_filtered['pais'].isin(selected_countries)]
        elif 'country' in df_projects_filtered.columns:
            df_projects_filtered = df_projects_filtered[df_projects_filtered['country'].isin(selected_countries)]
    
    all_regions = sorted(df_filtered['Region'].dropna().unique())
    selected_regions = st.sidebar.multiselect('3. Região(ões)', all_regions)

    if selected_regions:
        df_filtered = df_filtered[df_filtered['Region'].isin(selected_regions)]

    all_age_groups = sorted(df_filtered['age_group'].dropna().unique())
    selected_age_groups = st.sidebar.multiselect('4. Faixa Etária', all_age_groups)

    if selected_age_groups:
        df_filtered = df_filtered[df_filtered['age_group'].isin(selected_age_groups)]

    all_genders = sorted(df_filtered['Gender'].dropna().unique())
    selected_genders = st.sidebar.multiselect('5. Gênero', all_genders)

    if selected_genders:
        df_filtered = df_filtered[df_filtered['Gender'].isin(selected_genders)]
        
    # --- INÍCIO DA ADIÇÃO DO FILTRO DE SEL ---
    all_sels = sorted(df_filtered['SEL'].dropna().unique())
    selected_sels = st.sidebar.multiselect('6. Classe Social (SEL)', all_sels)

    if selected_sels:
        df_filtered = df_filtered[df_filtered['SEL'].isin(selected_sels)]
    # --- FIM DA ADIÇÃO DO FILTRO DE SEL ---

# --- ETAPA 5: Criar as abas do dashboard ---
if df_alloc_processed is not None and df_projects is not None:
    tab_graficos, tab_tabelas = st.tabs(["Gráficos de Cotas", "Tabelas de Dados"])

    with tab_graficos:
        st.header("Visão Gráfica da Demanda por Recrutamento")
        
        if df_filtered.empty:
            st.warning("Nenhum dado encontrado para a combinação de filtros selecionada.")
        else:
            st.markdown("---")
            total_recrutar = df_filtered['Pessoas_Para_Recrutar'].sum()
            total_alocados = df_filtered['allocated_completes'].sum()
            kpi1, kpi2 = st.columns(2)
            kpi1.metric(label="Painelistas Necessários", value=f"{total_recrutar:,}")
            kpi2.metric(label="Completes Necessários (Alocados)", value=f"{total_alocados:,}")
            st.markdown("---")
            
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
        st.header("Dados de Alocação")
        st.dataframe(df_filtered)
        st.info(f"Mostrando {len(df_filtered)} de {len(df_alloc_processed)} linhas.")

        st.header("Dados das Cotas Iniciais")
        st.dataframe(df_projects_filtered)
        st.info(f"Mostrando {len(df_projects_filtered)} de {len(df_projects)} linhas.")
