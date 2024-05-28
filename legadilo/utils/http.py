import httpx

FETCH_TIMEOUT = 300


def get_async_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        headers={"User-Agent": "Legadilo"}, timeout=FETCH_TIMEOUT, follow_redirects=True
    )


def get_rss_async_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        limits=httpx.Limits(max_connections=50, max_keepalive_connections=20, keepalive_expiry=5.0),
        timeout=FETCH_TIMEOUT,
        follow_redirects=True,
        headers={"User-Agent": "Legadilo RSS"},
    )
