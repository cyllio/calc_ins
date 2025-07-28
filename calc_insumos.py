# cd C:\Users\lucia\Downloads\insumos
# git init
# # git remote add origin https://github.com/cyllio/calc_ins.git
# git remote set-url origin https://github.com/cyllio/calc_ins.git
# git add .
# git commit -m "ajusta reset de campos ainda com lixo"
# git branch -M main
# git push -u origin main

import streamlit as st
import pandas as pd
from datetime import datetime
import requests
import base64
import re
import json

# Configuração da página
st.set_page_config(page_title="Cadastro de Insumos com Foto", layout="wide")
st.title("📸 Cadastro de Insumos para Receita")

# Lê a chave da OpenAI do secrets.toml
openai_api_key = st.secrets["openai"]["api_key"]
OPENAI_URL = "https://api.openai.com/v1/chat/completions"

# Inicialização de estados
if 'produtos' not in st.session_state:
    st.session_state['produtos'] = []
if 'nome_receita' not in st.session_state:
    st.session_state['nome_receita'] = ''
if 'rendimento' not in st.session_state:
    st.session_state['rendimento'] = ''
if 'observacoes' not in st.session_state:
    st.session_state['observacoes'] = ''
if 'capturar' not in st.session_state:
    st.session_state['capturar'] = False
if 'foto_bytes' not in st.session_state:
    st.session_state['foto_bytes'] = None
if 'foto_hash' not in st.session_state:
    st.session_state['foto_hash'] = None
if 'texto_original' not in st.session_state:
    st.session_state['texto_original'] = ''
if 'debug_info' not in st.session_state:
    st.session_state['debug_info'] = None
if 'campos_extraidos' not in st.session_state:
    st.session_state['campos_extraidos'] = {
        'descricao': '',
        'unidade': '',
        'volume': '',
        'preco': None,
        'marca': '',
        'validade': '',
        'lote': ''
    }
if 'quantidade_input' not in st.session_state:
    st.session_state['quantidade_input'] = 0.0
if 'preco_input' not in st.session_state:
    st.session_state['preco_input'] = 0.0

# Função para resetar o formulário (sem mexer em 'capturar')
def resetar_formulario():
    st.session_state['foto_bytes'] = None
    st.session_state['foto_hash'] = None
    st.session_state['texto_original'] = ''
    st.session_state['debug_info'] = None
    st.session_state['campos_extraidos'] = {
        'descricao': '',
        'unidade': '',
        'volume': '',
        'preco': None,
        'marca': '',
        'validade': '',
        'lote': ''
    }
    st.session_state['quantidade_input'] = 0.0
    st.session_state['preco_input'] = 0.0

# Função para gerar hash da foto
def get_foto_hash(foto_bytes):
    import hashlib
    return hashlib.md5(foto_bytes).hexdigest()

# Função para adicionar produto à lista
def adicionar_produto(produto):
    st.session_state['produtos'].append(produto)

# Função para buscar preço médio na internet (Mercado Livre)
def buscar_preco_medio(descricao):
    try:
        url = f"https://api.mercadolibre.com/sites/MLB/search?q={descricao}"
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            if data['results']:
                precos = [item['price'] for item in data['results'] if 'price' in item]
                if precos:
                    return round(sum(precos) / len(precos), 2)
    except Exception:
        pass
    return None

