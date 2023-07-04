from django.urls import path
from . import views
from django.views.decorators.csrf import csrf_exempt
from .views import NewView, ControlView, ControlExpView, ResultView, ResultExpView, DispositivoView, DispositivoTareasView
from .views import DispConfig, PlacasConfig, PlanifConfig, DispIndividual, PlanifIndividual, PlacasIndividual
# Local
from .views import LocalPalletsView, LocalPlacasView, LocalPlacasDetailView, LocalPalletPlacasView, LocalPalletsByAlmacenView, LocalAlmacenesView, LocalCListView, LocalPListView, LocalDispositivosView
from .views import local_image_callback, local_image_view

urlpatterns = [
    #       ------Planificador------
    path('new/', NewView.as_view()),
    path('results/', ResultView.as_view()),
    path('results/<int:pk>', ResultExpView.as_view()),
    path('control/', ControlView.as_view()),
    path('control/<int:pk>', csrf_exempt(ControlExpView.as_view())),
    path('dispositivo/', DispositivoView.as_view()),
    path('dispositivo/tareas', DispositivoTareasView.as_view()),
    
    path('config/disp', DispConfig.as_view()),
    path('config/disp/<int:pk>', DispIndividual.as_view()),
    path('config/placas', PlacasConfig.as_view()),
    path('config/placas/<int:pk>', PlacasIndividual.as_view()),
    path('config/planif', PlanifConfig.as_view()),
    path('config/planif/<int:pk>', PlanifIndividual.as_view()),

    #       ------Local------
    path('local/dispositivos/', LocalDispositivosView.as_view()),
    path('local/pallets', LocalPalletsView.as_view()),
    path('local/pallets/<int:number_of_pallet>/', LocalPalletPlacasView.as_view()),
    path('local/palletsAlmacen/<str:a_number>/', LocalPalletsByAlmacenView.as_view()),
    path('local/almacenes/', LocalAlmacenesView.as_view()),
    path('local/cassettes/<str:a_number>/', LocalCListView.as_view()),
    path('local/plista/<str:a_number>/<str:c_number>/', LocalPListView.as_view()),
    path('local/placas', LocalPlacasView.as_view()),
    path('local/placas/<int:idPlacas>', LocalPlacasDetailView.as_view()),
    path('local/switch_pallets/<int:dragged_pallet_id>/<int:target_pallet_id>/', views.local_switch_pallets),
    path('local/send_z_pos_ros2/<int:new_z_position>/', views.local_message_pos_z),
    path('local/emergency_stop/', views.local_emergency_stop),
    path('local/get_color/<int:idPallet>/', views.local_get_color_by_idPallets),
    path('local/get_color_alm/<str:almacen_id>/', views.local_get_color_by_almacen),
    path('local/send_selected_pallet/<int:id_pallet>/', views.local_message_pallet_selection),

    #       ------Local Cámara------
    path('local/image_callback/', local_image_callback),
    path('local/image_view/', local_image_view),

]