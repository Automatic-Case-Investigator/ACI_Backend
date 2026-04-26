from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("agent_settings", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="agentsettings",
            name="default_report_template_key",
            field=models.CharField(blank=True, default="default", max_length=128),
        ),
        migrations.AddField(
            model_name="agentsettings",
            name="report_templates",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
