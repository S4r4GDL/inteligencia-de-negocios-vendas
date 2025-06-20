import os
import django
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import joblib
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vendas_dashboard.settings')
django.setup()

from dashboard.models import Venda, Cliente, ProdutoVendido

def criar_modelo_predicao():
    """
    Cria e treina um modelo de predição de vendas baseado nos dados históricos
    """
    print("Iniciando criação do modelo de predição...")
    
    # 1. Extrair dados das vendas
    print("Extraindo dados das vendas...")
    vendas = list(Venda.objects.all().values(
        'venda_id', 'cliente_id', 'data', 'horario', 'vendedor', 
        'valor_final', 'desconto', 'forma_pagamento'
    ))
    
    if not vendas:
        print("Erro: Nenhuma venda encontrada no banco de dados")
        return False
    
    df_vendas = pd.DataFrame(vendas)
    print(f"Total de vendas carregadas: {len(df_vendas)}")
    
    # 2. Preparar features para o modelo
    print("Preparando features...")
    
    # Converter data para datetime
    df_vendas['data'] = pd.to_datetime(df_vendas['data'])
    df_vendas['horario'] = pd.to_datetime(df_vendas['horario'], format='%H:%M:%S').dt.time
    
    # Extrair features temporais
    df_vendas['ano'] = df_vendas['data'].dt.year
    df_vendas['mes'] = df_vendas['data'].dt.month
    df_vendas['dia'] = df_vendas['data'].dt.day
    df_vendas['dia_semana'] = df_vendas['data'].dt.dayofweek  # 0=Segunda, 6=Domingo
    df_vendas['hora'] = pd.to_datetime(df_vendas['horario'], format='%H:%M:%S').dt.hour
    
    # Criar features agregadas por cliente
    print("Criando features agregadas por cliente...")
    cliente_stats = df_vendas.groupby('cliente_id').agg({
        'valor_final': ['count', 'mean', 'sum', 'std'],
        'desconto': 'mean'
    }).round(2)
    
    cliente_stats.columns = ['_'.join(col).strip() for col in cliente_stats.columns]
    cliente_stats = cliente_stats.reset_index()
    cliente_stats.columns = ['cliente_id', 'total_compras', 'ticket_medio', 'valor_total_gasto', 'std_valor', 'desconto_medio']
    cliente_stats['std_valor'] = cliente_stats['std_valor'].fillna(0)
    
    # Merge com dados dos clientes
    df_vendas = df_vendas.merge(cliente_stats, on='cliente_id', how='left')
    
    # Criar features de vendedor
    print("Criando features de vendedor...")
    vendedor_stats = df_vendas.groupby('vendedor').agg({
        'valor_final': ['count', 'mean']
    }).round(2)
    vendedor_stats.columns = ['vendas_vendedor', 'ticket_medio_vendedor']
    vendedor_stats = vendedor_stats.reset_index()
    df_vendas = df_vendas.merge(vendedor_stats, on='vendedor', how='left')
    
    # Encoding de variáveis categóricas
    print("Fazendo encoding de variáveis categóricas...")
    forma_pagamento_map = {
        'DINHEIRO_A_VISTA': 1, 'CARTAO_DE_DEBITO': 2, 'CARTAO_DE_CREDITO': 3,
        'PIX': 4, '2X_DUP': 5, '3X_DUP': 6, '4X_DUP': 7, '5X_DUP': 8, '6X_DUP': 9
    }
    df_vendas['forma_pagamento_encoded'] = df_vendas['forma_pagamento'].map(forma_pagamento_map).fillna(0)
    
    # 3. Preparar dados para treinamento
    print("Preparando dados para treinamento...")
    
    # Features para o modelo
    features = [
        'cliente_id', 'vendedor', 'mes', 'dia_semana', 'hora',
        'total_compras', 'ticket_medio', 'valor_total_gasto', 'std_valor', 'desconto_medio',
        'vendas_vendedor', 'ticket_medio_vendedor', 'forma_pagamento_encoded', 'desconto'
    ]
    
    # Target
    target = 'valor_final'
    
    # Remover linhas com valores nulos
    df_model = df_vendas[features + [target]].dropna()
    print(f"Dados para treinamento: {len(df_model)} registros")
    
    if len(df_model) < 100:
        print("Erro: Dados insuficientes para treinamento")
        return False
    
    X = df_model[features]
    y = df_model[target]
    
    # 4. Dividir dados em treino e teste
    print("Dividindo dados em treino e teste...")
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # 5. Treinar modelos
    print("Treinando modelos...")
    
    # Random Forest
    rf_model = RandomForestRegressor(n_estimators=100, random_state=42, max_depth=10)
    rf_model.fit(X_train, y_train)
    
    # Linear Regression
    lr_model = LinearRegression()
    lr_model.fit(X_train, y_train)
    
    # 6. Avaliar modelos
    print("Avaliando modelos...")
    
    # Predições Random Forest
    rf_pred = rf_model.predict(X_test)
    rf_mae = mean_absolute_error(y_test, rf_pred)
    rf_rmse = np.sqrt(mean_squared_error(y_test, rf_pred))
    rf_r2 = r2_score(y_test, rf_pred)
    
    # Predições Linear Regression
    lr_pred = lr_model.predict(X_test)
    lr_mae = mean_absolute_error(y_test, lr_pred)
    lr_rmse = np.sqrt(mean_squared_error(y_test, lr_pred))
    lr_r2 = r2_score(y_test, lr_pred)
    
    print("\n=== RESULTADOS DOS MODELOS ===")
    print(f"Random Forest - MAE: {rf_mae:.2f}, RMSE: {rf_rmse:.2f}, R²: {rf_r2:.3f}")
    print(f"Linear Regression - MAE: {lr_mae:.2f}, RMSE: {lr_rmse:.2f}, R²: {lr_r2:.3f}")
    
    # Escolher melhor modelo
    if rf_r2 > lr_r2:
        best_model = rf_model
        best_model_name = "RandomForest"
        best_metrics = {"mae": rf_mae, "rmse": rf_rmse, "r2": rf_r2}
    else:
        best_model = lr_model
        best_model_name = "LinearRegression"
        best_metrics = {"mae": lr_mae, "rmse": lr_rmse, "r2": lr_r2}
    
    print(f"\nMelhor modelo: {best_model_name}")
    
    # 7. Salvar modelo e metadados
    print("Salvando modelo...")
    
    model_data = {
        'model': best_model,
        'model_name': best_model_name,
        'features': features,
        'metrics': best_metrics,
        'feature_stats': {
            'cliente_stats': cliente_stats,
            'vendedor_stats': vendedor_stats,
            'forma_pagamento_map': forma_pagamento_map
        },
        'created_at': datetime.now()
    }
    
    # Salvar modelo
    joblib.dump(model_data, 'modelo_predicao_vendas.pkl')
    print("Modelo salvo como 'modelo_predicao_vendas.pkl'")
    
    # 8. Criar predições de exemplo
    print("\nCriando predições de exemplo...")
    
    # Predições para próximos 30 dias
    hoje = datetime.now().date()
    predicoes_futuras = []
    
    for i in range(30):
        data_futura = hoje + timedelta(days=i)
        
        # Calcular médias históricas para essa data
        mes = data_futura.month
        dia_semana = data_futura.weekday()
        
        # Usar estatísticas médias dos dados históricos
        exemplo_features = {
            'cliente_id': df_vendas['cliente_id'].mode()[0],  # Cliente mais frequente
            'vendedor': df_vendas['vendedor'].mode()[0],  # Vendedor mais frequente
            'mes': mes,
            'dia_semana': dia_semana,
            'hora': 14,  # Hora média de pico
            'total_compras': df_vendas['total_compras'].mean(),
            'ticket_medio': df_vendas['ticket_medio'].mean(),
            'valor_total_gasto': df_vendas['valor_total_gasto'].mean(),
            'std_valor': df_vendas['std_valor'].mean(),
            'desconto_medio': df_vendas['desconto_medio'].mean(),
            'vendas_vendedor': df_vendas['vendas_vendedor'].mean(),
            'ticket_medio_vendedor': df_vendas['ticket_medio_vendedor'].mean(),
            'forma_pagamento_encoded': 3,  # Cartão de crédito
            'desconto': df_vendas['desconto'].mean()
        }
        
        # Fazer predição
        X_pred = pd.DataFrame([exemplo_features])
        predicao = best_model.predict(X_pred)[0]
        
        predicoes_futuras.append({
            'data': data_futura.isoformat(),
            'valor_previsto': round(predicao, 2),
            'dia_semana': dia_semana
        })
    
    # Salvar predições
    import json
    with open('predicoes_futuras.json', 'w') as f:
        json.dump(predicoes_futuras, f, indent=2)
    
    print("Predições futuras salvas em 'predicoes_futuras.json'")
    print(f"Exemplo de predição para amanhã: R$ {predicoes_futuras[1]['valor_previsto']}")
    
    return True

if __name__ == "__main__":
    sucesso = criar_modelo_predicao()
    if sucesso:
        print("\n✅ Modelo de predição criado com sucesso!")
    else:
        print("\n❌ Erro ao criar modelo de predição")

