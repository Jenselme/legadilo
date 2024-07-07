"""Base settings to build other settings files upon."""

import concurrent
import warnings
from pathlib import Path

import asgiref
import django
import environ
from django.contrib.messages import constants as messages
from django.utils.translation import gettext_lazy as _
from template_partials.apps import wrap_loaders

BASE_DIR = Path(__file__).resolve(strict=True).parent.parent
# legadilo/
APPS_DIR = BASE_DIR / "legadilo"
env = environ.Env()

READ_DOT_ENV_FILE = env.bool("DJANGO_READ_DOT_ENV_FILE", default=False)
if READ_DOT_ENV_FILE:
    # OS environment variables take precedence over variables from .env
    env.read_env(str(BASE_DIR / ".env"))

IS_PRODUCTION = env.bool("IS_PRODUCTION", default=True)

# GENERAL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#debug
DEBUG = not IS_PRODUCTION
# https://docs.djangoproject.com/en/dev/ref/settings/#secret-key
SECRET_KEY = env(
    "DJANGO_SECRET_KEY",
    default=env.NOTSET if IS_PRODUCTION else "local-secret-key",
)
# https://docs.djangoproject.com/en/dev/ref/settings/#allowed-hosts
ALLOWED_HOSTS = env.list(
    "DJANGO_ALLOWED_HOSTS",
    default=["www.legadilo.eu", "legadilo.eu"]
    if IS_PRODUCTION
    else ["localhost", "0.0.0.0", "127.0.0.1"],  # noqa: S104 binding to all interfaces
)
# Local time zone. Choices are
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# though not all of them may be available with every OS.
# In Windows, this must be set to your system time zone.
TIME_ZONE = "UTC"
# https://docs.djangoproject.com/en/dev/ref/settings/#language-code
LANGUAGE_CODE = "en-us"
# https://docs.djangoproject.com/en/dev/ref/settings/#languages
LANGUAGES = [
    ("en", _("English")),
    # ("fr", _("French")),
]

# https://docs.djangoproject.com/en/dev/ref/settings/#site-id
SITE_ID = 1
# https://docs.djangoproject.com/en/dev/ref/settings/#use-i18n
USE_I18N = True
# https://docs.djangoproject.com/en/dev/ref/settings/#use-tz
USE_TZ = True
# https://docs.djangoproject.com/en/dev/ref/settings/#locale-paths
LOCALE_PATHS = [str(BASE_DIR / "locale")]
ASGI_APPLICATION = "config.asgi.application"
VERSION = env.str("VERSION", "")


# DATABASES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#databases
DATABASES = {"default": env.db("DATABASE_URL")}
DATABASES["default"]["CONN_MAX_AGE"] = env.int("CONN_MAX_AGE", default=60 if IS_PRODUCTION else 0)
# https://blog.heroku.com/postgres-essentials#set-a-code-statement_timeout-code-for-web-dynos
DATABASES["OPTIONS"] = {"options": "-c statement_timeout=30000"}
# https://docs.djangoproject.com/en/stable/ref/settings/#std:setting-DEFAULT_AUTO_FIELD
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# CACHES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#caches
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": "django_cache_table",
    }
    if IS_PRODUCTION
    else {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "",
    },
}

# URLS
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#root-urlconf
ROOT_URLCONF = "config.urls"
# https://docs.djangoproject.com/en/dev/ref/settings/#wsgi-application
WSGI_APPLICATION = "config.wsgi.application"

# APPS
# ------------------------------------------------------------------------------
DJANGO_APPS = [
    "daphne",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.sites",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",  # Handy template tags
    "django.contrib.admin",
    "django.forms",
]
THIRD_PARTY_APPS = [
    "django_version_checks",
    "extra_checks",
    "anymail",
    "crispy_forms",
    "crispy_bootstrap5",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "axes",
    "django_htmx",
    "template_partials.apps.SimpleAppConfig",
]
LOCAL_APPS = [
    "legadilo.core",
    "legadilo.users",
    "legadilo.website",
    "legadilo.reading",
    "legadilo.feeds",
    "legadilo.import_export",
]
# https://docs.djangoproject.com/en/dev/ref/settings/#installed-apps
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# MIGRATIONS
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#migration-modules
MIGRATION_MODULES = {"sites": "legadilo.contrib.sites.migrations"}

