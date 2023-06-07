import datetime
import threading
import json
import pytz
import time
import random
from django.shortcuts import render
from django.http import JsonResponse
from django.db import transaction
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.views import View
from .models import Experimentos, Tareas, Placas, Condiciones, Resultados_lifespan
from .serializers import CreateEnsayoSerializer

# Create your views here.

timeout_seconds = 30

code = None

#       ------Nuevo Ensayo------

class NewView(APIView):
    serializer_class = CreateEnsayoSerializer
    lock = threading.Lock()
    def __init__(self, *args, **kwargs):
        self.code = None
    
    def acquire_lock(self):
        self.lock.acquire() # ////////////////////////////////// TODO Poner Timeout de seguridad
        # self.reset_timer()
        print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! lock acquired !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')

    def reset_timer(self):
        # if self.timer != None:
        #     self.timer.cancel()
        # self.timer = None
        # self.timer = threading.Timer(timeout_seconds, self.release_lock)
        # self.timer.start()
        print('timer reset')

    def release_lock(self):
        if self.lock.locked():
            self.lock.release()
            print('/////////////////////////////////////////// lock released ///////////////////////////////////////////')
    
    def get(self, request, *args, **kwargs):
        serializer = self.serializer_class
        if self.lock.locked():
            return JsonResponse({'status': 'repeat'})
        else:
            self.acquire_lock()
            capturas = list(Tareas.objects.values_list('fechayHora', flat=True))
            global code
            code = random.randint(1, 999999999999999)
            return JsonResponse({'capturas': capturas, 'num': code})
    
    def put(self, request, *args, **kwargs):
        if "release" in request.body.decode('utf-8'):
            self.release_lock()
        # elif ......

        return JsonResponse({'status': 204})
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class
        print('post')
        #Exp
        json_data = json.loads(request.body)

        idUsuarios = json_data['idUsuarios']
        nombreExperimento = json_data['nombreExperimento']
        fechaInicio = json_data['fechaInicio']
        ventanaEntreCapturas = json_data['ventanaEntreCapturas']
        numeroDeCapturas = json_data['numeroDeCapturas']
        aplicacion = json_data['aplicacion']
        nombreProyecto = json_data['nombreProyecto']
        condiciones = json_data['Condiciones']
        fecha = fechaInicio.split(' ')[0]
        hora = fechaInicio.split(' ')[1]
        año = int(fecha.split('-')[0])
        mes = int(fecha.split('-')[1])
        dia = int(fecha.split('-')[2])
        h = int(hora.split(':')[0])
        m = int(hora.split(':')[1])

        # Experimento
        experimento = Experimentos.objects.create(
            nombreExperimento=nombreExperimento,
            fechaInicio=str(datetime.datetime(year=año,month=mes,day=dia,hour=h,minute=m)),
            ventanaEntreCapturas=ventanaEntreCapturas,
            numeroDeCapturas=numeroDeCapturas,
            idUsuarios_id=idUsuarios,
            aplicacion=aplicacion,
            nombreProyecto=nombreProyecto
        )

        #Tareas
        fechayhora = datetime.datetime(year=año,month=mes,day=dia,hour=h,minute=m)
        for i in range(int(numeroDeCapturas)):
            tarea = Tareas.objects.create(
                fechayHora=str(fechayhora),
                idUsuarios_id=idUsuarios,
                idExperimentos=experimento,
                estado='pendiente',
            )
            fechayhora += datetime.timedelta(minutes=ventanaEntreCapturas)
        
        #Cond + Placas
        for c in condiciones:

            condicion = Condiciones.objects.create(
                nombreCondicion=c,
                descripcionCondicion='descripcionCondicion',
                nCondiciones=len(condiciones),
                idExperimentos=experimento,
            )

            for pl in condiciones[c]:
                placa = Placas.objects.create(
                    idPallets=pl[0],
                    idExperimentos=experimento,
                    idCondiciones=condicion,
                    tipoPlaca=pl[1],
                )

        self.release_lock()
        return JsonResponse({'success': True})
            
#       ------Panel de Control------

class ControlView(View):
    def get(self, request, *args, **kwargs):
        id_experimentos = Tareas.objects.exclude(estado='borrada').values_list('idExperimentos', flat=True).distinct()
        experimentos = []
        for id in id_experimentos:
            experimento = Experimentos.objects.get(idExperimentos=id)
            nombreExperimento = experimento.nombreExperimento
            aplicacion = experimento.aplicacion
            nombreProyecto = experimento.nombreProyecto
            tareas_totales = Tareas.objects.filter(idExperimentos=id)
            tareas_acabadas = Tareas.objects.filter(idExperimentos=id).exclude(estado='borrada')
            experimentos.append({
                'id': id,
                'nombre': nombreExperimento,
                'aplicacion': aplicacion,
                'proyecto': nombreProyecto,
                'porcentaje': len(tareas_acabadas)/len(tareas_totales)*100,
            })

        return JsonResponse({'experimentos':experimentos})

