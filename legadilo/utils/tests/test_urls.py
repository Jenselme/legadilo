import pytest
from django.test import RequestFactory

from legadilo.utils.urls import validate_from_url, validate_referer_url

absolute_urls_params = [
    ("http://testserver", "http://testserver/fallback", "http://testserver"),
    ("http://testserver/", "http://testserver/fallback", "http://testserver/"),
    ("http://testserver/test", "http://testserver/fallback", "http://testserver/test"),
    (
        "http://testserver/?param=value#hash",
        "http://testserver/fallback",
        "http://testserver/?param=value#hash",
    ),
    (
        "http://testserver/path/sub/?param=value#hash",
        "http://testserver/fallback",
        "http://testserver/path/sub/?param=value#hash",
    ),
    (
        "http://example.com",
        "http://testserver/fallback",
        "http://testserver/fallback",
    ),
    (
        "http://example.com/test",
        "http://testserver/fallback",
        "http://testserver/fallback",
    ),
    (
        "http://example.com/test/?param=value#hash",
        "http://testserver/fallback",
        "http://testserver/fallback",
    ),
]

relative_urls_params = [
    ("/", "/fallback", "/"),
    ("/test", "/fallback", "/test"),
    (
        "/?param=value#hash",
        "/fallback",
        "/?param=value#hash",
    ),
    (
        "/path/sub/?param=value#hash",
        "/fallback",
        "/path/sub/?param=value#hash",
    ),
]


@pytest.mark.parametrize(
    ("referer_url", "fallback_url", "expected_url"),
    absolute_urls_params,
)
def test_redirect_to_origin(referer_url, fallback_url, expected_url):
    factory = RequestFactory()
    request = factory.get("/", HTTP_REFERER=referer_url)

    validated_url = validate_referer_url(request, fallback_url)

    assert validated_url == expected_url


@pytest.mark.parametrize(
    ("from_url", "fallback_url", "expected_url"),
    [
        *absolute_urls_params,
        *relative_urls_params,
    ],
)
def test_validate_from_url(from_url, fallback_url, expected_url):
    factory = RequestFactory()
    request = factory.get("/")

    validated_url = validate_from_url(request, from_url, fallback_url)

    assert validated_url == expected_url
