"""
Playwright fallback — only when WB API doesn't return seller data.
Uses headless Chromium inside Docker.
"""

from playwright.sync_api import sync_playwright


def scrape_seller_price(article: str, seller_id: str) -> int | None:
    """
    Opens WB in browser, intercepts network request to card.wb.ru
    and extracts price by supplierId.
    Returns price in kopecks or None.
    """
    url = f"https://www.wildberries.ru/catalog/{article}/detail.aspx"
    target_price: int | None = None

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"],
            )
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                )
            )
            page = context.new_page()

            def handle_response(response):
                nonlocal target_price
                if "card.wb.ru/cards/detail" in response.url:
                    try:
                        data = response.json()
                        products = data.get("data", {}).get("products", [])
                        for product in products:
                            if str(product.get("supplierId")) == str(seller_id):
                                target_price = product.get("salePriceU")
                                break
                    except Exception:
                        pass

            page.on("response", handle_response)
            page.goto(url, wait_until="networkidle", timeout=30000)

            context.close()
            browser.close()
    except Exception:
        return None

    return target_price
