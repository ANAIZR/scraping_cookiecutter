from rest_framework import serializers
from src.apps.users.models import User
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from ..utils.update_system_role import update_system_role


class UsuarioGETSerializer(serializers.ModelSerializer):
    system_role_description = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "last_name",
            "email",
            "system_role",
            "system_role_description",
            "is_active",
            "date_joined",
            "deleted_at",
            "updated_at",
            "is_superuser",
        ]

    def get_system_role_description(self, obj):
        print("system_role:", obj.system_role)  # Esto te mostrará el valor real en consola
        role_dict = dict(User.ROLE_CHOICES)
        return role_dict.get(obj.system_role, "No definido")


class UserNameSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = ["id", "username", "last_name", "system_role"]


class UsuarioPOSTSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = "__all__"
        extra_kwargs = {"password": {"write_only": True, "required": True}}

    def create(self, validated_data):
        password = validated_data.pop("password", None)

        user = super().create(validated_data)

        if password:
            try:
                validate_password(password, user=user)
            except ValidationError as e:
                raise serializers.ValidationError({"password": list(e.messages)})
            user.set_password(password)

        update_system_role(user)
        user.save()

        self.send_welcome_email(user)

        return user

    def update(self, instance, validated_data):
        password = validated_data.get("password", None)

        user = super().update(instance, validated_data)

        if password:
            try:
                validate_password(password, user=user)
            except ValidationError as e:
                raise serializers.ValidationError({"password": list(e.messages)})

            user.set_password(password)

        update_system_role(user)
        user.save()

        return user

    def send_welcome_email(self, user):
        subject = "Bienvenido al portal de WEB SCRAPPER"
        message = (
            f"Hola {user.email}, gracias por registrarte en la plataforma de CRIFCAN."
        )
        from_email = settings.EMAIL_HOST_USER
        recipient_list = [user.email]

        send_mail(subject, message, from_email, recipient_list)


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()
    token = serializers.CharField(max_length=6)
    new_password = serializers.CharField(write_only=True)

    def validate_new_password(self, value):
        if len(value) < 6:
            raise serializers.ValidationError(
                "La contraseña debe tener al menos 6 caracteres."
            )
        return value
