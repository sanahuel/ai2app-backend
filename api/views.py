from django.shortcuts import render
from django.http import JsonResponse
from rest_framework.response import Response
from rest_framework.decorators import api_view
from django.views import View
# from .models import Ensayo 
# from .serializers import EnsayoSerializer, createEnsayoSerializer

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

class NewView(View):
    def get(self, request, *args, **kwargs):
        pass

    def post(self, request, *args, **kwargs):
        pass

class ControlView(View):
    def get():
        pass

    def get():
        pass

    def delete():
        pass

class ResultView(View):
    def get():
        pass

    def get():
        pass


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
