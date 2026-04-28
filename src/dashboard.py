import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sklearn.linear_model import LinearRegression
import numpy as np

# 1. SAYFA AYARLARI
st.set_page_config(page_title="İBB Deniz Stratejik Analiz v4.5", layout="wide")

# Gün isimleri sözlüğü
GUN_ESLESTIRME = {
    'Monday': 'Pazartesi', 'Tuesday': 'Salı', 'Wednesday': 'Çarşamba',
    'Thursday': 'Perşembe', 'Friday': 'Cuma', 'Saturday': 'Cumartesi', 'Sunday': 'Pazar'
}


# --- GÜVENLİ SIRALAMA FONKSİYONU (Kritik: Hataları Önler) ---
def guvenli_sirala(seri):
    """NaN değerleri temizler ve her şeyi string olarak sıralar."""
    temiz_liste = [str(x) for x in seri.unique() if pd.notna(x) and str(x).lower() != 'nan']
    return sorted(temiz_liste)


# 2. VERİ YÜKLEME VE ÖN İŞLEME
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

    # Varış Tahmini Mantığı (Hat isminden kalkış iskelesini çıkarır)
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
st.sidebar.title("🚢 Stratejik Menü")
sayfa = st.sidebar.radio("Görünüm Seçin:", [
    "Klasik Hat Analizi",
    "Akış Matrisi",
    "Yoğunluk Sıralaması (Liste)",
    "Yıllık Trend Analizi 📈",
    "Gelecek Yolcu Tahmini 🔮"
])
st.sidebar.divider()

# --- SAYFA 1: KLASİK HAT ANALİZİ ---
if sayfa == "Klasik Hat Analizi":
    st.title("⚓ Klasik Hat Analizi")
    y_k = st.sidebar.selectbox("Yıl", sorted(df['Yıl'].unique(), reverse=True), key="yk")
    g_k = st.sidebar.slider("Temmuz Ayının Hangi Günü?", 1, 31, 5, key="gk")

    gun_df_k = df[(df['Yıl'] == y_k) & (df['Ay_Gun'] == g_k)]
    gun_adi_k = gun_df_k['Gun_Adi_Tr'].iloc[0] if not gun_df_k.empty else "Bilinmiyor"
    st.subheader(f"📅 {g_k} Temmuz {y_k}, {gun_adi_k}")

    isk_list_k = guvenli_sirala(df['station_poi_desc_cd'])
    sec_kalkis_k = st.sidebar.selectbox("Kalkış İskelesi:", isk_list_k)

    hat_list_k = guvenli_sirala(df[df['station_poi_desc_cd'] == sec_kalkis_k]['line_name'])
    sec_hat_k = st.sidebar.selectbox("Varış Hattı:", hat_list_k)

    f_df_k = df[(df['Yıl'] == y_k) & (df['Ay_Gun'] == g_k) & (df['station_poi_desc_cd'] == sec_kalkis_k) & (
                df['line_name'] == sec_hat_k)]

    if not f_df_k.empty:
        g_df_k = f_df_k.groupby('transition_hour')['number_of_passenger'].sum().reset_index()
        col1, col2 = st.columns([1, 3])
        col1.metric("Toplam Yolcu", f"{int(g_df_k['number_of_passenger'].sum()):,}")
        col1.metric("Zirve Saat", f"{int(g_df_k.loc[g_df_k['number_of_passenger'].idxmax(), 'transition_hour'])}:00")

        fig_k = px.bar(g_df_k, x='transition_hour', y='number_of_passenger', color='number_of_passenger',
                       color_continuous_scale='Reds', template="plotly_dark")
        st.plotly_chart(fig_k, use_container_width=True)
    else:
        st.warning("Veri bulunamadı.")

# --- SAYFA 2: AKIŞ MATRİSİ ---
elif sayfa == "Akış Matrisi":
    st.title(":blue[İskeleler Arası Yolcu Akış Matrisi]")
    y_m = st.sidebar.selectbox("Yıl", sorted(df['Yıl'].unique(), reverse=True), key="ym")
    g_m = st.sidebar.slider("Gün", 1, 31, 5, key="gm")
    isk_m_list = guvenli_sirala(df['station_poi_desc_cd'])
    isk_m = st.sidebar.multiselect("İskeleler:", isk_m_list, default=isk_m_list[:5])

    f_df_m = df[(df['Yıl'] == y_m) & (df['Ay_Gun'] == g_m) & (df['station_poi_desc_cd'].isin(isk_m))]
    if not f_df_m.empty:
        matris = f_df_m.pivot_table(index='station_poi_desc_cd', columns='varis_tahmini', values='number_of_passenger',
                                    aggfunc='sum').fillna(0)
        st.plotly_chart(px.imshow(matris, text_auto=True, color_continuous_scale="Blues"), use_container_width=True)

