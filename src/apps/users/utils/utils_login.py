from rest_framework_simplejwt.tokens import RefreshToken, UntypedToken, AccessToken 
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError  


def get_tokens_for_user(user):
    tokens = RefreshToken.for_user(user)

    return {
        "refresh": str(tokens),
        "access": str(tokens.access_token),
    }


def validate_token(token):
    try:
        UntypedToken(token)
        return True
    except (InvalidToken, TokenError) as e:
        print(e)
        return False


def get_payload_from_token(token):
    try:
        return AccessToken(token).payload

    except (InvalidToken, TokenError) as e:
        print(e)
        return None
