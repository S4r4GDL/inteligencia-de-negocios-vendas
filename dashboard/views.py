from django.shortcuts import render
from django.http import JsonResponse
from django.db.models import Sum, Count, Avg, Q
from django.db.models.functions import TruncMonth, TruncDate, Extract
from datetime import datetime, timedelta
from decimal import Decimal
import json
from .models import Cliente, Venda, ProdutoVendido

def dashboard_view(request):
    """View principal do dashboard"""
    return render(request, 'dashboard/dashboard.html')

def vendas_view(request):
    """View da tela de vendas"""
    return render(request, 'dashboard/vendas.html')

def clientes_view(request):
    """View da tela de clientes"""
    return render(request, 'dashboard/clientes.html')

def produtos_view(request):
    """View da tela de produtos"""
    return render(request, 'dashboard/produtos.html')

def projecoes_view(request):
    """View da tela de projeções"""
    return render(request, 'dashboard/projecoes.html')

def dashboard_data(request):
    """API para dados do dashboard"""
    try:
        # Métricas principais
        total_vendas = Venda.objects.count()
        faturamento_total = Venda.objects.aggregate(total=Sum('valor_final'))['total'] or 0
        
        # Calcular lucro total de forma mais eficiente
        lucro_total = 0
        produtos_vendidos = ProdutoVendido.objects.all()[:1000]  # Limitar para performance
        for produto in produtos_vendidos:
            lucro_produto = (produto.valor_unitario - produto.produto_custo) * produto.quantidade_vendida
            lucro_total += lucro_produto
        
        # Ticket médio
        ticket_medio = faturamento_total / total_vendas if total_vendas > 0 else 0
        
        # Vendas por mês (últimos 12 meses)
        vendas_por_mes = list(Venda.objects.filter(
            data__gte=datetime.now().date() - timedelta(days=365)
        ).annotate(
            mes=TruncMonth('data')
        ).values('mes').annotate(
            total=Sum('valor_final'),
            quantidade=Count('venda_id')
        ).order_by('mes')[:12])
        
        # Top 10 produtos mais vendidos
        top_produtos = list(ProdutoVendido.objects.values(
            'produto_nome'
        ).annotate(
            quantidade_total=Sum('quantidade_vendida')
        ).order_by('-quantidade_total')[:10])
        
        # Top 10 clientes por valor
        top_clientes = list(Venda.objects.values(
            'cliente_id'
        ).annotate(
            total_gasto=Sum('valor_final')
        ).order_by('-total_gasto')[:10])
        
        # Adicionar nomes dos clientes de forma mais eficiente
        cliente_ids = [c['cliente_id'] for c in top_clientes]
        clientes_dict = {c.cliente_id: c.nome_set for c in Cliente.objects.filter(cliente_id__in=cliente_ids)}
        
        for cliente in top_clientes:
            cliente['nome'] = clientes_dict.get(cliente['cliente_id'], f"Cliente {cliente['cliente_id']}")
        
        # Vendas por dia da semana (últimos 3 meses) - simplificado
        tres_meses_atras = datetime.now().date() - timedelta(days=90)
        vendas_dia_semana = list(Venda.objects.filter(
            data__gte=tres_meses_atras
        ).annotate(
            dia_semana=Extract('data', 'week_day')
        ).values('dia_semana').annotate(
            media_vendas=Avg('valor_final')
        ).order_by('dia_semana')[:7])
        
        # Vendas por horário (últimos 3 meses) - simplificado
        vendas_por_hora = list(Venda.objects.filter(
            data__gte=tres_meses_atras
        ).annotate(
            hora=Extract('horario', 'hour')
        ).values('hora').annotate(
            quantidade=Count('venda_id')
        ).order_by('hora')[:24])
        
        # Converter datas para strings
        for venda in vendas_por_mes:
            if venda['mes']:
                venda['mes'] = venda['mes'].isoformat()
        
        data = {
            'metricas': {
                'total_vendas': total_vendas,
                'faturamento_total': float(faturamento_total),
                'lucro_total': float(lucro_total),
                'ticket_medio': float(ticket_medio)
            },
            'vendas_por_mes': vendas_por_mes,
            'top_produtos': top_produtos,
            'top_clientes': top_clientes,
            'vendas_dia_semana': vendas_dia_semana,
            'vendas_por_hora': vendas_por_hora
        }
        
        return JsonResponse(data)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def vendas_data(request):
    """API para dados de vendas com filtros"""
    try:
        vendas = Venda.objects.all()
        
        # Aplicar filtros
        cliente_id = request.GET.get('cliente_id')
        venda_id = request.GET.get('venda_id')
        data_inicio = request.GET.get('data_inicio')
        data_fim = request.GET.get('data_fim')
        forma_pagamento = request.GET.get('forma_pagamento')
        
        if cliente_id:
            vendas = vendas.filter(cliente_id__icontains=cliente_id)
        if venda_id:
            vendas = vendas.filter(venda_id__icontains=venda_id)
        if data_inicio:
            vendas = vendas.filter(data__gte=data_inicio)
        if data_fim:
            vendas = vendas.filter(data__lte=data_fim)
        if forma_pagamento:
            vendas = vendas.filter(forma_pagamento__icontains=forma_pagamento)
        
        # Preparar dados
        vendas_list = []
        for venda in vendas[:100]:  # Limitar a 100 resultados
            try:
                cliente = Cliente.objects.get(cliente_id=venda.cliente_id)
                nome_cliente = cliente.nome_set
            except Cliente.DoesNotExist:
                nome_cliente = f"Cliente {venda.cliente_id}"
            
            vendas_list.append({
                'venda_id': venda.venda_id,
                'cliente_id': venda.cliente_id,
                'nome_cliente': nome_cliente,
                'data': venda.data.strftime('%d/%m/%Y'),
                'horario': venda.horario.strftime('%H:%M:%S'),
                'vendedor': venda.vendedor,
                'valor_final': float(venda.valor_final),
                'desconto': float(venda.desconto),
                'forma_pagamento': venda.forma_pagamento
            })
        
        return JsonResponse({'vendas': vendas_list})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def clientes_data(request):
    """API para dados de clientes com filtros"""
    try:
        clientes = Cliente.objects.all()
        
        # Aplicar filtros
        cliente_id = request.GET.get('cliente_id')
        genero = request.GET.get('genero')
        data_nascimento = request.GET.get('data_nascimento')
        nome_set = request.GET.get('nome_set')
        
        if cliente_id:
            clientes = clientes.filter(cliente_id__icontains=cliente_id)
        if genero:
            clientes = clientes.filter(genero__icontains=genero)
        if data_nascimento:
            clientes = clientes.filter(data_nascimento=data_nascimento)
        if nome_set:
            clientes = clientes.filter(nome_set__icontains=nome_set)
        
        # Preparar dados
        clientes_list = []
        for cliente in clientes[:100]:  # Limitar a 100 resultados
            clientes_list.append({
                'cliente_id': cliente.cliente_id,
                'genero': cliente.genero,
                'cod_org': cliente.cod_org,
                'data_nascimento': cliente.data_nascimento.strftime('%d/%m/%Y') if cliente.data_nascimento else '',
                'nome_set': cliente.nome_set,
                'tipo_parceria': cliente.tipo_parceria,
                'parceiro': cliente.parceiro,
                'primeiro_contato': cliente.primeiro_contato.strftime('%d/%m/%Y %H:%M:%S'),
                'ultimo_contato': cliente.ultimo_contato.strftime('%d/%m/%Y %H:%M:%S'),
                'limite_calculado': float(cliente.limite_calculado)
            })
        
        return JsonResponse({'clientes': clientes_list})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def produtos_data(request):
    """API para dados de produtos com filtros"""
    try:
        produtos = ProdutoVendido.objects.all()
        
        # Aplicar filtros
        produto_id = request.GET.get('produto_id')
        produto_nome = request.GET.get('produto_nome')
        fabricante = request.GET.get('fabricante')
        
        if produto_id:
            produtos = produtos.filter(produto_id__icontains=produto_id)
        if produto_nome:
            produtos = produtos.filter(produto_nome__icontains=produto_nome)
        if fabricante:
            produtos = produtos.filter(fabricante__icontains=fabricante)
        
        # Preparar dados
        produtos_list = []
        for produto in produtos[:100]:  # Limitar a 100 resultados
            produtos_list.append({
                'venda_id': produto.venda_id,
                'produto_id': produto.produto_id,
                'produto_nome': produto.produto_nome,
                'valor_unitario': float(produto.valor_unitario),
                'quantidade_vendida': float(produto.quantidade_vendida),
                'desconto_item': float(produto.desconto_item),
                'preco_promocional': float(produto.preco_promocional),
                'produto_custo': float(produto.produto_custo),
                'produto_preco': float(produto.produto_preco),
                'fabricante': produto.fabricante
            })
        
        return JsonResponse({'produtos': produtos_list})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)



