from rest_framework import serializers
from src.apps.users.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from src.apps.users.utils.services import UserService, EmailService

from django.db import transaction

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
        email = validated_data.get("email", None)
        if email and User.objects.filter(email=email).exists():
            raise serializers.ValidationError(
                {"email": "Este correo ya está en uso por otro usuario."}
            )

        password = validated_data.pop("password", None)
        with transaction.atomic():
            user = super().create(validated_data)

            if password:
                try:
                    validate_password(password, user=user)
                except ValidationError as e:
                    raise serializers.ValidationError({"password": list(e.messages)})
                user.set_password(password)
                user.save()

            UserService.update_system_role(user)
            EmailService.send_welcome_email(user.email, user.username)

        return user

    def update(self, instance, validated_data):
        email = validated_data.get("email", None)
        password = validated_data.pop("password", None)

        if email and User.objects.filter(email=email).exclude(id=instance.id).exists():
            raise serializers.ValidationError({"email": "Este correo ya está en uso por otro usuario."})

        with transaction.atomic():
            was_inactive = not instance.is_active  
            prev_active_state = instance.is_active  

            old_name = instance.first_name  
            old_last_name = instance.last_name  

            user = super().update(instance, validated_data)

            if password:
                try:
                    validate_password(password, user=user)
                except ValidationError as e:
                    raise serializers.ValidationError({"password": list(e.messages)})
                
                user.set_password(password)

            if "is_active" in validated_data and validated_data["is_active"] and was_inactive:
                UserService.restore_user(user)  
            elif "is_active" in validated_data and not validated_data["is_active"]:
                UserService.soft_delete_user(user) 
            else:
                if (
                    instance.is_active == prev_active_state  
                    or instance.first_name != old_name  
                    or instance.last_name != old_last_name  
                ):
                    UserService.update_system_role(user)

            user.save()






class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()
    token = serializers.CharField(max_length=6)
    new_password = serializers.CharField(write_only=True)

    def validate(self, data):
        email = data.get("email")
        token = data.get("token")
        new_password = data.get("new_password")

        if len(new_password) < 6:
            raise serializers.ValidationError(
                {"new_password": "La contraseña debe tener al menos 6 caracteres."}
            )

        if not UserService.is_valid_reset_token(email, token):
            raise serializers.ValidationError(
                {"token": "Token inválido o ha expirado."}
            )

        return data
