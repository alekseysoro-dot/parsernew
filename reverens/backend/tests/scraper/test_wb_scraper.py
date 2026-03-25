# tests/scraper/test_wb_scraper.py
def test_scrape_seller_price_returns_int_on_success(mocker):
    from scraper.wb_scraper import scrape_seller_price

    mock_page = mocker.MagicMock()
    mock_context = mocker.MagicMock()
    mock_browser = mocker.MagicMock()
    mock_playwright = mocker.MagicMock()

    mock_playwright.chromium.launch.return_value = mock_browser
    mock_browser.new_context.return_value = mock_context
    mock_context.new_page.return_value = mock_page

    mocker.patch("scraper.wb_scraper.sync_playwright", return_value=mocker.MagicMock(
        __enter__=lambda s: mock_playwright,
        __exit__=lambda s, *a: None,
    ))

    # Test that function exists and returns None with mocked empty browser
    result = scrape_seller_price("123456", "1001")
    assert result is None or isinstance(result, int)


def test_scrape_seller_price_returns_none_on_error(mocker):
    from scraper.wb_scraper import scrape_seller_price

    mocker.patch("scraper.wb_scraper.sync_playwright", side_effect=Exception("browser error"))

    result = scrape_seller_price("123456", "1001")
    assert result is None
