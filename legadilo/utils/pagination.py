from django.core.paginator import Page, Paginator


def get_requested_page(paginator: Paginator, requested_page: int) -> Page:
    return (
        paginator.page(requested_page)
        if 1 <= requested_page <= paginator.num_pages
        else paginator.page(1)
    )