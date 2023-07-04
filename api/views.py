import datetime
import threading
import json
import pytz
import time
import random
import requests
import base64

from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.generics import RetrieveAPIView, ListAPIView

from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.db import transaction, utils
from django.utils import timezone
from django.views import View
from .models import Experimentos, Tareas, Placas, Condiciones, Resultados_lifespan, Dispositivos, Pallets
from django.db.models import Count
from django.db.models.functions import Substr
from .serializers import CreateEnsayoSerializer
from .serializers import PalletsSerializer, PlacasSerializer, PalletPlacasSerializer, DispositivosSerializar


# Create your views here.INSERT INTO api_dispositivos (IP, modelo, imgsPath)

timeout_seconds = 30

code = None

#           --PLANIFICADOR--
#       ------Dispositivo------

class DispositivoView(APIView):
    def get(self, request, *args, **kwargs):
        dispositivo = Dispositivos.objects.first()
        if dispositivo.modelo == 'miniTower':
            capacidad = 18
        else: return JsonResponse({'error': 'Error: Modelo desconocido'})
        
        pallets = Pallets.objects.all()
        pallets_ocupados = len(pallets)

        experimentos = Experimentos.objects.all()
        nExp = 0
        for exp in experimentos:
            fechaInicio = exp.fechaInicio
            ventanaEntreCapturas = exp.ventanaEntreCapturas
            numeroDeCapturas = exp.numeroDeCapturas
            fechafinal = fechaInicio + datetime.timedelta(minutes=ventanaEntreCapturas*numeroDeCapturas)
            if fechafinal > timezone.now():
                nExp += 1
        return JsonResponse({'pallets_disponibles': capacidad-pallets_ocupados, 'pallets_ocupados': pallets_ocupados, 'nExp': nExp})

class DispositivoTareasView(APIView):
    def get(self, request, *args, **kwargs):
        tareas = list(Tareas.objects.filter(estado='pendiente').values_list('fechayHora', 'idExperimentos'))
        formated = []
        for tarea in tareas:
            exp = Experimentos.objects.get(idExperimentos=tarea[1])
            formated.append((tarea[0],exp.color, exp.nombreExperimento))
        return JsonResponse({'tareas': formated})

#       ------Nuevo Ensayo------

