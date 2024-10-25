def update_system_role(user):
    if user.system_role == 1:
            user.is_superuser = True
            user.is_staff = True
    else:
        user.is_superuser = False
        user.is_staff = False

    user.save()
