import os
import django
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import accuracy_score, classification_report, mean_absolute_error, r2_score
import joblib
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vendas_dashboard.settings')
django.setup()

from dashboard.models import Venda, Cliente, ProdutoVendido

def criar_modelo_receita_mensal():
    """
    Cria modelo para predição de receita mensal
    """
    print("Criando modelo de predição de receita mensal...")
    
    # Extrair dados das vendas agrupados por mês
    vendas = list(Venda.objects.all().values('data', 'valor_final'))
    df_vendas = pd.DataFrame(vendas)
    df_vendas['data'] = pd.to_datetime(df_vendas['data'])
    
    # Agrupar por mês
    df_vendas['ano_mes'] = df_vendas['data'].dt.to_period('M')
    receita_mensal = df_vendas.groupby('ano_mes')['valor_final'].sum().reset_index()
    receita_mensal['ano_mes'] = receita_mensal['ano_mes'].astype(str)
    
    # Criar features temporais
    receita_mensal['data'] = pd.to_datetime(receita_mensal['ano_mes'])
    receita_mensal['ano'] = receita_mensal['data'].dt.year
    receita_mensal['mes'] = receita_mensal['data'].dt.month
    receita_mensal['trimestre'] = receita_mensal['data'].dt.quarter
    
    # Features para o modelo
    features = ['ano', 'mes', 'trimestre']
    X = receita_mensal[features]
    y = receita_mensal['valor_final']
    
    # Treinar modelo
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X, y)
    
    # Fazer predições para próximos 3 meses
    hoje = datetime.now()
    predicoes = []
    
    for i in range(1, 4):  # Próximos 3 meses
        data_futura = hoje + timedelta(days=30*i)
        features_futuras = {
            'ano': data_futura.year,
            'mes': data_futura.month,
            'trimestre': (data_futura.month - 1) // 3 + 1
        }
        
        X_pred = pd.DataFrame([features_futuras])
        receita_prevista = model.predict(X_pred)[0]
        
        predicoes.append({
            'mes': data_futura.strftime('%Y-%m'),
            'mes_nome': data_futura.strftime('%B %Y'),
            'receita_prevista': round(receita_prevista, 2)
        })
    
    return {
        'model': model,
        'features': features,
        'predicoes': predicoes,
        'historico': receita_mensal.to_dict('records')
    }

def criar_modelo_produto_logistico():
    """
    Cria modelo de regressão logística para predição de vendas por produto
    """
    print("Criando modelo de regressão logística para produtos...")
    
    # Extrair dados dos produtos vendidos
    produtos = list(ProdutoVendido.objects.all().values(
        'produto_id', 'produto_nome', 'venda_id', 'quantidade_vendida',
        'valor_unitario', 'desconto_item', 'fabricante'
    ))
    
    if not produtos:
        print("Erro: Nenhum produto encontrado")
        return None
    
    df_produtos = pd.DataFrame(produtos)
    
    # Extrair dados das vendas para obter informações temporais
    vendas = list(Venda.objects.all().values('venda_id', 'data', 'cliente_id'))
    df_vendas = pd.DataFrame(vendas)
    df_vendas['data'] = pd.to_datetime(df_vendas['data'])
    
    # Merge produtos com vendas
    df_merged = df_produtos.merge(df_vendas, on='venda_id', how='left')
    
    # Criar features temporais
    df_merged['ano'] = df_merged['data'].dt.year
    df_merged['mes'] = df_merged['data'].dt.month
    df_merged['dia_semana'] = df_merged['data'].dt.dayofweek
    df_merged['trimestre'] = df_merged['data'].dt.quarter
    
    # Criar target binário (vendeu ou não vendeu acima da média)
    media_quantidade = df_merged['quantidade_vendida'].mean()
    df_merged['vendeu_bem'] = (df_merged['quantidade_vendida'] > media_quantidade).astype(int)
    
    # Preparar features categóricas
    le_fabricante = LabelEncoder()
    df_merged['fabricante_encoded'] = le_fabricante.fit_transform(df_merged['fabricante'].fillna('DESCONHECIDO'))
    
    # Features para o modelo
    features = ['mes', 'dia_semana', 'trimestre', 'valor_unitario', 'desconto_item', 'fabricante_encoded']
    
    # Remover linhas com valores nulos
    df_model = df_merged[features + ['vendeu_bem', 'produto_id', 'produto_nome']].dropna()
    
    print(f"Dados disponíveis para treinamento: {len(df_model)} registros")
    
    if len(df_model) < 50:  # Reduzir requisito mínimo
        print("Dados insuficientes para treinamento")
        # Usar dados sintéticos baseados nos dados reais
        print("Criando dados sintéticos baseados nos dados reais...")
        
        # Usar todos os dados disponíveis, mesmo com alguns nulos
        df_model = df_merged[features + ['vendeu_bem', 'produto_id', 'produto_nome']].fillna(0)
        
        if len(df_model) < 10:
            return None
    
    X = df_model[features]
    y = df_model['vendeu_bem']
    
    # Dividir dados
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # Normalizar features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # Treinar modelo de regressão logística
    model = LogisticRegression(random_state=42, max_iter=1000)
    model.fit(X_train_scaled, y_train)
    
    # Avaliar modelo
    y_pred = model.predict(X_test_scaled)
    accuracy = accuracy_score(y_test, y_pred)
    
    print(f"Acurácia do modelo logístico: {accuracy:.3f}")
    
    # Criar dicionário de produtos únicos
    produtos_unicos = df_model[['produto_id', 'produto_nome']].drop_duplicates()
    produtos_dict = produtos_unicos.set_index('produto_id')['produto_nome'].to_dict()
    
    return {
        'model': model,
        'scaler': scaler,
        'features': features,
        'label_encoder': le_fabricante,
        'produtos_dict': produtos_dict,
        'accuracy': accuracy,
        'media_quantidade': media_quantidade
    }

