import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sklearn.linear_model import LinearRegression
import numpy as np

# 1. SAYFA AYARLARI
st.set_page_config(page_title="İBB Deniz Analitiği v5.0", layout="wide")

GUN_ESLESTIRME = {
    'Monday': 'Pazartesi', 'Tuesday': 'Salı', 'Wednesday': 'Çarşamba',
    'Thursday': 'Perşembe', 'Friday': 'Cuma', 'Saturday': 'Cumartesi', 'Sunday': 'Pazar'
}


def guvenli_sirala(seri):
    temiz_liste = [str(x) for x in seri.unique() if pd.notna(x) and str(x).lower() != 'nan']
    return sorted(temiz_liste)


@st.cache_data
def veri_yukle():
    df = pd.read_csv("data/sadece_deniz_temmuz.csv", encoding='utf-8-sig', low_memory=False)
    df['station_poi_desc_cd'] = df['station_poi_desc_cd'].astype(str).str.strip().str.upper().replace('NAN',
                                                                                                      'BİLİNMİYOR')
    df['line_name'] = df['line_name'].astype(str).str.strip().str.upper().replace('NAN', 'BİLİNMİYOR')
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

    df['varis_tahmini'] = df.apply(lambda x: varis_bul(x['line_name'], x['station_poi_desc_cd']),
                                   axis=1).str.strip().str.upper()
    return df


df = veri_yukle()

# --- SIDEBAR (NAVİGASYON VE FİLTRELER) ---
st.sidebar.title("🚢 Analiz Menüsü")
sayfa = st.sidebar.radio("Görünüm Seçin:", [
    "Klasik Hat Analizi",
    "Akış Matrisi",
    "Yoğunluk Sıralaması",
    "Yıllık Trend Analizi 📈",
    "Gelecek Yolcu Tahmini 🔮"
])
st.sidebar.divider()

# --- SAYFA 1: KLASİK HAT ANALİZİ ---
if sayfa == "Klasik Hat Analizi":
    st.title("⚓ Klasik Hat Analizi")
    y = st.sidebar.selectbox("Yıl", sorted(df['Yıl'].unique(), reverse=True))
    g = st.sidebar.slider("Gün", 1, 31, 5)
    kalkis = st.sidebar.selectbox("Kalkış:", guvenli_sirala(df['station_poi_desc_cd']))
    hat = st.sidebar.selectbox("Hat:", guvenli_sirala(df[df['station_poi_desc_cd'] == kalkis]['line_name']))

    f_df = df[(df['Yıl'] == y) & (df['Ay_Gun'] == g) & (df['station_poi_desc_cd'] == kalkis) & (df['line_name'] == hat)]
    if not f_df.empty:
        g_df = f_df.groupby('transition_hour')['number_of_passenger'].sum().reset_index()
        st.plotly_chart(px.bar(g_df, x='transition_hour', y='number_of_passenger', color_continuous_scale='Reds',
                               color='number_of_passenger', template="plotly_dark"), use_container_width=True)

# --- SAYFA 2: AKIŞ MATRİSİ ---
elif sayfa == "Akış Matrisi":
    st.title("⚓ Akış Matrisi")
    y_m = st.sidebar.selectbox("Yıl", sorted(df['Yıl'].unique(), reverse=True), key="ym")
    g_m = st.sidebar.slider("Gün", 1, 31, 5, key="gm")
    isk_m = st.sidebar.multiselect("İskeleler:", guvenli_sirala(df['station_poi_desc_cd']),
                                   default=guvenli_sirala(df['station_poi_desc_cd'])[:5])
    f_df_m = df[(df['Yıl'] == y_m) & (df['Ay_Gun'] == g_m) & (df['station_poi_desc_cd'].isin(isk_m))]
    if not f_df_m.empty:
        matris = f_df_m.pivot_table(index='station_poi_desc_cd', columns='varis_tahmini', values='number_of_passenger',
                                    aggfunc='sum').fillna(0)
        st.plotly_chart(px.imshow(matris, text_auto=True, color_continuous_scale="Blues"), use_container_width=True)

# --- SAYFA 3: YOĞUNLUK SIRALAMASI ---
elif sayfa == "Yoğunluk Sıralaması":
    st.title("📋 Günlük Sefer Sıralaması")
    y_l = st.sidebar.selectbox("Yıl", sorted(df['Yıl'].unique(), reverse=True), key="yl")
    g_l = st.sidebar.slider("Gün", 1, 31, 5, key="gl")
    s_l = st.sidebar.slider("Saat", 0, 23, 8, key="sl")
    f_df_l = df[(df['Yıl'] == y_l) & (df['Ay_Gun'] == g_l) & (df['transition_hour'] == s_l)]
    if not f_df_l.empty:
        list_df = f_df_l.groupby(['station_poi_desc_cd', 'varis_tahmini'])[
            'number_of_passenger'].sum().reset_index().sort_values(by='number_of_passenger', ascending=False)
        st.dataframe(list_df, use_container_width=True, height=600)

