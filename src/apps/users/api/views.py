from rest_framework import viewsets, generics, status
from rest_framework.response import Response
from .serializers import (
    UsuarioGETSerializer,
    UsuarioPOSTSerializer,
    PasswordResetRequestSerializer,
    PasswordResetSerializer,
)
from django.core.mail import send_mail
from django.core.cache import cache
import random
from django.utils import timezone
from src.apps.users.models import User
from django.conf import settings
from src.apps.users.permissions import IsAdminUser
from rest_framework.permissions import IsAuthenticated


class UsuarioView(viewsets.ModelViewSet):
    queryset = User.all_objects.all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method in ["POST", "PUT", "PATCH"]:
            return UsuarioPOSTSerializer
        return UsuarioGETSerializer

    def get_permissions(self):
        if self.action in ["create", "update", "destroy", "partial_update"]:
            return [IsAuthenticated(), IsAdminUser()]
        return [IsAuthenticated()]

    def destroy(self, request, *args, **kwargs):
        user = self.get_object()
        user.is_active = False
        user.deleted_at = timezone.now()
        user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def update(self, request, *args, **kwargs):
        user = self.get_object()
        is_active_new = request.data.get("is_active", None)

        serializer = self.get_serializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()

        if is_active_new is not None and is_active_new is True:
            user.is_active = True
            user.deleted_at = None
            user.save()

        return Response(status=status.HTTP_200_OK)


class PasswordResetRequestView(generics.GenericAPIView):
    serializer_class = PasswordResetRequestSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        try:
            user = User.objects.get(email=email)

            token = "{:06d}".format(random.randint(0, 999999))

            cache.set(f"password_reset_{email}", token, timeout=600)

            subject = "Restablecimiento de Contraseña"
            message = f"Tu token de restablecimiento de contraseña es: {token}"
            from_email = settings.DEFAULT_FROM_EMAIL
            recipient_list = [user.email]

            send_mail(subject, message, from_email, recipient_list)

            return Response(
                {
                    "message": "Se ha enviado un código de restablecimiento a tu correo electrónico."
                },
                status=status.HTTP_200_OK,
            )
        except User.DoesNotExist:
            return Response(
                {"error": "El correo electrónico no está registrado."},
                status=status.HTTP_400_BAD_REQUEST,
            )


class PasswordResetView(generics.GenericAPIView):
    serializer_class = PasswordResetSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        token = serializer.validated_data["token"]
        new_password = serializer.validated_data["new_password"]

        try:
            user = User.objects.get(email=email)
            cached_token = cache.get(f"password_reset_{email}")
            if cached_token != token:
                return Response(
                    {"error": "Token inválido o ha expirado."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            cache.delete(f"password_reset_{email}")

            user.set_password(new_password)
            user.save()
            return Response(
                {"message": "La contraseña ha sido restablecida exitosamente."},
                status=status.HTTP_200_OK,
            )
        except User.DoesNotExist:
            return Response(
                {"error": "Usuario no encontrado."}, status=status.HTTP_400_BAD_REQUEST
            )
