"""BIST-100 + emtia ticker listesi.

Kaynak: lib.zip'in `data/repositories/stock_repository.dart` içindeki
`_bist100Stocks` listesinden port edildi (2026-05-19).

BIST ticker'ları suffix'siz tutulur — BistAdapter `.IS` ekler.
Emtia ticker'ları (GC=F, SI=F) Yahoo Finance global formatta, suffix YOK.
"""
from __future__ import annotations

from finllm.markets.base import Ticker


# Sektörler — BIST'in resmi sektör isimleri (Türkçe)
BIST_100_TICKERS: list[Ticker] = [
    Ticker("AEFES", "bist", "Anadolu Efes", "Içecek"),
    Ticker("AFYON", "bist", "Afyon Çimento", "Çimento"),
    Ticker("AGESA", "bist", "AgeSA Hayat ve Emeklilik", "Sigorta"),
    Ticker("AGHOL", "bist", "AG Anadolu Grubu Holding", "Holding"),
    Ticker("AKBNK", "bist", "Akbank", "Bankacılık"),
    Ticker("AKCNS", "bist", "Akçansa", "Çimento"),
    Ticker("AKFGY", "bist", "Akfen GYO", "GYO"),
    Ticker("AKSA", "bist", "Aksa Akrilik", "Kimya"),
    Ticker("AKSEN", "bist", "Aksa Enerji", "Enerji"),
    Ticker("ALARK", "bist", "Alarko Holding", "Holding"),
    Ticker("ALFAS", "bist", "Alfa Solar Enerji", "Enerji"),
    Ticker("ARCLK", "bist", "Arçelik", "Dayanıklı Tüketim"),
    Ticker("ASELS", "bist", "Aselsan", "Savunma"),
    Ticker("ASTOR", "bist", "Astor Enerji", "Enerji"),
    Ticker("BASGZ", "bist", "Başkent Doğalgaz", "Enerji"),
    Ticker("BERA", "bist", "Bera Holding", "Holding"),
    Ticker("BIMAS", "bist", "BİM Mağazalar", "Perakende"),
    Ticker("BIOEN", "bist", "Biotrend Enerji", "Enerji"),
    Ticker("BRYAT", "bist", "Borusan Yatırım", "Holding"),
    Ticker("BTCIM", "bist", "Batıçim", "Çimento"),
    Ticker("CANTE", "bist", "Can2 Termik", "Enerji"),
    Ticker("CCOLA", "bist", "Coca-Cola İçecek", "Içecek"),
    Ticker("CEMTS", "bist", "Çemtaş", "Metal"),
    Ticker("CIMSA", "bist", "Çimsa", "Çimento"),
    Ticker("CWENE", "bist", "CW Enerji", "Enerji"),
    Ticker("DOAS", "bist", "Doğuş Otomotiv", "Otomotiv"),
    Ticker("DOHOL", "bist", "Doğan Holding", "Holding"),
    Ticker("ECILC", "bist", "Eczacıbaşı İlaç", "İlaç"),
    Ticker("EGEEN", "bist", "Ege Endüstri", "Otomotiv"),
    Ticker("EKGYO", "bist", "Emlak Konut GYO", "GYO"),
    Ticker("ENJSA", "bist", "Enerjisa Enerji", "Enerji"),
    Ticker("ENKAI", "bist", "Enka İnşaat", "İnşaat"),
    Ticker("EREGL", "bist", "Ereğli Demir Çelik", "Metal"),
    Ticker("EUPWR", "bist", "Europower Enerji", "Enerji"),
    Ticker("FROTO", "bist", "Ford Otosan", "Otomotiv"),
    Ticker("GARAN", "bist", "Garanti BBVA", "Bankacılık"),
    Ticker("GESAN", "bist", "Giresun Enerji", "Enerji"),
    Ticker("GUBRF", "bist", "Gübre Fabrikaları", "Kimya"),
    Ticker("HALKB", "bist", "Halkbank", "Bankacılık"),
    Ticker("HEKTS", "bist", "Hektaş", "Kimya"),
    Ticker("ISCTR", "bist", "İş Bankası C", "Bankacılık"),
    Ticker("ISGYO", "bist", "İş GYO", "GYO"),
    Ticker("KCHOL", "bist", "Koç Holding", "Holding"),
    Ticker("KLRHO", "bist", "Kiler Holding", "Holding"),
    Ticker("KMPUR", "bist", "Kimmtaş Poliüretan", "Kimya"),
    Ticker("KONTR", "bist", "Kontrolmatik", "Teknoloji"),
    Ticker("KONYA", "bist", "Konya Çimento", "Çimento"),
    Ticker("KOZAA", "bist", "Koza Anadolu", "Madencilik"),
    Ticker("KOZAL", "bist", "Koza Altın", "Madencilik"),
    Ticker("KRDMD", "bist", "Kardemir D", "Metal"),
    Ticker("KZBGY", "bist", "Kızılbük GYO", "GYO"),
    Ticker("LOGO", "bist", "Logo Yazılım", "Teknoloji"),
    Ticker("MAVI", "bist", "Mavi Giyim", "Tekstil"),
    Ticker("MGROS", "bist", "Migros", "Perakende"),
    Ticker("MPARK", "bist", "MLP Sağlık", "Sağlık"),
    Ticker("OBAMS", "bist", "Oba Makarna", "Gıda"),
    Ticker("ODAS", "bist", "Odaş Elektrik", "Enerji"),
    Ticker("OTKAR", "bist", "Otokar", "Otomotiv"),
    Ticker("OYAKC", "bist", "Oyak Çimento", "Çimento"),
    Ticker("PEKGY", "bist", "Pekintaş GYO", "GYO"),
    Ticker("PETKM", "bist", "Petkim", "Kimya"),
    Ticker("PGSUS", "bist", "Pegasus", "Havacılık"),
    Ticker("QUAGR", "bist", "QUA Granite", "Seramik"),
    Ticker("SAHOL", "bist", "Sabancı Holding", "Holding"),
    Ticker("SASA", "bist", "SASA Polyester", "Kimya"),
    Ticker("SDTTR", "bist", "SDT Uzay ve Teknoloji", "Savunma"),
    Ticker("SISE", "bist", "Şişecam", "Cam"),
    Ticker("SKBNK", "bist", "Şekerbank", "Bankacılık"),
    Ticker("SMRTG", "bist", "Smartiks Yazılım", "Teknoloji"),
    Ticker("SOKM", "bist", "Şok Marketler", "Perakende"),
    Ticker("TABGD", "bist", "Tab Gıda", "Gıda"),
    Ticker("TATGD", "bist", "Tat Gıda", "Gıda"),
    Ticker("TAVHL", "bist", "TAV Havalimanları", "Havacılık"),
    Ticker("TCELL", "bist", "Turkcell", "Telekomünikasyon"),
    Ticker("THYAO", "bist", "Türk Hava Yolları", "Havacılık"),
    Ticker("TKFEN", "bist", "Tekfen Holding", "Holding"),
    Ticker("TKNSA", "bist", "Teknosa", "Perakende"),
    Ticker("TMSN", "bist", "Tümosan Motor", "Otomotiv"),
    Ticker("TOASO", "bist", "Tofaş", "Otomotiv"),
    Ticker("TPMS", "bist", "Toprak Mahsulleri Ofisi", "Tarım"),
    Ticker("TTKOM", "bist", "Türk Telekom", "Telekomünikasyon"),
    Ticker("TTRAK", "bist", "Türk Traktör", "Otomotiv"),
    Ticker("TUKAS", "bist", "Tukaş Gıda", "Gıda"),
    Ticker("TUPRS", "bist", "Tüpraş", "Petrol"),
    Ticker("TURSG", "bist", "Türkiye Sigorta", "Sigorta"),
    Ticker("ULKER", "bist", "Ülker Bisküvi", "Gıda"),
    Ticker("ULUUN", "bist", "Ulusoy Un Sanayi", "Gıda"),
    Ticker("VAKBN", "bist", "Vakıfbank", "Bankacılık"),
    Ticker("VESBE", "bist", "Vestel Beyaz Eşya", "Dayanıklı Tüketim"),
    Ticker("VESTL", "bist", "Vestel Elektronik", "Elektronik"),
    Ticker("YKBNK", "bist", "Yapı Kredi", "Bankacılık"),
    Ticker("YYLGD", "bist", "Yayla Agro Gıda", "Gıda"),
    Ticker("ZOREN", "bist", "Zorlu Enerji", "Enerji"),
    Ticker("ZTCNM", "bist", "Zubeyde Tüneli Çimento", "Çimento"),
    Ticker("SNGYO", "bist", "Sinpaş GYO", "GYO"),
    Ticker("ANGEN", "bist", "Anadolu Genetik", "Sağlık"),
    Ticker("SMEN", "bist", "Söktaş Mensucat", "Tekstil"),
    Ticker("KCAER", "bist", "Kocaerli", "Tarım"),
    Ticker("ANSGR", "bist", "Anadolu Sigorta", "Sigorta"),
    Ticker("ARDYZ", "bist", "Ardor Yazılım", "Teknoloji"),
    Ticker("KARTN", "bist", "Kartonsan", "Ambalaj"),
]


BIST_COMMODITIES: list[Ticker] = [
    Ticker("GC=F", "bist", "Gram Altın", "Emtia", is_commodity=True),
    Ticker("SI=F", "bist", "Gram Gümüş", "Emtia", is_commodity=True),
]


BIST_ALL: list[Ticker] = BIST_100_TICKERS + BIST_COMMODITIES


# USDTRY paritesi — emtia çevirimi için
BIST_FX_TICKER = "USDTRY=X"

# Troy ons → gram
TROY_OUNCE_TO_GRAM = 31.1035
