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


# 2. VERİ YÜKLEME (GÜVENLİ HALE GETİRİLDİ)
@st.cache_data
def veri_yukle():
    df = pd.read_csv("data/sadece_deniz_temmuz.csv", encoding='utf-8-sig')

    # --- KRİTİK TEMİZLİK: Hataları engelleyen kısım ---
    # Sütunlardaki boşlukları temizle ve her şeyi metne (str) çevir
    df['station_poi_desc_cd'] = df['station_poi_desc_cd'].fillna("Bilinmiyor").astype(str)
    df['line_name'] = df['line_name'].fillna("Bilinmiyor").astype(str)

    # Zaman bileşenleri
    df['transition_date'] = pd.to_datetime(df['transition_date'])
    df['Yıl'] = df['transition_date'].dt.year.fillna(0).astype(int)
    df['Ay_Gun'] = df['transition_date'].dt.day.fillna(0).astype(int)
    df['Gun_Adi_Tr'] = df['transition_date'].dt.day_name().map(GUN_ESLESTIRME).fillna("Bilinmiyor")

    # Varış tahmini (Matris sayfası için)
    def varis_bul(line, origin):
        line_str = str(line).replace("-", " ")
        parts = line_str.split()
        remaining = [p for p in parts if p not in str(origin)]
        return " ".join(remaining) if remaining else line_str

    df['varis_tahmini'] = df.apply(lambda x: varis_bul(x['line_name'], x['station_poi_desc_cd']), axis=1)

    return df


# Veriyi yükle
try:
    df = veri_yukle()
except Exception as e:
    st.error(f"Veri yükleme hatası: {e}")
    st.stop()

# --- 3. NAVİGASYON (SIDEBAR) ---
st.sidebar.title("🚢 Analiz Menüsü")
sayfa_secimi = st.sidebar.radio("Görünüm Seçin:", ["Klasik Hat Analizi (Kırmızı)", "Akış Matrisi (Mavi)"])
st.sidebar.divider()

# --- SAYFA 1: KLASİK HAT ANALİZİ ---
if sayfa_secimi == "Klasik Hat Analizi (Kırmızı)":
    st.sidebar.header("🔍 Operasyonel Filtreler")

    # Yıl seçimi (Sıralama hatası engellendi)
    yillar = sorted([int(y) for y in df['Yıl'].unique() if y > 0], reverse=True)
    secilen_yil = st.sidebar.selectbox("Yıl Seçin:", yillar)

    secilen_gun = st.sidebar.slider("Temmuz Ayının Hangi Günü?", 1, 31, 5)

    # Dinamik gün ismi bulma
    ornek_df = df[(df['Yıl'] == secilen_yil) & (df['Ay_Gun'] == secilen_gun)]
    secilen_gun_adi = ornek_df['Gun_Adi_Tr'].iloc[0] if not ornek_df.empty else "Bilinmiyor"

    # İskele seçimi (Sıralama hatası engellendi)
    tum_iskeleler = sorted([str(i) for i in df['station_poi_desc_cd'].unique()])
    secilen_kalkis = st.sidebar.selectbox("Kalkış İskelesi (Nereden?):", tum_iskeleler)

    # Hat seçimi
    hatlar_df = df[df['station_poi_desc_cd'] == secilen_kalkis]
    tum_hatlar = sorted([str(h) for h in hatlar_df['line_name'].unique()])
    secilen_hat = st.sidebar.selectbox("Varış Hattı (Nereye?):", tum_hatlar)

    # Filtreleme
    sonuc_df = df[(df['Yıl'] == secilen_yil) & (df['Ay_Gun'] == secilen_gun) &
                  (df['station_poi_desc_cd'] == secilen_kalkis) & (df['line_name'] == secilen_hat)]

    st.title(f"⚓ {secilen_gun} Temmuz {secilen_yil}, {secilen_gun_adi}")
    st.info(f"**Analiz Edilen Rota:** {secilen_hat}")

    if not sonuc_df.empty:
        grafik_df = sonuc_df.groupby('transition_hour')['number_of_passenger'].sum().reset_index()

        col1, col2, col3 = st.columns(3)
        col1.metric("Günlük Toplam Yolcu", f"{grafik_df['number_of_passenger'].sum():,}")

        # Zirve saat bulma
        if not grafik_df.empty:
            pik_saat = grafik_df.loc[grafik_df['number_of_passenger'].idxmax(), 'transition_hour']
            col2.metric("Zirve Saat", f"{pik_saat}:00")

        col3.metric("Haftanın Günü", secilen_gun_adi)

        # GRAFİK
        fig = px.bar(grafik_df, x='transition_hour', y='number_of_passenger',
                     labels={'transition_hour': 'Saat', 'number_of_passenger': 'Yolcu Sayısı'},
                     text_auto='.2s', color='number_of_passenger',
                     color_continuous_scale='Reds', template="plotly_dark")
        fig.update_layout(xaxis=dict(tickmode='linear', tick0=0, dtick=1))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Bu seçim için veri bulunamadı.")

# --- SAYFA 2: AKIŞ MATRİSİ ---
else:
    st.title(":blue[İskeleler Arası Yolcu Akış Matrisi]")

    # Sidebar filtreleri (Key kullanarak çakışma engellendi)
    yillar_m = sorted([int(y) for y in df['Yıl'].unique() if y > 0], reverse=True)
    secilen_yil_m = st.sidebar.selectbox("Yıl Seçin", yillar_m, key="y2")
    secilen_gun_m = st.sidebar.slider("Gün Seçin", 1, 31, 5, key="g2")

    iskeler_m = sorted([str(i) for i in df['station_poi_desc_cd'].unique()])
    secilen_iskeler = st.sidebar.multiselect("Başlangıç İskeleleri:", iskeler_m, default=iskeler_m[:5])

    f_df = df[(df['Yıl'] == secilen_yil_m) & (df['Ay_Gun'] == secilen_gun_m) & (
        df['station_poi_desc_cd'].isin(secilen_iskeler))]

    if not f_df.empty:
        st.subheader(f"📊 {secilen_gun_m} Temmuz {secilen_yil_m} Matrisi")
        matris = f_df.pivot_table(index='station_poi_desc_cd', columns='varis_tahmini',
                                  values='number_of_passenger', aggfunc='sum').fillna(0)

        fig_heat = px.imshow(matris, text_auto=True, color_continuous_scale="Blues", aspect="auto")
        st.plotly_chart(fig_heat, use_container_width=True)
    else:
        st.info("Filtreleri kullanarak veri görüntüleyebilirsiniz.")