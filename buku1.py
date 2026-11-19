
from bs4 import BeautifulSoup
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import requests

RATING_MAP = {
    "One": 1,
    "Two": 2,
    "Three": 3,
    "Four": 4,
    "Five": 5,
}

BASE_URL = "https://books.toscrape.com"
FRANKFURTER_URL = "https://api.frankfurter.dev/v2/rates"


# 1. MENGAMBIL KURS GBP KE IDR
def get_gbp_to_idr_rate():
    response = requests.get(
        FRANKFURTER_URL,
        params={
            "base": "GBP",
            "quotes": "IDR"
        },
        timeout=15
    )

    response.raise_for_status()
    data = response.json()

    if isinstance(data, list):
        for item in data:
            if item.get("quote") == "IDR":
                return float(item["rate"])

    raise ValueError("Data kurs GBP ke IDR tidak ditemukan.")


def scrape_books(max_pages):
    books = []
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    for page in range(1, max_pages + 1):

        if page == 1:
            url = f"{BASE_URL}/index.html"
        else:
            url = f"{BASE_URL}/catalogue/page-{page}.html"

        response = requests.get(
            url,
            headers=headers,
            timeout=15
        )

        response.raise_for_status()
        response.encoding = "utf-8"

        soup = BeautifulSoup(response.text, "html.parser")

        articles = soup.select("article.product_pod")

        for article in articles:

            title_el = article.select_one("h3 a")

            title = (
                title_el.get("title", "").strip()
                if title_el else "Tanpa Judul"
            )

            price_el = article.select_one("p.price_color")

            raw_price = (
                price_el.get_text(strip=True)
                if price_el else "0"
            )

            cleaned_price = (
                raw_price.replace("£", "")
                .replace("GBP", "")
                .replace(",", "")
                .strip()
            )

            harga_gbp = float(cleaned_price)

            rating_el = article.select_one("p.star-rating")

            rating = None

            if rating_el:
                for cls in rating_el.get("class", []):
                    if cls in RATING_MAP:
                        rating = RATING_MAP[cls]
                        break

            avail_el = article.select_one(
                "p.instock.availability"
            )

            ketersediaan = (
                avail_el.get_text(" ", strip=True)
                if avail_el else "Tidak diketahui"
            )

            books.append({
                "judul": title,
                "harga_gbp": harga_gbp,
                "rating": rating,
                "ketersediaan": ketersediaan
            })

    return pd.DataFrame(books)


st.set_page_config(
    page_title="Dashboard Katalog Buku",
    layout="wide"
)

st.title("Dashboard Katalog Buku")

st.write(
    "Mengambil data buku melalui web scraping "
    "dan kurs GBP/IDR melalui REST API."
)

jumlah_halaman = st.slider(
    "Jumlah halaman katalog yang diambil",
    min_value=1,
    max_value=3,
    value=2
)

if st.button(
    "Ambil Data dan Tampilkan Dashboard",
    type="primary"
):

    try:
        with st.spinner(
            "Mengambil kurs GBP/IDR dan melakukan scraping data buku..."
        ):

            kurs_idr = get_gbp_to_idr_rate()
            df_buku = scrape_books(jumlah_halaman)

        if df_buku.empty:

            st.warning(
                "Tidak ada data buku yang berhasil diambil."
            )

        else:

            df_buku["harga_idr"] = (
                df_buku["harga_gbp"] * kurs_idr
            ).round(2)

            st.success(
                f"Berhasil mengambil {len(df_buku)} buku "
                f"dari {jumlah_halaman} halaman."
            )

            st.info(
                f"Kurs yang digunakan: "
                f"1 GBP = Rp {kurs_idr:,.2f}"
            )

            st.subheader("Tabel Data Katalog Buku")

            st.dataframe(
                df_buku,
                use_container_width=True
            )

            st.subheader("Visualisasi")

            col1, col2 = st.columns(2)

            # Grafik distribusi harga
            with col1:

                fig1, ax1 = plt.subplots(figsize=(6, 4))

                ax1.hist(
                    df_buku["harga_idr"].dropna(),
                    bins=10,
                    edgecolor="black"
                )

                ax1.set_title(
                    "Distribusi Harga Buku (IDR)"
                )

                ax1.set_xlabel("Harga (IDR)")
                ax1.set_ylabel("Jumlah Buku")

                ax1.grid(
                    axis="y",
                    linestyle="--",
                    alpha=0.5
                )

                fig1.tight_layout()

                st.pyplot(fig1)

                plt.close(fig1)

            with col2:

                rating_counts = (
                    df_buku["rating"]
                    .value_counts()
                    .reindex(
                        [1, 2, 3, 4, 5],
                        fill_value=0
                    )
                )

                fig2, ax2 = plt.subplots(figsize=(6, 4))

                ax2.bar(
                    rating_counts.index.astype(str),
                    rating_counts.values,
                    edgecolor="black"
                )

                ax2.set_title(
                    "Jumlah Buku per Kategori Rating"
                )

                ax2.set_xlabel("Rating (1 - 5)")
                ax2.set_ylabel("Jumlah Buku")

                ax2.grid(
                    axis="y",
                    linestyle="--",
                    alpha=0.5
                )

                fig2.tight_layout()

                st.pyplot(fig2)

                plt.close(fig2)

    except requests.RequestException as e:

        st.error(
            f"Gagal mengakses jaringan/API/situs: {e}"
        )

    except Exception as e:

        st.error(
            f"Terjadi kesalahan saat memproses data: {e}"
        )
