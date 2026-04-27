import pandas as pd
import glob
import os


def karakter_duzelt(metin):
    if not isinstance(metin, str): return metin
    # Çift kodlama (Double Encoding) sorunlarını çözen sözlük
    duzeltmeler = {
        'ÃÂ¼': 'ü', 'Ã¼': 'ü', 'ÃÂœ': 'Ü', 'Ãœ': 'Ü',
        'ÃÂ¶': 'ö', 'Ã¶': 'ö', 'ÃÂ–': 'Ö', 'Ã–': 'Ö',
        'ÃÂ§': 'ç', 'Ã§': 'ç', 'ÃÂ‡': 'Ç', 'Ã‡': 'Ç',
        'ÃÂŸ': 'ş', 'ÅŸ': 'ş', 'ÃÂž': 'Ş', 'Åž': 'Ş',
        'ÃÂ°': 'i', 'Ä°': 'İ', 'Ä±': 'ı', 'ÃÂ±': 'ı',
        'ÃÂ ': 'ğ', 'ÄŸ': 'ğ', 'ÃÂž': 'Ğ', 'Äž': 'Ğ'
    }
    for bozuk, duzgun in duzeltmeler.items():
        metin = metin.replace(bozuk, duzgun)
    return metin


def deniz_verisini_isleh(data_klasoru):
    secilen_sutunlar = ['transition_date', 'transition_hour', 'road_type', 'line_name', 'station_poi_desc_cd',
                        'number_of_passenger']
    # Sadece ham verileri al (islenmiş dosyayı hariç tut)
    dosyalar = [f for f in glob.glob(os.path.join(data_klasoru, "*.csv")) if "sadece_deniz" not in f]

    liste = []
    for dosya in dosyalar:
        try:
            # Türkçe karakter desteği için iso-8859-9 ile oku
            try:
                df = pd.read_csv(dosya, encoding='iso-8859-9', usecols=secilen_sutunlar)
            except:
                df = pd.read_csv(dosya, encoding='utf-8', usecols=secilen_sutunlar)

            # Sadece Deniz Ulaşımı
            df = df[df['road_type'].str.contains('DEN', na=False)]
            df = df.drop(columns=['road_type'])

            # İsimleri Onar
            df['station_poi_desc_cd'] = df['station_poi_desc_cd'].apply(karakter_duzelt)
            df['line_name'] = df['line_name'].apply(karakter_duzelt)

            liste.append(df)
            print(f"Başarıyla İşlendi: {os.path.basename(dosya)}")
        except Exception as e:
            print(f"Hata: {os.path.basename(dosya)} dosyası atlandı. {e}")

    return pd.concat(liste, ignore_index=True)


if __name__ == "__main__":
    path = "../data"
    cikti_yolu = "../data/sadece_deniz_temmuz.csv"

    # 1. Ham verileri birleştir ve temizle
    df_ana = deniz_verisini_isleh(path)

    # 2. Tarih sütununu gerçek tarihe çevir
    df_ana['transition_date'] = pd.to_datetime(df_ana['transition_date'])

    # 3. RİSK YÖNETİMİ: GitHub 100MB sınırı için 2022 ve sonrasını filtrele
    # Bu adım dosya boyutunu güvenli seviyeye çeker.
    df_hafif = df_ana[df_ana['transition_date'].dt.year >= 2022]

    # 4. Kaydet (utf-8-sig formatı Excel ve Dashboard için en iyisidir)
    df_hafif.to_csv(cikti_yolu, index=False, encoding='utf-8-sig')

    print("\n" + "=" * 40)
    print(f"İŞLEM TAMAM: 2022-2024 verisi hazır.")
    print(f"Satır Sayısı: {len(df_hafif)}")
    print(f"Boyut Tahmini: ~75 MB")
    print("=" * 40)