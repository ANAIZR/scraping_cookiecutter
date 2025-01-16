from ..serializers.login_serializers import LoginSerializer
from ....users.api.serializers import UsuarioGETSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from ....users.utils.utils_login import get_tokens_for_user
from rest_framework import status
from rest_framework.permissions import AllowAny
import os


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data["user"]
            user_serializer = UsuarioGETSerializer(user)
            tokens = get_tokens_for_user(user)

            # Guardar el access token en la base de datos
            user.access_token = tokens["access"]
            user.save()

            return Response(
                {
                    "user": user_serializer.data,
                    "access_token": tokens["access"],
                    "refresh_token": tokens["refresh"],
                },
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_401_UNAUTHORIZED)