# AUTHENTICATION
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#authentication-backends
AUTHENTICATION_BACKENDS = [
    # AxesStandaloneBackend should be the first backend in the AUTHENTICATION_BACKENDS list.
    "axes.backends.AxesStandaloneBackend",
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]
# https://docs.djangoproject.com/en/dev/ref/settings/#auth-user-model
AUTH_USER_MODEL = "users.User"
# https://docs.djangoproject.com/en/dev/ref/settings/#login-redirect-url
LOGIN_REDIRECT_URL = "users:redirect"
# https://docs.djangoproject.com/en/dev/ref/settings/#login-url
LOGIN_URL = "account_login"

# PASSWORDS
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#password-hashers
PASSWORD_HASHERS = [
    # https://docs.djangoproject.com/en/dev/topics/auth/passwords/#using-argon2-with-django
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
]
# https://docs.djangoproject.com/en/dev/ref/settings/#auth-password-validators
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# MIDDLEWARE
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#middleware
MIDDLEWARE = [
    "legadilo.core.middlewares.CSPMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
    # AxesMiddleware should be the last middleware in the MIDDLEWARE list.
    # It only formats user lockout messages and renders Axes lockout responses
    # on failed user authentication attempts from login views.
    # If you do not want Axes to override the authentication response
    # you can skip installing the middleware and use your own views.
    "axes.middleware.AxesMiddleware",
]

# STATIC
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#static-root
STATIC_ROOT = str(BASE_DIR / "staticfiles")
# https://docs.djangoproject.com/en/dev/ref/settings/#static-url
STATIC_URL = "/static/"
# https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#std:setting-STATICFILES_DIRS
STATICFILES_DIRS = [
    str(APPS_DIR / "static"),
    str(BASE_DIR / "node_modules/@popperjs/core/dist/umd/"),
    str(BASE_DIR / "node_modules/bootstrap/dist/"),
    str(BASE_DIR / "node_modules/bootstrap5-tags/"),
    str(BASE_DIR / "node_modules/htmx.org/dist"),
]
# https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#staticfiles-finders
STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
]
# https://docs.djangoproject.com/en/dev/ref/settings/#std-setting-STORAGES
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# MEDIA
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#media-root
MEDIA_ROOT = str(APPS_DIR / "media")
# https://docs.djangoproject.com/en/dev/ref/settings/#media-url
MEDIA_URL = "/media/"

# TEMPLATES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#templates
TEMPLATES = [
    {
        # https://docs.djangoproject.com/en/dev/ref/settings/#std:setting-TEMPLATES-BACKEND
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "NAME": "default-template-backend",
        # https://docs.djangoproject.com/en/dev/ref/settings/#dirs
        "DIRS": [str(APPS_DIR / "templates")],
        "OPTIONS": {
            # https://docs.djangoproject.com/en/dev/ref/settings/#template-context-processors
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.template.context_processors.i18n",
                "django.template.context_processors.media",
                "django.template.context_processors.static",
                "django.template.context_processors.tz",
                "django.contrib.messages.context_processors.messages",
                "legadilo.users.context_processors.allauth_settings",
                "legadilo.core.context_processors.provide_global_context",
            ],
            "libraries": {
                "util_tags": "legadilo.core.template_tags.util_tags",
                "feeds": "legadilo.reading.templatetags",
            },
            "debug": DEBUG,
        },
    },
]
wrap_loaders("default-template-backend")

MESSAGE_TAGS = {
    messages.ERROR: "danger",
}

# https://docs.djangoproject.com/en/dev/ref/settings/#form-renderer
FORM_RENDERER = "django.forms.renderers.TemplatesSetting"

# http://django-crispy-forms.readthedocs.io/en/latest/install.html#template-packs
CRISPY_TEMPLATE_PACK = "bootstrap5"
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"

# FIXTURES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#fixture-dirs
FIXTURE_DIRS = (str(APPS_DIR / "fixtures"),)

