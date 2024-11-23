from ninja import NinjaAPI
from ninja.security import django_auth

from legadilo.reading.api import reading_api_router

api = NinjaAPI(title="Legadilo API", auth=[django_auth], docs_url="/docs/")
api.add_router("reading/", reading_api_router)
