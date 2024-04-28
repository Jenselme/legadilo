from django.urls import reverse

from legadilo.utils.urls import validate_from_url


def get_from_url_for_article_details(request, query_dict) -> str:
    return validate_from_url(
        request, query_dict.get("from_url"), reverse("feeds:default_reading_list")
    )