def receita_mensal_data(request):
    """API para dados de receita mensal"""
    try:
        import joblib
        
        # Carregar modelos
        modelos_data = joblib.load('modelos_projecoes_v2.pkl')
        receita_data = modelos_data['receita_mensal']
        
        return JsonResponse({'predicoes': receita_data['predicoes']})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import json

@csrf_exempt
def simular_produto(request):
    """API para simular predição de produto"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Método não permitido'}, status=405)
    
    try:
        import json
        import joblib
        import sys
        import os
        
        # Adicionar o diretório atual ao path para importar o módulo
        sys.path.append(os.path.dirname(os.path.abspath(__file__ + '/../')))
        from criar_modelos_v2 import fazer_predicao_produto
        
        # Carregar dados da requisição
        dados = json.loads(request.body)
        
        # Carregar modelos
        modelos_data = joblib.load('modelos_projecoes_v2.pkl')
        produto_data = modelos_data['produto_logistico']
        
        # Fazer predição
        resultado = fazer_predicao_produto(
            produto_id=dados.get('produto_id'),
            produto_nome=dados.get('produto_nome'),
            modelo_data=produto_data
        )
        
        if resultado and 'error' not in resultado:
            return JsonResponse(resultado)
        else:
            return JsonResponse(resultado or {'error': 'Erro desconhecido'}, status=400)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

