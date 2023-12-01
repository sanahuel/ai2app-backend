from django.urls import path
from . import views
from django.views.decorators.csrf import csrf_exempt
from .views import NewView, ControlView, ControlExpView, ResultView, ResultExpView, DispositivoView, DispositivoTareasView
from .views import DispConfig, PlacasConfig, PlanifConfig, DispIndividual, PlanifIndividual, PlacasIndividual, IPsConfig, IPsIndividual
# Local
from .views import LocalPalletsView, LocalPlacasView, LocalPlacasDetailView, LocalPalletPlacasView, LocalPalletsByAlmacenView, LocalAlmacenesView, LocalCListView, LocalPListView, LocalDispositivosView, LocalExperimentosView, LocalDistrPallet
from .views import local_image_callback_1, local_image_view_1, local_image_callback_2, local_image_view_2

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
    path('config/ips', IPsConfig.as_view()),
    path('config/ips/<int:pk>', IPsIndividual.as_view()),

    #       ------Local------
    path('local/dispositivos/', LocalDispositivosView.as_view()),
    path('local/experimentos/', LocalExperimentosView.as_view()),
    path('local/pallets', LocalPalletsView.as_view()),
    path('local/pallets/<int:number_of_pallet>/', LocalPalletPlacasView.as_view()),
    path('local/palletsAlmacen/<str:a_number>/', LocalPalletsByAlmacenView.as_view()),
    path('local/almacenes/', LocalAlmacenesView.as_view()),
    path('local/cassettes/<str:a_number>/', LocalCListView.as_view()),
    path('local/plista/<str:a_number>/<str:c_number>/', LocalPListView.as_view()),
    path('local/placas', LocalPlacasView.as_view()),
    path('local/placas/<int:idPlacas>', LocalPlacasDetailView.as_view()),
    path('local/switch_pallets/<int:dragged_pallet_id>/<int:target_pallet_id>/', views.local_switch_pallets),
    path('local/move_pallet/', views.local_move_pallet_to_empty),
    path('local/send_z_pos_ros2/<int:new_z_position>/', views.local_message_pos_z),
    path('local/emergency_stop/', views.local_emergency_stop),
    path('local/estado_dispositivo/', views.local_estado_dispositivo),
    path('local/get_color/<int:idPallet>/', views.local_get_color_by_idPallets),
    path('local/get_color_alm/<str:almacen_id>/', views.local_get_color_by_almacen),
    path('local/distr_pallet/<int:idPallet>', LocalDistrPallet.as_view()),
    path('local/update_ip/<int:ip>/', views.local_update_ip),
    path('local/update_path/<int:ip>/', views.local_update_imgs_path),
    path('local/update_modelo/<int:ip>/', views.local_update_modelo),
    path('local/update_n_almacenes/<int:ip>/', views.local_update_n_almacenes),
    path('local/update_n_cassettes/<int:ip>/', views.local_update_n_cassettes),
    path('local/update_est_exp/<int:idExperimento>/', views.local_update_experimentos_estado),
    path('local/send_selected_pallet/<int:id_pallet>/', views.local_message_pallet_selection),
    path('local/raspon/', views.local_turn_on_rasp),
    path('local/raspoff/', views.local_turn_off_rasp),
    path('local/raspreboot/', views.local_reboot_rasp),
    path('local/stopdock/', views.local_stop_dockers),
    path('local/camon/', views.local_turn_on_cam),
    path('local/camoff/', views.local_turn_camera_off),
    path('local/dispon/', views.local_turn_display_on),
    path('local/dispoff/', views.local_turn_display_off),
    path('local/toweron/', views.local_turn_tower_on),
    path('local/toweroff/', views.local_turn_tower_off),
    path('local/raspstatus/', views.local_rasp_status),
    path('local/dockerprocs/', views.local_docker_processes),
    path('local/sensor_msgs/', views.local_sensor_messages),
    path('local/receive_alarm/', views.ros2_data_view),
    path('local/handle_alarm/', views.handle_alarm),
    path('local/capture_progress/', views.local_capture_progress),
    
    #       ------Local Cámara------
    path('local/image_callback/', local_image_callback_1),
    path('local/image_view/camera1', local_image_view_1),

    path('local/image_callback_2/', local_image_callback_2),
    path('local/image_view/camera2', local_image_view_2),]