class ControlExpView(View):
    def get(self, request,  *args, **kwargs):
        experimento = Experimentos.objects.get(idExperimentos= self.kwargs['pk'])
        
        #info
        nombreExperimento = experimento.nombreExperimento
        aplicacion = experimento.aplicacion
        nombreProyecto = experimento.nombreProyecto
        
        tareas_totales = Tareas.objects.filter(idExperimentos= self.kwargs['pk'])
        placas_totales = Placas.objects.filter(idExperimentos= self.kwargs['pk'])
        
        #condiciones
        condiciones = Condiciones.objects.filter(idExperimentos= self.kwargs['pk']).values_list('nombreCondicion', flat=True)
        
        #placas
        placas = Placas.objects.filter(idExperimentos= self.kwargs['pk']).values_list('idPlacas', flat=True)
        
        #capturas
        capturas = Tareas.objects.filter(idExperimentos= self.kwargs['pk']).values_list('fechayHora', flat=True)
        events = []
        
        for t in capturas:
            events.append({
                'title': nombreExperimento,
                'start': t,
                'allDay': False
            })
        
        data = {
            'nombre':nombreExperimento,
            'proyecto':nombreProyecto,
            'aplicacion':aplicacion,
            'nplacas':len(placas_totales),
            'ncapturas':len(tareas_totales),
            'condiciones': list(condiciones),
            'placas': list(placas),
            'capturas': events,
        }
        
        
        return JsonResponse(data)

    def put(self, request, *args, **kwargs):
        json_data = json.loads(request.body)

        table = json_data['table']
        id = json_data['id']

        print(f'{table}')
        print(id)
        if table == 'Placas':
            try:
                with transaction.atomic():
                    placa = Placas.objects.get(idPlacas=id, idExperimentos=self.kwargs['pk'])
                    placa.cancelada = True
                    placa.save()
                    return JsonResponse({'message': 'Placa cancelada'})
            except Placas.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Placa not found'})
        
        elif table == 'Condiciones':
            try:
                with transaction.atomic():
                    placas = Placas.objects.filter(idCondiciones=id, idExperimentos=self.kwargs['pk']).values_list('idPlacas', flat=True)
                    for idPlaca in placas:
                        placa = Placas.objects.get(idPlacas=idPlaca, idExperimentos=self.kwargs['pk'])
                        placa.cancelada = True
                        placa.save()
                    return JsonResponse({'message': 'Condicion cancelada'})
            except Placas.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Placa not found'})
            
        elif table == 'Tareas':
            try:
                with transaction.atomic():
                    # 2023-03-03T08:30:00.000Z -> 2023-03-03 08:30:00.000
                    tarea = Tareas.objects.get(fechayHora=id[:-1].replace('T',' '), idExperimentos=self.kwargs['pk'])
                    tarea.cancelada = True
                    tarea.save()
                    return JsonResponse({'message': 'Tarea cancelada'})
            except Tareas.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Tarea not found'})
        
        return JsonResponse({'message': 'table not found'})

    def delete(self, request, *args, **kwargs):
        try:
            experimento = Experimentos.objects.get(idExperimentos=self.kwargs['pk'])
            experimento.delete()
        except Experimentos.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Experimento not found'})
        
        return JsonResponse({'message': 'Experimento eliminado'})

#       ------Resultados------

class ResultView(View):
    def get(self, request, *args, **kwargs):
        id_experimentos = Tareas.objects.filter(estado='borrada').values_list('idExperimentos', flat=True).distinct()
        experimentos = []
        for id in id_experimentos:
            experimento = Experimentos.objects.get(idExperimentos=id)
            nombreExperimento = experimento.nombreExperimento
            aplicacion = experimento.aplicacion
            nombreProyecto = experimento.nombreProyecto
            experimentos.append({
                'id': id,
                'nombre': nombreExperimento,
                'aplicacion': aplicacion,
                'proyecto': nombreProyecto,
            })
            
        return JsonResponse({'experimentos':experimentos})

class ResultExpView(View):
    def get(self, request, *args, **kwargs):
        experimento = Experimentos.objects.get(idExperimentos=self.kwargs['pk'])
        aplicacion = experimento.aplicacion
        idcondiciones = Condiciones.objects.filter(idExperimentos=self.kwargs['pk']).values_list('idCondiciones', flat=True)
        print(aplicacion)
        if aplicacion == 'lifespan':
           condiciones = {}
           placas = {}
           for idCondicion in idcondiciones:
            idplacas = Placas.objects.filter(idCondiciones=idCondicion).values_list('idPlacas', flat=True)
            condiciones[Condiciones.objects.get(idCondiciones=idCondicion).nombreCondicion] = idplacas
            ####### FILTRAR CONDICIONES CANCELADAS
            for idPlaca in idplacas:
                placas[idPlaca] = Resultados_lifespan.objects.filter(idPlacas=idPlaca).values_list('vivos', flat=True)

            #######  BUSCAR TABLA RESULTADOS
            return  JsonResponse({'condiciones': list(condiciones), 'placas': list(placas)})

        if aplicacion == 'healthspan':
            pass

        return JsonResponse({'message':1})
        
        


from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView

class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Add custom claims
        token['username'] = user.username
        # ...

        return token

class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer
