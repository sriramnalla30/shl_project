"""
scrape_catalog.py — Crawl SHL Individual Test Solutions catalog.

Reference URL: https://www.shl.com/solutions/products/product-catalog/

This script is run OFFLINE, never in production.
The current catalog (shl_product_catalog.json) was scraped on 2026-05-08
and contains 377 records. Re-run this script only when the catalog needs
refreshing.

# TODO: Implement full scraper with:
#   - requests + BeautifulSoup4
#   - Pagination of the Individual Test Solutions listing
#   - Detail page parsing for each assessment
#   - Exponential backoff retries (max 3)
#   - Polite 1 req/s rate limit
#   - --diff mode to show changes since last run
#   - Output: shl_product_catalog.json
"""


def main():
    raise NotImplementedError(
        "Catalog already scraped. See shl_product_catalog.json in workspace root. "
        "Re-implement this script when a catalog refresh is needed."
    )


if __name__ == "__main__":
    main()
