from rest_framework import serializers
from src.apps.users.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from src.apps.users.utils.services import UserService
import logging
from django.db import transaction
from src.apps.users.utils.tasks import send_welcome_email_task, update_system_role_task, restore_user_task, soft_delete_user_task

logger = logging.getLogger(__name__)


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

            def post_commit_tasks():
                if user.id and user.email:  #
                    update_system_role_task.apply_async(args=[user.id])
                    send_welcome_email_task.apply_async(args=[user.email, user.username])

            transaction.on_commit(post_commit_tasks)

        return user


    def update(self, instance, validated_data):
        email = validated_data.get("email", None)
        password = validated_data.pop("password", None)

        if email and User.objects.filter(email=email).exclude(id=instance.id).exists():
            raise serializers.ValidationError(
                {"email": "Este correo ya está en uso por otro usuario."}
            )

        old_role = instance.system_role
        old_is_active = instance.is_active  
        old_deleted_at = instance.deleted_at

        with transaction.atomic():
            user = super().update(instance, validated_data)

            if password:
                try:
                    validate_password(password, user=user)
                except ValidationError as e:
                    raise serializers.ValidationError({"password": list(e.messages)})

                user.set_password(password)

            user.save()

            def post_commit_tasks():
                if "is_active" in validated_data:
                    if validated_data["is_active"] is False and old_is_active is True:
                        soft_delete_user_task.apply_async(args=[user.id])
                    elif validated_data["is_active"] is True and old_deleted_at is not None:
                        restore_user_task.apply_async(args=[user.id])

                if "system_role" in validated_data and validated_data["system_role"] != old_role:
                    update_system_role_task.apply_async(args=[user.id])

            transaction.on_commit(post_commit_tasks)

        return user




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
