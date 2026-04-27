import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Sayfa Ayarları
st.set_page_config(page_title="Deniz Taksi Stratejik Analiz", layout="wide")

# Gün isimlerini Türkçeleştirmek için sözlük
GUN_ESLESTIRME = {
    'Monday': 'Pazartesi', 'Tuesday': 'Salı', 'Wednesday': 'Çarşamba',
    'Thursday': 'Perşembe', 'Friday': 'Cuma', 'Saturday': 'Cumartesi', 'Sunday': 'Pazar'
}


# 2. Veri Yükleme Fonksiyonu
@st.cache_data
def veri_yukle():
    # Karakter onarımı yapılmış dosyayı oku
    df = pd.read_csv("data/sadece_deniz_temmuz.csv", encoding='utf-8-sig')

    # Temizlik işlemleri
    df = df.dropna(subset=['station_poi_desc_cd', 'line_name'])
    df['station_poi_desc_cd'] = df['station_poi_desc_cd'].astype(str)
    df['line_name'] = df['line_name'].astype(str)

    # Zaman bileşenleri
    df['transition_date'] = pd.to_datetime(df['transition_date'])
    df['Yıl'] = df['transition_date'].dt.year
    df['Ay_Gun'] = df['transition_date'].dt.day
    df['Gun_Adi_Tr'] = df['transition_date'].dt.day_name().map(GUN_ESLESTIRME)

    return df


df = veri_yukle()

# --- SIDEBAR (Filtre Paneli) ---
st.sidebar.header("🔍 Operasyonel Filtreler")

# Yıl ve Gün Seçimi
secilen_yil = st.sidebar.selectbox("Yıl Seçin:", sorted(df['Yıl'].unique(), reverse=True))
secilen_gun = st.sidebar.slider("Temmuz Ayının Hangi Günü?", 1, 31, 5)

# Seçilen günün ismini dinamik olarak bulalım
ornek_satir = df[(df['Yıl'] == secilen_yil) & (df['Ay_Gun'] == secilen_gun)].iloc[0:1]
secilen_gun_adi = ornek_satir['Gun_Adi_Tr'].values[0] if not ornek_satir.empty else "Bilinmiyor"

# İskele ve Hat (O-D) Seçimi
tum_iskeleler = sorted(df['station_poi_desc_cd'].unique())
secilen_kalkis = st.sidebar.selectbox("Kalkış İskelesi (Nereden?):", tum_iskeleler)

hatlar = sorted(df[df['station_poi_desc_cd'] == secilen_kalkis]['line_name'].unique())
secilen_hat = st.sidebar.selectbox("Varış İskelesi (Nereye?):", hatlar)

# --- ANALİZ MANTIĞI ---
mask = (df['Yıl'] == secilen_yil) & (df['Ay_Gun'] == secilen_gun) & \
       (df['station_poi_desc_cd'] == secilen_kalkis) & (df['line_name'] == secilen_hat)
sonuc_df = df[mask]

# --- EKRAN TASARIMI ---
st.title(f"⚓ {secilen_gun} Temmuz {secilen_yil}, {secilen_gun_adi}")
st.info(f"**Analiz Edilen Rota:** {secilen_hat}")

if not sonuc_df.empty:
    # KPI Kartları
    col1, col2, col3 = st.columns(3)

    # Veriyi grafik için topluyoruz (Agregasyon)
    # Bu adım, o karmaşık kutucukları birleştirip tek bir toplam oluşturur
    grafik_df = sonuc_df.groupby('transition_hour')['number_of_passenger'].sum().reset_index()

    with col1:
        toplam_yolcu = grafik_df['number_of_passenger'].sum()
        st.metric("Günlük Toplam Yolcu", f"{toplam_yolcu:,}")

    with col2:
        pik_saat = grafik_df.loc[grafik_df['number_of_passenger'].idxmax(), 'transition_hour']
        st.metric("Zirve Saat", f"{pik_saat}:00")

    with col3:
        st.metric("Haftanın Günü", secilen_gun_adi)

    # GRAFİK: Saatlik Akış
    st.subheader("🕒 Saatlik Yolcu Yoğunluğu")

    fig = px.bar(grafik_df,
                 x='transition_hour',
                 y='number_of_passenger',
                 labels={'transition_hour': 'Saat', 'number_of_passenger': 'Yolcu Sayısı'},
                 text_auto='.2s',  # Sütun tepesine toplamı yazar (Örn: 1.2k)
                 color='number_of_passenger',
                 color_continuous_scale='Reds',
                 template="plotly_dark")

    # X eksenini her saati gösterecek şekilde sabitleyelim
    fig.update_layout(xaxis=dict(tickmode='linear', tick0=0, dtick=1))
    st.plotly_chart(fig, use_container_width=True)

    # Detaylı Veri Tablosu
    with st.expander("📊 Bu Grafiğin Ham Verilerini İncele"):
        st.dataframe(
            grafik_df.rename(columns={'transition_hour': 'Saat', 'number_of_passenger': 'Toplam Yolcu'}).reset_index(
                drop=True))

else:
    st.warning(f"Seçtiğiniz tarihte ({secilen_gun_adi}) bu rota için veri bulunamadı.")
    st.write("İpucu: Hattın o gün seferi olmayabilir veya veri setinde kayıt yoktur.")