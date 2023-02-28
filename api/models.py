from django.db import models
from django.contrib.auth.models import User

# Create your models here.

'''
class Ensayo(models.Model):
    nombre = models.TextField(null=True)
    inicio = models.TextField(null=True)
    fin = models.TextField(null=True)
    horas = models.TextField(null=True)

    def __str__(self):
        return self.nombre[0:50]
'''

class Experimentos(models.Model):
    idExperimentos = models.AutoField(primary_key=True)
    nombreExperimento = models.CharField(max_length=45)
    fechaInicio = models.DateTimeField()
    ventanaEntreCapturas = models.TimeField()
    numeroDeCapturas = models.IntegerField()
    idUsuario = models.ForeignKey(User, on_delete=models.CASCADE)
    aplicacion = models.CharField(max_length=45)
    nombreProyecto = models.CharField(max_length=45)

class Tareas(models.Model):
    idTareas = models.AutoField(primary_key=True)
    fechayHora = models.DateTimeField()
    rutaDeImagenes = models.CharField(max_length=90)
    idUsuario = models.ForeignKey(User, on_delete=models.CASCADE)
    idExperimento = models.ForeignKey(Experimentos,on_delete=models.CASCADE)
    parametrosProcesamiento = models.CharField(max_length=45)
    estado = models.CharField(max_length=45)

class Condiciones(models.Model):
    idCondiciones = models.AutoField(primary_key=True)
    ### idExperimento = models.ForeignKey(Experimentos,on_delete=models.CASCADE)
    nCondiciones = models.IntegerField()
    descripcionCondicion = models.CharField(max_length=45)

class Placas(models.Model):
    idPlacas =  models.AutoField(primary_key=True)
    idRanura = models.IntegerField()
    idExperimento = models.ForeignKey(Experimentos,on_delete=models.CASCADE)
    idCondiciones = models.ForeignKey(Condiciones,on_delete=models.CASCADE)
    tipoPlaca = models.CharField(max_length=45)

class Resultados_lifespan(models.Model):
    idResultados = models.AutoField(primary_key=True)
    idPlacas = models.ForeignKey(Placas,on_delete=models.CASCADE)
    idTareas = models.ForeignKey(Tareas,on_delete=models.CASCADE)
    modo = models.CharField(max_length=45)
    vivos = models.IntegerField()
    muertos = models.IntegerField()