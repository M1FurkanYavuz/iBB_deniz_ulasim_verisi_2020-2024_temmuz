import streamlit as st
import pandas as pd
import plotly.express as px

# 1. SAYFA AYARLARI
st.set_page_config(page_title="İBB Deniz Ulaşım Analizi", layout="wide")

GUN_ESLESTIRME = {
    'Monday': 'Pazartesi', 'Tuesday': 'Salı', 'Wednesday': 'Çarşamba',
    'Thursday': 'Perşembe', 'Friday': 'Cuma', 'Saturday': 'Cumartesi', 'Sunday': 'Pazar'
}


# --- GÜVENLİ SIRALAMA FONKSİYONU (TypeError Koruması) ---
def guvenli_sirala(seri):
    """NaN değerleri temizler ve her şeyi string olarak sıralar."""
    temiz_liste = [str(x) for x in seri.unique() if pd.notna(x) and str(x).lower() != 'nan']
    return sorted(temiz_liste)


# 2. VERİ YÜKLEME
@st.cache_data
def veri_yukle():
    df = pd.read_csv("data/sadece_deniz_temmuz.csv", encoding='utf-8-sig', low_memory=False)

    # Veri Temizliği ve Standardizasyon
    df['station_poi_desc_cd'] = df['station_poi_desc_cd'].astype(str).str.strip().str.upper().replace('NAN',
                                                                                                      'BİLİNMİYOR')
    df['line_name'] = df['line_name'].astype(str).str.strip().str.upper().replace('NAN', 'BİLİNMİYOR')

    # Tarih İşlemleri
    df['transition_date'] = pd.to_datetime(df['transition_date'], errors='coerce')
    df = df.dropna(subset=['transition_date'])

    df['Yıl'] = df['transition_date'].dt.year.astype(int)
    df['Ay_Gun'] = df['transition_date'].dt.day.astype(int)
    df['Gun_Adi_Tr'] = df['transition_date'].dt.day_name().map(GUN_ESLESTIRME)

    # Varış Tahmini Mantığı
    def varis_bul(line, origin):
        l, o = str(line).replace("-", " "), str(origin)
        parts = l.split()
        res = [p for p in parts if p not in o]
        return " ".join(res) if res else l

    df['varis_tahmini'] = df.apply(lambda x: varis_bul(x['line_name'], x['station_poi_desc_cd']),
                                   axis=1).str.strip().str.upper()

    return df


df = veri_yukle()

# --- 3. NAVİGASYON (SIDEBAR) ---
st.sidebar.title("🚢 Analiz Menüsü")
sayfa = st.sidebar.radio("Görünüm Seçin:", ["Klasik Hat Analizi", "Akış Matrisi", "Yoğunluk Sıralaması (Liste)"])
st.sidebar.divider()

# --- SAYFA 1: KLASİK HAT ANALİZİ ---
if sayfa == "Klasik Hat Analizi":
    st.sidebar.header("🔍 Operasyonel Filtreler")

    yillar_k = sorted([int(x) for x in df['Yıl'].unique() if x > 0], reverse=True)
    sec_yil_k = st.sidebar.selectbox("Yıl Seçin:", yillar_k)
    sec_gun_k = st.sidebar.slider("Temmuz Ayının Hangi Günü?", 1, 31, 5)

    gun_df_k = df[(df['Yıl'] == sec_yil_k) & (df['Ay_Gun'] == sec_gun_k)]
    gun_adi_k = gun_df_k['Gun_Adi_Tr'].iloc[0] if not gun_df_k.empty else "Bilinmiyor"

    st.title(f"⚓ {sec_gun_k} Temmuz {sec_yil_k}, {gun_adi_k}")

    iskeleler_k = guvenli_sirala(df['station_poi_desc_cd'])
    sec_kalkis_k = st.sidebar.selectbox("Kalkış İskelesi (Nereden?):", iskeleler_k)

    hatlar_serisi_k = df[df['station_poi_desc_cd'] == sec_kalkis_k]['line_name']
    hatlar_k = guvenli_sirala(hatlar_serisi_k)
    sec_hat_k = st.sidebar.selectbox("Varış Hattı (Nereye?):", hatlar_k)

    f_df_k = df[(df['Yıl'] == sec_yil_k) & (df['Ay_Gun'] == sec_gun_k) &
                (df['station_poi_desc_cd'] == sec_kalkis_k) & (df['line_name'] == sec_hat_k)]

    if not f_df_k.empty:
        g_df_k = f_df_k.groupby('transition_hour')['number_of_passenger'].sum().reset_index()

        c1, c2, c3 = st.columns(3)
        c1.metric("Toplam Yolcu", f"{g_df_k['number_of_passenger'].sum():,}")
        c2.metric("Zirve Saat", f"{g_df_k.loc[g_df_k['number_of_passenger'].idxmax(), 'transition_hour']}:00")
        c3.metric("Gün", gun_adi_k)

        st.subheader("🕒 Saatlik Yolcu Yoğunluğu")
        fig_k = px.bar(g_df_k, x='transition_hour', y='number_of_passenger',
                       text_auto='.2s', color='number_of_passenger',
                       color_continuous_scale='Reds', template="plotly_dark")
        fig_k.update_layout(xaxis=dict(tickmode='linear', tick0=0, dtick=1))
        st.plotly_chart(fig_k, use_container_width=True)
    else:
        st.warning("Veri bulunamadı.")

