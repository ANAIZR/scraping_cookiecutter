from rest_framework import serializers
from ....users.models import User
from django.contrib.auth.hashers import check_password




class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        email = data.get("email")
        password = data.get("password")

        if email and password:
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                raise serializers.ValidationError("Usuario no encontrado.")

            if not check_password(password, user.password):
                raise serializers.ValidationError("Datos invalidos")

            if not user.is_active:
                raise serializers.ValidationError("El usuario no está activo.")

        else:
            raise serializers.ValidationError(
                "Debe incluir tanto 'email' como 'password'."
            )

        data["user"] = user
        return data
