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

# --- İSKELE KOORDİNAT SÖZLÜĞÜ ---
# (Analiz için en kritik iskelelerin yaklaşık koordinatları)
ISKELE_KOORDINAT = {
    'KADIKÖY': [40.9910, 29.0232], 'EMINÖNÜ': [41.0185, 28.9744],
    'BEŞIKTAŞ': [41.0422, 29.0083], 'ÜSKÜDAR': [41.0272, 29.0115],
    'KARAKÖY': [41.0215, 28.9755], 'BOSTANCI': [40.9515, 29.0944],
    'ADALAR': [40.8745, 29.1275], 'ORTAKÖY': [41.0474, 29.0253],
    'EMIRGAN': [41.1030, 29.0560], 'ARNAVUTKÖY': [41.0668, 29.0435],
    'BEBEK': [41.0772, 29.0445], 'KANLICA': [41.1010, 29.0655],
    'ÇENGELKÖY': [41.0510, 29.0520], 'KUZGUNCUK': [41.0360, 29.0305],
    'ANADOLU HISARI': [41.0830, 29.0665], 'RUMELI HISARI': [41.0850, 29.0570]
}


@st.cache_data
def veri_yukle():
    df = pd.read_csv("data/sadece_deniz_temmuz.csv", encoding='utf-8-sig', low_memory=False)
    df['station_poi_desc_cd'] = df['station_poi_desc_cd'].astype(str).replace('nan', 'Bilinmiyor')
    df['line_name'] = df['line_name'].astype(str).replace('nan', 'Bilinmiyor')
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

    df['varis_tahmini'] = df.apply(lambda x: varis_bul(x['line_name'], x['station_poi_desc_cd']), axis=1)
    return df


df = veri_yukle()

# --- NAVİGASYON ---
st.sidebar.title("🚢 Analiz Menüsü")
sayfa = st.sidebar.radio("Görünüm Seçin:", ["Klasik Hat Analizi", "Akış Matrisi", "Harita Üzerinde Yoğunluk"])
st.sidebar.divider()


# --- YARDIMCI FONKSİYON ---
def guvenli_liste(seri):
    liste = [str(x) for x in seri.unique() if str(x).lower() != 'nan']
    return sorted(liste)


# --- SAYFA 1: KLASİK (ÖNCEKİ KODUN AYNISI) ---
if sayfa == "Klasik Hat Analizi":
    st.sidebar.header("🔍 Operasyonel Filtreler")
    sec_yil = st.sidebar.selectbox("Yıl:", sorted(df['Yıl'].unique(), reverse=True))
    sec_gun = st.sidebar.slider("Günü Seçin:", 1, 31, 5)

    gun_df = df[(df['Yıl'] == sec_yil) & (df['Ay_Gun'] == sec_gun)]
    gun_adi = gun_df['Gun_Adi_Tr'].iloc[0] if not gun_df.empty else "Bilinmiyor"

    st.title(f"⚓ {sec_gun} Temmuz {sec_yil}, {gun_adi}")

    sec_kalkis = st.sidebar.selectbox("Kalkış İskelesi:", guvenli_liste(df['station_poi_desc_cd']))
    hatlar = guvenli_liste(df[df['station_poi_desc_cd'] == sec_kalkis]['line_name'])
    sec_hat = st.sidebar.selectbox("Varış Hattı:", hatlar)

    f_df = df[(df['Yıl'] == sec_yil) & (df['Ay_Gun'] == sec_gun) &
              (df['station_poi_desc_cd'] == sec_kalkis) & (df['line_name'] == sec_hat)]

    if not f_df.empty:
        g_df = f_df.groupby('transition_hour')['number_of_passenger'].sum().reset_index()
        st.plotly_chart(px.bar(g_df, x='transition_hour', y='number_of_passenger', template="plotly_dark",
                               color_continuous_scale="Reds", color='number_of_passenger'), use_container_width=True)
    else:
        st.warning("Veri bulunamadı.")

