# Generated by Django 5.0.3 on 2024-03-18 03:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0002_friendinvitation_friendgroup_friend_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='avatar_url',
            field=models.CharField(max_length=100000),
        ),
    ]
