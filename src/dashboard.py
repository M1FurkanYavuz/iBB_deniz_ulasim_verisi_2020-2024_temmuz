import streamlit as st
import pandas as pd
import plotly.express as px

# 1. SAYFA AYARLARI
st.set_page_config(page_title="İBB Deniz Ulaşım Analizi", layout="wide")

# Gün isimlerini Türkçeleştirmek için sözlük
GUN_ESLESTIRME = {
    'Monday': 'Pazartesi', 'Tuesday': 'Salı', 'Wednesday': 'Çarşamba',
    'Thursday': 'Perşembe', 'Friday': 'Cuma', 'Saturday': 'Cumartesi', 'Sunday': 'Pazar'
}


# 2. VERİ YÜKLEME (CACHE)
@st.cache_data
def veri_yukle():
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

    # Sayfa 2 (Matris) için varış tahmini
    def varis_bul(line, origin):
        parts = line.replace("-", " ").split()
        remaining = [p for p in parts if p not in origin]
        return " ".join(remaining) if remaining else line

    df['varis_tahmini'] = df.apply(lambda x: varis_bul(x['line_name'], x['station_poi_desc_cd']), axis=1)

    return df


df = veri_yukle()

# --- 3. NAVİGASYON (SIDEBAR) ---
st.sidebar.title("🚢 Analiz Menüsü")
sayfa_secimi = st.sidebar.radio("Görünüm Seçin:", ["Klasik Hat Analizi (Kırmızı)", "Akış Matrisi (Mavi)"])
st.sidebar.divider()

# --- SAYFA 1: KLASİK HAT ANALİZİ (SENİN KODUN) ---
if sayfa_secimi == "Klasik Hat Analizi (Kırmızı)":
    st.sidebar.header("🔍 Operasyonel Filtreler")

    secilen_yil = st.sidebar.selectbox("Yıl Seçin:", sorted(df['Yıl'].unique(), reverse=True))
    secilen_gun = st.sidebar.slider("Temmuz Ayının Hangi Günü?", 1, 31, 5)

    # Gün ismini bulma
    ornek_satir = df[(df['Yıl'] == secilen_yil) & (df['Ay_Gun'] == secilen_gun)].iloc[0:1]
    secilen_gun_adi = ornek_satir['Gun_Adi_Tr'].values[0] if not ornek_satir.empty else "Bilinmiyor"

    tum_iskeleler = sorted(df['station_poi_desc_cd'].unique())
    secilen_kalkis = st.sidebar.selectbox("Kalkış İskelesi (Nereden?):", tum_iskeleler)

    hatlar = sorted(df[df['station_poi_desc_cd'] == secilen_kalkis]['line_name'].unique())
    secilen_hat = st.sidebar.selectbox("Varış Hattı (Nereye?):", hatlar)

    # Analiz Mantığı
    mask = (df['Yıl'] == secilen_yil) & (df['Ay_Gun'] == secilen_gun) & \
           (df['station_poi_desc_cd'] == secilen_kalkis) & (df['line_name'] == secilen_hat)
    sonuc_df = df[mask]

    st.title(f"⚓ {secilen_gun} Temmuz {secilen_yil}, {secilen_gun_adi}")
    st.info(f"**Analiz Edilen Rota:** {secilen_hat}")

    if not sonuc_df.empty:
        grafik_df = sonuc_df.groupby('transition_hour')['number_of_passenger'].sum().reset_index()

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Günlük Toplam Yolcu", f"{grafik_df['number_of_passenger'].sum():,}")
        with col2:
            pik_saat = grafik_df.loc[grafik_df['number_of_passenger'].idxmax(), 'transition_hour']
            st.metric("Zirve Saat", f"{pik_saat}:00")
        with col3:
            st.metric("Haftanın Günü", secilen_gun_adi)

        st.subheader("🕒 Saatlik Yolcu Yoğunluğu")
        fig = px.bar(grafik_df, x='transition_hour', y='number_of_passenger',
                     labels={'transition_hour': 'Saat', 'number_of_passenger': 'Yolcu Sayısı'},
                     text_auto='.2s', color='number_of_passenger',
                     color_continuous_scale='Reds', template="plotly_dark")
        fig.update_layout(xaxis=dict(tickmode='linear', tick0=0, dtick=1))
        st.plotly_chart(fig, use_container_width=True)

        with st.expander("📊 Ham Verileri İncele"):
            st.dataframe(grafik_df.rename(columns={'transition_hour': 'Saat', 'number_of_passenger': 'Toplam Yolcu'}))
    else:
        st.warning(f"Seçtiğiniz tarihte ({secilen_gun_adi}) bu rota için veri bulunamadı.")

# --- SAYFA 2: AKIŞ MATRİSİ (AKIŞ ODAKLI GÖRÜNÜM) ---
else:
    st.title(":blue[İskeleler Arası Yolcu Akış Matrisi]")

    # Filtreler
    secilen_yil_m = st.sidebar.selectbox("Yıl Seçin:", sorted(df['Yıl'].unique(), reverse=True), key="yil_m")
    secilen_gun_m = st.sidebar.slider("Günü Seçin:", 1, 31, 5, key="gun_m")

    tum_iskeler_m = sorted(df['station_poi_desc_cd'].unique())
    secilen_baslangic = st.sidebar.multiselect("Başlangıç İskelelerini Seçin:", tum_iskeler_m,
                                               default=tum_iskeler_m[:5])

    f_df = df[(df['Yıl'] == secilen_yil_m) & (df['Ay_Gun'] == secilen_gun_m) & (
        df['station_poi_desc_cd'].isin(secilen_baslangic))]

    if not f_df.empty:
        st.subheader(f"📊 {secilen_gun_m} Temmuz {secilen_yil_m} - Yolcu Geçiş Matrisi")
        matris = f_df.pivot_table(index='station_poi_desc_cd', columns='varis_tahmini',
                                  values='number_of_passenger', aggfunc='sum').fillna(0)

        fig_heat = px.imshow(matris, text_auto=True, color_continuous_scale="Blues",
                             labels=dict(x="Varış Güzergahı", y="Başlangıç İskelesi", color="Yolcu"),
                             aspect="auto")
        st.plotly_chart(fig_heat, use_container_width=True)

        # Ek bir grafik: En yoğun rotalar
        st.subheader("🔝 En Yoğun 5 Akış")
        akis_ozet = f_df.groupby(['station_poi_desc_cd', 'varis_tahmini'])['number_of_passenger'].sum().nlargest(
            5).reset_index()
        st.table(akis_ozet)
    else:
        st.error("Veri bulunamadı.")