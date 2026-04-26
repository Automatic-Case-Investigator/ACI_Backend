from django.db import models


class SIEMInfo(models.Model):
    SIEM_CHOICES = {"WZ": "Wazuh"}
    PROTOCOL_CHOICE = {"HTTP": "http:", "HTTPS": "https:"}
    siem_type = models.CharField(max_length=2, choices=SIEM_CHOICES)
    use_api_key = models.BooleanField()
    api_key = models.CharField(max_length=256)
    username = models.CharField(max_length=256)
    password = models.CharField(max_length=256)
    protocol = models.CharField(max_length=10, choices=PROTOCOL_CHOICE)
    hostname = models.CharField(max_length=256)
    name = models.CharField(max_length=256)
    base_dir = models.CharField(max_length=256)

    def save(self, *args, **kwargs):
        if self.siem_type not in [key for key in self.SIEM_CHOICES.keys()]:
            raise ValueError("Invalid choice value")
        super().save(*args, **kwargs)


class SIEMConfigFile(models.Model):
    siem = models.ForeignKey(
        SIEMInfo, on_delete=models.CASCADE, related_name="config_files"
    )
    filename = models.CharField(max_length=512)
    content = models.BinaryField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["siem", "filename"], name="unique_siem_config_filename"
            )
        ]
