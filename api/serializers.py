from rest_framework.serializers import ModelSerializer
from .models import Experimentos, Condiciones, Placas
'''
class EnsayoSerializer(ModelSerializer):
    class Meta:
        model = Ensayo
        fields = '__all__'
'''

class CreatePlacasSerializer(ModelSerializer):
    class Meta:
        model = Placas
        fields = (
            'idPallets',
            'tipoPlaca'
        )

class CreateEnsayoSerializer(ModelSerializer):
    condiciones = CreatePlacasSerializer

    class Meta:
        model = Experimentos
        fields = (
            'nombreExperimento',
            'fechaInicio', 
            'ventanaEntreCapturas', 
            'numeroDeCapturas',
            'aplicacion',
            'nombreProyecto',
            )
