import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# 1. SAYFA AYARLARI
st.set_page_config(page_title="İBB Deniz Ulaşım Analizi", layout="wide")

GUN_ESLESTIRME = {
    'Monday': 'Pazartesi', 'Tuesday': 'Salı', 'Wednesday': 'Çarşamba',
    'Thursday': 'Perşembe', 'Friday': 'Cuma', 'Saturday': 'Cumartesi', 'Sunday': 'Pazar'
}

# --- AKILLI KOORDİNAT SÖZLÜĞÜ ---
ISKELE_KOORDINAT = {
    'KADIKÖY': [40.9910, 29.0232], 'EMİNÖNÜ': [41.0185, 28.9744],
    'BEŞİKTAŞ': [41.0422, 29.0083], 'ÜSKÜDAR': [41.0272, 29.0115],
    'KARAKÖY': [41.0215, 28.9755], 'BOSTANCI': [40.9515, 29.0944],
    'ADALAR': [40.8745, 29.1275], 'ORTAKÖY': [41.0474, 29.0253],
    'EMİRGAN': [41.1030, 29.0560], 'ARNAVUTKÖY': [41.0668, 29.0435],
    'BEBEK': [41.0772, 29.0445], 'KANLICA': [41.1010, 29.0655],
    'ÇENGELKÖY': [41.0510, 29.0520], 'KUZGUNCUK': [41.0360, 29.0305],
    'ANADOLU HİSARI': [41.0830, 29.0665], 'RUMELİ HİSARI': [41.0850, 29.0570],
    'KABATAŞ': [41.0333, 28.9933], 'SARIYER': [41.1663, 29.0573],
    'BEYKOZ': [41.1345, 29.0912], 'KANDİLLİ': [41.0754, 29.0588],
    'ÇUBUKLU': [41.1085, 29.0825], 'İSTİNYE': [41.1135, 29.0555],
    'PAŞABAHÇE': [41.1177, 29.0934], 'HAREM': [41.0115, 29.0105],
    'SİRKECİ': [41.0158, 28.9774], 'YENİKAPI': [40.9995, 28.9535],
    'MODA': [40.9785, 29.0245], 'MALTEPE': [40.9165, 29.1315], 'PENDİK': [40.8765, 29.2315]
}


def koord_bul(isim):
    """İsim içinde anahtar kelimeyi arayan akıllı fonksiyon"""
    ust_isim = str(isim).upper()
    for durak in ISKELE_KOORDINAT:
        if durak in ust_isim:
            return ISKELE_KOORDINAT[durak]
    return None


@st.cache_data
def veri_yukle():
    df = pd.read_csv("data/sadece_deniz_temmuz.csv", encoding='utf-8-sig', low_memory=False)
    df['station_poi_desc_cd'] = df['station_poi_desc_cd'].astype(str).str.strip().str.upper()
    df['line_name'] = df['line_name'].astype(str).str.strip().str.upper()
    df['transition_date'] = pd.to_datetime(df['transition_date'], errors='coerce')
    df = df.dropna(subset=['transition_date'])
    df['Yıl'] = df['transition_date'].dt.year.astype(int)
    df['Ay_Gun'] = df['transition_date'].dt.day.astype(int)
    df['Gun_Adi_Tr'] = df['transition_date'].dt.day_name().map(GUN_ESLESTIRME)

    def varis_bul(line, origin):
        l, o = str(line).replace("-", " "), str(origin)
        parts = l.split()
        res = [p for p in parts if p not in o]
        return " ".join(res) if res else l

    df['varis_tahmini'] = df.apply(lambda x: varis_bul(x['line_name'], x['station_poi_desc_cd']),
                                   axis=1).str.strip().str.upper()
    return df


df = veri_yukle()

# --- NAVİGASYON ---
st.sidebar.title("🚢 Menü")
sayfa = st.sidebar.radio("Görünüm Seçin:", ["Klasik Hat Analizi", "Akış Matrisi", "Harita Üzerinde Yoğunluk"])
st.sidebar.divider()


def guvenli_liste(seri):
    return sorted([str(x) for x in seri.unique() if str(x).lower() != 'nan'])