class NewView(APIView):
    permission_classes = [IsAuthenticated]
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
            get=[]
            self.acquire_lock()
            capturas = list(Tareas.objects.values_list('fechayHora', 'idExperimentos'))
            for i in range(len(capturas)):
                experimento = Experimentos.objects.filter(idExperimentos=capturas[i][1]).first()
                get.append((capturas[i][0],experimento.nombreExperimento))
            almacenes = {}
            dispositivo = Dispositivos.objects.first()
            ### TODO Implementar otros dispositivos...
            if dispositivo.modelo == "miniTower":
                almacenes[1] = [0,0,0,0,0,0,0,0,0]
                almacenes[2] = [0,0,0,0,0,0,0,0,0]
            pallets  = Pallets.objects.all()
            for pallet in pallets:
                localizacion = pallet.localizacion
                almacen = int(localizacion[1])
                num_pallet = (int(localizacion[4])-1)*9 + int(localizacion[7]) - 1
                almacenes[almacen][num_pallet] = 1
            return JsonResponse({'capturas': get, 'almacenes': almacenes})
    
    def put(self, request, *args, **kwargs):
        if "release" in request.body.decode('utf-8'):
            self.release_lock()
        # elif ......

        return JsonResponse({'status': 204})
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class
        json_data = json.loads(request.body)

        ### DATOS
        nombreExperimento = json_data['datos']['nombreExperimento']
        nombreProyecto = json_data['datos']['nombreProyecto']
        aplicacion = json_data['datos']['aplicacion']
        color = json_data['datos']['color']
        idUsuarios = json_data['datos']['userId']
        dispositivo = Dispositivos.objects.first()

        ### CONDICIONES
        nCondiciones = json_data['condiciones']['nCondiciones']
        condiciones = json_data['condiciones']['condiciones']
        placas = json_data['condiciones']['placas']

        ### CAPTURA
        fechaInicio = json_data['captura']['fechaInicio']
        ventanaEntreCapturas = json_data['captura']['ventanaEntreCapturas']
        numeroDeCapturas = json_data['captura']['numeroDeCapturas']
        pallets = json_data['captura']['pallets']
        placasPorCondicion = json_data['captura']['placasPorCondicion']
        tareas = json_data['captura']['tareas']
        fecha = fechaInicio.split(' ')[0]
        hora = fechaInicio.split(' ')[1]
        año = int(fecha.split('-')[0])
        mes = int(fecha.split('-')[1])
        dia = int(fecha.split('-')[2])
        h = int(hora.split(':')[0])
        m = int(hora.split(':')[1])


        ### PARAMETROS
        tipoImg = json_data['parametros']['tipoImg']
        resolucion = json_data['parametros']['resolucion']
        frecuencia = json_data['parametros']['frecuencia']
        nImgs = json_data['parametros']['nImgs']

        ### CHANGES
        changes = json_data['changes']

        ### Experimento
        experimento = Experimentos.objects.create(
            nombreExperimento=nombreExperimento,
            fechaInicio=str(datetime.datetime(year=año,month=mes,day=dia,hour=h,minute=m)),
            ventanaEntreCapturas=ventanaEntreCapturas,
            numeroDeCapturas=numeroDeCapturas,
            idUsuarios_id=idUsuarios,
            aplicacion=aplicacion,
            nombreProyecto=nombreProyecto,
            tipoImgs=tipoImg,
            resolucionImgs=resolucion,
            numeroImgs=nImgs,
            frecuencia=frecuencia,
            color=color,
        )

        ### Tareas
        for tarea in tareas:
            fechaInicio = tarea['event']
            holguraPositiva = tarea['holguraPositiva']
            holguraNegativa = tarea['holguraNegativa']

            fecha = fechaInicio.split('T')[0]
            hora = fechaInicio.split('T')[1]
            año = int(fecha.split('-')[0])
            mes = int(fecha.split('-')[1])
            dia = int(fecha.split('-')[2])
            h = int(hora.split(':')[0])
            m = int(hora.split(':')[1])

            tarea = Tareas.objects.create(
                # idDispositivos = dispositivo,
                fechayHora=str(datetime.datetime(year=año,month=mes,day=dia,hour=h,minute=m)),
                idUsuarios_id=idUsuarios,
                idExperimentos=experimento,
                estado='pendiente',
                holguraPositiva=holguraPositiva,
                holguraNegativa=holguraNegativa,
                cancelada=False,
            )

        ### Pallets
        palletsBBDD = []
        for pallet in pallets:
            pallets = Pallets.objects.create(
                idDispositivos=dispositivo,
                localizacion=pallet,
                
            )
            palletsBBDD.append(pallets.idPallets)
        
        ### Cond + Placas
        for c in condiciones:
            condicion = Condiciones.objects.create(
                nombreCondicion=c['name'],
                nCondiciones=nCondiciones,
                idExperimentos=experimento,
            )

            if(c['name']!=''):
                for pl in placas[c['name']]:
                    placa = Placas.objects.create(
                        idPallets=palletsBBDD[pl['pallet']],
                        idExperimentos=experimento,
                        idCondiciones=condicion,
                        cancelada=False,
                        posicion=pl['posicion'],
                    )

        ### Changes
        if len(changes) > 0:
            for change in changes:
                tarea = Tareas.objects.get(idTareas=change[0])
                fechayHora = change[1]
                fecha = fechayHora.split('T')[0]
                hora = fechayHora.split('T')[1]
                año = int(fecha.split('-')[0])
                mes = int(fecha.split('-')[1])
                dia = int(fecha.split('-')[2])
                h = int(hora.split(':')[0])
                m = int(hora.split(':')[1])
                tarea.fechayHora = str(datetime.datetime(year=año,month=mes,day=dia,hour=h,minute=m))
                tarea.holguraPositiva = change[2]
                tarea.holguraNegativa = change[3]
                tarea.save()


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
        color = experimento.color
        
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
                'allDay': False,
                'color': color
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
            return  JsonResponse({'aplicacion': aplicacion,'condiciones': list(condiciones), 'placas': list(placas)})

        if aplicacion == 'healthspan':
            return JsonResponse({'aplicacion': aplicacion})

        return JsonResponse({'message':1})
        
