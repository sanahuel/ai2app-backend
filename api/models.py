from django.db import models

# Create your models here.

class Ensayo(models.Model):
    nombre = models.TextField(null=True)
    inicio = models.TextField(null=True)
    fin = models.TextField(null=True)
    horas = models.TextField(null=True)

    def __str__(self):
        return self.nombre[0:50]