# --- SAYFA 2: MATRİS (ÖNCEKİ KODUN AYNISI) ---
elif sayfa == "Akış Matrisi":
    st.title(":blue[İskeleler Arası Akış Matrisi]")
    y_m = st.sidebar.selectbox("Yıl", sorted(df['Yıl'].unique(), reverse=True), key="ym")
    g_m = st.sidebar.slider("Gün", 1, 31, 5, key="gm")
    isk_m = st.sidebar.multiselect("İskeleler:", guvenli_liste(df['station_poi_desc_cd']),
                                   default=guvenli_liste(df['station_poi_desc_cd'])[:5])
    m_df = df[(df['Yıl'] == y_m) & (df['Ay_Gun'] == g_m) & (df['station_poi_desc_cd'].isin(isk_m))]
    if not m_df.empty:
        matris = m_df.pivot_table(index='station_poi_desc_cd', columns='varis_tahmini', values='number_of_passenger',
                                  aggfunc='sum').fillna(0)
        st.plotly_chart(px.imshow(matris, text_auto=True, color_continuous_scale="Blues"), use_container_width=True)

# --- SAYFA 3: HARİTA ÜZERİNDE YOĞUNLUK (YENİ) ---
else:
    st.title("🗺️ İstanbul Boğazı Güzergah Yoğunluk Haritası")

    st.sidebar.header("📍 Harita Filtreleri")
    h_yil = st.sidebar.selectbox("Yıl Seçin", sorted(df['Yıl'].unique(), reverse=True), key="hy")
    h_gun = st.sidebar.slider("Günü Seçin", 1, 31, 5, key="hg")
    h_saat = st.sidebar.slider("Saat Aralığı Seçin", 0, 23, 8)

    # Gün adını yakala
    h_gun_df = df[(df['Yıl'] == h_yil) & (df['Ay_Gun'] == h_gun)]
    h_gun_adi = h_gun_df['Gun_Adi_Tr'].iloc[0] if not h_gun_df.empty else "Bilinmiyor"

    st.markdown(f"**Tarih:** {h_gun} Temmuz {h_yil}, {h_gun_adi} | **Saat:** {h_saat}:00 - {h_saat + 1}:00")

    # Veriyi Filtrele
    h_filt_df = df[(df['Yıl'] == h_yil) & (df['Ay_Gun'] == h_gun) & (df['transition_hour'] == h_saat)]

    if not h_filt_df.empty:
        # Güzergah bazlı topla
        rota_df = h_filt_df.groupby(['station_poi_desc_cd', 'varis_tahmini'])['number_of_passenger'].sum().reset_index()
        rota_df = rota_df.sort_values(by='number_of_passenger', ascending=False)

        col_map, col_list = st.columns([2, 1])

        with col_map:
            st.subheader(f"En Yoğun 5 Güzergah (Görsel)")
            top_5_rota = rota_df.head(5)

            # Plotly Harita Hazırlığı
            fig_map = go.Figure()

            for i, row in top_5_rota.iterrows():
                start_node = row['station_poi_desc_cd']
                end_node = row['varis_tahmini']

                if start_node in ISKELE_KOORDINAT and end_node in ISKELE_KOORDINAT:
                    start_coords = ISKELE_KOORDINAT[start_node]
                    end_coords = ISKELE_KOORDINAT[end_node]

                    # Çizgi Ekleme
                    fig_map.add_trace(go.Scattermapbox(
                        mode="lines+markers",
                        lon=[start_coords[1], end_coords[1]],
                        lat=[start_coords[0], end_coords[0]],
                        marker={'size': 10},
                        line=dict(width=row['number_of_passenger'] / 100 + 2, color='red'),
                        hoverinfo='text',
                        text=f"{start_node} ➔ {end_node}<br>Yolcu: {row['number_of_passenger']}",
                        name=f"{start_node}-{end_node}"
                    ))

            fig_map.update_layout(
                mapbox_style="carto-positron",  # Sade İstanbul haritası
                mapbox_zoom=11,
                mapbox_center={"lat": 41.03, "lon": 29.02},
                margin={"r": 0, "t": 0, "l": 0, "b": 0},
                showlegend=False
            )
            st.plotly_chart(fig_map, use_container_width=True)

        with col_list:
            st.subheader("📋 Tüm Sefer Sıralaması")
            st.write("Yoğunluğa göre azalan liste:")
            list_df = rota_df.rename(
                columns={'station_poi_desc_cd': 'Kalkış', 'varis_tahmini': 'Varış', 'number_of_passenger': 'Yolcu'})
            st.dataframe(list_df, use_container_width=True, height=500)

    else:
        st.warning("Seçilen saatte sefer bulunamadı.")