#       ------Configuración------

import json

class DispConfig(APIView):
    # permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        with open('./data/dispositivos.json', 'r') as f:
            data = json.load(f)
            return JsonResponse(data)
        
    def post(self, request, *args, **kwargs):
        body_unicode = request.body.decode('utf-8')
        data = json.loads(body_unicode)

        with open('./data/dispositivos.json', 'r') as f:
            existing_data = json.load(f)
            dispositivos = existing_data.get('dispositivos', [])
        nDisp_values = [device['nDisp'] for device in dispositivos]
        IP_values = [device['IP'] for device in dispositivos]
        if data['nDisp'] not in nDisp_values:
            if data['IP'] not in IP_values:
                dispositivos.append(data)
                with open('./data/dispositivos.json', 'w') as f:
                    f.write(json.dumps({"dispositivos": dispositivos}))
                    return JsonResponse({'message':1})
            else:
                return JsonResponse({'error': 'IP'})
        else:
            return JsonResponse({'error': 'nDisp'})
        
class DispIndividual(APIView):
    def get(self, request, *args, **kwargs):
        with open('./data/dispositivos.json', 'r') as f:
            data = json.load(f)
        for device in data['dispositivos']:
            if int(device['nDisp']) == int(self.kwargs['pk']):
                return JsonResponse(device)
        return JsonResponse({'error': 'Error: Entry not found.'})
    
    def put(self, request, *args, **kwargs):
        new_dispositivos = []
        body_unicode = request.body.decode('utf-8')
        body = json.loads(body_unicode)

        with open('./data/dispositivos.json', 'r') as f:
            data = json.load(f)
        
        nDisp_values = [int(device['nDisp']) for device in data['dispositivos']]

        if (int(body['nDisp']) in nDisp_values) and (int(body['nDisp']) != int(self.kwargs['pk'])):
            return JsonResponse({'error': 'nDisp'})
        
        dispositivos = data['dispositivos']
        for device in dispositivos:
            if int(device['nDisp']) == int(self.kwargs['pk']):
                new_dispositivos.append(body)
            else:
                new_dispositivos.append(device)
        
        with open('./data/dispositivos.json', 'w') as f:
            f.write(json.dumps({"dispositivos": new_dispositivos}))
        
        return JsonResponse({'message':1})
        
    def delete(self, request, *args, **kwargs):
        id = self.kwargs['pk']
        with open('./data/dispositivos.json', 'r') as f:
            data = json.load(f)
        
        if 'dispositivos' in data:
            dispositivos = data['dispositivos']
            if id < len(dispositivos):
                del dispositivos[id]
                data['dispositivos'] = dispositivos
                with open('./data/dispositivos.json', 'w') as f:
                    json.dump(data, f)

                return JsonResponse({'message': 1})
    
        return JsonResponse({'message': 'Error: Entry not found.'})



