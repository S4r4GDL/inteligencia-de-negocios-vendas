from django.db import models

class Cliente(models.Model):
    cliente_id = models.CharField(max_length=20, primary_key=True)
    genero = models.CharField(max_length=1)
    cod_org = models.CharField(max_length=20)
    data_nascimento = models.DateField()
    nome_set = models.CharField(max_length=100)
    tipo_parceria = models.CharField(max_length=10, blank=True)
    parceiro = models.CharField(max_length=20, blank=True)
    primeiro_contato = models.DateTimeField()
    ultimo_contato = models.DateTimeField()
    limite_calculado = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = 'clientes'

    def __str__(self):
        return f"{self.cliente_id} - {self.nome_set}"

class Venda(models.Model):
    venda_id = models.CharField(max_length=20, primary_key=True)
    cliente_id = models.CharField(max_length=20)
    data = models.DateField()
    horario = models.TimeField()
    vendedor = models.CharField(max_length=20)
    desconto = models.DecimalField(max_digits=10, decimal_places=2)
    valor_final = models.DecimalField(max_digits=10, decimal_places=2)
    forma_pagamento = models.CharField(max_length=50)

    class Meta:
        db_table = 'vendas'

    def __str__(self):
        return f"Venda {self.venda_id} - {self.valor_final}"

class ProdutoVendido(models.Model):
    id = models.AutoField(primary_key=True)
    venda_id = models.CharField(max_length=20)
    produto_id = models.CharField(max_length=20)
    produto_nome = models.CharField(max_length=200)
    valor_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    quantidade_vendida = models.DecimalField(max_digits=10, decimal_places=2)
    desconto_item = models.DecimalField(max_digits=10, decimal_places=2)
    preco_promocional = models.DecimalField(max_digits=10, decimal_places=2)
    produto_custo = models.DecimalField(max_digits=10, decimal_places=2)
    produto_preco = models.DecimalField(max_digits=10, decimal_places=2)
    fabricante = models.CharField(max_length=10)

    class Meta:
        db_table = 'produtos_vendidos'

    def __str__(self):
        return f"{self.produto_nome} - Venda {self.venda_id}"

