from django.shortcuts import render

def index(request):
    return render(request, 'vendas_app/index.html')


