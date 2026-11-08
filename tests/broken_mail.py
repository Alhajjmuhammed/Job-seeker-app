"""Test-only email backend that always fails, to simulate an SMTP outage."""
from django.core.mail.backends.base import BaseEmailBackend


class Broken(BaseEmailBackend):
    def send_messages(self, email_messages):
        raise ConnectionRefusedError('SMTP down (test)')
