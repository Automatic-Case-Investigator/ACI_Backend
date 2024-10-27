from django.db import models


class SOARInfo(models.Model):
    SOAR_CHOICES = [("TH", "The Hive")]
    PROTOCOL_CHOICE = [("HTTP", "http:"), ("HTTPS", "https:")]
    soar_type = models.CharField(max_length=2, choices=SOAR_CHOICES)
    api_key = models.CharField(max_length=256)
    protocol = models.CharField(max_length=10, choices=PROTOCOL_CHOICE)
    hostname = models.CharField(max_length=256)
    base_dir = models.CharField(max_length=256)

    def save(self, *args, **kwargs):
        if self.soar_type not in [choice[0] for choice in self.SOAR_CHOICES]:
            raise ValueError("Invalid choice value")
        super().save(*args, **kwargs)
