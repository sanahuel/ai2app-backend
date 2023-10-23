import datetime
import threading
import json
import pytz
import time
import random
import requests
import base64
import subprocess
import os

from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.generics import RetrieveAPIView, ListAPIView

from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.db import transaction, utils
from django.utils import timezone
from django.views import View
from .models import Experimentos, Tareas, Placas, Condiciones, Resultados_lifespan, Resultados_healthspan, Dispositivos, Pallets
from django.db.models import Count
from django.db.models.functions import Substr
from .serializers import CreateEnsayoSerializer
from .serializers import PalletsSerializer, PlacasSerializer, PalletPlacasSerializer, DispositivosSerializar


# Create your views here.INSERT INTO api_dispositivos (IP, modelo, imgsPath)

TIME_ZONE = "Europe/Madrid"

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

        experimentos = Experimentos.objects.exclude(estado="borrada")
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
def check_tareas(tareas):
    # TODO cambiar duacion????
    duracion = 60 #min

    pass

class NewView(APIView):
    # permission_classes = [IsAuthenticated]
    serializer_class = CreateEnsayoSerializer
    lock = threading.Lock()
    
    def acquire_lock(self):
        self.lock.acquire() # ////////////////////////////////// TODO Poner Timeout de seguridad
        print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! lock acquired !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')

    def release_lock(self):
        if self.lock.locked():
            self.lock.release()
            print('/////////////////////////////////////////// lock released ///////////////////////////////////////////')
    
    def get(self, request, *args, **kwargs):
        print(request.body.decode('utf-8'))
        serializer = self.serializer_class
        if self.lock.locked():
            return JsonResponse({'status': 'repeat'})
        else:
            self.acquire_lock()
            get=[]
            capturas = list(Tareas.objects.filter(estado='pendiente').order_by('fechayHora').values_list('fechayHora', 'idExperimentos')) 
            # Si las capturas no están ordenadas cronológicamente el algoritmo del planificador no funcionará
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
        gusanosPorCondicion = json_data['datos']['gusanosPorCondicion']

        ### CONDICIONES
        nCondiciones = json_data['condiciones']['nCondiciones']
        condiciones = json_data['condiciones']['condiciones']
        placas = json_data['condiciones']['placas']
        tipoPlaca = json_data['condiciones']['tipoPlaca']

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

        ### COMPROBAR SOLAPES
        # check = check_tareas(tareas)
        # if check: 
        #     return JsonResponse({'success': False}) #si hay solapes no crear ensayo

        with transaction.atomic():
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
                gusanosPorCondicion=gusanosPorCondicion,
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
                meses = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']

                ## Tareas Operativo
                command = f'TZ={TIME_ZONE} ' + "at {:02d}:{:02d} {:02d} {} {} -f /home/usuario/Escritorio/ai2app-backend/dummy.py 2>&1 | awk 'END{{print $2}}'".format(h, m, dia, meses[mes-1], str(año))
                print(f'===============command============')
                print(command)
                print('====================================')
                output = subprocess.check_output(command, shell=True).decode().strip()

                tarea = Tareas.objects.create(
                    idDispositivos = dispositivo,
                    fechayHora=str(datetime.datetime(year=año,month=mes,day=dia,hour=h,minute=m)), ###h+2 TODO cambiar...zona horaria
                    idUsuarios_id=idUsuarios,
                    idExperimentos=experimento,
                    estado='pendiente',
                    holguraPositiva=holguraPositiva,
                    holguraNegativa=holguraNegativa,
                    cancelada=False,
                    idOperativo=int(output),
                )

            ### Pallets
            palletsBBDD = []
            for pallet in pallets:
                pallets = Pallets.objects.create(
                    idDispositivos=dispositivo,
                    localizacion=pallet,
                )
                palletsBBDD.append(pallets)
            
            ### Cond + Placas
            for c in condiciones:
                if(c['name']!=''):
                    condicion = Condiciones.objects.create(
                        nombreCondicion=c['name'],
                        nCondiciones=nCondiciones,
                        idExperimentos=experimento,
                    )
                
                    for pl in placas[c['name']]:
                        placa = Placas.objects.create(
                            idPallets=palletsBBDD[pl['pallet']],
                            idExperimentos=experimento,
                            idCondiciones=condicion,
                            cancelada=False,
                            posicion=pl['posicion'],
                            tipoPlaca=tipoPlaca,
                        )

            ### Changes TODO idOperativo
            if len(changes) > 0:
                for change in changes:
                    tarea = Tareas.objects.get(idTareas=change[0])
                    
                    # Borrar tarea antigua
                    id_operativo = tarea.idOperativo
                    output = subprocess.check_output(f'atrm {id_operativo}', shell=True)
                    print(output)
                
                    #Crear tarea nueva
                    fechayHora = change[1]
                    fecha = fechayHora.split('T')[0]
                    hora = fechayHora.split('T')[1]
                    año = int(fecha.split('-')[0])
                    mes = int(fecha.split('-')[1])
                    dia = int(fecha.split('-')[2])
                    h = int(hora.split(':')[0])
                    m = int(hora.split(':')[1])
                    meses = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
                    command = "at {:02d}:{:02d} {:02d} {} {} -f /home/usuario/Escritorio/ai2app-backend/dummy.py 2>&1 | awk 'END{{print $2}}'".format(h, m, dia, meses[mes-1], str(año))
                    output = subprocess.check_output(command, shell=True).decode().strip()
                    tarea.idOperativo = int(output)

                    # Cambiar fechayHora y holguras
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
            tareas_pendientes = Tareas.objects.filter(idExperimentos=id).filter(estado='pendiente')
            tareas_canceladas = Tareas.objects.filter(idExperimentos=id).filter(estado='cancelada')
            experimentos.append({
                'id': id,
                'nombre': nombreExperimento,
                'aplicacion': aplicacion,
                'proyecto': nombreProyecto,
                'porcentaje': (1-(len(tareas_pendientes)+len(tareas_canceladas))/len(tareas_totales)+0.01)*100,
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
        condiciones_array = []
        condiciones = Condiciones.objects.filter(idExperimentos= self.kwargs['pk']).values_list('nombreCondicion', 'idCondiciones')
        for c in condiciones:
            placas_no_canceladas = Placas.objects.filter(idCondiciones=c[1]).exclude(cancelada=True)
            condiciones_array.append([
                c[0],
                len(list(placas_no_canceladas))>0,
            ])
        print(condiciones_array)
        #placas
        placas_array = []
        placas = Placas.objects.filter(idExperimentos= self.kwargs['pk']).values_list('idPlacas', 'cancelada', 'idPallets')
        for pl in placas:
            localizacion = Pallets.objects.filter(idPallets= pl[2]).values_list('localizacion', flat=True)[0]
            placas_array.append([
                pl[0],
                pl[1],
                f'Almacen {localizacion[1]} Cassette {localizacion[4]} Pallet {localizacion[-1]}'
            ])

        #capturas
        capturas = Tareas.objects.filter(estado='pendiente').filter(idExperimentos= self.kwargs['pk']).values_list('fechayHora', 'estado')
        events = []
        id = 0
        capturas_otros = Tareas.objects.filter(estado='pendiente').exclude(idExperimentos= self.kwargs['pk']).values_list('fechayHora', 'idExperimentos')
        
        for t in capturas:
            if t[1] == 'cancelada':
                events.append({
                'title': nombreExperimento,
                'start': t[0],
                'allDay': False,
                'color': '#ddd',
                'editable': False,
                'id': id,
            })
            else:
                events.append({
                'title': nombreExperimento,
                'start': t[0],
                'allDay': False,
                'color': color,
                'id': id,
            })
            id+=1
        for t in capturas_otros:
            nombre = Experimentos.objects.filter(idExperimentos= t[1]).values_list('nombreExperimento', flat=True).first()
            events.append({
                'title': nombre,
                'start': t[0],
                'allDay': False,
                'color': '#ddd',
                'editable': False,
                'id': id,

            })
            id+=1
            
        
        data = {
            'nombre':nombreExperimento,
            'proyecto':nombreProyecto,
            'aplicacion':aplicacion,
            'nplacas':len(placas_totales),
            'ncapturas':len(tareas_totales),
            'condiciones': condiciones_array,
            'placas': placas_array,
            'capturas': events,
            'color': color,
        }
        
        
        return JsonResponse(data)

    def put(self, request, *args, **kwargs):
        json_data = json.loads(request.body)

        table = json_data['table']

        if table == 'Placas':
            id = json_data['id']
            try:
                with transaction.atomic():
                    placa = Placas.objects.get(idPlacas=id, idExperimentos=self.kwargs['pk'])
                    placa.cancelada = True
                    placa.save()
                    return JsonResponse({'message': 'Placa cancelada'})
            except Placas.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Placa not found'})
        
        elif table == 'Condiciones':
            id = json_data['id']
            try:
                with transaction.atomic():
                    condicion_id = Condiciones.objects.filter(nombreCondicion=id, idExperimentos=self.kwargs['pk']).values('idCondiciones').first()['idCondiciones']
                    placas = Placas.objects.filter(idCondiciones=int(condicion_id), idExperimentos=self.kwargs['pk']).values_list('idPlacas', flat=True)
                    for idPlaca in placas:
                        placa = Placas.objects.get(idPlacas=idPlaca, idExperimentos=self.kwargs['pk'])
                        placa.cancelada = True
                        placa.save()
                    return JsonResponse({'message': 'Condicion cancelada'})
            except Placas.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Placa not found'})
            
        elif table == 'Tareas_Cancel':
            id = json_data['id']
            try:
                with transaction.atomic():
                    # 2023-03-03T08:30:00.000Z -> 2023-03-03 08:30:00.000
                    fecha = id[:-1].replace('T',' ')
                    fecha_ajustada = fecha[:10] + ' ' + str(int(fecha[10:13])+2) + fecha[13:] # TODO Arreglar zona horaria
                    tarea = Tareas.objects.get(fechayHora=fecha_ajustada, idExperimentos=self.kwargs['pk'])
                    output = subprocess.check_output(f'atrm {tarea.idOperativo}', shell=True)
                    print(output)
                    tarea.estado = 'cancelada'
                    tarea.save()
                    return JsonResponse({'message': 'Tarea cancelada'})
            except Tareas.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Tarea not found'})
        
        elif table == 'Tareas_Drag':
            with transaction.atomic():
                from_date = json_data['from'][:-1].replace('T',' ')
                to_date = json_data['to'][:-1].replace('T',' ')            
                tarea = Tareas.objects.filter(estado='pendiente').get(fechayHora=from_date[:10] + ' ' + str(int(from_date[10:13])+2) + from_date[13:])
                tarea.fechayHora = to_date[:10] + ' ' + str(int(to_date[10:13])+2) + to_date[13:]
                
                # Borrar tarea antigua
                id_operativo = tarea.idOperativo
                output = subprocess.check_output(f'atrm {id_operativo}', shell=True)
                print(output)
                
                #Crear tarea nueva
                fecha = json_data['to'][:-1].split('T')[0]
                hora = json_data['to'][:-1].split('T')[1]
                año = int(fecha.split('-')[0])
                mes = int(fecha.split('-')[1])
                dia = int(fecha.split('-')[2])
                h = int(hora.split(':')[0])
                m = int(hora.split(':')[1])
                meses = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
                command = "at {:02d}:{:02d} {:02d} {} {} -f /home/usuario/Escritorio/ai2app-backend/dummy.py 2>&1 | awk 'END{{print $2}}'".format(h, m, dia, meses[mes-1], str(año))
                output = subprocess.check_output(command, shell=True).decode().strip()
                tarea.idOperativo = int(output)

                tarea.save()
                return JsonResponse({'message': 'Tarea editada'})

        return JsonResponse({'message': 'table not found'})

    def delete(self, request, *args, **kwargs):
        try:
            #Delete Pallets
            # idPallets = Placas.objects.filter(idExperimentos=self.kwargs['pk']).values_list('idPallets', flat=True)
            # for id in idPallets:
            #     try:
            #         pallet = Pallets.objects.get(idPallets= id)
            #         print(pallet)
            #         pallet.delete()
            #     except:
            #         pass
            
            #Delete at job
            idOperativos = Tareas.objects.filter(idExperimentos=self.kwargs['pk']).values_list('idOperativo', flat=True)
            for id in idOperativos:
                try:
                    output = subprocess.check_output(f'atrm {id}', shell=True)
                    print(output)
                except:
                    pass
            Tareas.objects.filter(idExperimentos=self.kwargs['pk']).delete()

            #Change to borrada
            experimento = Experimentos.objects.get(idExperimentos=self.kwargs['pk'])
            experimento.estado = 'borrada'
            experimento.save()

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

        ## APLICACION = LIFESPAN
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

        ## APLICACION = HEALTHSPAN
        if aplicacion == 'healthspan':
           condiciones = {}
           placas = {}
           for idCondicion in idcondiciones:
            idplacas = Placas.objects.filter(idCondiciones=idCondicion).values_list('idPlacas', flat=True)
            condiciones[Condiciones.objects.get(idCondiciones=idCondicion).nombreCondicion] = idplacas
            
            ####### FILTRAR CONDICIONES CANCELADAS
            for idPlaca in idplacas:
                placas[idPlaca] = {}
                placas[idPlaca]['cantidadMov'] = Resultados_healthspan.objects.filter(idPlacas=idPlaca).values_list('cantidadMov', flat=True)
                # otros indicadores. . .

            #######  BUSCAR TABLA RESULTADOS
            return  JsonResponse({'aplicacion': aplicacion,'condiciones': list(condiciones), 'placas': list(placas)})

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
        print(body)
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
    
class LocalExperimentosView(APIView):
    def get(self, request, *args, **kwargs):
        queryset = Experimentos.objects.all()
        queryset = Experimentos.objects.exclude(estado='descargado')
        #queryset = queryset.filter(estado__ne = 'descargado')
        serializer = ExperimentosSerializer(queryset, many=True)
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
    
@require_POST
@csrf_exempt
def local_move_pallet_to_empty(request):
    # Get the ID of the pallet and the new position from the request data

    body = json.loads(request.body)
    pallet_id = body.get('pallet_id', '')
    new_position = body.get('new_position', '')

    # Perform the logic to switch the pallet to the new position
    # ...
    print('I got this pallet ID: ' + str(pallet_id) + '. And this is the new position: ' + str(new_position))
    dragged_pallet = Pallets.objects.get(idPallets=pallet_id)
    dragged_pallet.localizacion = new_position

    dragged_pallet.save()

    # Return a JSON response indicating the success of the operation
    return JsonResponse({'success': True})
    
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

    dispositivo = Dispositivos.objects.first()

    if (dispositivo.estado == 'funciona'):
        dispositivo.estado = 'pausa'
        dispositivo.save()

    else:
        dispositivo.estado = 'funciona'
        dispositivo.save()

    if response.status_code == 200:
        return JsonResponse({'Correcto': 'Parada de emergencia correcta.', 'Estado': dispositivo.estado})

    else:
        return JsonResponse({'Error': 'Mostrando mensaje de error.'})
    
def local_get_color_by_idPallets(request, idPallet):
    try:
        placa = Placas.objects.filter(idPallets__idPallets=idPallet).first()
        color = str(placa.idExperimentos.color) if placa else "#CBCBD1"  # Use the first Placa's Experimento color or return default color
        estado = str(placa.idExperimentos.estado) if placa else "error"  # Use the first Placa's Experimento state or return default color
    except Exception as e:
        color = "#a1b1c1"  # Return a default color in case of any error
        estado = "descargado"
        print(e)

    return JsonResponse({'color': color, 'estado': estado})


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
            color = str(placa.idExperimentos.color) if placa else "#CBCBD1"
            color_list.append(color)

        return JsonResponse({'colors': color_list})

    except Exception as e:
        return JsonResponse({'error': str(e)})
    
def get_max_position(placas):
    max_rows, max_cols = 0, 0

    for placa in placas:
        #tipoPlaca = "5x3" filas x columnas
        max_rows = int(placa.tipoPlaca[0])
        max_cols = int(placa.tipoPlaca[2])
        break

    return max_rows, max_cols

class LocalDistrPallet(APIView):
    def get(self, request, *args, **kwargs):
        placas = Placas.objects.filter(idPallets=self.kwargs['idPallet'])

        # Initialize a dictionary to store the result
        result = {
            'cond': [],
            'condArray': []
        }

        # Step 1: Retrieve unique Condiciones associated with Placas
        condiciones = Condiciones.objects.filter(placas__in=placas).distinct()

        # Step 2: Populate the 'cond' array
        result['cond'] = [cond.nombreCondicion for cond in condiciones]

        # Create a dictionary to map 'nombreCondicion' to its index in 'cond'
        cond_index_map = {cond.nombreCondicion: i for i, cond in enumerate(condiciones)}

        # Step 3: Create a 2D array (condArray) to represent the matrix
        max_rows, max_cols = get_max_position(placas)

        # Initialize the 2D array with None values
        condArray = [[None for _ in range(max_cols)] for _ in range(max_rows)]

        # Populate the condArray with Placas data
        for placa in placas:
            row_str, col_str = placa.posicion.split(',')
            row = int(row_str)
            col = int(col_str)

            condArray[row][col] = cond_index_map[placa.idCondiciones.nombreCondicion]  # Use the dictionary to get the index

        result['condArray'] = condArray

        return JsonResponse(result)
    
@csrf_exempt 
def local_update_ip(request, ip):
    if request.method == 'POST':
        # Retrieve the instance of the model
        instance = get_object_or_404(Dispositivos, idDispositivos=ip)
        
        # Retrieve the new imgsPath value from the request body
        body = json.loads(request.body)
        new_ip = body.get('IP', '')
        
        # Modify the field value
        instance.IP = new_ip
        
        # Save the instance
        instance.save()
        
        # Return a success response
        return JsonResponse({'message': 'IP updated successfully'})
    
    # Return an error response for unsupported methods
    return JsonResponse({'message': 'Method not allowed'}, status=405)

@csrf_exempt 
def local_update_imgs_path(request, ip):
    if request.method == 'POST':
        # Retrieve the instance of the model
        instance = get_object_or_404(Dispositivos, idDispositivos=ip)
        
        # Retrieve the new imgsPath value from the request body
        body = json.loads(request.body)
        new_imgs_path = body.get('imgsPath', '')
        
        # Modify the field value
        instance.imgsPath = new_imgs_path
        
        # Save the instance
        instance.save()
        
        # Return a success response
        return JsonResponse({'message': 'imgsPath updated successfully'})
    
    # Return an error response for unsupported methods
    return JsonResponse({'message': 'Method not allowed'}, status=405)

@csrf_exempt 
def local_update_modelo(request, ip):
    if request.method == 'POST':
        # Retrieve the instance of the model
        instance = get_object_or_404(Dispositivos, idDispositivos=ip)
        
        # Retrieve the new imgsPath value from the request body
        body = json.loads(request.body)
        new_modelo = body.get('modelo', '')
        
        # Modify the field value
        instance.Modelo = new_modelo
        
        # Save the instance
        instance.save()
        
        # Return a success response
        return JsonResponse({'message': 'modelo updated successfully'})
    
    # Return an error response for unsupported methods
    return JsonResponse({'message': 'Method not allowed'}, status=405)

@csrf_exempt 
def local_update_n_almacenes(request, ip):
    if request.method == 'POST':
        # Retrieve the instance of the model
        instance = get_object_or_404(Dispositivos, idDispositivos=ip)
        
        # Retrieve the new imgsPath value from the request body
        body = json.loads(request.body)
        new_n_almacenes = body.get('nAlmacenes', '')
        
        # Modify the field value
        instance.nAlmacenes = new_n_almacenes
        
        # Save the instance
        instance.save()
        
        # Return a success response
        return JsonResponse({'message': 'nAlmacenes updated successfully'})
    
    # Return an error response for unsupported methods
    return JsonResponse({'message': 'Method not allowed'}, status=405) 

@csrf_exempt 
def local_update_n_cassettes(request, ip):
    if request.method == 'POST':
        # Retrieve the instance of the model
        instance = get_object_or_404(Dispositivos, idDispositivos=ip)
        
        # Retrieve the new imgsPath value from the request body
        body = json.loads(request.body)
        new_n_cassettes = body.get('nCassettes', '')
        
        # Modify the field value
        instance.nCassettes = new_n_cassettes
        
        # Save the instance
        instance.save()
        
        # Return a success response
        return JsonResponse({'message': 'nCassettes updated successfully'})
    
    # Return an error response for unsupported methods
    return JsonResponse({'message': 'Method not allowed'}, status=405)

import paramiko

@csrf_exempt 
def local_turn_on_rasp(request):
    if request.method == 'POST':
        
        # Retrieve the new imgsPath value from the request body
        body = json.loads(request.body)
        ip = body.get('auxRasP', '')

        #print(f'\n\n\n /////////// Esta es la IP de encendido: {ip} /////////// \n\n\n')
        print('Connecting to a Raspberry')
        
        # Return a success response
        return JsonResponse({'message': 'Raspberry ON'})
    
    # Return an error response for unsupported methods
    return JsonResponse({'message': 'Method not allowed'}, status=405)

@csrf_exempt 
def local_turn_off_rasp(request):
    if request.method == 'POST':
        
        # Retrieve the new imgsPath value from the request body
        body = json.loads(request.body)
        ip = body.get('auxRasP', '')

        #print(f'\n\n\n /////////// Esta es la IP de apagado: {ip} /////////// \n\n\n')
        
        # Create a client object
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            # Connect to the raspberry
            client.connect(ip, username="pi", password="raspberry")
            time.sleep(2)

            # Execute the commands
            # Start a single shell session and run multiple commands
            shell = client.invoke_shell()

            # Execute the commands
            stdin, stdout, stderr = client.exec_command("sudo halt")

        except paramiko.SSHException as e:
            print(f"SSH Exception: {e}")
        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            client.close()

        # Return a success response
        return JsonResponse({'message': 'Raspberry OFF'})
    
    # Return an error response for unsupported methods
    return JsonResponse({'message': 'Method not allowed'}, status=405)

@csrf_exempt 
def local_reboot_rasp(request):
    if request.method == 'POST':
        
        # Retrieve the new imgsPath value from the request body
        body = json.loads(request.body)
        ip = body.get('auxRasP', '')

        #print(f'\n\n\n /////////// Esta es la IP de reboot: {ip} /////////// \n\n\n')
        
        # Create a client object
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            # Connect to the raspberry
            client.connect(ip, username="pi", password="raspberry")
            time.sleep(2)

            # Execute the commands
            # Start a single shell session and run multiple commands
            shell = client.invoke_shell()

            # Execute the commands
            stdin, stdout, stderr = client.exec_command("sudo reboot")

        except paramiko.SSHException as e:
            print(f"SSH Exception: {e}")
        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            client.close()

        # Return a success response
        return JsonResponse({'message': 'Rebooting Raspberry'})
    
    # Return an error response for unsupported methods
    return JsonResponse({'message': 'Method not allowed'}, status=405)

@csrf_exempt 
def local_stop_dockers(request):
    if request.method == 'POST':
        
        # Retrieve the new imgsPath value from the request body
        body = json.loads(request.body)
        ip = body.get('auxRasP', '')

        # Create a client object
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            # Connect to the raspberry
            client.connect(ip, username="pi", password="raspberry")
            time.sleep(2)

            # Execute the commands
            # Start a single shell session and run multiple commands
            shell = client.invoke_shell()

            # Execute the commands
            stdin, stdout, stderr = client.exec_command("docker kill $(docker ps -q)")

        except paramiko.SSHException as e:
            print(f"SSH Exception: {e}")
        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            client.close()

        # Return a success response
        return JsonResponse({'message': 'Dockers Stopped'})
    
    # Return an error response for unsupported methods
    return JsonResponse({'message': 'Method not allowed'}, status=405)

# TURN ON CAMERA

name_docker = 'ubuntu:latest_2'
ros_workspace = '/home/pi/ros2_ws_raspberry:/home/ros2_ws_raspberry/'
docker_down_flag = False

def check_docker_processes(IP):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        # Connect to the raspberry
        client.connect(IP, username="pi", password="raspberry")

        # Execute the commands
        # Start a single shell session and run multiple commands
        shell = client.invoke_shell()

        # Execute the commands within the same shell
        stdin, stdout, stderr = client.exec_command("ps -la | grep camara")
        output = stdout.read().decode('utf-8').strip()
        print(f'Recibo esto: {output}')
        if not output:
            return 0
            
        else:
            return 1
        
    except paramiko.SSHException as e:
        print(f"SSH Exception: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        client.close()

def ssh_launch_cameras(IP):
    print('Connecting to a Raspberry')
    # Create a client object
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    run_docker = "docker run --rm -it --net=host " + \
                 "--privileged " + \
                 "--tmpfs /dev/shm:exec " + \
                 "-v /run/udev:/run/udev:ro " + \
                 "-e MTX_PATHS_CAM_SOURCE=rpiCamera " + \
                 "-v /tmp/.X11-unix:/tmp/.X11-unix:ro " + \
                 "-e DISPLAY=$DISPLAY " + \
                 "-v " + ros_workspace + " " + \
                 name_docker

    try:
        # Connect to the raspberry
        client.connect(IP, username="pi", password="raspberry")

        # Execute the commands
        # Start a single shell session and run multiple commands
        shell = client.invoke_shell()

        # Execute the commands within the same shell
        shell.send("export DISPLAY=:0\n")
        shell.send("xhost +\n")
        shell.send(run_docker + "\n")
        print('Connecting to the docker')

        shell.send("ulimit -c 0\n")
        shell.send("cd /home/ros2_ws_raspberry/\n")
        shell.send("source install/setup.bash\n")
        shell.send("ros2 run camara_hq_completo_ros2 camara_hq_completo_ros2_node\n")
        time.sleep(10)

        global docker_down_flag
        while docker_down_flag != True:
            # Do something useless to stop the thread from finishing
            aux = check_docker_processes(IP)
            
            if aux == 0:
                docker_down_flag = True
                
            time.sleep(5)

        if not shell.closed:
            shell.send('\x03')

        stdin, stdout, stderr = client.exec_command("exit")

    except paramiko.SSHException as e:
        print(f"SSH Exception: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        client.close()


@csrf_exempt 
def local_turn_on_cam(request):
    if request.method == 'POST':
        
        # Retrieve the new imgsPath value from the request body
        body = json.loads(request.body)
        ip = body.get('auxRasP', '')

        #print(f'\n\n\n /////////// Esta es la IP de reboot: {ip} /////////// \n\n\n')
        
        # Create a client object
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            camera_thread_1 = threading.Thread(target=ssh_launch_cameras, args=(ip,))
            camera_thread_1.start()

        except paramiko.SSHException as e:
            print(f"SSH Exception: {e}")
        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            client.close()

        # Return a success response
        return JsonResponse({'message': 'nCassettes updated successfully'})
    
    # Return an error response for unsupported methods
    return JsonResponse({'message': 'Method not allowed'}, status=405)

import subprocess

@csrf_exempt 
def local_rasp_status(request):
    if request.method == 'POST':
        
        # Retrieve the new imgsPath value from the request body
        body = json.loads(request.body)
        ip = body.get('auxRasP', '')

        try:
            # Run the ping command
            result = subprocess.run(['ping', '-c', '1', ip], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            # Check if the device is reachable (exit code 0) or not (non-zero exit code)
            if result.returncode == 0:
                response_data = {
                    'message': f'Device {ip} is reachable.',
                    'status': 'reachable',
                }
            else:
                response_data = {
                    'message': f'Device {ip} is not reachable.',
                    'status': 'unreachable',
                }

        except Exception as e:
            response_data = {
                'message': str(e),
                'status': 'error',
            }
        print(f'Devuelvo esto {response_data}')
        return JsonResponse(response_data)
    
    # Return an error response for unsupported methods
    return JsonResponse({'message': 'Method not allowed', 'status': 'unreachable'}, status=405)

@csrf_exempt 
def local_turn_display_on(request):
    if request.method == 'POST':
        
        # Retrieve the new imgsPath value from the request body
        body = json.loads(request.body)
        ip = body.get('auxRasP', '')

        #print(f'\n\n\n /////////// Esta es la IP de reboot: {ip} /////////// \n\n\n')
        
        # Create a client object
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            # Connect to the raspberry
            client.connect(ip, username="pi", password="raspberry")
            time.sleep(2)

            # Execute the commands
            # Start a single shell session and run multiple commands
            shell = client.invoke_shell()

            # Execute the commands
            stdin, stdout, stderr = client.exec_command("date") #Change

        except paramiko.SSHException as e:
            print(f"SSH Exception: {e}")
        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            client.close()

        # Return a success response
        return JsonResponse({'message': 'nCassettes updated successfully'})
    
    # Return an error response for unsupported methods
    return JsonResponse({'message': 'Method not allowed'}, status=405)

import copy

@csrf_exempt 
def local_docker_processes(request):
    if request.method == 'POST':
        # Retrieve the new imgsPath value from the request body
        body = json.loads(request.body)
        ip = body.get('auxRasP', '')
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        val = 0

        try:
            # Connect to the raspberry
            client.connect(ip, username="pi", password="raspberry")
            time.sleep(2)

            # Execute the commands
            stdin, stdout, stderr = client.exec_command("docker ps -a")
            stdout = copy.copy(stdout.readlines())
            print('Num_process:', len(stdout)-1)
            val = len(stdout)-1

        except paramiko.SSHException as e:
            print(f"SSH Exception: {e}")
        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            client.close()

            # Return a success response
            return JsonResponse({'processes': str(val)})
    
    # Return an error response for unsupported methods
    return JsonResponse({'message': 'Method not allowed'}, status=405)


def ssh_stop_cameras(IP):
    print('Connecting to a Raspberry')
    # Create a client object
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        # Connect to the raspberry
        client.connect(IP, username="pi", password="raspberry")
        time.sleep(2)

        # Execute the commands
        # Start a single shell session and run multiple commands
        shell = client.invoke_shell()

        # Execute the commands
        stdin, stdout, stderr = client.exec_command("ps -la | grep camara | awk '{print $4}'")
        aux_char = (stdout.read().decode('utf-8'))
        # print(f"Se me devuelto esto {aux_char}")
        stop_string = "sudo kill -9 " + aux_char + "\n"
        print(stop_string)
        shell.send(stop_string)
        time.sleep(1)
        shell.send("y\n")
        docker_down_flag = True
        # stdin, stdout, stderr = client.exec_command("docker kill $(docker ps -q)")

    except paramiko.SSHException as e:
        print(f"SSH Exception: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        client.close()


@csrf_exempt 
def local_turn_camera_off(request):
    if request.method == 'POST':
        # Retrieve the new imgsPath value from the request body
        body = json.loads(request.body)
        ip = body.get('auxRasP', '')
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        val = 0

        try:
            camera_thread_1 = threading.Thread(target=ssh_stop_cameras, args=(ip,))
            camera_thread_1.start()

        except paramiko.SSHException as e:
            print(f"SSH Exception: {e}")
        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            client.close()

            # Return a success response
            return JsonResponse({'processes': str(val)})
    
    # Return an error response for unsupported methods
    return JsonResponse({'message': 'Method not allowed'}, status=405)

@csrf_exempt 
def local_turn_display_off(request):
    if request.method == 'POST':
        # Retrieve the new imgsPath value from the request body
        body = json.loads(request.body)
        ip = body.get('auxRasP', '')
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        val = 0

        try:
            camera_thread_1 = threading.Thread(target=ssh_launch_cameras, args=(ip,))
            camera_thread_1.start()

        except paramiko.SSHException as e:
            print(f"SSH Exception: {e}")
        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            client.close()

            # Return a success response
            return JsonResponse({'processes': str(val)})
    
    # Return an error response for unsupported methods
    return JsonResponse({'message': 'Method not allowed'}, status=405)

# To display the sensor messages info we need to create a global variable first

global_sensor_msgs = {
    'fc_garra_a1': False,
    'fc_garra_a2': False,
    'fc_garra_b1': False,
    'fc_garra_b2': False,

    'altura1': 0.0,
    'altura2': 0.0,

    'fc_altura_top_1': False,
    'fc_altura_top_2': False,
    'fc_altura_bot_1': False,
    'fc_altura_bot_2': False,

    'temperatura': 0.0,

    'palet_a': False,
    'palet_b': False,

    'palet_descolocat_1': 0,
    'palet_descolocat_2': 0,
}

@csrf_exempt 
def local_sensor_messages(request):
    if request.method == 'POST':
        global global_sensor_msgs
        # Retrieve the info from the message
        body = json.loads(request.body)

        global_sensor_msgs['fc_garra_a1'] = body.get('fc_garra_a1', '')
        global_sensor_msgs['fc_garra_a2'] = body.get('fc_garra_a2', '')
        global_sensor_msgs['fc_garra_b1'] = body.get('fc_garra_b1', '')
        global_sensor_msgs['fc_garra_b2'] = body.get('fc_garra_b2', '')

        global_sensor_msgs['altura1'] = body.get('altura1', '')
        global_sensor_msgs['altura2'] = body.get('altura2', '')

        global_sensor_msgs['fc_altura_top_1'] = body.get('fc_altura_top_1', '')
        global_sensor_msgs['fc_altura_top_2'] = body.get('fc_altura_top_2', '')
        global_sensor_msgs['fc_altura_bot_1'] = body.get('fc_altura_bot_1', '')
        global_sensor_msgs['fc_altura_bot_2'] = body.get('fc_altura_bot_2', '')

        global_sensor_msgs['temperatura'] = body.get('temperatura', '')

        global_sensor_msgs['palet_a'] = body.get('palet_a', '')
        global_sensor_msgs['palet_b'] = body.get('palet_b', '')

        global_sensor_msgs['palet_descolocat_1'] = body.get('palet_descolocat_1', '')
        global_sensor_msgs['palet_descolocat_2'] = body.get('palet_descolocat_2', '')

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # Return a success response
        return JsonResponse({'status': 200})
    
    elif request.method == 'GET':
        response_data = {
            'fc_garra_a1': global_sensor_msgs['fc_garra_a1'],
            'fc_garra_a2': global_sensor_msgs['fc_garra_a2'],
            'fc_garra_b1': global_sensor_msgs['fc_garra_b1'],
            'fc_garra_b2': global_sensor_msgs['fc_garra_b2'],

            'altura1': global_sensor_msgs['altura1'],
            'altura2': global_sensor_msgs['altura2'],

            'fc_altura_top_1': global_sensor_msgs['fc_altura_top_1'],
            'fc_altura_top_2': global_sensor_msgs['fc_altura_top_2'],
            'fc_altura_bot_1': global_sensor_msgs['fc_altura_bot_1'],
            'fc_altura_bot_2': global_sensor_msgs['fc_altura_bot_2'],

            'temperatura': global_sensor_msgs['temperatura'],

            'palet_a': global_sensor_msgs['palet_a'],
            'palet_b': global_sensor_msgs['palet_b'],

            'palet_descolocat_1': global_sensor_msgs['palet_descolocat_1'],
            'palet_descolocat_2': global_sensor_msgs['palet_descolocat_2'],
        }
        return JsonResponse(response_data)
    # Return an error response for unsupported methods
    return JsonResponse({'message': 'Method not allowed'}, status=405)

@csrf_exempt 
def local_update_experimentos_estado(request, idExperimento):
    if request.method == 'POST':
        # Retrieve the instance of the model
        instance = get_object_or_404(Experimentos, idExperimentos=idExperimento)
        
        # Retrieve the new imgsPath value from the request body
        body = json.loads(request.body)
        nEstado = body.get('nEstado', '')
        
        # Modify the field value
        instance.estado = nEstado

        if (nEstado == 'descargado'):
            placas = Placas.objects.filter(idExperimentos = idExperimento)
            id_pallets = list(placas.values_list('idPallets', flat=True).distinct())
            print(id_pallets)
            pallets_list = []
            for idPal in id_pallets:
                pallets = Pallets.objects.filter(idPallets = idPal)
                pallets_list.append(pallets)
                Pallets.objects.filter(idPallets = idPal).delete()

            print(pallets_list[0])
        
        # Save the instance
        instance.save()
        
        # Return a success response
        return JsonResponse({'message': 'nEstado updated successfully'})
    
    # Return an error response for unsupported methods
    return JsonResponse({'message': 'Method not allowed'}, status=405)

#           --LOCAL WEBSOCKETS--

from channels.generic.websocket import AsyncWebsocketConsumer

class AlarmConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Add the connected WebSocket client to a group
        await self.channel_layer.group_add("alarms", self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        # Remove the WebSocket client from the group
        await self.channel_layer.group_discard("alarms", self.channel_name)

    async def receive(self, content):
        print(content)
        # Handle incoming JSON messages (if needed)
        pass

    async def send(self, event):
        # Send the alarm message to the WebSocket client
        alarm_message = event['message']
        await self.send_json({'message': alarm_message})

# myapp/views.py

from channels.layers import get_channel_layer
from django.http import HttpResponse
from rest_framework.decorators import api_view
from asgiref.sync import async_to_sync

channel_layer = get_channel_layer()

@api_view(['POST'])
def trigger_alarm(request):
    alarm_message = request.data.get('message')

    # Broadcast the alarm message to all connected WebSocket clients
    async_to_sync(channel_layer.group_send)("alarms", {"type": "send_alarm_message", "message": alarm_message})

    return HttpResponse("Alarm triggered successfully")


#           --LOCAL CÁMARAS--

latest_image_data_1 = ''

@csrf_exempt
def local_image_callback_1(request):
    image_data = request.body

    image_data_encoded = base64.b64encode(image_data).decode('utf-8')

    global latest_image_data_1
    latest_image_data_1 = image_data_encoded

    return JsonResponse({'message': 'Image saved successfully'})

def local_image_view_1(request):
    global latest_image_data_1

    context = {
        'image_data_encoded': latest_image_data_1
    }

    return JsonResponse(context)

latest_image_data_2 = ''

@csrf_exempt
def local_image_callback_2(request):
    image_data = request.body

    image_data_encoded = base64.b64encode(image_data).decode('utf-8')

    global latest_image_data_2
    latest_image_data_2 = image_data_encoded

    return JsonResponse({'message': 'Image saved successfully'})

def local_image_view_2(request):
    global latest_image_data_2

    context = {
        'image_data_encoded': latest_image_data_2
    }

    return JsonResponse(context)

#   --- Gestión de alarmas ---

MAX_VALOR = 30
MIN_VALOR = 0

class ContainerAlarm:
    def __init__(self):
        self.condition = threading.Condition()
        self.contador = 0
        self.vect = [''] * MAX_VALOR
        self.bufIN = 0
        self.bufOUT = 0

    def put_item(self, value):
        with self.condition:

            while self.contador == MAX_VALOR:
                self.condition.wait()

            self.vect[self.bufIN] = value

            if (self.bufIN < MAX_VALOR - 1):
                self.bufIN += 1

            else:
                self.bufIN = 0

            self.contador += 1
            self.condition.notify_all()

    def get_item(self):
        with self.condition:

            valor = self.vect[self.bufOUT]
            return valor
        
    def acknowledge_alarm(self):
        with self.condition:
            
            while self.contador == MIN_VALOR:
                #self.condition.wait()
                return

            valor = self.vect[self.bufOUT]

            if (self.bufOUT < MAX_VALOR - 1):
                self.bufOUT += 1

            else:
                self.bufOUT = 0

            self.contador -= 1
            self.condition.notify_all()
            return valor

    def read_items(self):
        with self.condition:
            self.condition.notify_all()
            return self.contador

contenedorAlarma = ContainerAlarm()

info_alarma = ''

from django.core.mail import send_mail

@csrf_exempt
def ros2_data_view(request):

    global contenedorAlarma
    global info_alarma

    if request.method == 'POST':
        data = request.POST.get('data', '')
        info_alarma = data

        # Send email
        subject = 'Alarm Notification'
        message = f'An alarm has been triggered. Alarm information: {info_alarma}'
        from_email = 'alarm.sender@outlook.com'  # Set the from_email if not using DEFAULT_FROM_EMAIL in settings
        recipient_list = ['elzaka81@gmail.com']  # Add the recipient email address

        # Use Django's send_mail function to send the email
        send_mail(subject, message, from_email, recipient_list)

        contenedorAlarma.put_item(info_alarma)

        # Send SSE event to connected clients
        # send_event('ros2_events', 'message', str(data))
        return HttpResponse(status=200)

    elif request.method == 'GET':
        return JsonResponse({'info': info_alarma}) 
    
@csrf_exempt
def handle_alarm(request):
    
    global contenedorAlarma

    if request.method == 'POST':
        data = request.POST.get('data', '')

        contenedorAlarma.acknowledge_alarm()

        # Send SSE event to connected clients
        # send_event('ros2_events', 'message', str(data))
        return HttpResponse(status=200)

    elif request.method == 'GET':

        dato = contenedorAlarma.read_items()
        return JsonResponse({'dato': dato}) 