# SECURITY
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#session-cookie-httponly
SESSION_COOKIE_HTTPONLY = True
# https://docs.djangoproject.com/en/dev/ref/settings/#csrf-cookie-httponly
CSRF_COOKIE_HTTPONLY = True
# https://docs.djangoproject.com/en/dev/ref/settings/#x-frame-options
X_FRAME_OPTIONS = "DENY"
# https://docs.djangoproject.com/en/dev/ref/settings/#secure-proxy-ssl-header
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
# https://docs.djangoproject.com/en/dev/ref/settings/#secure-ssl-redirect
SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=IS_PRODUCTION)
# https://docs.djangoproject.com/en/dev/ref/settings/#session-cookie-secure
SESSION_COOKIE_SECURE = IS_PRODUCTION
# https://docs.djangoproject.com/en/dev/ref/settings/#csrf-cookie-secure
CSRF_COOKIE_SECURE = IS_PRODUCTION
# https://docs.djangoproject.com/en/dev/topics/security/#ssl-https
# https://docs.djangoproject.com/en/dev/ref/settings/#secure-hsts-seconds
# TODO: set this to 60 seconds first and then to 518400 once you prove the former works
SECURE_HSTS_SECONDS = 60
# https://docs.djangoproject.com/en/dev/ref/settings/#secure-hsts-include-subdomains
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool("DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS", default=True)
# https://docs.djangoproject.com/en/dev/ref/settings/#secure-hsts-preload
SECURE_HSTS_PRELOAD = env.bool("DJANGO_SECURE_HSTS_PRELOAD", default=True)
# https://docs.djangoproject.com/en/dev/ref/middleware/#x-content-type-options-nosniff
SECURE_CONTENT_TYPE_NOSNIFF = True


# CSP
# ------------------------------------------------------------------------------
# https://django-csp.readthedocs.io/en/latest/configuration.html
# https://content-security-policy.com/
# https://csp-evaluator.withgoogle.com/
CSP_DEFAULT_SRC = ("'self'",)
CSP_SCRIPT_SRC = ("'strict-dynamic'", "'unsafe-inline'", "https:")
CSP_SCRIPT_SRC_ATTR = None
CSP_SCRIPT_SRC_ELEM = None
CSP_IMG_SRC = ("'self'", "data:")
CSP_OBJECT_SRC = ("'none'",)
CSP_MEDIA_SRC = ("'self'",)
CSP_FRAME_SRC = ("'none'",)
CSP_FONT_SRC = ("'self'",)
CSP_CONNECT_SRC = ("'self'",)
CSP_STYLE_SRC = ("'strict-dynamic'", "'unsafe-inline'", "https:")
CSP_STYLE_SRC_ATTR = None
CSP_STYLE_SRC_ELEM = None
CSP_BASE_URI = ("'none'",)
CSP_FRAME_ANCESTORS = ("'none'",)
CSP_FORM_ACTION = ("'self'",)
CSP_MANIFEST_SRC = ("'self'",)
CSP_WORKER_SRC = ("'self'",)
CSP_PLUGIN_TYPES = None
CSP_REQUIRE_SRI_FOR = None
CSP_INCLUDE_NONCE_IN = ("script-src", "style-src")
# Those are forced to true in production
CSP_UPGRADE_INSECURE_REQUESTS = IS_PRODUCTION
CSP_BLOCK_ALL_MIXED_CONTENT = IS_PRODUCTION


# EMAIL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#default-from-email
DEFAULT_FROM_EMAIL = env(
    "DJANGO_DEFAULT_FROM_EMAIL",
    default="Legadilo <noreply@legadilo.eu>",
)
# https://docs.djangoproject.com/en/dev/ref/settings/#server-email
SERVER_EMAIL = env("DJANGO_SERVER_EMAIL", default=DEFAULT_FROM_EMAIL)
# https://docs.djangoproject.com/en/dev/ref/settings/#email-subject-prefix
EMAIL_SUBJECT_PREFIX = env(
    "DJANGO_EMAIL_SUBJECT_PREFIX",
    default="[Legadilo] ",
)
# https://anymail.readthedocs.io/en/stable/installation/#installing-anymail
# https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
# https://anymail.readthedocs.io/en/stable/installation/#anymail-settings-reference
# https://anymail.readthedocs.io/en/stable/esps
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
# https://docs.djangoproject.com/en/dev/ref/settings/#email-host
EMAIL_HOST = env("EMAIL_HOST", default="mailpit")
# https://docs.djangoproject.com/en/dev/ref/settings/#email-port
EMAIL_PORT = env.int("EMAIL_PORT", default=1025)
# https://docs.djangoproject.com/en/dev/ref/settings/#email-timeout
EMAIL_TIMEOUT = env.int("EMAIL_TIMEOUT", default=30)


