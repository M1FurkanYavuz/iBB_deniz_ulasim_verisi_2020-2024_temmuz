import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="İBB Deniz Ulaşım Analizi", layout="wide")

# --- GENİŞLETİLMİŞ VE TEMİZLENMİŞ KOORDİNAT LİSTESİ ---
# Verideki isimler genellikle büyük harf ve Türkçe karakterlidir.
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
    'ÇUBUKLU': [41.1085, 29.0825]
}


@st.cache_data
def veri_yukle():
    df = pd.read_csv("data/sadece_deniz_temmuz.csv", encoding='utf-8-sig', low_memory=False)
    # İsimleri standardize et (Büyük harf ve temiz boşluk)
    df['station_poi_desc_cd'] = df['station_poi_desc_cd'].astype(str).str.strip().str.upper()
    df['line_name'] = df['line_name'].astype(str).str.strip().str.upper()

    df['transition_date'] = pd.to_datetime(df['transition_date'], errors='coerce')
    df = df.dropna(subset=['transition_date'])
    df['Yıl'] = df['transition_date'].dt.year
    df['Ay_Gun'] = df['transition_date'].dt.day

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
sayfa = st.sidebar.radio("Görünüm Seçin:", ["Klasik Hat Analizi", "Akış Matrisi", "Harita Üzerinde Yoğunluk"])

# --- SAYFA 1 & 2 (Aynen Kalıyor) ---
if sayfa == "Klasik Hat Analizi":
    st.title("⚓ Klasik Hat Analizi")
    # ... (Önceki kodun aynısı buraya gelecek)

elif sayfa == "Akış Matrisi":
    st.title("⚓ Akış Matrisi")
    # ... (Önceki kodun aynısı buraya gelecek)

# --- SAYFA 3: HARİTA (GÜNCELLENDİ) ---
else:
    st.title("🗺️ İstanbul Boğazı Güzergah Yoğunluk Haritası")

    h_yil = st.sidebar.selectbox("Yıl", sorted(df['Yıl'].unique(), reverse=True), key="hy")
    h_gun = st.sidebar.slider("Gün", 1, 31, 5, key="hg")
    h_saat = st.sidebar.slider("Saat", 0, 23, 8, key="hs")

    h_filt_df = df[(df['Yıl'] == h_yil) & (df['Ay_Gun'] == h_gun) & (df['transition_hour'] == h_saat)]

    if not h_filt_df.empty:
        rota_df = h_filt_df.groupby(['station_poi_desc_cd', 'varis_tahmini'])['number_of_passenger'].sum().reset_index()
        rota_df = rota_df.sort_values(by='number_of_passenger', ascending=False)

        col_map, col_list = st.columns([2, 1])

        with col_map:
            fig_map = go.Figure()

            # 1. TEMEL HARİTA KATMANI (Her zaman görünmesi için boş noktalar ekliyoruz)
            fig_map.add_trace(go.Scattermapbox(
                lat=[41.01, 41.10], lon=[28.95, 29.10],
                mode='markers', marker=dict(size=0, opacity=0), showlegend=False
            ))

            cizilen_rota_sayisi = 0
            for i, row in rota_df.head(10).iterrows():  # En yoğun 10 rotayı deneyelim
                start, end = row['station_poi_desc_cd'], row['varis_tahmini']

                if start in ISKELE_KOORDINAT and end in ISKELE_KOORDINAT:
                    s_coords, e_coords = ISKELE_KOORDINAT[start], ISKELE_KOORDINAT[end]

                    fig_map.add_trace(go.Scattermapbox(
                        mode="lines+markers",
                        lon=[s_coords[1], e_coords[1]],
                        lat=[s_coords[0], e_coords[0]],
                        marker={'size': 8, 'color': 'darkblue'},
                        line=dict(width=(row['number_of_passenger'] / 100) + 1, color='red'),
                        text=f"{start} -> {end}<br>Yolcu: {row['number_of_passenger']}",
                        hoverinfo='text',
                        name=f"{start}-{end}"
                    ))
                    cizilen_rota_sayisi += 1

            fig_map.update_layout(
                mapbox_style="carto-positron",
                mapbox_zoom=10.5,
                mapbox_center={"lat": 41.04, "lon": 29.02},
                margin={"r": 0, "t": 0, "l": 0, "b": 0},
                height=600,
                showlegend=False
            )

            if cizilen_rota_sayisi == 0:
                st.info(
                    "Seçilen saatteki iskeleler koordinat listesinde bulunamadı. Lütfen farklı bir saat seçin veya koordinat listesini güncelleyin.")

            st.plotly_chart(fig_map, use_container_width=True)

        with col_list:
            st.subheader("📋 Sefer Sıralaması")
            st.dataframe(rota_df.rename(
                columns={'station_poi_desc_cd': 'Kalkış', 'varis_tahmini': 'Varış', 'number_of_passenger': 'Yolcu'}),
                         use_container_width=True, height=550)
    else:
        st.warning("Bu tarih ve saatte sefer verisi bulunamadı.")