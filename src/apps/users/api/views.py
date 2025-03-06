from rest_framework import viewsets, generics, status
from rest_framework.response import Response
from .serializers import (
    UsuarioGETSerializer,
    UsuarioPOSTSerializer,
    PasswordResetRequestSerializer,
    PasswordResetSerializer,
    LoginSerializer,
)
from src.apps.users.models import User
from src.apps.users.permissions import IsAdminUser
from rest_framework.permissions import IsAuthenticated
from src.apps.users.utils.tasks import send_password_reset_email_task, reset_password_task, soft_delete_user_task
from src.apps.users.utils.utils_login import get_tokens_for_user
from rest_framework.views import APIView

from rest_framework.permissions import AllowAny
from rest_framework.pagination import PageNumberPagination

class Pagination(PageNumberPagination):
    page_size = 10 
    page_size_query_param = 'page_size' 
    max_page_size = 100 
class UsuarioView(viewsets.ModelViewSet):
    queryset = User.all_objects.all()
    permission_classes = [IsAuthenticated, IsAdminUser]
    pagination_class = Pagination

    def get_serializer_class(self):
        if self.request.method in ["POST", "PUT", "PATCH"]:
            return UsuarioPOSTSerializer
        return UsuarioGETSerializer


    def destroy(self, request, *args, **kwargs):
        user = self.get_object()
        soft_delete_user_task.apply_async((user.id,))
        return Response(status=status.HTTP_204_NO_CONTENT)

    def update(self, request, *args, **kwargs):
        user = self.get_object()
        serializer = self.get_serializer(user, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()  

            return Response(serializer.data, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class PasswordResetRequestView(generics.GenericAPIView):
    serializer_class = PasswordResetRequestSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]

        send_password_reset_email_task.apply_async((email,)) 

        return Response(
            {"message": "Se ha enviado un código de restablecimiento a tu correo."},
            status=status.HTTP_200_OK,
        )


class PasswordResetView(generics.GenericAPIView):
    serializer_class = PasswordResetSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        token = serializer.validated_data["token"]
        new_password = serializer.validated_data["new_password"]

        reset_password_task.apply_async((email, token, new_password))  

        return Response(
            {"message": "La contraseña se actualizará en breve."},
            status=status.HTTP_200_OK,
        )

class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data["user"]
            user_serializer = UsuarioGETSerializer(user)
            tokens = get_tokens_for_user(user)

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