class PlanifConfig(APIView):
    def get(self, request, *args, **kwargs):
        with open('./data/planificador.json', 'r') as f:
            data = json.load(f)
            return JsonResponse(data)
        
    def post(self, request, *args, **kwargs):
        body_unicode = request.body.decode('utf-8')

        with open('./data/planificador.json', 'r') as f:
            existing_data = json.load(f)
            configs = existing_data.get('planificador', [])

        nombre_values = [device['nombre'] for device in configs]
        ids_values = [int(device['id']) for device in configs]
        if (ids_values): max_id = max(ids_values)
        else: max_id = 0
        data = json.loads(body_unicode)
        data['id'] = max_id + 1

        if data['nombre'] not in nombre_values:
            configs.append(data)
            with open('./data/planificador.json', 'w') as f:
                f.write(json.dumps({"planificador": configs}))
                return JsonResponse({'message':1})
        else:
            return JsonResponse({'error': 'nombre'})
        
class PlanifIndividual(APIView):
    def get(self, request, *args, **kwargs):
        with open('./data/planificador.json', 'r') as f:
            data = json.load(f)
        for planif in data['planificador']:
            if str(planif['id']) == str(self.kwargs['pk']):
                return JsonResponse(planif)
        return JsonResponse({'error': 'Error: Entry not found.'})
    
    def put(self, request, *args, **kwargs):
        new_planificador = []
        body_unicode = request.body.decode('utf-8')
        body = json.loads(body_unicode)
        with open('./data/planificador.json', 'r') as f:
            data = json.load(f)
        
        if 'planificador' in data:
            planificador = data['planificador']
            
            for planif in planificador:
                if str(planif['id']) != str(self.kwargs['pk']):
                    new_planificador.append(planif)
            
            new_planificador.append(body)
            with open('./data/planificador.json', 'w') as f:
                json.dump({"planificador": new_planificador}, f)
            
            return JsonResponse({'message':1})
    def delete(self, request, *args, **kwargs):
        new_planificador = []
        with open('./data/planificador.json', 'r') as f:
            data = json.load(f)
        
        if 'planificador' in data:
            planificador = data['planificador']
            
            for planif in planificador:
                if str(planif['id']) != str(self.kwargs['pk']):
                    new_planificador.append(planif)
            
            with open('./data/planificador.json', 'w') as f:
                json.dump({"planificador": new_planificador}, f)
            
            return JsonResponse({'message': 1})
        return JsonResponse({'error':"Error reading data"})
        
class PlacasConfig(APIView):
    def get(self, request, *args, **kwargs):
        with open('./data/placas.json', 'r') as f:
            data = json.load(f)
            return JsonResponse(data)
        
    def post(self, request, *args, **kwargs):
        body_unicode = request.body.decode('utf-8')

        with open('./data/placas.json', 'r') as f:
            existing_data = json.load(f)
            configs = existing_data.get('placas', [])

        nombre_values = [dist['nombre'] for dist in configs]
        ids_values = [int(dist['id']) for dist in configs]

        if (ids_values): max_id = max(ids_values)
        else: max_id = 0

        data = json.loads(body_unicode)
        data['id'] = max_id + 1

        if data['nombre'] not in nombre_values:
            configs.append(data)
            with open('./data/placas.json', 'w') as f:
                f.write(json.dumps({"placas": configs}))
                return JsonResponse({'message':1})
        else:
            return JsonResponse({'error': 'nombre'})

class PlacasIndividual(APIView):
    def get(self, request, *args, **kwargs):
        with open('./data/placas.json', 'r') as f:
            data = json.load(f)
        for placas in data['placas']:
            if str(placas['id']) == str(self.kwargs['pk']):
                return JsonResponse(placas)
        return JsonResponse({'error': 'Error: Entry not found.'})
    
    def put(self, request, *args, **kwargs):
        new_placas = []
        body_unicode = request.body.decode('utf-8')
        body = json.loads(body_unicode)
        with open('./data/placas.json', 'r') as f:
            data = json.load(f)
        
        if 'placas' in data:
            placas = data['placas']
            
            for placa in placas:
                if str(placa['id']) != str(self.kwargs['pk']):
                    new_placas.append(placa)
            
            new_placas.append(body)
            with open('./data/placas.json', 'w') as f:
                json.dump({"placas": new_placas}, f)
            
        return JsonResponse({'message':1})
    def delete(self, request, *args, **kwargs):
        new_placas = []
        with open('./data/placas.json', 'r') as f:
            data = json.load(f)
        
        if 'placas' in data:
            placas = data['placas']
            
            for placa in placas:
                if str(placa['id']) != str(self.kwargs['pk']):
                    new_placas.append(placa)
            
            with open('./data/placas.json', 'w') as f:
                json.dump({"placas": new_placas}, f)
            
            return JsonResponse({'message': 1})
        return JsonResponse({'error':"Error reading data"})

