# Generated by Django 4.2.16 on 2024-10-29 05:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('foodgram', '0006_alter_recipe_short_link_hash_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='recipe',
            name='short_link_hash',
            field=models.CharField(max_length=6),
        ),
    ]
