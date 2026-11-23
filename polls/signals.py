from .voting import claim_anonymous_votes, read_voter_token


def claim_votes_on_login(sender, request, user, **kwargs):
    """Giriş veya kayıt anında (user_logged_in), tarayıcının anonim oylarını hesaba bağlar.

    Kayıt, giriş ve admin girişi aynı sinyali tetikler; tek yerde çözülür. `request` boş olabilir.
    """
    if request is None:
        return
    claim_anonymous_votes(user, read_voter_token(request))
