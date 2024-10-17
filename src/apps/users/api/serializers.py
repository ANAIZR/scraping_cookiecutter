from rest_framework import serializers
from src.apps.users.models import User

from django.core.mail import send_mail
from django.conf import settings

class UsuarioGETSerializer(serializers.ModelSerializer):
    

    class Meta:
        model = User
        fields = [
            "id",
            "first_name",
            "last_name",
            "email",
            "is_active",
            "date_joined",
            "deleted_at",
            "updated_at",
            "is_superuser",
        ]

    




class UsuarioPOSTSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = "__all__"
        extra_kwargs = {"password": {"write_only": True, "required": False}}

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        user = super().create(validated_data)
        if password:
            user.set_password(password)

        self.send_welcome_email(user)
        return user

    def update(self, instance, validated_data):
        password = validated_data.get("password", None)
        user = super().update(instance, validated_data)
        if password:
            instance.set_password(password)
            instance.save()

        self.update_charge(user)
        return user

    def update_charge(self, user):
        if user.charge.filter(id=1).exists():
            user.is_superuser = True
            user.is_staff = True
        else:
            user.is_superuser = False
            user.is_staff = False
        user.save()

    def send_welcome_email(self, user):
        subject = 'Bienvenido al portal de CRIFCAN'
        message = f'Hola {user.email}, gracias por registrarte en la plataforma de CRIFCAN.' 
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