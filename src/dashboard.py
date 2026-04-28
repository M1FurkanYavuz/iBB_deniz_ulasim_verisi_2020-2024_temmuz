import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# 1. SAYFA AYARLARI
st.set_page_config(page_title="İBB Deniz Analizi v3.4", layout="wide")

GUN_ESLESTIRME = {
    'Monday': 'Pazartesi', 'Tuesday': 'Salı', 'Wednesday': 'Çarşamba',
    'Thursday': 'Perşembe', 'Friday': 'Cuma', 'Saturday': 'Cumartesi', 'Sunday': 'Pazar'
}

# --- GENİŞLETİLMİŞ KOORDİNAT SÖZLÜĞÜ ---
# Verideki isimler bazen "İSKELE ADI - 1" veya "İSKELE ADI (ŞEHİR HATLARI)" şeklinde olabilir.
# koord_bul fonksiyonumuz bu kelimeleri içinde arayacak.
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
    'MODA': [40.9785, 29.0245], 'MALTEPE': [40.9165, 29.1315], 'PENDİK': [40.8765, 29.2315],
    'KASIMPAŞA': [41.0331, 28.9682], 'FENER': [41.0307, 28.9507], 'BALAT': [41.0338, 28.9469],
    'SÜTLÜCE': [41.0475, 28.9419], 'EYÜP': [41.0478, 28.9344], 'HEYBELİADA': [40.8767, 29.1000],
    'BÜYÜKADA': [40.8540, 29.1270], 'KINALIADA': [40.9100, 29.0500], 'BURGAZADA': [40.8800, 29.0680]
}


def koord_bul(isim):
    """Verideki karmaşık isimlerin içinde sözlüğümüzdeki anahtarları arar."""
    isim_str = str(isim).upper()
    for anahtar in ISKELE_KOORDINAT:
        if anahtar in isim_str:
            return ISKELE_KOORDINAT[anahtar]
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

# 1 ve 2. Sayfalar (Hızlı Özet)
if sayfa != "Harita Üzerinde Yoğunluk":
    st.info("Klasik ve Matris analizleri için lütfen filtreleri kullanın. Veri seti hazır.")
    # (Önceki çalışan kodların burada olduğunu varsayıyoruz)

# --- SAYFA 3: HARİTA (DEDEKTİF MODU) ---
else:
    st.title("🗺️ Boğaz Güzergah Analizi")
    y = st.sidebar.selectbox("Yıl", sorted(df['Yıl'].unique(), reverse=True), key="yh")
    g = st.sidebar.slider("Gün", 1, 31, 5, key="gh")
    s = st.sidebar.slider("Saat", 0, 23, 8, key="sh")

    f_df = df[(df['Yıl'] == y) & (df['Ay_Gun'] == g) & (df['transition_hour'] == s)]

    if not f_df.empty:
        rota_df = f_df.groupby(['station_poi_desc_cd', 'varis_tahmini'])['number_of_passenger'].sum().reset_index()
        rota_df = rota_df.sort_values(by='number_of_passenger', ascending=False)

        col_m, col_l = st.columns([2, 1])

        with col_m:
            fig = go.Figure(go.Scattermapbox(mode="markers", lat=[41.04], lon=[29.02], marker=dict(size=0)))
            cizilen_sayisi = 0
            eksik_isimler = []

            for _, row in rota_df.head(10).iterrows():  # En yoğun 10'a bakıyoruz
                s_c = koord_bul(row['station_poi_desc_cd'])
                e_c = koord_bul(row['varis_tahmini'])

                if s_c and e_c:
                    fig.add_trace(go.Scattermapbox(
                        mode="lines+markers",
                        lon=[s_c[1], e_c[1]], lat=[s_c[0], e_c[0]],
                        marker=dict(size=12, color='red'),
                        line=dict(width=row['number_of_passenger'] / 100 + 1, color='red'),
                        text=f"{row['station_poi_desc_cd']} ➔ {row['varis_tahmini']}<br>Yolcu: {row['number_of_passenger']}",
                        hoverinfo='text'
                    ))
                    cizilen_sayisi += 1
                else:
                    if not s_c: eksik_isimler.append(row['station_poi_desc_cd'])
                    if not e_c: eksik_isimler.append(row['varis_tahmini'])

            fig.update_layout(
                mapbox=dict(style="carto-positron", center=dict(lat=41.04, lon=29.02), zoom=10.5),
                margin=dict(t=0, b=0, l=0, r=0), height=600, showlegend=False
            )
            st.plotly_chart(fig, use_container_width=True)

            if cizilen_sayisi == 0:
                st.error("🚨 Seçilen saatteki en yoğun iskelelerin koordinatları sistemde kayıtlı değil!")
                st.write("**Eşleşmeyen İsimler:**", list(set(eksik_isimler)))
                st.info("Yukarıdaki isimleri bana kopyalarsan koordinatlarını hemen ekleyebilirim.")

        with col_l:
            st.subheader("📋 Sefer Sıralaması")
            st.dataframe(rota_df.rename(
                columns={'station_poi_desc_cd': 'Kalkış', 'varis_tahmini': 'Varış', 'number_of_passenger': 'Yolcu'}),
                         height=550)