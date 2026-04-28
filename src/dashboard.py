import streamlit as st
import pandas as pd
import plotly.express as px

# 1. SAYFA YAPILANDIRMASI
st.set_page_config(page_title="İBB Deniz Ulaşım Analizi", layout="wide")


# Veri Yükleme (Cache ile hızlandırılmış)
@st.cache_data
def veri_getir():
    # GitHub'daki işlenmiş veriyi okur
    df = pd.read_csv("data/sadece_deniz_temmuz.csv")
    df['transition_date'] = pd.to_datetime(df['transition_date'])
    df['station_poi_desc_cd'] = df['station_poi_desc_cd'].fillna("Bilinmiyor").astype(str)
    df['line_name'] = df['line_name'].fillna("Bilinmiyor").astype(str)

    # Matris sayfasında kullanılacak varış tahmini mantığı
    def varis_bul(line, origin):
        parts = line.replace("-", " ").split()
        remaining = [p for p in parts if p not in origin]
        return " ".join(remaining) if remaining else line

    df['varis_tahmini'] = df.apply(lambda x: varis_bul(x['line_name'], x['station_poi_desc_cd']), axis=1)
    return df


df = veri_getir()

# --- 2. SOL PANEL (NAVİGASYON VE FİLTRELER) ---
st.sidebar.title("🚢 Menü")
sayfa = st.sidebar.radio("Analiz Türü Seçin:", ["Klasik Hat Analizi (Favori)", "Akış Matrisi (Detaylı)"])

st.sidebar.divider()
st.sidebar.header("🔍 Filtreler")

# Tarih Seçimi (Tüm sayfalar için ortak)
max_tarih = df['transition_date'].max()
secilen_tarih = st.sidebar.date_input("Tarih Seçin", value=max_tarih)

# --- SAYFA 1: KLASİK HAT ANALİZİ (Senin sevdiğin sade görünüm) ---
if sayfa == "Klasik Hat Analizi (Favori)":
    gun_metni = secilen_tarih.strftime('%d %B %Y, %A')
    st.title(f":blue[{gun_metni}]")
    st.subheader("İskele Bazlı Varış İskelesi / Hattı Analizi")

    # İskele seçimi (Tekli seçim - Klasik mantık)
    iskeleler = sorted(df['station_poi_desc_cd'].unique())
    secilen_iskele = st.sidebar.selectbox("Başlangıç İskelesi Seçin:", iskeleler)

    # Veri Filtreleme
    f_df = df[(df['transition_date'].dt.date == secilen_tarih) & (df['station_poi_desc_cd'] == secilen_iskele)]

    if not f_df.empty:
        # KPI
        st.metric("Bu İskeleden Kalkan Toplam Yolcu", f"{f_df['number_of_passenger'].sum():,}")

        # Grafik
        grafik_data = f_df.groupby('line_name')['number_of_passenger'].sum().sort_values(ascending=True).reset_index()
        fig = px.bar(grafik_data, x='number_of_passenger', y='line_name',
                     orientation='h',
                     title=f"{secilen_iskele} İskelesinden Gidilen Yönler",
                     labels={'number_of_passenger': 'Yolcu Sayısı', 'line_name': 'Varış İskelesi / Hattı'},
                     color='number_of_passenger',
                     color_continuous_scale="Blues")
        st.plotly_chart(fig, use_container_width=True)

        # Tablo
        st.write("Veri Detayı:")
        st.dataframe(f_df[['transition_hour', 'line_name', 'number_of_passenger']].sort_values(by='transition_hour'),
                     use_container_width=True)
    else:
        st.warning("Seçilen tarihte bu iskeleden veri bulunamadı.")

# --- SAYFA 2: AKIŞ MATRİSİ (Modern O-D Görünümü) ---
else:
    st.title(":blue[İskeleler Arası Yolcu Akış Matrisi]")

    # Çoklu İskele seçimi
    iskeleler = sorted(df['station_poi_desc_cd'].unique())
    secilen_iskeler = st.sidebar.multiselect("Başlangıç İskelelerini Seçin:", iskeleler, default=iskeleler[:5])

    f_df = df[(df['transition_date'].dt.date == secilen_tarih) & (df['station_poi_desc_cd'].isin(secilen_iskeler))]

    if not f_df.empty:
        # Isı Haritası (Heatmap)
        matris = f_df.pivot_table(index='station_poi_desc_cd', columns='varis_tahmini',
                                  values='number_of_passenger', aggfunc='sum').fillna(0)

        fig_heat = px.imshow(matris, text_auto=True, color_continuous_scale="Blues",
                             labels=dict(x="Varış Güzergahı", y="Başlangıç İskelesi", color="Yolcu"),
                             aspect="auto")
        st.plotly_chart(fig_heat, use_container_width=True)

        # Saatlik Trend
        st.subheader("⏰ Saatlik Yolcu Yoğunluğu")
        saatlik = f_df.groupby('transition_hour')['number_of_passenger'].sum().reset_index()
        fig_line = px.line(saatlik, x='transition_hour', y='number_of_passenger', markers=True)
        st.plotly_chart(fig_line, use_container_width=True)
    else:
        st.error("Veri bulunamadı.")