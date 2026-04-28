import streamlit as st
import pandas as pd
import plotly.express as px

# 1. SAYFA AYARLARI VE TASARIM
st.set_page_config(page_title="İBB Deniz Analizi", layout="wide")

# Veri Yükleme (Cache kullanarak hızı artırıyoruz)
@st.cache_data
def veri_getir():
    df = pd.read_csv("data/sadece_deniz_temmuz.csv")
    df['transition_date'] = pd.to_datetime(df['transition_date'])
    return df

df = veri_getir()

# --- 2. SOL PANEL (FİLTRELER) ---
st.sidebar.header("🔍 Analiz Filtreleri")

# Tarih Filtresi
min_tarih = df['transition_date'].min()
max_tarih = df['transition_date'].max()
secilen_tarih = st.sidebar.date_input("Tarih Seçin", value=max_tarih, min_value=min_tarih, max_value=max_tarih)

# İskele Filtresi (Çoklu Seçim)
tum_iskeler = sorted(df['station_poi_desc_cd'].dropna().astype(str).unique())
secilen_iskeler = st.sidebar.multiselect("İskeleleri Filtrele", options=tum_iskeler, default=tum_iskeler[:5])

# Veriyi Filtreleme
mask = (df['transition_date'].dt.date == secilen_tarih) & (df['station_poi_desc_cd'].isin(secilen_iskeler))
filtrelenmis_df = df[mask]

# --- 3. ANA SAYFA (TASARIM VE ÖZET) ---
st.title(f":blue[Deniz Taşımacılığı Analiz Paneli]")
st.markdown(f"**Seçilen Tarih:** {secilen_tarih.strftime('%d %B %Y, %A')}")

# KPI Metrikleri (Özet Kutuları)
toplam_yolcu = filtrelenmis_df['number_of_passenger'].sum()
en_yogun_iskele = filtrelenmis_df.groupby('station_poi_desc_cd')['number_of_passenger'].sum().idxmax() if not filtrelenmis_df.empty else "N/A"

col1, col2, col3 = st.columns(3)
col1.metric("Toplam Yolcu Sayısı", f"{toplam_yolcu:,}")
col2.metric("En Yoğun İskele", en_yogun_iskele)
col3.metric("Filtrelenmiş Veri Satırı", len(filtrelenmis_df))

st.divider()

# --- 4. GÖRSELLEŞTİRME (YENİ GRAFİKLER) ---

c1, c2 = st.columns(2)

with c1:
    st.subheader("⏰ Saatlik Yolcu Yoğunluğu")
    if not filtrelenmis_df.empty:
        saatlik = filtrelenmis_df.groupby('transition_hour')['number_of_passenger'].sum().reset_index()
        fig_hour = px.line(saatlik, x='transition_hour', y='number_of_passenger',
                           markers=True, line_shape="spline",
                           labels={'transition_hour': 'Saat', 'number_of_passenger': 'Yolcu'})
        st.plotly_chart(fig_hour, use_container_width=True)
    else:
        st.warning("Bu tarih/iskele kombinasyonunda veri yok.")

with c2:
    st.subheader("🚢 En Çok Kullanılan 10 İskele")
    if not filtrelenmis_df.empty:
        iskele_bazli = filtrelenmis_df.groupby('station_poi_desc_cd')['number_of_passenger'].sum().sort_values(ascending=False).head(10).reset_index()
        fig_bar = px.bar(iskele_bazli, x='number_of_passenger', y='station_poi_desc_cd',
                         orientation='h', color='number_of_passenger',
                         labels={'number_of_passenger': 'Toplam Yolcu', 'station_poi_desc_cd': 'İskele'})
        fig_bar.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_bar, use_container_width=True)

# --- 5. ANALİZ NOTU (TASARIM) ---
with st.expander("ℹ️ Analist Notu ve Veri Açıklaması"):
    st.write("""
    Bu dashboard, İBB Açık Veri Portalı üzerinden alınan deniz ulaşımı verileriyle hazırlanmıştır.
    - **Filtreler:** Sol panelden tarih ve iskele bazlı özelleştirme yapabilirsiniz.
    - **KPI:** Yukarıdaki metrikler seçilen filtrelere göre anlık güncellenir.
    - **Görselleştirme:** Saatlik trend grafiği, ulaşımın yoğunlaştığı saatleri (pik saatler) analiz etmenizi sağlar.
    """)