from django.urls import path
from . import views

app_name = 'port'

urlpatterns = [
    path('', views.port_home, name='home'),
    path('add/<str:item_type>/', views.add_item, name='add_item'),
    path('delivery-orders/', views.delivery_orders, name='delivery_orders'),
    path('delivery-orders/<int:order_id>/', views.delivery_order_detail, name='delivery_order_detail'),
    path('delivery-orders/<int:order_id>/add-container/', views.add_container_to_order, name='add_container_to_order'),
    path('delivery-orders/bulk-status/', views.bulk_status_change, name='bulk_status_change'),
    path('containers/', views.containers_list, name='containers_list'),
    path('containers/bulk-status/', views.container_bulk_status_change, name='container_bulk_status_change'),
    path('containers/bulk-assign/', views.container_bulk_assign, name='container_bulk_assign'),
    path('containers/delete-multiple/', views.container_bulk_delete, name='container_bulk_delete'),
    path('drivers/', views.drivers_list, name='drivers_list'),
    path('trucks/', views.trucks_list, name='trucks_list'),
    path('trucks/bulk-status/', views.truck_bulk_status_change, name='truck_bulk_status_change'),
    path('trucks/add/', views.add_truck, name='add_truck'),
    path('trucks/edit/<str:plate_number>/', views.edit_truck, name='edit_truck'),
    path('trucks/delete/<str:truck_id>/', views.delete_truck, name='delete_truck'),
    path('edit/<str:item_type>/<int:item_id>/', views.edit_item, name='edit_item'),
    path('delete/<str:item_type>/<int:item_id>/', views.delete_item, name='delete_item'),
    path('data-entry/', views.data_entry, name='data_entry'),
    path('containers/update/', views.update_containers, name='update_containers'),
    path('api/containers/', views.containers_api, name='containers_api'),
    path('api/search-container/', views.search_container, name='search_container'),
    path('get_permit_containers/<int:permit_id>/', views.get_permit_containers, name='get_permit_containers'),
    path('trips/', views.trip_list, name='trip_list'),
    path('trips/add/', views.TripCreateView.as_view(), name='add_trip'),
    path('trips/<int:trip_id>/', views.trip_detail, name='trip_detail'),
    path('trips/<int:trip_id>/edit/', views.edit_trip, name='edit_trip'),
    path('trips/<int:trip_id>/update/', views.update_trip, name='update_trip'),
    path('trips/<int:trip_id>/delete/', views.delete_trip, name='delete_trip'),
    path('containers/<int:container_id>/edit/', views.edit_container, name='edit_container'),
    path('delivery-orders/delete/<int:order_id>/', views.delete_delivery_order, name='delete_delivery_order'),
    path('delete-multiple-orders/', views.delete_multiple_orders, name='delete_multiple_orders'),
    path('containers/<int:container_id>/update-driver/', views.update_container_driver, name='update_container_driver'),
    path('containers/<int:container_id>/update-truck/', views.update_container_truck, name='update_container_truck'),
    path('trips/<int:trip_id>/remove-container/<int:container_id>/', 
         views.remove_container_from_trip, name='remove_container_from_trip'),
    path('trips/export/csv/', views.export_trips_csv, name='export_trips_csv'),
    path('trips/export/pdf/', views.export_trips_pdf, name='export_trips_pdf'),
    path('trips/<int:trip_id>/export/pdf/', views.export_trip_pdf, name='export_trip_pdf'),
    path('trips/<int:trip_id>/export/excel/', views.export_trip_excel, name='export_trip_excel'),
    path('api/dashboard-stats/', views.dashboard_stats_api, name='dashboard_stats_api'),
    path('drivers/edit/<int:driver_id>/', views.edit_driver, name='edit_driver'),
    path('drivers/delete/<int:driver_id>/', views.delete_driver, name='delete_driver'),
    
    # ===== مسارات إدارة الشركات =====
    path('companies/', views.companies_list, name='companies_list'),
    path('companies/add/', views.add_company, name='add_company'),
    path('companies/<int:company_id>/', views.company_detail, name='company_detail'),
    path('companies/<int:company_id>/edit/', views.edit_company, name='edit_company'),
    path('companies/<int:company_id>/delete/', views.delete_company, name='delete_company'),
    
    # ===== مسارات المعاملات المالية مع السائقين =====
    path('financial/driver-transactions/', views.driver_transactions_list, name='driver_transactions_list'),
    path('financial/driver-transactions/add/', views.add_driver_transaction, name='add_driver_transaction'),
    path('financial/driver-balances/', views.driver_balances, name='driver_balances'),
    
    # ===== مسارات المعاملات المالية مع الشركات =====
    path('financial/company-transactions/', views.company_transactions_list, name='company_transactions_list'),
    path('financial/company-transactions/add/', views.add_company_transaction, name='add_company_transaction'),
    
    # ===== مسارات التقارير المالية =====
    path('financial/reports/', views.financial_reports, name='financial_reports'),
] 