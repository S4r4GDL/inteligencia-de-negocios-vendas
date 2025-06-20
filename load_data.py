import os
import django
import csv
from datetime import datetime
from decimal import Decimal

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vendas_dashboard.settings')
django.setup()

from dashboard.models import Cliente, Venda, ProdutoVendido

def parse_decimal(value):
    """Converte string com vírgula para Decimal"""
    if not value or value == '':
        return Decimal('0.00')
    return Decimal(value.replace(',', '.'))

def parse_date(date_str):
    """Converte string de data para objeto date"""
    if not date_str or date_str.strip() == '' or date_str == '0000-00-00':
        return datetime(1900, 1, 1).date()
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return datetime(1900, 1, 1).date()

def parse_datetime(datetime_str):
    """Converte string de datetime para objeto datetime"""
    return datetime.strptime(datetime_str, '%Y-%m-%d %H:%M:%S')

def parse_time(time_str):
    """Converte string de time para objeto time"""
    return datetime.strptime(time_str, '%H:%M:%S').time()

def load_clientes():
    """Carrega dados dos clientes"""
    print("Carregando clientes...")
    count = 0
    with open('clientes.csv', 'r', encoding='utf-8-sig') as file:
        reader = csv.DictReader(file, delimiter=';')
        for row in reader:
            # Remove aspas dos valores
            for key in row:
                if row[key]:
                    row[key] = row[key].strip('"')
            
            try:
                cliente = Cliente(
                    cliente_id=row['cliente_id'],
                    genero=row['genero'],
                    cod_org=row['cod_org'],
                    data_nascimento=parse_date(row['data_nascimento']),
                    nome_set=row['nome_set'],
                    tipo_parceria=row['tipo_parceria'],
                    parceiro=row['parceiro'],
                    primeiro_contato=parse_datetime(row['primeiro_contato']),
                    ultimo_contato=parse_datetime(row['ultimo_contato']),
                    limite_calculado=parse_decimal(row['limite_calculado'])
                )
                cliente.save()
                count += 1
                if count % 100 == 0:
                    print(f"Processados {count} clientes...")
            except Exception as e:
                print(f"Erro ao processar cliente {row['cliente_id']}: {e}")
                continue
    print(f"Clientes carregados com sucesso! Total: {count}")

def load_vendas():
    """Carrega dados das vendas"""
    print("Carregando vendas...")
    count = 0
    with open('vendas_normalizada.csv', 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file, delimiter=';')
        for row in reader:
            try:
                venda = Venda(
                    venda_id=row['venda_id'],
                    cliente_id=row['cliente_id'],
                    data=parse_date(row['data']),
                    horario=parse_time(row['horario']),
                    vendedor=row['vendedor'],
                    desconto=parse_decimal(row['desconto']),
                    valor_final=parse_decimal(row['valor_final']),
                    forma_pagamento=row['forma_pagamento']
                )
                venda.save()
                count += 1
                if count % 100 == 0:
                    print(f"Processadas {count} vendas...")
            except Exception as e:
                print(f"Erro ao processar venda {row['venda_id']}: {e}")
                continue
    print(f"Vendas carregadas com sucesso! Total: {count}")

def load_produtos():
    """Carrega dados dos produtos vendidos"""
    print("Carregando produtos vendidos...")
    count = 0
    with open('produtos_vendidos.csv', 'r', encoding='utf-8-sig') as file:
        reader = csv.DictReader(file, delimiter=';')
        for row in reader:
            # Remove aspas dos valores
            for key in row:
                if row[key]:
                    row[key] = row[key].strip('"')
            
            try:
                produto = ProdutoVendido(
                    venda_id=row['venda_id'],
                    produto_id=row['produto_id'],
                    produto_nome=row['produto_nome'],
                    valor_unitario=parse_decimal(row['valor_unitario']),
                    quantidade_vendida=parse_decimal(row['quantidade_vendida']),
                    desconto_item=parse_decimal(row['desconto_item']),
                    preco_promocional=parse_decimal(row['preco_promocional']),
                    produto_custo=parse_decimal(row['produto_custo']),
                    produto_preco=parse_decimal(row['produto_preco']),
                    fabricante=row['fabricante']
                )
                produto.save()
                count += 1
                if count % 1000 == 0:
                    print(f"Processados {count} produtos...")
            except Exception as e:
                print(f"Erro ao processar produto {row['produto_id']}: {e}")
                continue
    print(f"Produtos vendidos carregados com sucesso! Total: {count}")

if __name__ == '__main__':
    # Limpar dados existentes
    print("Limpando dados existentes...")
    Cliente.objects.all().delete()
    Venda.objects.all().delete()
    ProdutoVendido.objects.all().delete()
    
    # Carregar dados
    load_clientes()
    load_vendas()
    load_produtos()
    
    print("Todos os dados foram carregados com sucesso!")

