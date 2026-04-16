import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import requests
import yfinance as yf
from datetime import datetime, date
import warnings
warnings.filterwarnings('ignore')
import time

# Configuração para deploy
st.set_page_config(page_title="Provisão ROI", layout="wide", initial_sidebar_state="expanded")

# Inicializa session_state corretamente
if 'btc_live' not in st.session_state:
    st.session_state.btc_live = False
if 'last_btc_update' not in st.session_state:
    st.session_state.last_btc_update = None

# ==================== APIs ao VIVO ====================

@st.cache_data(ttl=300)
def get_selic_live():
    """SELIC oficial BCB"""
    try:
        url = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados?formato=json&dataInicial=14/04/2016&dataFinal=14/04/2026"
        response = requests.get(url, timeout=10)
        data = response.json()
        df = pd.DataFrame(data)
        df['date'] = pd.to_datetime(df['data'])
        df['selic_rate'] = pd.to_numeric(df['valor'])
        return df[['date', 'selic_rate']].tail(60).reset_index(drop=True)
    except:
        dates = pd.date_range(end=date.today(), periods=60)
        return pd.DataFrame({'date': dates, 'selic_rate': [14.75]*60})

@st.cache_data(ttl=300)
def get_selic_complete_historic():
    """HISTÓRICO COMPLETO SELIC"""
    try:
        url = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados?formato=json&dataInicial=14/04/2016&dataFinal=14/04/2026"
        response = requests.get(url, timeout=10)
        data = response.json()
        df = pd.DataFrame(data)
        df['date'] = pd.to_datetime(df['data'])
        df['selic_rate'] = pd.to_numeric(df['valor'])
        df['year'] = df['date'].dt.year
        
        df_2020 = df[df['date'] >= '2020-01-01'].copy()
        return df.sort_values('date').reset_index(drop=True), df_2020.sort_values('date').reset_index(drop=True)
    except:
        return None, None

@st.cache_data(ttl=60)
def get_ibov_live():
    """IBOV ao vivo"""
    try:
        ibov = yf.download('^BVSP', period='3mo', progress=False)
        df = ibov[['Close']].reset_index()
        df.columns = ['date', 'ibov']
        df['date'] = pd.to_datetime(df['date'])
        return df.tail(60).reset_index(drop=True)
    except:
        dates = pd.date_range(end=date.today(), periods=60)
        return pd.DataFrame({'date': dates, 'ibov': [125000]*60})

