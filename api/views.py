import datetime
import json
import pytz
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

@api_view(['GET'])
def getRoutes(request):
    return Response('Prueba API')
'''
@api_view(['GET'])
def getEnsayos(request):
    ensayos = Ensayo.objects.all()
    serializer = EnsayoSerializer(ensayos, many=True)
    return Response(serializer.data)

@api_view(['POST'])
def createEnsayo(request):
    data = request.data
    ensayo = Ensayo.objects.create(
        nombre = data['nombre'],
        inicio = data['inicio'],
        fin = data['fin'],
        horas = data['horas']
    )
    serializaer = createEnsayoSerializer(ensayo, many=False)
    return Response(serializaer.data)
'''
#       ------Nuevo Ensayo------

class NewView(APIView):
    serializer_class = CreateEnsayoSerializer

    def get(self, request, *args, **kwargs):
        serializer = self.serializer_class
        capturas = list(Tareas.objects.values_list('fechayHora', flat=True))
        return JsonResponse({'capturas': capturas})

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class

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
                # PONER ESTADO CON NOMBRE OFICIAL
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

        return JsonResponse({'success': True})

#       ------Panel de Control------

class ControlView(View):
    def get(self, request, *args, **kwargs):
        ####   CAMBIAR ESTADO A NOMBRE OFICIAL
        id_experimentos = Tareas.objects.exclude(estado='acabado').values_list('idExperimentos', flat=True).distinct()
        experimentos = []
        for id in id_experimentos:
            experimento = Experimentos.objects.get(idExperimentos=id)
            nombreExperimento = experimento.nombreExperimento
            aplicacion = experimento.aplicacion
            nombreProyecto = experimento.nombreProyecto
            tareas_totales = Tareas.objects.filter(idExperimentos=id)
            tareas_acabadas = Tareas.objects.filter(idExperimentos=id).exclude(estado='acabado')
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
        print(self.kwargs['pk'])
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
            'placas':len(placas_totales),
            'capturas':len(tareas_totales),
            'condiciones': list(condiciones),
            'placas': list(placas),
            'capturas': events,
        }
        
        
        return JsonResponse(data)

    def put(self, request, *args, **kwargs):
        table = request.POST.get('table')
        id = request.POST.get('id')
        if table == 'Placas':
            try:
                with transaction.atomic():
                    placa = Placas.objects.get(idPlacas=id, idExperimentos=self.kwargs['pk'])
                    placa.cancelada = True
                    placa.save()
                    return JsonResponse({'message': 'Placa cancelada'})
            except Placas.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Placa not found'})
        
        elif table == 'Condicion':
            try:
                with transaction.atomic():
                    placas = Condiciones.objects.filter(idCondiciones=id, idExperimentos=self.kwargs['pk']).values_list('idPlacas', flat=True)
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
                    tarea = Tareas.objects.get(idTareas=id, idExperimentos=self.kwargs['pk'])
                    tarea.cancelada = True
                    tarea.save()
                    return JsonResponse({'message': 'Tarea cancelada'})
            except Tareas.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Tarea not found'})
        

    def delete(self, request, *args, **kwargs):
        try:
            Experimentos.objects.filter(idExperimentos=self.kwargs['pk']).delete()
        except Experimentos.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Experimento not found'})
        
        return JsonResponse({'message': 'Experimento eliminado'})

#       ------Resultados------

class ResultView(View):
    def get(self, request, *args, **kwargs):
        #####   CAMBIAR ESTADO A NOMBRE OFICIAL
        id_experimentos = Tareas.objects.filter(estado='acabado').values_list('idExperimentos', flat=True).distinct()
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