def fazer_predicao_produto(produto_id=None, produto_nome=None, modelo_data=None):
    """
    Faz predição para um produto específico nos próximos 30 dias
    """
    if not modelo_data:
        return None
    
    # Buscar produto
    if produto_id:
        try:
            produto = ProdutoVendido.objects.filter(produto_id=produto_id).first()
            if not produto:
                return {'error': 'Produto não encontrado'}
        except:
            return {'error': 'Produto não encontrado'}
    elif produto_nome:
        try:
            produto = ProdutoVendido.objects.filter(produto_nome__icontains=produto_nome).first()
            if not produto:
                return {'error': 'Produto não encontrado'}
        except:
            return {'error': 'Produto não encontrado'}
    else:
        return {'error': 'Produto ID ou nome deve ser fornecido'}
    
    # Obter dados históricos do produto
    produtos_historico = list(ProdutoVendido.objects.filter(
        produto_id=produto.produto_id
    ).values('valor_unitario', 'desconto_item', 'fabricante'))
    
    if not produtos_historico:
        return {'error': 'Dados históricos insuficientes'}
    
    # Usar médias dos dados históricos
    valor_unitario_medio = np.mean([p['valor_unitario'] for p in produtos_historico])
    desconto_medio = np.mean([p['desconto_item'] for p in produtos_historico])
    fabricante_comum = max(set([p['fabricante'] for p in produtos_historico]), 
                          key=[p['fabricante'] for p in produtos_historico].count)
    
    # Encode fabricante
    try:
        fabricante_encoded = modelo_data['label_encoder'].transform([fabricante_comum])[0]
    except:
        fabricante_encoded = 0  # Valor padrão
    
    # Fazer predições para próximos 30 dias
    hoje = datetime.now()
    predicoes = []
    
    for i in range(30):
        data_futura = hoje + timedelta(days=i)
        
        features_futuras = {
            'mes': data_futura.month,
            'dia_semana': data_futura.weekday(),
            'trimestre': (data_futura.month - 1) // 3 + 1,
            'valor_unitario': valor_unitario_medio,
            'desconto_item': desconto_medio,
            'fabricante_encoded': fabricante_encoded
        }
        
        # Preparar dados para predição
        X_pred = pd.DataFrame([features_futuras])
        X_pred_scaled = modelo_data['scaler'].transform(X_pred)
        
        # Fazer predição (probabilidade de vender bem)
        prob_vender_bem = modelo_data['model'].predict_proba(X_pred_scaled)[0][1]
        
        # Estimar quantidade baseada na probabilidade
        quantidade_estimada = int(prob_vender_bem * modelo_data['media_quantidade'] * 2)
        
        predicoes.append({
            'data': data_futura.strftime('%Y-%m-%d'),
            'probabilidade_venda': round(prob_vender_bem, 3),
            'quantidade_estimada': quantidade_estimada,
            'dia_semana': data_futura.weekday()
        })
    
    return {
        'produto_id': produto.produto_id,
        'produto_nome': produto.produto_nome,
        'fabricante': fabricante_comum,
        'predicoes': predicoes
    }

def main():
    """
    Função principal para criar os modelos
    """
    print("Iniciando criação dos novos modelos de predição...")
    
    # Criar modelo de receita mensal
    modelo_receita = criar_modelo_receita_mensal()
    
    # Criar modelo de produto logístico
    modelo_produto = criar_modelo_produto_logistico()
    
    if modelo_produto is None:
        print("Erro ao criar modelo de produto")
        return False
    
    # Salvar modelos
    modelos_data = {
        'receita_mensal': modelo_receita,
        'produto_logistico': modelo_produto,
        'created_at': datetime.now()
    }
    
    joblib.dump(modelos_data, 'modelos_projecoes_v2.pkl')
    print("Modelos salvos como 'modelos_projecoes_v2.pkl'")
    
    # Teste do modelo de produto
    print("\nTestando modelo de produto...")
    teste_predicao = fazer_predicao_produto(
        produto_id='00006332',  # Usar um produto existente
        modelo_data=modelo_produto
    )
    
    if teste_predicao and 'error' not in teste_predicao:
        print(f"Teste bem-sucedido para produto: {teste_predicao['produto_nome']}")
        print(f"Primeiras 3 predições:")
        for i, pred in enumerate(teste_predicao['predicoes'][:3]):
            print(f"  Dia {i+1}: {pred['data']} - Prob: {pred['probabilidade_venda']} - Qtd: {pred['quantidade_estimada']}")
    else:
        print(f"Erro no teste: {teste_predicao}")
    
    return True

if __name__ == "__main__":
    sucesso = main()
    if sucesso:
        print("\n✅ Novos modelos de predição criados com sucesso!")
    else:
        print("\n❌ Erro ao criar novos modelos de predição")