@st.cache_data(ttl=120)
def get_crypto_live():
    """Crypto CoinGecko - BTC BRL"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        }
        url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=brl&include_24h_change=true"
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            btc_price = data['bitcoin']['brl']
            btc_change = data['bitcoin'].get('brl_24h_change', 0)
            
            st.session_state.btc_live = True
            st.session_state.last_btc_update = datetime.now().strftime("%H:%M:%S")
            
            return {
                'btc_brl': float(btc_price),
                'btc_change': float(btc_change)
            }
        return {'btc_brl': 350000, 'btc_change': 2.5}
    except:
        return {'btc_brl': 350000, 'btc_change': 2.5}

# ==================== CONFIGURAÇÕES RENDA FIXA ====================
RENDA_FIXA_CONFIG = {
    'Renda Fixa': {'yield': 0.98, 'name': 'Renda Fixa Geral'},
    'CDB': {'yield': 1.02, 'name': 'CDB 100%+ CDI'},
    'CDI': {'yield': 1.05, 'name': 'CDI'},
    'LCA': {'yield': 1.05, 'name': 'LCA Isento IR'},
    'Debêntures': {'yield': 1.15, 'name': 'Debêntures Incentivadas'}
}

# ==================== APP PRINCIPAL ====================
st.title("🌐 **Provisão de ROI - Mercado Financeiro**")
st.markdown("**🏦 SELIC | 📈 IBOV | ₿ BTC**")

if st.button("🔄 **ATUALIZAR Dados ao Vivo**", type="primary", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

# DADOS ao VIVO
col1, col2, col3, col4 = st.columns(4)
crypto_live = get_crypto_live()
selic_now = get_selic_live()
ibov_now = get_ibov_live()

btc_status = "🟢 LIVE" if st.session_state.btc_live else "⚪"
col1.metric("🏦 SELIC", f"{selic_now['selic_rate'].iloc[-1]:.2f}%")
col2.metric("📊 CDI Est.", f"{selic_now['selic_rate'].iloc[-1]*0.99:.2f}%")
col3.metric("📈 IBOV", f"{ibov_now['ibov'].iloc[-1]:,.0f}")
col4.metric(f"₿ BTC {btc_status}", f"R$ {crypto_live['btc_brl']:,.0f}", 
            delta=f"{crypto_live['btc_change']:.1f}%")

if st.session_state.last_btc_update:
    st.caption(f"₿ Atualizado: {st.session_state.last_btc_update}")

# SIDEBAR
st.sidebar.header("💼 **Seu Portfolio Renda Fixa**")
selic_value = st.sidebar.number_input("SELIC/Tesouro Direto (R$)", value=15000.0, min_value=0.0)

st.sidebar.markdown("---")
st.sidebar.header("📈 **Renda Fixa - Investimentos**")

rf_investimentos = {}
total_rf_investido = 0
total_titulos_renda_fixa = 0

# ATIVOS INDIVIDUAIS
ativos_individual = ['CDB', 'CDI', 'LCA', 'Debêntures']
for ativo in ativos_individual:
    config = RENDA_FIXA_CONFIG[ativo]
    with st.sidebar.expander(f"**{ativo}** ({config['name']})", expanded=False):
        col_a, col_b = st.columns(2)
        with col_a:
            valor_investido = st.number_input(
                f"Valor {ativo} (R$)", 
                value=0.0, min_value=0.0, key=f"valor_{ativo.lower()}", format="%.0f"
            )
        with col_b:
            qtd_titulos = st.number_input(
                f"Qtd. {ativo}", 
                value=0, min_value=0, step=1, key=f"qtd_{ativo.lower()}"
            )
        
        preco_medio = valor_investido / qtd_titulos if qtd_titulos > 0 else 0
        
        rf_investimentos[ativo] = {
            'valor': valor_investido,
            'titulos': qtd_titulos,
            'preco_medio': preco_medio
        }
        total_rf_investido += valor_investido
        total_titulos_renda_fixa += qtd_titulos

# RENDA FIXA GERAL
config_rf_geral = RENDA_FIXA_CONFIG['Renda Fixa']
preco_medio_rf_geral = total_rf_investido / total_titulos_renda_fixa if total_titulos_renda_fixa > 0 else 0

with st.sidebar.expander(f"**Renda Fixa** ({config_rf_geral['name']})", expanded=True):
    col_a, col_b = st.columns(2)
    col_a.metric("💰 Total Investido", f"R$ {total_rf_investido:,.0f}")
    col_b.metric("📊 Total Títulos", f"{total_titulos_renda_fixa:,}")
    st.caption(f"💰 Preço Médio Geral: R$ {preco_medio_rf_geral:,.2f}")

rf_investimentos['Renda Fixa'] = {
    'valor': total_rf_investido,
    'titulos': total_titulos_renda_fixa,
    'preco_medio': preco_medio_rf_geral
}

total_invested = selic_value + total_rf_investido

# PREVISÕES
st.markdown("---")
st.header("🎯 **Previsões Renda Fixa**")

horizons = {"1M (30 dias)": 30, "3M (90 dias)": 90, "6M (180 dias)": 180, "1A (365 dias)": 365}
results = []
selic_rate = selic_now['selic_rate'].iloc[-1]/100

for h_name, days in horizons.items():
    col1, col2, col3 = st.columns(3)
    total_return = 0
    
    # SELIC/Tesouro
    selic_ret = selic_value * (selic_rate * days/365)
    roi_selic = (selic_ret/selic_value*100) if selic_value else 0
    col1.metric(f"🏦 SELIC {h_name}", f"R$ {selic_ret:,.0f}", f"{roi_selic:.2f}%")
    total_return += selic_ret
    
    # RENDA FIXA
    rf_total_ret = 0
    for ativo, dados_invest in rf_investimentos.items():
        if dados_invest['valor'] > 0 and ativo in RENDA_FIXA_CONFIG:
            config = RENDA_FIXA_CONFIG[ativo]
            yield_rate = config['yield'] * selic_rate * (days/365)
            ret_ativo = dados_invest['valor'] * yield_rate
            rf_total_ret += ret_ativo
    
    roi_rf = (rf_total_ret/total_rf_investido*100) if total_rf_investido else 0
    col2.metric(f"💵 Renda Fixa {h_name}", f"R$ {rf_total_ret:,.0f}", f"{roi_rf:.2f}%")
    total_return += rf_total_ret
    
    # TOTAL
    roi_total = (total_return/total_invested*100) if total_invested else 0
    col3.metric("💎 **TOTAL**", f"R$ {total_return:,.0f}", f"{roi_total:.2f}%")
    
    results.append({
        'Horizonte': h_name, 'Total': total_return, 'ROI': roi_total,
        'SELIC': selic_ret, 'Renda_Fixa': rf_total_ret
    })

# RESULTADOS VISUAIS
st.markdown("---")
col1, col2 = st.columns(2)

with col1:
    st.subheader("📊 **Projeção Visual**")
    df_results = pd.DataFrame(results)
    fig = px.bar(df_results, x='Horizonte', y=['SELIC', 'Renda_Fixa', 'Total'], 
                title="Retorno Projetado - Renda Fixa",
                color_discrete_map={'SELIC': '#1f77b4', 'Renda_Fixa': '#ff7f0e', 'Total': '#2ca02c'})
    st.plotly_chart(fig, height=400, use_container_width=True)

with col2:
    st.subheader("💰 **Resumo Portfolio**")
    st.metric("Total Investido", f"R$ {total_invested:,.0f}")
    st.metric("SELIC/Tesouro", f"R$ {selic_value:,.0f}")
    st.metric("Renda Fixa", f"R$ {total_rf_investido:,.0f}")
    st.metric("**ROI 1 Ano**", f"{results[-1]['ROI']:.2f}%")
    st.metric("**Ganho 1A**", f"R$ {results[-1]['Total']:,.0f}")

# DETALHAMENTO
with st.expander("📋 **Detalhamento Renda Fixa**"):
    detalhe_data = []
    for ativo, config in RENDA_FIXA_CONFIG.items():
        inv = rf_investimentos.get(ativo, {'valor': 0, 'titulos': 0, 'preco_medio': 0})
        rent_1a = config['yield'] * selic_rate * 100
        detalhe_data.append({
            'Ativo': ativo,
            'Valor (R$)': f"{inv['valor']:,.0f}",
            'Títulos': inv['titulos'],
            'Preço Médio': f"R$ {inv['preco_medio']:,.2f}",
            'Yield x CDI': f"{config['yield']:.0%}",
            'Rentabilidade 1A': f"{rent_1a:.2f}%"
        })
    
    df_detalhe = pd.DataFrame(detalhe_data)
    st.dataframe(df_detalhe, use_container_width=True)

# HISTÓRICO SELIC (SIMPLIFICADO)
with st.expander("📈 **Histórico SELIC**", expanded=True):
    selic_complete, selic_2020 = get_selic_complete_historic()
    
    if selic_complete is not None:
        anos_disponiveis = sorted(selic_complete['year'].unique())
        selected_year = st.selectbox("🎯 Selecione o Ano:", anos_disponiveis, index=len(anos_disponiveis)-1)
        
        selic_year = selic_complete[selic_complete['year'] == selected_year]
        
        col1, col2 = st.columns([2, 1])
        with col1:
            fig_selic = px.line(selic_year, x='date', y='selic_rate',
                               title=f"🏦 SELIC {selected_year}",
                               markers=True)
            fig_selic.update_layout(height=300)
            st.plotly_chart(fig_selic, use_container_width=True)
        
        with col2:
            st.metric("📈 Máx", f"{selic_year['selic_rate'].max():.2f}%")
            st.metric("📉 Mín", f"{selic_year['selic_rate'].min():.2f}%")
            st.metric("📊 Média", f"{selic_year['selic_rate'].mean():.2f}%")

st.markdown("---")
st.success("✅ **Monitor ao vivo**: SELIC | IBOV | BTC\n✅ **Previsões precisas**: 1M/3M/6M/1A")
