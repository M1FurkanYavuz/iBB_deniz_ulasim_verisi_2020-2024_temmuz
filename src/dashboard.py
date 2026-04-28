import streamlit as st
import pandas as pd
import plotly.express as px

# 1. SAYFA AYARLARI
st.set_page_config(page_title="İBB Deniz Ulaşım Analizi", layout="wide")

# Gün isimleri sözlüğü
GUN_ESLESTIRME = {
    'Monday': 'Pazartesi', 'Tuesday': 'Salı', 'Wednesday': 'Çarşamba',
    'Thursday': 'Perşembe', 'Friday': 'Cuma', 'Saturday': 'Cumartesi', 'Sunday': 'Pazar'
}


# 2. VERİ YÜKLEME
@st.cache_data
def veri_yukle():
    df = pd.read_csv("data/sadece_deniz_temmuz.csv", encoding='utf-8-sig', low_memory=False)

    # Veri Temizliği
    df['station_poi_desc_cd'] = df['station_poi_desc_cd'].astype(str).str.strip().str.upper()
    df['line_name'] = df['line_name'].astype(str).str.strip().str.upper()
    df['transition_date'] = pd.to_datetime(df['transition_date'], errors='coerce')
    df = df.dropna(subset=['transition_date'])

    df['Yıl'] = df['transition_date'].dt.year.astype(int)
    df['Ay_Gun'] = df['transition_date'].dt.day.astype(int)
    df['Gun_Adi_Tr'] = df['transition_date'].dt.day_name().map(GUN_ESLESTIRME)

    # Varış Tahmini Mantığı (Matris ve Liste için)
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
st.sidebar.title("🚢 Analiz Menüsü")
sayfa = st.sidebar.radio("Görünüm Seçin:", ["Klasik Hat Analizi", "Akış Matrisi", "Yoğunluk Sıralaması (Liste)"])
st.sidebar.divider()

# --- SAYFA 1: KLASİK HAT ANALİZİ ---
if sayfa == "Klasik Hat Analizi":
    st.sidebar.header("🔍 Operasyonel Filtreler")

    sec_yil = st.sidebar.selectbox("Yıl Seçin:", sorted(df['Yıl'].unique(), reverse=True))
    sec_gun = st.sidebar.slider("Temmuz Ayının Hangi Günü?", 1, 31, 5)

    # Gün adını bul
    gun_df = df[(df['Yıl'] == sec_yil) & (df['Ay_Gun'] == sec_gun)]
    gun_adi = gun_df['Gun_Adi_Tr'].iloc[0] if not gun_df.empty else "Bilinmiyor"

    st.title(f"⚓ {sec_gun} Temmuz {sec_yil}, {gun_adi}")

    # İskele ve Hat Filtreleri
    iskeler = sorted(df['station_poi_desc_cd'].unique())
    sec_kalkis = st.sidebar.selectbox("Kalkış İskelesi (Nereden?):", iskeler)

    hatlar = sorted(df[df['station_poi_desc_cd'] == sec_kalkis]['line_name'].unique())
    sec_hat = st.sidebar.selectbox("Varış Hattı (Nereye?):", hatlar)

    f_df = df[(df['Yıl'] == sec_yil) & (df['Ay_Gun'] == sec_gun) &
              (df['station_poi_desc_cd'] == sec_kalkis) & (df['line_name'] == sec_hat)]

    if not f_df.empty:
        g_df = f_df.groupby('transition_hour')['number_of_passenger'].sum().reset_index()

        col1, col2, col3 = st.columns(3)
        col1.metric("Günlük Toplam Yolcu", f"{g_df['number_of_passenger'].sum():,}")
        col2.metric("Zirve Saat", f"{g_df.loc[g_df['number_of_passenger'].idxmax(), 'transition_hour']}:00")
        col3.metric("Haftanın Günü", gun_adi)

        st.subheader("🕒 Saatlik Yolcu Yoğunluğu")
        fig = px.bar(g_df, x='transition_hour', y='number_of_passenger',
                     text_auto='.2s', color='number_of_passenger',
                     color_continuous_scale='Reds', template="plotly_dark")
        fig.update_layout(xaxis=dict(tickmode='linear', tick0=0, dtick=1))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Seçilen kriterlerde veri bulunamadı.")

# --- SAYFA 2: AKIŞ MATRİSİ ---
elif sayfa == "Akış Matrisi":
    st.title(":blue[İskeleler Arası Yolcu Akış Matrisi]")

    y_m = st.sidebar.selectbox("Yıl Seçin", sorted(df['Yıl'].unique(), reverse=True), key="ym")
    g_m = st.sidebar.slider("Gün Seçin", 1, 31, 5, key="gm")
    isk_m = st.sidebar.multiselect("Başlangıç İskelelerini Seçin:", sorted(df['station_poi_desc_cd'].unique()),
                                   default=sorted(df['station_poi_desc_cd'].unique())[:5])

    m_df = df[(df['Yıl'] == y_m) & (df['Ay_Gun'] == g_m) & (df['station_poi_desc_cd'].isin(isk_m))]

    if not m_df.empty:
        matris = m_df.pivot_table(index='station_poi_desc_cd', columns='varis_tahmini',
                                  values='number_of_passenger', aggfunc='sum').fillna(0)

        st.subheader(f"📊 {g_m} Temmuz {y_m} Geçiş Yoğunluğu")
        fig_heat = px.imshow(matris, text_auto=True, color_continuous_scale="Blues", aspect="auto")
        st.plotly_chart(fig_heat, use_container_width=True)
    else:
        st.info("Filtreleri kullanarak matrisi oluşturabilirsiniz.")

# --- SAYFA 3: YOĞUNLUK SIRALAMASI (LİSTE) ---
else:
    st.title("📋 Sefer Yoğunluk Sıralaması")

    y_l = st.sidebar.selectbox("Yıl Seçin", sorted(df['Yıl'].unique(), reverse=True), key="yl")
    g_l = st.sidebar.slider("Gün Seçin", 1, 31, 5, key="gl")
    s_l = st.sidebar.slider("Saat Seçin", 0, 23, 8, key="sl")

    # Gün adını bul
    gun_df_l = df[(df['Yıl'] == y_l) & (df['Ay_Gun'] == g_l)]
    gun_adi_l = gun_df_l['Gun_Adi_Tr'].iloc[0] if not gun_df_l.empty else "Bilinmiyor"

    st.markdown(f"**Seçili Zaman:** {g_l} Temmuz {y_l}, {gun_adi_l} | Saat {s_l}:00 - {s_l + 1}:00")

    l_df = df[(df['Yıl'] == y_l) & (df['Ay_Gun'] == g_l) & (df['transition_hour'] == s_l)]

    if not l_df.empty:
        # Veriyi grupla ve sırala
        liste_df = l_df.groupby(['station_poi_desc_cd', 'varis_tahmini'])['number_of_passenger'].sum().reset_index()
        liste_df = liste_df.sort_values(by='number_of_passenger', ascending=False)
        liste_df.columns = ['Kalkış İskelesi', 'Varış Güzergahı', 'Toplam Yolcu']

        # İlk 5'i vurgula
        st.subheader("🔝 En Yoğun 5 Sefer")
        st.table(liste_df.head(5))

        st.divider()

        # Tüm listeyi tablo olarak ver
        st.subheader("📊 Tüm Seferlerin Listesi")
        st.dataframe(liste_df, use_container_width=True, height=600)
    else:
        st.warning("Seçilen saat diliminde herhangi bir sefer kaydı bulunamadı.")