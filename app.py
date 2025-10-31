import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Configuração e Carregamento de Dados (Cache)
# Esta função lerá o arquivo CSV APENAS uma vez para performance
@st.cache_data
def load_data():
    # Altere 'regression_data.csv' para o nome do seu arquivo, se for diferente
    try:
        df = pd.read_csv('regression_data.csv')
    except FileNotFoundError:
        st.error("Erro: O arquivo 'regression_data.csv' não foi encontrado. Certifique-se de que ele está no mesmo diretório do app.py.")
        st.stop()
    
    # A lógica de tratamento de dados permanece, mas adaptada ao CSV
    # Certifica-se de que a coluna DayName está ordenada corretamente, assumindo que existe
    day_order = ['Segunda', 'Terca', 'Quarta', 'Quinta', 'Sexta', 'Sabado', 'Domingo']
    if 'DayName' in df.columns:
        df['DayName'] = pd.Categorical(df['DayName'], categories=day_order, ordered=True)
    
    return df

df = load_data()

# 2. Título da Aplicação
st.title("Análise de Regressão por Grupo (Streamlit)")
st.subheader("Filtros Cumulativos para Análise Exploratória")

# 3. Criação dos Filtros (Widgets Streamlit)
ALL = 'Todos'
country_options = [ALL] + df['Country'].unique().tolist()
recruit_options = [ALL] + df['recruit_translation'].unique().tolist()
# Adaptação para garantir a ordem correta dos dias no filtro
day_options = [ALL] + df['DayName'].cat.categories.tolist()

col1, col2, col3 = st.columns(3)

with col1:
    selected_country = st.selectbox('País', country_options)

with col2:
    selected_recruit = st.selectbox('Recrutamento', recruit_options)

with col3:
    selected_day = st.selectbox('Dia da Semana', day_options)


# 4. Lógica de Filtragem Cumulativa
dff = df.copy()

if selected_country != ALL:
    dff = dff[dff['Country'] == selected_country]
if selected_recruit != ALL:
    dff = dff[dff['recruit_translation'] == selected_recruit]
if selected_day != ALL:
    dff = dff[dff['DayName'] == selected_day]

# 5. Geração e Exibição do Gráfico (Plotly)
fig = px.scatter(
    dff,
    x='Panelists_Coef',
    y='N_Day',
    color='Country',
    symbol='DayName',
    hover_data=['recruit_translation'],
    title=f"Dados Selecionados (N={len(dff)})",
    labels={
        'Panelists_Coef': 'Coeficiente de Panelists (Impacto no Spend)',
        'N_Day': 'Nº de Observações (N_Day)'
    }
)

st.plotly_chart(fig, use_container_width=True)

# Opcional: Mostrar o DataFrame filtrado
st.markdown("---")
st.caption("Tabela de Dados Filtrada:")
st.dataframe(dff[['Country', 'recruit_translation', 'DayName', 'Panelists_Coef', 'N_Day']])