#       ------Token------

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


#           --LOCAL--
class LocalDispositivosView(APIView):
    def get(self, request, *args, **kwargs):
        queryset = Dispositivos.objects.all()
        serializer = DispositivosSerializar(queryset, many=True)
        return Response(serializer.data)

class LocalPalletsView(APIView):
    def get(self, request, *args, **kwargs):
        queryset = Pallets.objects.all()
        serializer = PalletsSerializer(queryset, many=True)
        return Response(serializer.data)

class LocalPlacasView(APIView):
    def get(self, request, *args, **kwargs):
        queryset = Placas.objects.all()
        serializer = PlacasSerializer(queryset, many=True)
        return Response(serializer.data)
    
class LocalPlacasDetailView(RetrieveAPIView):
    queryset = Placas.objects.all()
    serializer_class = PlacasSerializer
    lookup_field = 'idPlacas'

class LocalPalletPlacasView(RetrieveAPIView):
    queryset = Pallets.objects.all()
    serializer_class = PalletPlacasSerializer
    lookup_url_kwarg = 'number_of_pallet'
    lookup_field = 'idPallets'

class LocalPalletsByAlmacenView(ListAPIView):
    serializer_class = PalletsSerializer

    def get_queryset(self):
        a_number = self.kwargs['a_number']
        queryset = Pallets.objects.filter(localizacion__startswith=f"{a_number}")
        queryset = sorted(queryset, key=lambda p: local_extract_p_position(p.localizacion))
        queryset = sorted(queryset, key=lambda p: local_extract_c_position(p.localizacion))
        return queryset
    
class LocalAlmacenesView(ListAPIView):
    def get(self, request):
        a_count = Pallets.objects.annotate(AlmacenesC=Substr('localizacion', 1, 2)).values('AlmacenesC').annotate(count=Count('AlmacenesC')).order_by('AlmacenesC')
        return Response(a_count)
    
class LocalCListView(ListAPIView):
    def get(self, request, a_number):
        c_values = Pallets.objects.filter(localizacion__startswith=a_number).annotate(c_number=Substr('localizacion', 4, 2)).values('c_number').distinct().order_by('c_number')
        return Response(c_values)

class LocalPListView(ListAPIView):
    serializer_class = PalletsSerializer

    def get_queryset(self):
        a_number = self.kwargs['a_number']
        c_number = self.kwargs['c_number']
        queryset = Pallets.objects.filter(localizacion__startswith=f"{a_number}-{c_number}")
        queryset = sorted(queryset, key=lambda p: local_extract_p_position(p.localizacion))
        return queryset

import re

def local_extract_c_position(localizacion):
    parts = localizacion.split('-')
    c_part = parts[1]
    c_value = re.search(r'\d+', c_part)
    if c_value:
        return int(c_value.group())
    return 0

def local_extract_p_position(localizacion):
    parts = localizacion.split('-')
    p_part = parts[2]
    p_value = re.search(r'\d+', p_part)
    if p_value:
        return int(p_value.group())
    return 0

