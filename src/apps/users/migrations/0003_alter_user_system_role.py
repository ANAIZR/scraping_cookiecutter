# Generated by Django 5.1.1 on 2024-10-24 17:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_user_system_role_user_username_alter_user_first_name'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='system_role',
            field=models.CharField(choices=[(1, 'Administrador'), (2, 'Funcionario')], default='funcionario', max_length=20),
        ),
    ]