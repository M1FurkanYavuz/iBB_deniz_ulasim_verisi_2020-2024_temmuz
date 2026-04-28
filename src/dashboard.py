import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os

# 1. TEMEL AYARLAR
st.set_page_config(page_title="İBB Deniz Analizi v3.3", layout="wide")

# Veri yolu kontrolü
DATA_PATH = "data/sadece_deniz_temmuz.csv"


# 2. HATA YAKALAYICI İLE VERİ YÜKLEME
@st.cache_data
def veri_yukle():
    if not os.path.exists(DATA_PATH):
        st.error(f"Dosya bulunamadı: {DATA_PATH}. Lütfen GitHub'da 'data' klasöründe bu dosyanın olduğundan emin olun.")
        return None
    try:
        df = pd.read_csv(DATA_PATH, encoding='utf-8-sig', low_memory=False)
        # Temizlik
        df['station_poi_desc_cd'] = df['station_poi_desc_cd'].astype(str).str.strip().str.upper()
        df['line_name'] = df['line_name'].astype(str).str.strip().str.upper()
        df['transition_date'] = pd.to_datetime(df['transition_date'], errors='coerce')
        df = df.dropna(subset=['transition_date'])
        df['Yıl'] = df['transition_date'].dt.year.astype(int)
        df['Ay_Gun'] = df['transition_date'].dt.day.astype(int)

        def varis_bul(line, origin):
            l, o = str(line).replace("-", " "), str(origin)
            res = [p for p in l.split() if p not in o]
            return " ".join(res) if res else l

        df['varis_tahmini'] = df.apply(lambda x: varis_bul(x['line_name'], x['station_poi_desc_cd']),
                                       axis=1).str.strip().str.upper()
        return df
    except Exception as e:
        st.error(f"Kod çalışırken bir hata oluştu: {e}")
        return None


df = veri_yukle()

# Eğer veri yüklenemediyse uygulamayı durdur
if df is None:
    st.warning("Veri yüklenemediği için uygulama başlatılamıyor.")
    st.stop()

# --- NAVİGASYON ---
st.sidebar.title("🚢 Menü")
sayfa = st.sidebar.radio("Görünüm Seçin:", ["Klasik Hat Analizi", "Akış Matrisi", "Harita Üzerinde Yoğunluk"])

# KOORDİNAT SÖZLÜĞÜ (Kısaltılmış test versiyonu)
ISKELE_KOORD = {
    'KADIKÖY': [40.9910, 29.0232], 'EMİNÖNÜ': [41.0185, 28.9744],
    'BEŞİKTAŞ': [41.0422, 29.0083], 'ÜSKÜDAR': [41.0272, 29.0115],
    'KARAKÖY': [41.0215, 28.9755], 'BOSTANCI': [40.9515, 29.0944]
}

# SAYFA MANTIKLARI (Basitleştirilmiş)
if sayfa == "Klasik Hat Analizi":
    st.title("⚓ Klasik Analiz")
    st.write("Veri yüklendi, filtreleri kullanarak başlayın.")
    # (Buraya önceki çalışan filtre kodlarını ekleyebilirsin)

elif sayfa == "Akış Matrisi":
    st.title("⚓ Matris")
    # (Buraya önceki çalışan matris kodlarını ekleyebilirsin)

else:
    st.title("🗺️ Harita")
    y = st.sidebar.selectbox("Yıl", sorted(df['Yıl'].unique(), reverse=True), key="yh")
    g = st.sidebar.slider("Gün", 1, 31, 5, key="gh")
    s = st.sidebar.slider("Saat", 0, 23, 8, key="sh")

    f_df = df[(df['Yıl'] == y) & (df['Ay_Gun'] == g) & (df['transition_hour'] == s)]

    if not f_df.empty:
        rota_df = f_df.groupby(['station_poi_desc_cd', 'varis_tahmini'])['number_of_passenger'].sum().reset_index()
        col1, col2 = st.columns([2, 1])
        with col1:
            fig = go.Figure(go.Scattermapbox(mode="markers", lat=[41.04], lon=[29.02], marker=dict(size=0)))
            fig.update_layout(mapbox=dict(style="carto-positron", center=dict(lat=41.04, lon=29.02), zoom=10),
                              margin=dict(t=0, b=0, l=0, r=0), height=500)
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            st.dataframe(rota_df.sort_values(by='number_of_passenger', ascending=False))