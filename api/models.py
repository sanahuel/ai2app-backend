from django.db import models
from django.contrib.auth.models import User
import os

# Create your models here.

class Dispositivos(models.Model):
    idDispositivos = models.AutoField(primary_key=True)
    IP = models.CharField(max_length=45)
    modelo = models.CharField(max_length=45)
    imgsPath = models.CharField(max_length=200)
    nCassettes = models.IntegerField()
    nAlmacenes = models.IntegerField()

class Experimentos(models.Model):
    idExperimentos = models.AutoField(primary_key=True)
    nombreExperimento = models.CharField(max_length=90)
    fechaInicio = models.DateTimeField()
    ventanaEntreCapturas = models.IntegerField()
    numeroDeCapturas = models.IntegerField()
    idUsuarios = models.ForeignKey(User, on_delete=models.CASCADE)
    aplicacion = models.CharField(max_length=90)
    nombreProyecto = models.CharField(max_length=90)
    tipoImgs = models.CharField(max_length=45)
    resolucionImgs = models.CharField(max_length=45, null=True)
    numeroImgs = models.IntegerField()
    frecuencia = models.IntegerField()
    color = models.CharField(max_length=45, default='#0646b4')
    gusanosPorCondicion = models.IntegerField(null=True)
    estado = models.CharField(max_length=45, null=False, default='pendiente')
    temperatura = models.CharField(max_length=45, null=False)
    humedad = models.CharField(max_length=45, null=False)


class Tareas(models.Model):
    idTareas = models.AutoField(primary_key=True)
    fechayHora = models.DateTimeField()
    holguraPositiva = models.IntegerField()
    holguraNegativa = models.IntegerField()
    idUsuarios = models.ForeignKey(User, on_delete=models.CASCADE)
    idExperimentos = models.ForeignKey(Experimentos,on_delete=models.CASCADE)
    estado = models.CharField(max_length=45)
    cancelada = models.BooleanField(default=False)
    idDispositivos = models.ForeignKey(Dispositivos,on_delete=models.CASCADE)
    idOperativo = models.IntegerField()
    duracion = models.IntegerField()

class Condiciones(models.Model):
    idCondiciones = models.AutoField(primary_key=True)
    idExperimentos = models.ForeignKey(Experimentos,on_delete=models.CASCADE)
    nCondiciones = models.IntegerField()
    nombreCondicion = models.CharField(max_length=45)
    descripcionCondicion = models.CharField(max_length=45)

class Pallets(models.Model):
    idPallets = models.AutoField(primary_key=True)
    idDispositivos = models.ForeignKey(Dispositivos,on_delete=models.CASCADE)
    localizacion = models.CharField(max_length=45)
    idExperimentos = models.ForeignKey(Experimentos, on_delete=models.CASCADE)

class Placas(models.Model):
    idPlacas =  models.AutoField(primary_key=True)
    idPallets = models.ForeignKey(Pallets, on_delete=models.CASCADE)
    idExperimentos = models.ForeignKey(Experimentos,on_delete=models.CASCADE)
    idCondiciones = models.ForeignKey(Condiciones,on_delete=models.CASCADE)
    tipoPlaca = models.CharField(max_length=45)
    cancelada = models.BooleanField(default=False)
    posicion = models.CharField(max_length=45)

class Resultados_lifespan(models.Model):
    idResultados = models.AutoField(primary_key=True)
    idPlacas = models.ForeignKey(Placas,on_delete=models.CASCADE)
    idTareas = models.ForeignKey(Tareas,on_delete=models.CASCADE)
    modo = models.CharField(max_length=45)
    vivos = models.IntegerField(null=True)
    muertos = models.IntegerField(null=True)

class Resultados_healthspan(models.Model):
    idResultados = models.AutoField(primary_key=True)
    idPlacas = models.ForeignKey(Placas,on_delete=models.CASCADE)
    idTareas = models.ForeignKey(Tareas,on_delete=models.CASCADE)
    modo = models.CharField(max_length=45)
    cantidadMov = models.IntegerField(null=True) #int??
    ### . . .

