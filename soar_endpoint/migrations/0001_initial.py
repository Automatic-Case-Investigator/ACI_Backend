# Generated by Django 5.1.2 on 2024-10-27 05:20

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='SOARInfo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('soar_type', models.CharField(choices=[('TH', 'The Hive')], max_length=2)),
                ('api_key', models.CharField(max_length=256)),
                ('protocol', models.CharField(choices=[('HTTP', 'http:'), ('HTTPS', 'https:')], max_length=10)),
                ('hostname', models.CharField(max_length=256)),
                ('base_dir', models.CharField(max_length=256)),
            ],
        ),
    ]
