from rest_framework_simplejwt.tokens import RefreshToken, UntypedToken, AccessToken  # type: ignore
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError  # type: ignore


def get_tokens_for_user(user):
    tokens = RefreshToken.for_user(user)

    return {
        # refresh sera usando en un futuro para volver a crear un nuevo token
        # cuando el original expire
        "refresh": str(tokens),
        # lo que usaremos ahora es el access_token
        "access": str(tokens.access_token),
    }


# funcion para validar token
def validate_token(token):
    try:
        # UntypedToken: va a decirnos si es valido o no
        # al tratae de vrificar que el token sea alido,
        # si en caso no lo es, entrara en un error
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