# Função para extrair texto da imagem usando OpenAI Vision (GPT-4o)
def extrair_texto_imagem_openai(image_bytes):
    image_base64 = base64.b64encode(image_bytes).decode()
    headers = {
        "Authorization": f"Bearer {openai_api_key}",
        "Content-Type": "application/json"
    }
    prompt = (
        "Extraia todos os textos legíveis da imagem de embalagem de produto alimentício. "
        "Se possível, identifique: nome popular do produto, fabricante/marca, unidade de medida (apenas a unidade, como kg, g, ml, l, etc), volume/capacidade (ex: 2kg, 350g, 1lt), preço, validade, lote. "
        "No campo 'unidade' coloque apenas a unidade, sem números. No campo 'volume' coloque o valor completo, como '2kg', '350g', etc. "
        "Se algum campo não estiver claro, sugira o melhor conteúdo para suprir a ausência. "
        "Responda no formato JSON com as chaves: descricao, marca, unidade, volume, preco, validade, lote."
    )
    data = {
        "model": "gpt-4o",
        "messages": [
            {"role": "system", "content": "Você é um extrator de dados estruturados de imagens de embalagens."},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
                ]
            }
        ],
        "max_tokens": 512
    }
    response = requests.post(OPENAI_URL, headers=headers, json=data)
    debug_info = {'status_code': response.status_code}
    if response.status_code == 200:
        result = response.json()
        debug_info['result'] = result
        try:
            texto = result['choices'][0]['message']['content']
            return texto, debug_info
        except Exception:
            return '', debug_info
    else:
        try:
            debug_info['result'] = response.json()
        except Exception:
            debug_info['result'] = response.text
        return '', debug_info

# Função para parsing dos campos extraídos (garantindo separação correta)
def extrair_campos_automaticamente(texto_extraido):
    campos = {
        'descricao': '',
        'unidade': '',
        'volume': '',
        'preco': None,
        'marca': '',
        'validade': '',
        'lote': ''
    }
    # Tenta extrair JSON do texto
    try:
        match = re.search(r'\{.*\}', texto_extraido, re.DOTALL)
        if match:
            dados = json.loads(match.group(0))
            for k in campos:
                if k in dados:
                    campos[k] = dados[k]
            try:
                campos['preco'] = float(str(campos['preco']).replace(',', '.')) if campos['preco'] else None
            except:
                campos['preco'] = None
    except Exception:
        pass

    # Parsing manual para garantir separação correta
    linhas = texto_extraido.split('\n')
    volume_pattern = re.compile(r'(\d+[\.,]?\d*)\s*(kg|g|ml|l|lt|unid|unidade|unidades|metros|cm)\b', re.IGNORECASE)
    unidade_pattern = re.compile(r'\b(kg|g|ml|l|lt|unid|unidade|unidades|metros|cm)\b', re.IGNORECASE)

    volumes_encontrados = []
    unidades_encontradas = []

    for linha in linhas:
        # Volume/capacidade: número + unidade
        for m in volume_pattern.finditer(linha):
            volumes_encontrados.append(m.group(0).replace(' ', ''))
        # Unidade: só a unidade, sem número antes
        for m in unidade_pattern.finditer(linha):
            # Só adiciona se não for parte de um volume já encontrado
            if not any(m.group(0) in v for v in volumes_encontrados):
                unidades_encontradas.append(m.group(0))

    # Preenche os campos corretamente
    if volumes_encontrados:
        campos['volume'] = volumes_encontrados[0]
    if unidades_encontradas:
        campos['unidade'] = unidades_encontradas[0]
    elif campos['volume']:
        # Se não achou unidade isolada, extrai só a unidade do volume
        unidade_match = unidade_pattern.search(campos['volume'])
        if unidade_match:
            campos['unidade'] = unidade_match.group(0)

    # Ajusta campos obrigatórios
    if not campos['descricao']:
        campos['descricao'] = "Produto não identificado. Informe o nome popular."
    if not campos['marca']:
        campos['marca'] = "Marca não identificada. Informe o fabricante."
    return campos

# Interface principal
st.subheader("Adicionar Produto com Foto")

# Botão para ativar a captura
if st.button("📷 CAPTURAR"):
    st.session_state['capturar'] = True
    resetar_formulario()

# Mostra mensagem quando a câmera não está ativa
if not st.session_state['capturar']:
    st.info("📷 Clique em 'CAPTURAR' para ativar a câmera e tirar uma foto do produto.")

# Dica para câmera traseira
if st.session_state['capturar']:
    st.warning("Se estiver no celular, use o ícone de troca de câmera para selecionar a câmera traseira.")

