import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="İBB Deniz O-D Analizi", layout="wide")


@st.cache_data
def veri_getir():
    df = pd.read_csv("data/sadece_deniz_temmuz.csv")
    df['transition_date'] = pd.to_datetime(df['transition_date'])
    df['station_poi_desc_cd'] = df['station_poi_desc_cd'].fillna("Bilinmiyor").astype(str)
    df['line_name'] = df['line_name'].fillna("Bilinmiyor").astype(str)

    # --- BA MANTIĞI: Hat adından Varış İskelesini Tahmin Etme ---
    # Örn: "EMINONU-KDK" -> Varış: KDK
    def varis_bul(line, origin):
        parts = line.replace("-", " ").split()
        # Origin ismindeki kelimeleri çıkar, geri kalanı varış kabul et
        remaining = [p for p in parts if p not in origin]
        return " ".join(remaining) if remaining else line

    df['varis_iskelesi'] = df.apply(lambda x: varis_bul(x['line_name'], x['station_poi_desc_cd']), axis=1)
    return df


df = veri_getir()

# --- SOL PANEL ---
st.sidebar.header("🔍 O-D Filtreleri")
secilen_tarih = st.sidebar.date_input("Analiz Tarihi", value=df['transition_date'].max())

tum_iskeler = sorted(df['station_poi_desc_cd'].unique())
secilen_baslangic = st.sidebar.multiselect("Başlangıç İskeleleri", options=tum_iskeler, default=tum_iskeler[:5])

# VERİ FİLTRELEME
mask = (df['transition_date'].dt.date == secilen_tarih) & (df['station_poi_desc_cd'].isin(secilen_baslangic))
f_df = df[mask]

# --- ANA SAYFA ---
st.title("⚓ İskeleler Arası Yolcu Akış Matrisi")
st.markdown(f"**Tarih:** {secilen_tarih.strftime('%d %B %Y')}")

if not f_df.empty:
    # 1. MATRİS (HEATMAP) HAZIRLIĞI
    # Satırlar: Başlangıç İskelesi, Sütunlar: Varış Hattı/İskelesi
    matris = f_df.pivot_table(
        index='station_poi_desc_cd',
        columns='varis_iskelesi',
        values='number_of_passenger',
        aggfunc='sum'
    ).fillna(0)

    st.subheader("📊 Nereden Nereye? (Yolcu Yoğunluk Matrisi)")
    st.write("Kutulardaki renk koyulaştıkça yolcu akışı artmaktadır.")

    fig_heatmap = px.imshow(
        matris,
        labels=dict(x="Varış Güzergahı", y="Başlangıç İskelesi", color="Yolcu"),
        x=matris.columns,
        y=matris.index,
        color_continuous_scale="Blues",
        text_auto=True,  # Sayıları kutuların içine yazar
        aspect="auto"
    )
    st.plotly_chart(fig_heatmap, use_container_width=True)

    # 2. EN YOĞUN AKIŞLAR TABLOSU
    st.subheader("🔝 En Yoğun 10 İskeleler Arası Akış")
    akis_ozet = f_df.groupby(['station_poi_desc_cd', 'varis_iskelesi'])['number_of_passenger'].sum().reset_index()
    akis_ozet = akis_ozet.sort_values(by='number_of_passenger', ascending=False).head(10)
    akis_ozet.columns = ['Nereden', 'Nereye/Hangi Hattaki', 'Toplam Yolcu']

    st.table(akis_ozet)

else:
    st.error("Seçilen kriterlerde veri yok. Lütfen farklı iskele veya tarih seçin.")