# --- SAYFA 1: KLASİK ---
if sayfa == "Klasik Hat Analizi":
    st.title("⚓ Klasik Hat Analizi")
    y = st.sidebar.selectbox("Yıl", sorted(df['Yıl'].unique(), reverse=True))
    g = st.sidebar.slider("Gün", 1, 31, 5)
    kalkis = st.sidebar.selectbox("Kalkış İskelesi:", guvenli_liste(df['station_poi_desc_cd']))
    hat = st.sidebar.selectbox("Varış Hattı:", guvenli_liste(df[df['station_poi_desc_cd'] == kalkis]['line_name']))

    f_df = df[(df['Yıl'] == y) & (df['Ay_Gun'] == g) & (df['station_poi_desc_cd'] == kalkis) & (df['line_name'] == hat)]
    if not f_df.empty:
        g_df = f_df.groupby('transition_hour')['number_of_passenger'].sum().reset_index()
        st.plotly_chart(px.bar(g_df, x='transition_hour', y='number_of_passenger', color_continuous_scale="Reds",
                               color='number_of_passenger', template="plotly_dark"), use_container_width=True)

# --- SAYFA 2: MATRİS ---
elif sayfa == "Akış Matrisi":
    st.title("⚓ Akış Matrisi")
    y = st.sidebar.selectbox("Yıl", sorted(df['Yıl'].unique(), reverse=True), key="y_m")
    g = st.sidebar.slider("Gün", 1, 31, 5, key="g_m")
    isk = st.sidebar.multiselect("İskeleler:", guvenli_liste(df['station_poi_desc_cd']),
                                 default=guvenli_liste(df['station_poi_desc_cd'])[:5])
    f_df = df[(df['Yıl'] == y) & (df['Ay_Gun'] == g) & (df['station_poi_desc_cd'].isin(isk))]
    if not f_df.empty:
        matris = f_df.pivot_table(index='station_poi_desc_cd', columns='varis_tahmini', values='number_of_passenger',
                                  aggfunc='sum').fillna(0)
        st.plotly_chart(px.imshow(matris, text_auto=True, color_continuous_scale="Blues"), use_container_width=True)

# --- SAYFA 3: HARİTA ---
else:
    st.title("🗺️ İstanbul Boğazı Güzergah Yoğunluk Haritası")
    y = st.sidebar.selectbox("Yıl", sorted(df['Yıl'].unique(), reverse=True), key="y_h")
    g = st.sidebar.slider("Gün", 1, 31, 5, key="g_h")
    s = st.sidebar.slider("Saat", 0, 23, 8, key="s_h")

    f_df = df[(df['Yıl'] == y) & (df['Ay_Gun'] == g) & (df['transition_hour'] == s)]

    if not f_df.empty:
        rota_df = f_df.groupby(['station_poi_desc_cd', 'varis_tahmini'])['number_of_passenger'].sum().reset_index()
        rota_df = rota_df.sort_values(by='number_of_passenger', ascending=False)

        col_m, col_l = st.columns([2, 1])
        with col_m:
            fig = go.Figure(go.Scattermapbox(mode="markers", lat=[41.04], lon=[29.02], marker=dict(size=0)))
            cizilen = 0
            eksik = set()
            for _, row in rota_df.head(5).iterrows():
                s_c, e_c = koord_bul(row['station_poi_desc_cd']), koord_bul(row['varis_tahmini'])
                if s_c and e_c:
                    fig.add_trace(go.Scattermapbox(mode="lines+markers", lon=[s_c[1], e_c[1]], lat=[s_c[0], e_c[0]],
                                                   marker=dict(size=10, color='red'),
                                                   line=dict(width=row['number_of_passenger'] / 100 + 1, color='red'),
                                                   text=f"{row['station_poi_desc_cd']} -> {row['varis_tahmini']}<br>Yolcu: {row['number_of_passenger']}",
                                                   hoverinfo='text'))
                    cizilen += 1
                else:
                    if not s_c: eksik.add(row['station_poi_desc_cd'])
                    if not e_c: eksik.add(row['varis_tahmini'])

            fig.update_layout(mapbox=dict(style="carto-positron", center=dict(lat=41.04, lon=29.02), zoom=10.5),
                              margin=dict(t=0, b=0, l=0, r=0), height=600, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
            if cizilen == 0: st.error("Harita verisi bulunamadı. Eksik iskeleler: " + ", ".join(eksik))
        with col_l:
            st.dataframe(rota_df.rename(
                columns={'station_poi_desc_cd': 'Kalkış', 'varis_tahmini': 'Varış', 'number_of_passenger': 'Yolcu'}),
                         height=550)