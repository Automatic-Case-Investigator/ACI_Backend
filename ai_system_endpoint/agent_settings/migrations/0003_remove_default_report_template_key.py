from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("agent_settings", "0002_report_templates"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="agentsettings",
            name="default_report_template_key",
        ),
    ]