# --- SAYFA 4 VE 5 İÇİN ORTAK FİLTRELER ---
elif sayfa in ["Yıllık Trend Analizi 📈", "Gelecek Yolcu Tahmini 🔮"]:
    st.sidebar.header("🎯 Güzergah Hedefleme")
    g_isk = st.sidebar.selectbox("Kalkış İskelesi:", guvenli_sirala(df['station_poi_desc_cd']), key="gisk")
    g_hat = st.sidebar.selectbox("Varış Güzergahı:",
                                 guvenli_sirala(df[df['station_poi_desc_cd'] == g_isk]['line_name']), key="ghat")
    g_gun = st.sidebar.slider("Ayın Günü (Örn: 8 Temmuz):", 1, 31, 8, key="ggun")
    g_saat = st.sidebar.slider("Saat Dilimi:", 0, 23, 13, key="gsaat")

    # Filtreleme İşlemi
    trend_data = df[(df['station_poi_desc_cd'] == g_isk) &
                    (df['line_name'] == g_hat) &
                    (df['Ay_Gun'] == g_gun) &
                    (df['transition_hour'] == g_saat)]

    if sayfa == "Yıllık Trend Analizi 📈":
        st.title("📈 Noktasal Yıllık Trend Analizi")
        st.subheader(f"📍 {g_isk} ➔ {g_hat} | Gün: {g_gun} Temmuz | Saat: {g_saat}:00")

        if not trend_data.empty:
            res_df = trend_data.groupby('Yıl')['number_of_passenger'].sum().reset_index()
            # Eksik yılları da görelim
            tüm_yillar = pd.DataFrame({'Yıl': range(2020, 2025)})
            res_df = pd.merge(tüm_yillar, res_df, on='Yıl', how='left').fillna(0)

            c1, c2 = st.columns([1, 2])
            c1.write("**Tarihsel Veri Tablosu**")
            c1.dataframe(res_df.set_index('Yıl'))

            fig = px.bar(res_df, x='Yıl', y='number_of_passenger', text_auto=True, title="Yıllara Göre Yolcu Değişimi",
                         color='number_of_passenger', color_continuous_scale="Viridis")
            c2.plotly_chart(fig, use_container_width=True)
        else:
            st.error("Bu rota ve saat dilimi için tarihsel veri bulunamadı.")

    else:  # Gelecek Yolcu Tahmini 🔮
        st.title("🔮 2036 Projeksiyon Simülatörü")
        hedef_yil = st.sidebar.slider("Tahmin Hedef Yılı:", 2025, 2036, 2030)

        st.subheader(f"🔮 {g_isk} ➔ {g_hat} için {hedef_yil} Vizyonu")

        if not trend_data.empty:
            res_df = trend_data.groupby('Yıl')['number_of_passenger'].sum().reset_index()

            if len(res_df) > 1:  # Regresyon için en az 2 veri noktası lazım
                # Model Eğitimi
                X = res_df[['Yıl']].values
                y = res_df['number_of_passenger'].values
                model = LinearRegression().fit(X, y)

                # Gelecek Yılları Oluştur
                future_years = np.array(range(2025, hedef_yil + 1)).reshape(-1, 1)
                predictions = model.predict(future_years)
                # Negatif tahmini engelle
                predictions = np.maximum(predictions, 0)

                # Görselleştirme Hazırlığı
                pred_df = pd.DataFrame(
                    {'Yıl': range(2025, hedef_yil + 1), 'number_of_passenger': predictions, 'Tip': 'Tahmin'})
                res_df['Tip'] = 'Gerçek'
                plot_df = pd.concat([res_df, pred_df])

                fig_pred = px.line(plot_df, x='Yıl', y='number_of_passenger', color='Tip', markers=True,
                                   title=f"2020 - {hedef_yil} Yolcu Tahmin Çizgisi")

                # Trend çizgisi (Kesikli)
                all_X = np.array(range(2020, hedef_yil + 1)).reshape(-1, 1)
                all_y = model.predict(all_X)
                fig_pred.add_trace(
                    go.Scatter(x=list(range(2020, hedef_yil + 1)), y=all_y, mode='lines', name='Regresyon Eğilimi',
                               line=dict(dash='dash', color='red')))

                st.plotly_chart(fig_pred, use_container_width=True)

                # Özet Metrikler
                y24 = res_df[res_df['Yıl'] == 2024]['number_of_passenger'].sum()
                y_target = predictions[-1]

                c1, c2 = st.columns(2)
                c1.metric("2024 Mevcut", f"{int(y24)}")
                c2.metric(f"{hedef_yil} Beklenen", f"{int(y_target)}", delta=f"{int(y_target - y24)} yolcu")
            else:
                st.warning("Tahmin yapabilmek için bu rotada en az 2 farklı yıla ait veri olması gerekir.")
        else:
            st.error("Tahmin için yeterli veri kaynağı bulunamadı.")