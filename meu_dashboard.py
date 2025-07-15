import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(layout="wide")

# O @st.cache_data foi removido para garantir que o código de tratamento de dados seja sempre executado.
def load_and_process_data(file_path):
    df = pd.read_csv(file_path)
    
    def extract_quota_data(row):
        try:
            # Garante que a tupla tenha 4 elementos, preenchendo com None se faltar
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
    
    df_clean = df[['pais', 'age_group', 'SEL', 'Gender', 'Region', 'Pessoas_Para_Recrutar']].copy()
    
    df_clean['Pessoas_Para_Recrutar'] = pd.to_numeric(df_clean['Pessoas_Para_Recrutar'], errors='coerce')
    df_clean.dropna(subset=['Pessoas_Para_Recrutar', 'age_group', 'SEL', 'Gender'], inplace=True)
    df_clean['Pessoas_Para_Recrutar'] = df_clean['Pessoas_Para_Recrutar'].astype(int)
    
    return df_clean

df_processed = load_and_process_data('GeminiCheck.csv')

st.title("Recruitment Dashboard")

st.sidebar.header("Filters")

# --- Lógica de Filtros ---
# Filtra o dataframe principal uma única vez ao final

# Filtro de País
countries = sorted(df_processed['pais'].unique())
selected_countries = st.sidebar.multiselect('Select Country(s)', countries, default=countries)

# Filtro de Faixa Etária
age_groups = sorted(df_processed['age_group'].unique())
selected_age_groups = st.sidebar.multiselect('Select Age Group(s)', age_groups, default=age_groups)

# Filtro de Gênero
genders = sorted(df_processed['Gender'].unique())
selected_genders = st.sidebar.multiselect('Select Gender(s)', genders, default=genders)

# Filtro de SEL
sels = sorted(df_processed['SEL'].unique())
selected_sels = st.sidebar.multiselect('Select SEL(s)', sels, default=sels)

# Aplica todos os filtros de uma vez para criar o dataframe final
df_filtered = df_processed[
    df_processed['pais'].isin(selected_countries) &
    df_processed['age_group'].isin(selected_age_groups) &
    df_processed['Gender'].isin(selected_genders) &
    df_processed['SEL'].isin(selected_sels)
]

st.header("Recruitment Overview")

if df_filtered.empty:
    st.warning("No data available for the selected filters.")
else:
    col1, col2 = st.columns(2)

    with col1:
        by_age = df_filtered.groupby('age_group')['Pessoas_Para_Recrutar'].sum().sort_values(ascending=False).reset_index()
        fig_age = px.bar(
            by_age, x='age_group', y='Pessoas_Para_Recrutar',
            title='Demand by Age Group',
            labels={'age_group': 'Age Group', 'Pessoas_Para_Recrutar': 'People to Recruit'},
            template='plotly_dark', color_discrete_sequence=px.colors.qualitative.Pastel
        )
        st.plotly_chart(fig_age, use_container_width=True)

    with col2:
        by_gender = df_filtered.groupby('Gender')['Pessoas_Para_Recrutar'].sum().reset_index()
        fig_gender = px.pie(
            by_gender, names='Gender', values='Pessoas_Para_Recrutar',
            title='Demand by Gender', hole=0.3,
            template='plotly_dark', color_discrete_sequence=px.colors.qualitative.Pastel
        )
        st.plotly_chart(fig_gender, use_container_width=True)

    col3, col4 = st.columns(2)

    with col3:
        by_country = df_filtered.groupby('pais')['Pessoas_Para_Recrutar'].sum().sort_values(ascending=False).reset_index()
        fig_country = px.bar(
            by_country, x='pais', y='Pessoas_Para_Recrutar',
            title='Demand by Country',
            labels={'pais': 'Country', 'Pessoas_Para_Recrutar': 'People to Recruit'},
            template='plotly_dark', color_discrete_sequence=px.colors.qualitative.Vivid
        )
        st.plotly_chart(fig_country, use_container_width=True)
        
    with col4:
        by_sel = df_filtered.groupby('SEL')['Pessoas_Para_Recrutar'].sum().sort_values(ascending=False).reset_index()
        fig_sel = px.bar(
            by_sel, x='SEL', y='Pessoas_Para_Recrutar',
            title='Demand by Socioeconomic Level (SEL)',
            labels={'SEL': 'Socioeconomic Level', 'Pessoas_Para_Recrutar': 'People to Recruit'},
            template='plotly_dark', color_discrete_sequence=px.colors.qualitative.Vivid
        )
        st.plotly_chart(fig_sel, use_container_width=True)

    st.write("Detailed Data:")
    st.dataframe(df_filtered)

    # Função de download precisa estar dentro do else para não dar erro se df_filtered estiver vazio
    @st.cache_data
    def convert_df_to_csv(df):
        return df.to_csv(index=False).encode('utf-8')

    csv = convert_df_to_csv(df_filtered)

    st.download_button(
       label="Download data as CSV",
       data=csv,
       file_name='filtered_recruitment_data.csv',
       mime='text/csv',
    )
