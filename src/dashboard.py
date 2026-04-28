import streamlit as st
import pandas as pd
import plotly.express as px

# 1. SAYFA AYARLARI
st.set_page_config(page_title="İBB Deniz Akış Analizi", layout="wide")


@st.cache_data
def veri_getir():
    df = pd.read_csv("data/sadece_deniz_temmuz.csv")
    df['transition_date'] = pd.to_datetime(df['transition_date'])
    # Veri temizliği (Hata almamak için)
    df['station_poi_desc_cd'] = df['station_poi_desc_cd'].fillna("Bilinmiyor").astype(str)
    df['line_name'] = df['line_name'].fillna("Bilinmiyor").astype(str)
    return df


df = veri_getir()

# --- 2. SOL PANEL (FİLTRELER) ---
st.sidebar.header("🔍 Akış Filtreleri")

# Tarih Seçimi
max_tarih = df['transition_date'].max()
secilen_tarih = st.sidebar.date_input("Analiz Tarihi", value=max_tarih)

# İskele Seçimi (Başlangıç Noktaları)
tum_iskeler = sorted(df['station_poi_desc_cd'].unique())
secilen_iskeler = st.sidebar.multiselect(
    "Başlangıç İskelelerini Seçin",
    options=tum_iskeler,
    default=["KADIKÖY", "ÜSKÜDAR", "BEŞİKTAŞ"] if "KADIKÖY" in tum_iskeler else tum_iskeler[:3]
)

# Veriyi Filtreleme
mask = (df['transition_date'].dt.date == secilen_tarih) & (df['station_poi_desc_cd'].isin(secilen_iskeler))
filtrelenmis_df = df[mask]

# --- 3. ANA SAYFA VE ÖZET ---
st.title(f":blue[İskeleler Arası Yolcu Akış Analizi]")
st.markdown(f"**Seçilen Başlangıç Noktaları:** {', '.join(secilen_iskeler)}")

# KPI Metrikleri
toplam_akıs = filtrelenmis_df['number_of_passenger'].sum()
en_aktif_hat = filtrelenmis_df.groupby('line_name')[
    'number_of_passenger'].sum().idxmax() if not filtrelenmis_df.empty else "Veri Yok"

c1, c2 = st.columns(2)
c1.metric("Toplam Çıkış Yapan Yolcu", f"{toplam_akıs:,}")
col2_label = "En Çok Yolcu Alan Güzergah"
c2.metric(col2_label, en_aktif_hat)

st.divider()

# --- 4. GÖRSELLEŞTİRME (AKIŞ ODAKLI) ---

col_left, col_right = st.columns([1, 1])

with col_left:
    st.subheader("🚢 İskelelerden Hatlara Dağılım (Nereye Gittiler?)")
    if not filtrelenmis_df.empty:
        # Hangi iskeleden hangi hatta ne kadar yolcu gitti?
        akis_df = filtrelenmis_df.groupby(['station_poi_desc_cd', 'line_name'])[
            'number_of_passenger'].sum().reset_index()

        fig_akis = px.bar(akis_df,
                          x='number_of_passenger',
                          y='line_name',
                          color='station_poi_desc_cd',
                          title="İskele Bazlı Hat Dağılımı",
                          labels={'number_of_passenger': 'Yolcu Sayısı', 'line_name': 'Varış Hattı / Güzergah',
                                  'station_poi_desc_cd': 'Çıkış İskelesi'},
                          orientation='h',
                          height=600)
        fig_akis.update_layout(barmode='stack', yaxis={'categoryorder': 'total ascending'})
        st.plotly_chart(fig_akis, use_container_width=True)
    else:
        st.info("Seçilen kriterlerde veri bulunamadı.")

with col_right:
    st.subheader("⏰ Hat Bazlı Saatlik Değişim")
    if not filtrelenmis_df.empty:
        # En yoğun 5 hattı seçelim ki grafik karışmasın
        top_5_hat = filtrelenmis_df.groupby('line_name')['number_of_passenger'].sum().nlargest(5).index
        saatlik_akis = \
        filtrelenmis_df[filtrelenmis_df['line_name'].isin(top_5_hat)].groupby(['transition_hour', 'line_name'])[
            'number_of_passenger'].sum().reset_index()

        fig_saat = px.line(saatlik_akis,
                           x='transition_hour',
                           y='number_of_passenger',
                           color='line_name',
                           markers=True,
                           title="En Yoğun 5 Hattın Günlük Seyri",
                           labels={'transition_hour': 'Saat', 'number_of_passenger': 'Yolcu Sayısı',
                                   'line_name': 'Hat'})
        st.plotly_chart(fig_saat, use_container_width=True)

# --- 5. DETAYLI VERİ TABLOSU ---
with st.expander("📊 Ham Veri Kesiti (Seçili Filtrelere Göre)"):
    st.dataframe(filtrelenmis_df.sort_values(by='number_of_passenger', ascending=False), use_container_width=True)