# Só mostra a câmera se o usuário clicou em CAPTURAR
if st.session_state['capturar']:
    st.success("📸 Câmera ativada! Tire uma foto do produto.")
    foto = st.camera_input("Tire uma foto do produto (os dados serão extraídos automaticamente)")
    
    if foto is not None:
        foto_bytes = foto.getvalue()
        foto_hash = get_foto_hash(foto_bytes)
        
        # Só processa se a foto for nova
        if foto_hash != st.session_state['foto_hash']:
            st.session_state['foto_bytes'] = foto_bytes
            st.session_state['foto_hash'] = foto_hash
            st.session_state['capturar'] = False  # Desativa a câmera após captura
            
            with st.spinner('Extraindo dados da embalagem com IA OpenAI...'):
                texto_extraido, debug_info = extrair_texto_imagem_openai(foto_bytes)
            
            st.session_state['texto_original'] = texto_extraido
            st.session_state['debug_info'] = debug_info
            campos = extrair_campos_automaticamente(texto_extraido)
            # Busca preço médio se não veio da IA
            if (campos['preco'] is None or campos['preco'] == 0) and campos['descricao']:
                preco_medio = buscar_preco_medio(campos['descricao'])
                if preco_medio:
                    campos['preco'] = preco_medio
            st.session_state['campos_extraidos'] = campos
            st.session_state['quantidade_input'] = 0.0
            st.session_state['preco_input'] = campos['preco'] if campos['preco'] else 0.0
            st.rerun()
        else:
            st.session_state['foto_bytes'] = foto_bytes
            st.session_state['capturar'] = False

# Exibe a imagem capturada, se houver
if st.session_state['foto_bytes']:
    st.image(st.session_state['foto_bytes'], caption="Foto capturada", width=200)

# Exibe o texto original extraído, se houver
if st.session_state['texto_original']:
    st.text_area("Texto original extraído da embalagem:", value=st.session_state['texto_original'], height=100)
elif st.session_state['foto_bytes']:
    st.warning("Nenhum texto extraído da embalagem. Confira a qualidade da foto e se há texto visível.")

# Debug
if st.session_state['debug_info']:
    with st.expander("🔎 Debug IA (clique para ver detalhes)"):
        st.write(st.session_state['debug_info'])

# Formulário único para edição dos dados
st.subheader("Dados do Produto")
col1, col2 = st.columns([2, 2])

with col1:
    descricao = st.text_input("Descrição do produto:", value=st.session_state['campos_extraidos']['descricao'])
    quantidade = st.number_input(
        "Quantidade utilizada na receita:",
        min_value=0.0,
        step=0.01,
        format="%.2f",
        value=st.session_state['quantidade_input'],
        key="quantidade_input"
    )
    unidade = st.text_input("Unidade de medida (kg, g, ml, l, unid, etc):", value=st.session_state['campos_extraidos']['unidade'])
    volume = st.text_input("Volume/Capacidade do produto (1lt, 350g, 2kg, etc):", value=st.session_state['campos_extraidos']['volume'])
    preco = st.number_input(
        "Preço médio de mercado (R$):",
        min_value=0.0,
        step=0.01,
        format="%.2f",
        value=st.session_state['preco_input'],
        key="preco_input"
    )

with col2:
    marca = st.text_input("Marca (opcional):", value=st.session_state['campos_extraidos']['marca'])
    validade = st.text_input("Validade (opcional):", value=st.session_state['campos_extraidos']['validade'])
    lote = st.text_input("Lote (opcional):", value=st.session_state['campos_extraidos']['lote'])

# Botão para adicionar produto
if st.button("✅ INSERIR PRODUTO"):
    if descricao and unidade:
        produto = {
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'descricao_produto': descricao,
            'quantidade': st.session_state['quantidade_input'],
            'unidade_medida': unidade,
            'volume_capacidade': volume,
            'preco_medio_mercado': st.session_state['preco_input'],
            'marca': marca,
            'validade': validade,
            'lote': lote,
            'texto_original': st.session_state['texto_original']
        }
        adicionar_produto(produto)
        st.success("✅ Produto adicionado com sucesso!")
        resetar_formulario()
        st.session_state['capturar'] = False
        st.rerun()
    else:
        st.warning("⚠️ Preencha ao menos a descrição e unidade!")

