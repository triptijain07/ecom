from django.db import models

class Shop(models.Model):
    name = models.CharField(max_length=255)
    address = models.TextField()
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)   # e.g., 12.971599
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)  # e.g., 77.594566
    owner_id = models.IntegerField()  # store user id from AuthService

    class Meta:
        unique_together = ('owner_id', 'name')  # prevent duplicate shop names per owner

    def __str__(self):
        return self.name