# --- SAYFA 3: YOĞUNLUK SIRALAMASI (LİSTE) ---
elif sayfa == "Yoğunluk Sıralaması (Liste)":
    st.title("📋 Saatlik Sefer Yoğunluk Sıralaması")
    y_l = st.sidebar.selectbox("Yıl", sorted(df['Yıl'].unique(), reverse=True), key="yl")
    g_l = st.sidebar.slider("Gün", 1, 31, 5, key="gl")
    s_l = st.sidebar.slider("Saat", 0, 23, 8, key="sl")

    f_df_l = df[(df['Yıl'] == y_l) & (df['Ay_Gun'] == g_l) & (df['transition_hour'] == s_l)]
    if not f_df_l.empty:
        list_df = f_df_l.groupby(['station_poi_desc_cd', 'varis_tahmini'])[
            'number_of_passenger'].sum().reset_index().sort_values(by='number_of_passenger', ascending=False)
        list_df.columns = ['Kalkış İskelesi', 'Tahmini Varış', 'Toplam Yolcu']
        st.subheader(f"🔝 En Yoğun Seferler (Saat {s_l}:00)")
        st.dataframe(list_df, use_container_width=True, height=500)
    else:
        st.warning("Veri bulunamadı.")

# --- SAYFA 4: YILLIK TREND ANALİZİ 📈 ---
elif sayfa == "Yıllık Trend Analizi 📈":
    st.title("📈 Yıllar Arası Temmuz Ayı Kıyaslaması")
    trend_df = df.groupby('Yıl')['number_of_passenger'].sum().reset_index()

    c1, c2 = st.columns([1, 2])
    with c1:
        st.subheader("Yıllık Veriler")
        st.table(trend_df)
        if len(trend_df) > 1:
            degisim = ((trend_df.iloc[-1]['number_of_passenger'] - trend_df.iloc[0]['number_of_passenger']) /
                       trend_df.iloc[0]['number_of_passenger']) * 100
            st.metric("Toplam Büyüme (2020-2024)", f"%{degisim:.2f}")
    with c2:
        fig_trend = px.line(trend_df, x='Yıl', y='number_of_passenger', markers=True, title="Yıllık Yolcu Sayısı Seyri")
        st.plotly_chart(fig_trend, use_container_width=True)

# --- SAYFA 5: GELECEK YOLCU TAHMİNİ 🔮 ---
else:
    st.title("🔮 Scikit-Learn ile 2026 Projeksiyonu")
    y_df = df.groupby('Yıl')['number_of_passenger'].sum().reset_index()

    # Model Kurma
    X = y_df[['Yıl']].values
    y = y_df['number_of_passenger'].values
    model = LinearRegression().fit(X, y)

    # Tahmin
    gelecek = np.array([[2025], [2026]])
    tahminler = model.predict(gelecek)

    t_df = pd.DataFrame({'Yıl': [2025, 2026], 'number_of_passenger': tahminler, 'Durum': 'Tahmin'})
    y_df['Durum'] = 'Gerçekleşen'
    final_df = pd.concat([y_df, t_df])

    fig_pred = px.scatter(final_df, x='Yıl', y='number_of_passenger', color='Durum', size='number_of_passenger',
                          color_discrete_map={'Gerçekleşen': 'blue', 'Tahmin': 'green'},
                          title="2026 Yolcu Tahmin Modeli")

    # Trend Çizgisi
    full_X = np.array([[2020], [2026]])
    full_y = model.predict(full_X)
    fig_pred.add_trace(go.Scatter(x=[2020, 2026], y=full_y, mode='lines', name='Regresyon Çizgisi',
                                  line=dict(dash='dash', color='red')))

    st.plotly_chart(fig_pred, use_container_width=True)

    st.divider()
    y24 = y_df[y_df['Yıl'] == 2024]['number_of_passenger'].values[0]
    y26 = tahminler[1]
    st.metric("2026 Tahmini Yolcu Hedefi", f"{int(y26):,}", delta=f"{int(y26 - y24):,} yolcu artışı bekleniyor")