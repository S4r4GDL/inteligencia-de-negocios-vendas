import pandas as pd
import os
import unicodedata

def detectar_separador(caminho_arquivo):
    """
    Detecta automaticamente o separador CSV com base na primeira linha do arquivo.
    """
    with open(caminho_arquivo, 'r', encoding='utf-8') as f:
        linha = f.readline()
        if linha.count(';') > linha.count(','):
            return ';'
        else:
            return ','

def normalizar_texto_upper_com_underscore(texto):
    """
    Remove acentos e substitui espaços por underline, retornando texto em caixa alta.
    Exemplo: 'Cartão de Crédito' → 'CARTAO_DE_CREDITO'
    """
    if pd.isnull(texto):
        return texto
    texto = str(texto).strip().upper()
    texto = unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('utf-8')
    texto = texto.replace(' ', '_')
    return texto

def normalizar_vendas(arquivo_entrada):
    """
    Lê um arquivo CSV de vendas, separa a coluna 'DATA' em 'data' e 'horario',
    normaliza 'forma_pagamento' (sem acento, com underscore e em upper case),
    e salva o resultado em um novo arquivo.
    """
    separador = detectar_separador(arquivo_entrada)

    # Leitura do CSV com o separador detectado
    df = pd.read_csv(arquivo_entrada, sep=separador)

    # Conversão da coluna DATA para datetime
    df['DATA'] = pd.to_datetime(df['DATA'])

    # Criação das colunas separadas
    df['data'] = df['DATA'].dt.date
    df['horario'] = df['DATA'].dt.time

    # Remoção da coluna original
    df.drop(columns=['DATA'], inplace=True)

    # Normalização da coluna 'forma_pagamento'
    df['forma_pagamento'] = df['forma_pagamento'].apply(normalizar_texto_upper_com_underscore)

    # Reorganização das colunas
    colunas_ordenadas = [
        'cliente_id', 'venda_id', 'data', 'horario',
        'vendedor', 'desconto', 'valor_final', 'forma_pagamento'
    ]
    df = df[colunas_ordenadas]

    # Geração do nome do arquivo de saída
    base, ext = os.path.splitext(arquivo_entrada)
    arquivo_saida = f"{base}_normalizada{ext}"

    # Exporta com o mesmo separador
    df.to_csv(arquivo_saida, index=False, sep=separador)

    print(f"Arquivo salvo como: {arquivo_saida}")

# Exemplo de uso
vendas = 'vendas.csv'
normalizar_vendas(vendas)