# ADMIN
# ------------------------------------------------------------------------------
# Django Admin URL.
ADMIN_URL = env("DJANGO_ADMIN_URL", default=env.NOTSET if IS_PRODUCTION else "admin/")
# https://docs.djangoproject.com/en/dev/ref/settings/#admins
ADMINS = env.list("DJANGO_ADMINS", default=[])
# https://docs.djangoproject.com/en/dev/ref/settings/#managers
MANAGERS = ADMINS
# https://cookiecutter-django.readthedocs.io/en/latest/settings.html#other-environment-settings
# Force the `admin` sign in process to go through the `django-allauth` workflow
DJANGO_ADMIN_FORCE_ALLAUTH = env.bool("DJANGO_ADMIN_FORCE_ALLAUTH", default=False)

# LOGGING
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#logging
# See https://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
tracebacks_suppress = [django, asgiref, concurrent]
if DEBUG:
    import debug_toolbar
    import django_htmx

    tracebacks_suppress.extend((debug_toolbar, django_htmx))

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s",
        },
        "rich": {"datefmt": "[%X]"},
    },
    "filters": {},
    "handlers": {
        "console": {
            "level": "INFO",
            "filters": [],
            "class": "logging.StreamHandler",
        },
        "rich": {
            "class": "rich.logging.RichHandler",
            "filters": [],
            "level": "DEBUG",
            "rich_tracebacks": env.bool("LOGGING_RICH_TRACEBACK", default=True),
            "tracebacks_show_locals": env.bool("LOGGING_RICH_TRACEBACK", default=True),
            "tracebacks_suppress": tracebacks_suppress,
        },
    },
    "root": {"level": "INFO" if DEBUG else "WARNING", "handlers": ["rich"]},
    "loggers": {
        "django": {
            "handlers": ["rich"],
            "level": "INFO" if DEBUG else "WARNING",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["rich"],
            "level": "ERROR",
            "propagate": False,
        },
        "django.security.DisallowedHost": {
            "level": "ERROR",
            "handlers": ["rich"],
            "propagate": False,
        },
        "httpx": {
            "handlers": ["rich"],
            "level": "WARNING",
        },
        "httpcore": {
            "handlers": ["rich"],
            "level": "WARNING",
        },
        "legadilo": {
            "level": "DEBUG" if DEBUG else "INFO",
            "handlers": ["rich"],
            "propagate": False,
        },
    },
}
# We know about this one and already handle is correctly.
warnings.filterwarnings(
    "ignore", message=r"To avoid breaking existing software while fixing issue 310.*"
)


# django-allauth
# ------------------------------------------------------------------------------
ACCOUNT_ALLOW_REGISTRATION = env.bool("DJANGO_ACCOUNT_ALLOW_REGISTRATION", True)
# https://django-allauth.readthedocs.io/en/latest/configuration.html
ACCOUNT_AUTHENTICATION_METHOD = "email"
# https://django-allauth.readthedocs.io/en/latest/configuration.html
ACCOUNT_EMAIL_REQUIRED = True
# https://django-allauth.readthedocs.io/en/latest/configuration.html
ACCOUNT_USERNAME_REQUIRED = False
# https://django-allauth.readthedocs.io/en/latest/configuration.html
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
# https://django-allauth.readthedocs.io/en/latest/configuration.html
ACCOUNT_EMAIL_VERIFICATION = "mandatory"
# https://django-allauth.readthedocs.io/en/latest/configuration.html
ACCOUNT_ADAPTER = "legadilo.users.adapters.AccountAdapter"
# https://django-allauth.readthedocs.io/en/latest/forms.html
ACCOUNT_FORMS = {"signup": "legadilo.users.forms.UserSignupForm"}
# https://django-allauth.readthedocs.io/en/latest/configuration.html
SOCIALACCOUNT_ADAPTER = "legadilo.users.adapters.SocialAccountAdapter"
# https://django-allauth.readthedocs.io/en/latest/forms.html
SOCIALACCOUNT_FORMS = {"signup": "legadilo.users.forms.UserSocialSignupForm"}


