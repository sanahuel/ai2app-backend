from rest_framework.serializers import ModelSerializer
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from .models import Experimentos, Condiciones, Placas, Pallets, Dispositivos

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

# ----LOCAL----
class DispositivosSerializar(serializers.ModelSerializer):
    class Meta:
        model = Dispositivos
        fields = '__all__'

class CondicionesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Condiciones
        fields = '__all__'

class ExperimentosSerializer(serializers.ModelSerializer):
    condiciones = CondicionesSerializer(many=True, read_only=True)
    class Meta:
        model = Experimentos
        fields = '__all__'

class PlacasSerializer(serializers.ModelSerializer):
    experimentos = ExperimentosSerializer(read_only=True)
    condiciones = CondicionesSerializer(read_only=True)
    class Meta:
        model = Placas
        fields = '__all__'

class PalletsSerializer(serializers.ModelSerializer):
    placas = PlacasSerializer(many=True, read_only=True)
    class Meta:
        model = Pallets
        fields = '__all__'

class PalletPlacasSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pallets
        fields = ('idPallets', 'idDispositivos', 'localizacion')

    def get_placas(self, obj):
        placas = Placas.objects.filter(idPallets=obj.idPallets)
        serializer = PlacasSerializer(placas, many=True)
        return serializer.data
    
# class AlmacenPalletsSerializer(serializers.ModelSerializer):
#     pallets = serializers.SerializerMethodField()

#     class Meta:
#         model = Pallets
#         fields = ('idPallets', 'idDispositivo', 'placas', 'idAlmacen')

#     def get_pallets(self, obj):
#         pallets = Placas.objects.filter(idPallets=obj.idPallets)
#         serializer = PlacasSerializer(pallets, many=True)
#         return serializer.data
    
class AlmacenesSerializer(serializers.ModelSerializer):
    placas = PlacasSerializer(many=True, read_only=True)
    class Meta:
        model = Pallets
        fields = '__all__'

class CustomTokenObtainPairSerializer(serializers.Serializer):
    username = serializers.CharField()
    email = serializers.EmailField()

    def validate(self, attrs):
        username = attrs.get('username')
        email = attrs.get('email')

        if not username or not email:
            raise serializers.ValidationError('Username and email are required')

        refresh = RefreshToken.for_user(self.user)
        token = {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'username': username,
            'email': email,
        }

        return token