# --- SAYFA 2: AKIŞ MATRİSİ ---
elif sayfa == "Akış Matrisi":
    st.title(":blue[İskeleler Arası Yolcu Akış Matrisi]")

    y_m = st.sidebar.selectbox("Yıl", sorted(df['Yıl'].unique(), reverse=True), key="ym")
    g_m = st.sidebar.slider("Gün", 1, 31, 5, key="gm")

    iskeleler_m = guvenli_sirala(df['station_poi_desc_cd'])
    isk_m = st.sidebar.multiselect("İskeleler:", iskeleler_m, default=iskeleler_m[:5])

    f_df_m = df[(df['Yıl'] == y_m) & (df['Ay_Gun'] == g_m) & (df['station_poi_desc_cd'].isin(isk_m))]

    if not f_df_m.empty:
        matris_m = f_df_m.pivot_table(index='station_poi_desc_cd', columns='varis_tahmini',
                                      values='number_of_passenger', aggfunc='sum').fillna(0)

        fig_heat_m = px.imshow(matris_m, text_auto=True, color_continuous_scale="Blues", aspect="auto")
        st.plotly_chart(fig_heat_m, use_container_width=True)
    else:
        st.info("Filtre seçimi yapın.")

# --- SAYFA 3: YOĞUNLUK SIRALAMASI (LİSTE) ---
else:
    st.title("📋 Sefer Yoğunluk Sıralaması")

    y_l = st.sidebar.selectbox("Yıl Seçiniz", sorted(df['Yıl'].unique(), reverse=True), key="yl")
    g_l = st.sidebar.slider("Gün Seçiniz", 1, 31, 5, key="gl")
    s_l = st.sidebar.slider("Saat Dilimi Seçiniz", 0, 23, 8, key="sl")

    # Gün adını bul
    gun_df_l = df[(df['Yıl'] == y_l) & (df['Ay_Gun'] == g_l)]
    gun_adi_l = gun_df_l['Gun_Adi_Tr'].iloc[0] if not gun_df_l.empty else "Bilinmiyor"

    st.markdown(f"**Tarih:** {g_l} Temmuz {y_l}, {gun_adi_l} | **Saat:** {s_l}:00 - {s_l + 1}:00")

    f_df_l = df[(df['Yıl'] == y_l) & (df['Ay_Gun'] == g_l) & (df['transition_hour'] == s_l)]

    if not f_df_l.empty:
        # Seferleri topla ve sırala
        sefer_listesi = f_df_l.groupby(['station_poi_desc_cd', 'varis_tahmini'])[
            'number_of_passenger'].sum().reset_index()
        sefer_listesi = sefer_listesi.sort_values(by='number_of_passenger', ascending=False)
        sefer_listesi.columns = ['Kalkış İskelesi', 'Tahmini Varış', 'Toplam Yolcu Sayısı']

        st.subheader("🔝 Seçilen Saatteki En Yoğun Seferler")
        st.dataframe(sefer_listesi, use_container_width=True, height=600)
    else:
        st.warning("Seçilen zaman diliminde herhangi bir sefer verisi bulunamadı.")