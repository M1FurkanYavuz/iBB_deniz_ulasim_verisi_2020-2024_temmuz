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


# 2. VERİ YÜKLEME (EN RADİKAL TEMİZLİK)
@st.cache_data
def veri_yukle():
    # Dosyayı oku (Düşük bellek uyarısını kapatmak için low_memory=False)
    df = pd.read_csv("data/sadece_deniz_temmuz.csv", encoding='utf-8-sig', low_memory=False)

    # 1. Aşama: Boşlukları hemen yok et ve tipleri sabitle
    df['station_poi_desc_cd'] = df['station_poi_desc_cd'].astype(str).replace('nan', 'Bilinmiyor').fillna('Bilinmiyor')
    df['line_name'] = df['line_name'].astype(str).replace('nan', 'Bilinmiyor').fillna('Bilinmiyor')

    # 2. Aşama: Tarih işlemleri
    df['transition_date'] = pd.to_datetime(df['transition_date'], errors='coerce')
    df = df.dropna(subset=['transition_date'])  # Tarihi bozuk olanları at

    df['Yıl'] = df['transition_date'].dt.year.astype(int)
    df['Ay_Gun'] = df['transition_date'].dt.day.astype(int)
    df['Gun_Adi_Tr'] = df['transition_date'].dt.day_name().map(GUN_ESLESTIRME)

    # 3. Aşama: Varış Tahmini
    def varis_bul(line, origin):
        l, o = str(line), str(origin)
        parts = l.replace("-", " ").split()
        res = [p for p in parts if p not in o]
        return " ".join(res) if res else l

    df['varis_tahmini'] = df.apply(lambda x: varis_bul(x['line_name'], x['station_poi_desc_cd']), axis=1)

    return df


# Veriyi yükle
df = veri_yukle()

# --- 3. NAVİGASYON ---
st.sidebar.title("🚢 Menü")
# Sidebar'a bir 'Önbelleği Temizle' butonu koyalım ki hata donup kalmasın
if st.sidebar.button("⚙️ Veriyi Yenile (Cache Clear)"):
    st.cache_data.clear()
    st.rerun()

sayfa = st.sidebar.radio("Görünüm:", ["Klasik Hat Analizi (Kırmızı)", "Akış Matrisi (Mavi)"])


# --- YARDIMCI FONKSİYON: GÜVENLİ SIRALAMA ---
def guvenli_liste(seri):
    # Bu fonksiyon listenin içinde asla 'nan' veya 'float' bırakmaz, sadece sıralı metin döndürür
    liste = [str(x) for x in seri.unique() if str(x).lower() != 'nan']
    return sorted(liste)


# --- SAYFA 1: KLASİK ANALİZ ---
if sayfa == "Klasik Hat Analizi (Kırmızı)":
    st.sidebar.header("🔍 Filtreler")

    yillar = sorted([int(y) for y in df['Yıl'].unique()], reverse=True)
    secilen_yil = st.sidebar.selectbox("Yıl Seçin:", yillar)
    secilen_gun = st.sidebar.slider("Gün Seçin:", 1, 31, 5)

    # Gün adı bulma
    gun_df = df[(df['Yıl'] == secilen_yil) & (df['Ay_Gun'] == secilen_gun)]
    gun_adi = gun_df['Gun_Adi_Tr'].iloc[0] if not gun_df.empty else "Veri Yok"

    # İskele ve Hat seçimi (Güvenli liste kullanıyoruz)
    iskeleler = guvenli_liste(df['station_poi_desc_cd'])
    secilen_kalkis = st.sidebar.selectbox("Nereden?", iskeleler)

    hatlar = guvenli_liste(df[df['station_poi_desc_cd'] == secilen_kalkis]['line_name'])
    secilen_hat = st.sidebar.selectbox("Nereye?", hatlar)

    # Filtreleme
    f_df = df[(df['Yıl'] == secilen_yil) & (df['Ay_Gun'] == secilen_gun) &
              (df['station_poi_desc_cd'] == secilen_kalkis) & (df['line_name'] == secilen_hat)]

    st.title(f"⚓ {secilen_gun} Temmuz {secilen_yil}, {gun_adi}")

    if not f_df.empty:
        g_df = f_df.groupby('transition_hour')['number_of_passenger'].sum().reset_index()
        col1, col2 = st.columns(2)
        col1.metric("Toplam Yolcu", f"{g_df['number_of_passenger'].sum():,}")
        col2.metric("Gün", gun_adi)

        fig = px.bar(g_df, x='transition_hour', y='number_of_passenger',
                     template="plotly_dark", color_continuous_scale="Reds", color='number_of_passenger')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Veri bulunamadı.")

# --- SAYFA 2: MATRİS ---
else:
    st.title(":blue[İskeleler Arası Akış Matrisi]")
    y_m = st.sidebar.selectbox("Yıl", sorted(df['Yıl'].unique(), reverse=True), key="ym")
    g_m = st.sidebar.slider("Gün", 1, 31, 5, key="gm")
    isk_m = st.sidebar.multiselect("İskeleler:", guvenli_liste(df['station_poi_desc_cd']),
                                   default=guvenli_liste(df['station_poi_desc_cd'])[:5])

    m_df = df[(df['Yıl'] == y_m) & (df['Ay_Gun'] == g_m) & (df['station_poi_desc_cd'].isin(isk_m))]

    if not m_df.empty:
        matris = m_df.pivot_table(index='station_poi_desc_cd', columns='varis_tahmini',
                                  values='number_of_passenger', aggfunc='sum').fillna(0)
        st.plotly_chart(px.imshow(matris, text_auto=True, color_continuous_scale="Blues"), use_container_width=True)
    else:
        st.info("Filtre seçimi yapın.")