# django-version-checks (https://pypi.org/project/django-version-checks/)
# ------------------------------------------------------------------------------
VERSION_CHECKS = {
    "python": "==3.12.*",
    "postgresql": "==16.*",
}


# django-extra-checks
# ------------------------------------------------------------------------------
EXTRA_CHECKS = {
    "checks": [
        # require non empty `upload_to` argument.
        "field-file-upload-to",
        # Use UniqueConstraint with the constraints option instead.
        "no-unique-together",
        # verbose_name must use gettext.
        "field-verbose-name-gettext",
        # help_text must use gettext.
        "field-help-text-gettext",
        # text fields shouldn't use null=True.
        "field-text-null",
        # don't pass null=False to model fields (this is django default).
        "field-null",
        # Related fields must specify related_name explicitly.
        "field-related-name",
        # If field nullable (null=True), then default=None argument is redundant and should be
        # removed.
        "field-default-null",
        # Fields with choices must have companion CheckConstraint to enforce choices on database
        # level, details.
        "field-choices-constraint",
    ]
}

# Axes (https://django-axes.readthedocs.io/en/latest/4_configuration.html)
# ------------------------------------------------------------------------------
# Block by Username only (i.e.: Same user different IP is still blocked, but different user same
# IP is not)
AXES_LOCKOUT_PARAMETERS = ["username"]
# Disable logging the IP-Address of failed login attempts by returning None for attempts to get the
# IP.
# Ignore assigning a lambda function to a variable for brevity
AXES_CLIENT_IP_CALLABLE = lambda x: None  # noqa: E731


# Set dev tooling
# ---------------
if DEBUG:
    # http://whitenoise.evans.io/en/latest/django.html#using-whitenoise-in-development
    INSTALLED_APPS = ["whitenoise.runserver_nostatic", *INSTALLED_APPS]
    # https://django-debug-toolbar.readthedocs.io/en/latest/installation.html#prerequisites
    INSTALLED_APPS += ["debug_toolbar", "django_watchfiles", "django_browser_reload"]
    # https://django-debug-toolbar.readthedocs.io/en/latest/installation.html#middleware
    MIDDLEWARE += ["debug_toolbar.middleware.DebugToolbarMiddleware"]
    MIDDLEWARE.insert(0, "django_browser_reload.middleware.BrowserReloadMiddleware")
    # https://django-debug-toolbar.readthedocs.io/en/latest/configuration.html#debug-toolbar-config
    DEBUG_TOOLBAR_CONFIG = {
        "DISABLE_PANELS": ["debug_toolbar.panels.redirects.RedirectsPanel"],
        "SHOW_TEMPLATE_CONTEXT": True,
    }
    # https://django-debug-toolbar.readthedocs.io/en/latest/installation.html#internal-ips
    INTERNAL_IPS = ["127.0.0.1", "10.0.2.2"]
    if env("USE_DOCKER", default="no") == "yes":
        import socket

        hostname, _, ips = socket.gethostbyname_ex(socket.gethostname())  # type: ignore[assignment]
        INTERNAL_IPS += [".".join(ip.split(".")[:-1] + ["1"]) for ip in ips]


# Sentry
# ------------------------------------------------------------------------------
SENTRY_DSN = env.str(
    "SENTRY_DSN",
    default="",
)
if not DEBUG and SENTRY_DSN:
    try:
        import sentry_sdk

        def before_send_to_sentry(event, hint):
            if event.get("logger") == "django.channels.server":
                return None

            # Don't send any private information. The id is more than enough.
            if user := event.get("user"):
                user.pop("email", None)
                user["username"] = f"user:{user["id"]}"

            return event

        sentry_sdk.init(
            dsn=SENTRY_DSN,
            # Set traces_sample_rate to 1.0 to capture 100%
            # of transactions for performance monitoring.
            traces_sample_rate=0.1,
            # Set profiles_sample_rate to 1.0 to profile 100%
            # of sampled transactions.
            # We recommend adjusting this value in production.
            profiles_sample_rate=0.1,
            before_send=before_send_to_sentry,
            send_default_pii=True,
        )
    except ImportError:
        print("Failed to import sentry_sdk")  # noqa: T201 print found


# Your stuff...
# ------------------------------------------------------------------------------
