from django.db import models
from django.utils.text import slugify 
from django.utils import timezone

# Create your models here.

class Location(models.Model):
    city = models.CharField(max_length=50)
    state = models.CharField(max_length=50)
    country = models.CharField(max_length=100)
    lat = models.DecimalField(max_digits=7, decimal_places=5)
    long = models.DecimalField(max_digits=7, decimal_places=5)

    def __str__(self):
        name = self.city + ", " + self.state
        return name

class Race(models.Model):
    name = models.CharField(max_length=250)
    length = models.CharField(max_length=50)
    date = models.DateTimeField("race date")
    location = models.ForeignKey(Location, on_delete=models.CASCADE)
    slug = models.SlugField(unique=True, default='slug')

    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)
        super(Race, self).save(*args, **kwargs)

    def __str__(self):
        return self.name   


# one hour of weather
class Weather(models.Model):
    location = models.ForeignKey(Location, on_delete=models.CASCADE)
    datetime = models.DateTimeField()
    humidity = models.IntegerField(null=True, blank=True)
    temp = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    rain = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    precip_prob = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    precip = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    showers = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    snowfall = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    wind_speed = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    wind_direction = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    wind_gusts = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    class Meta:
        unique_together = ('location', 'datetime')

    def __str__(self):
        local_dt = timezone.localtime(self.datetime)
        return f"{self.location.city}, {self.location.state} - {local_dt.strftime('%y/%m/%d %H:%M')}"  

    