from http import HTTPStatus

import pytest
from allauth.account.models import EmailAddress, EmailConfirmationHMAC
from django.contrib.sites.models import Site
from django.core import mail
from django.urls import reverse

from legadilo.users.admin import User
from legadilo.users.models import UserSettings


@pytest.mark.django_db(reset_sequences=True)
class TestUserRegistration:
    user_email = "tester@legadilo.eu"
    password = "tester-password"  # noqa: S105 possible hardcoded password.

    def test_registration_success(self, client, mocker, snapshot):
        self.client = client
        self.mocker = mocker
        self.snapshot = snapshot
        # For some reason, reset_sequences=True will reset the values of the site object.
        # Let's reput ours.
        site = Site.objects.get_current()
        site.name = "Legadilo"
        site.domain = "legadilo.eu"
        site.save()

        self.mocker.patch("django.middleware.csrf.get_random_string", return_value="mockedtoken")
        self.mocker.patch.object(EmailConfirmationHMAC, "key", "mockkey")

        self._test_user_registration()
        self._test_cannot_login_email_not_validated()
        self._test_confirm_email()
        self._test_login()

    def _test_user_registration(self):
        response = self.client.post(
            "/accounts/signup/",
            {
                "email": self.user_email,
                "password1": self.password,
                "password2": self.password,
            },
        )

        assert response.status_code == HTTPStatus.FOUND
        assert response["Location"] == "/accounts/confirm-email/"

        assert User.objects.count() == 1
        assert UserSettings.objects.count() == 1
        user = User.objects.select_related("settings").get()
        user_settings = UserSettings.objects.get()
        assert user.email == self.user_email
        assert user.settings == user_settings
        assert user.reading_lists.count() > 1
        assert user.reading_lists.filter(is_default=True).count() == 1

        assert len(mail.outbox) == 1
        email_message = mail.outbox[0]
        assert email_message.subject == "[Legadilo] Please Confirm Your Email Address"
        self.snapshot.assert_match(email_message.body, "registration_email_body.html")
        assert email_message.from_email == "Legadilo <noreply@legadilo.eu>"
        assert email_message.reply_to == []
        assert email_message.to == [self.user_email]
        assert email_message.cc == []
        assert email_message.bcc == []
        assert email_message.attachments == []
        assert email_message.alternatives == []  # type: ignore[attr-defined]

    def _test_cannot_login_email_not_validated(self):
        response = self.client.post(
            "/accounts/login/", {"email": self.user_email, "password": self.password}
        )

        assert response.status_code == HTTPStatus.OK
        self.snapshot.assert_match(response.content, "login_failure_response.html")

    def _test_confirm_email(self):
        email_address = EmailAddress.objects.get()
        self.mocker.patch.object(
            EmailConfirmationHMAC, "from_key", return_value=EmailConfirmationHMAC(email_address)
        )

        confirm_page = self.client.get("http://testserver/accounts/confirm-email/mockkey/")

        assert confirm_page.status_code == HTTPStatus.OK
        self.snapshot.assert_match(confirm_page.content, "confirm_email_page.html")

        submit_confirmation_response = self.client.post(
            "http://testserver/accounts/confirm-email/mockkey/"
        )
        assert submit_confirmation_response.status_code == HTTPStatus.FOUND
        assert submit_confirmation_response["Location"] == "/accounts/login/"

    def _test_login(self):
        response = self.client.get("/accounts/login/")
        assert response.status_code == HTTPStatus.OK
        self.snapshot.assert_match(response.content, "login_page.html")

        login_response = self.client.post(
            "/accounts/login/", {"login": self.user_email, "password": self.password}
        )
        assert login_response.status_code == HTTPStatus.FOUND, login_response.content
        assert login_response["Location"] == reverse("users:redirect")

        login_redirect_response = self.client.get(login_response["Location"])
        assert login_redirect_response.status_code == HTTPStatus.FOUND
        assert login_redirect_response["Location"] == reverse("reading:default_reading_list")

        page_response = self.client.get(login_redirect_response["Location"])
        assert page_response.status_code == HTTPStatus.OK
        self.snapshot.assert_match(page_response.content, "page_response.html")