@api_view(['GET'])
def local_switch_pallets(request, dragged_pallet_id, target_pallet_id):
    try:
        dragged_pallet = Pallets.objects.get(idPallets=dragged_pallet_id)
        target_pallet = Pallets.objects.get(idPallets=target_pallet_id)

        # Perform the switching of desired attributes between the pallets
        aux1 = target_pallet.localizacion
        aux2 = dragged_pallet.localizacion
        #dragged_pallet.localizacion, target_pallet.localizacion = target_pallet.localizacion, dragged_pallet.localizacion
        dragged_pallet.localizacion = aux1
        target_pallet.localizacion = aux2
        dragged_pallet.save()
        target_pallet.save()

        # Create a response JSON with the updated values
        response_data = {
            'success': True,
            'dragged_pallet': {
                'localizacion': dragged_pallet.localizacion,
            },
            'target_pallet': {
                'idExperimentos': target_pallet.localizacion,
            }
        }

        # Return the response
        return Response(response_data)
    except Pallets.DoesNotExist:
        # Return an error response if the pallets are not found
        response_data = {'success': False, 'message': 'Pallets not found'}
        return Response(response_data)
    
def local_get_color_of_pallet(request, idPallet):
    return 1
    
def local_message_pos_z(request, new_z_position):

    data = "ZPos:" + str(new_z_position)
    url = "http://192.168.1.118:8095/publish/"
    response = requests.post(url, data=data)

    if response.status_code == 200:
        return JsonResponse({'Correcto': 'Posición en \'Z\' enviada correctamente'})

    else:
        return JsonResponse({'Error': 'Posición en \'Z\' no enviada correctamente'})
    
def local_message_pallet_selection(request, id_pallet):

    data = "Selected Pallet: " + str(id_pallet)
    url = "http://192.168.1.118:8095/publish/"
    response = requests.post(url, data=data)

    if response.status_code == 200:
        return JsonResponse({'Correcto': 'Pallet seleccionado correctamente'})

    else:
        return JsonResponse({'Error': 'No ha sido posible seleciconar pallet'})
    
def local_emergency_stop(request):

    data = "Performing emergency stop"
    url = "http://192.168.1.118:8095/publish/"
    response = requests.post(url, data=data)

    if response.status_code == 200:
        return JsonResponse({'Correcto': 'Parada de emergencia correcta.'})

    else:
        return JsonResponse({'Error': 'Mostrando mensaje de error.'})
    
def local_get_color_by_idPallets(request, idPallet):

    try:
        placa = Placas.objects.filter(idPallets=idPallet).first()
        color = '#' + str(placa.idExperimentos.color) if placa else "#CBCBD1"  # Use the first Placa's Experimento color or return default color
    except Exception as e:
        color = "#cbcbd1"  # Return a default color in case of any error

    return JsonResponse({'color': color})

def local_get_color_by_almacen(request, almacen_id):
    try:
        # Fetch all the pallets associated with the given almacen_id
        pallets = Pallets.objects.filter(localizacion__startswith=f"{almacen_id}")
        pallets = sorted(pallets, key=lambda p: local_extract_p_position(p.localizacion))
        pallets = sorted(pallets, key=lambda p: local_extract_c_position(p.localizacion))
        color_list = []

        # Iterate through each pallet and fetch the color by its Placas
        for pallet in pallets:
            placa = Placas.objects.filter(idPallets=pallet.idPallets).first()
            if(pallet.idPallets==14):
                print('soy el pallet 14: ' + str(placa.idPlacas))
            color = str(placa.idExperimentos.color) if placa else "#CBCBD1"
            color_list.append(color)

        return JsonResponse({'colors': color_list})

    except Exception as e:
        return JsonResponse({'error': str(e)})

latest_image_data = ''
counter = 0

@csrf_exempt
def local_image_callback(request):
    image_data = request.body

    image_data_encoded = base64.b64encode(image_data).decode('utf-8')

    global latest_image_data
    latest_image_data = image_data_encoded

    return JsonResponse({'message': 'Image saved successfully'})

def local_image_view(request):
    global latest_image_data

    context = {
        'image_data_encoded': latest_image_data
    }

    return JsonResponse(context)