st.divider()
st.subheader("Produtos Cadastrados")
if st.session_state['produtos']:
    df = pd.DataFrame(st.session_state['produtos'])
    st.dataframe(df.drop(columns=['texto_original']), use_container_width=True)
else:
    st.info("Nenhum produto cadastrado ainda.")

st.divider()
st.subheader("Finalizar Receita")
st.session_state['nome_receita'] = st.text_input("Nome da Receita:", value=st.session_state['nome_receita'])
st.session_state['rendimento'] = st.text_input("Rendimento total (ex: 2kg divididos em 10 potes de 200g):", value=st.session_state['rendimento'])
st.session_state['observacoes'] = st.text_area("Observações:", value=st.session_state['observacoes'])

def gerar_nome_csv(nome_receita):
    nome = nome_receita.strip().replace(' ', '_').lower()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    return f"{nome}_{timestamp}.csv"

if st.button("🎯 Finalizar e Salvar Receita"):
    if st.session_state['produtos'] and st.session_state['nome_receita']:
        df = pd.DataFrame(st.session_state['produtos'])
        df['nome_receita'] = st.session_state['nome_receita']
        df['rendimento_total'] = st.session_state['rendimento']
        df['observacoes'] = st.session_state['observacoes']

        # Calcula totais
        total_custo = df['preco_medio_mercado'].sum()
        total_qtd = df['quantidade'].sum()
        total_volume = ''
        if 'volume_capacidade' in df.columns and df['volume_capacidade'].apply(lambda x: isinstance(x, str) and x.strip() != '').any():
            total_volume = ' / '.join(df['volume_capacidade'].dropna().unique())

        # Adiciona linha de total
        rodape = pd.DataFrame({
            'timestamp': [''],
            'descricao_produto': ['TOTAL'],
            'quantidade': [total_qtd],
            'unidade_medida': [''],
            'volume_capacidade': [total_volume],
            'preco_medio_mercado': [total_custo],
            'marca': [''],
            'validade': [''],
            'lote': [''],
            'texto_original': [''],
            'nome_receita': [''],
            'rendimento_total': [''],
            'observacoes': ['']
        })

        df_final = pd.concat([df, rodape], ignore_index=True)
        nome_csv = gerar_nome_csv(st.session_state['nome_receita'])
        df_final.to_csv(nome_csv, sep=';', index=False)

        st.success(f"✅ Receita salva em {nome_csv}!")
        st.download_button(
            label="📥 Baixar CSV da Receita",
            data=df_final.to_csv(sep=';', index=False),
            file_name=nome_csv,
            mime="text/csv"
        )

        # Limpa a lista de produtos e campos de receita após salvar
        st.session_state['produtos'] = []
        st.session_state['nome_receita'] = ''
        st.session_state['rendimento'] = ''
        st.session_state['observacoes'] = ''
        resetar_formulario()
        st.session_state['capturar'] = False
        st.rerun()
        st.success("Formulário limpo para nova receita!")
    else:
        st.warning("⚠️ Cadastre ao menos um produto e informe o nome da receita!")

st.divider()
with st.expander("ℹ️ Estrutura das Colunas do CSV"):
    st.write("""
    - timestamp: Data e hora do cadastro
    - descricao_produto: Descrição do produto
    - quantidade: Quantidade utilizada na receita
    - unidade_medida: Unidade de medida (kg, g, ml, l, unid, etc)
    - volume_capacidade: Volume/Capacidade do produto (1lt, 350g, 2kg, etc)
    - preco_medio_mercado: Preço médio de mercado
    - marca: Marca do produto
    - validade: Validade
    - lote: Lote
    - texto_original: Texto original extraído da imagem
    - nome_receita: Nome da receita
    - rendimento_total: Rendimento total informado
    - observacoes: Observações gerais da receita
    """)