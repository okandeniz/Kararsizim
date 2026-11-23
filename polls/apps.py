from django.apps import AppConfig


class PollsConfig(AppConfig):
    name = "polls"

    def ready(self):
        from django.contrib.auth.signals import user_logged_in

        from .signals import claim_votes_on_login

        user_logged_in.connect(claim_votes_on_login, dispatch_uid="polls.claim_votes_on_login")
