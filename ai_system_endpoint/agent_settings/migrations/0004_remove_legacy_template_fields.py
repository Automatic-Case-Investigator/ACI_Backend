from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("agent_settings", "0003_remove_default_report_template_key"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="agentsettings",
            name="org_id",
        ),
        migrations.RemoveField(
            model_name="agentsettings",
            name="report_template",
        ),
    ]
