from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('vendas/', views.vendas_view, name='vendas'),
    path('clientes/', views.clientes_view, name='clientes'),
    path('produtos/', views.produtos_view, name='produtos'),
    path('projecoes/', views.projecoes_view, name='projecoes'),
    
    # APIs
    path('api/dashboard/', views.dashboard_data, name='dashboard_data'),
    path('api/vendas/', views.vendas_data, name='vendas_data'),
    path('api/clientes/', views.clientes_data, name='clientes_data'),
    path('api/produtos/', views.produtos_data, name='produtos_data'),
    path('api/receita-mensal/', views.receita_mensal_data, name='receita_mensal_data'),
    path('api/simular-produto/', views.simular_produto, name='simular_produto'),
]

