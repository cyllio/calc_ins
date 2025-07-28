<<<<<<< HEAD
import streamlit as st
import pandas as pd
import os
from datetime import datetime
from PIL import Image
import io
import requests
import base64

# Configuração da página
st.set_page_config(page_title="Cadastro de Insumos com Foto", layout="wide")
st.title("📸 Cadastro de Insumos para Receita")

# Lê a chave da OpenAI do secrets.toml
openai_api_key = st.secrets["openai"]["api_key"]
OPENAI_URL = "https://api.openai.com/v1/chat/completions"

# Função para inicializar lista de produtos na sessão
if 'produtos' not in st.session_state:
    st.session_state['produtos'] = []
if 'nome_receita' not in st.session_state:
    st.session_state['nome_receita'] = ''
if 'rendimento' not in st.session_state:
    st.session_state['rendimento'] = ''
if 'observacoes' not in st.session_state:
    st.session_state['observacoes'] = ''
# Estados para controle da captura
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
        'preco': 0.0,
        'marca': '',
        'validade': '',
        'lote': ''
    }

# Função para gerar hash da foto
def get_foto_hash(foto_bytes):
    import hashlib
    return hashlib.md5(foto_bytes).hexdigest()

# Função para adicionar produto à lista
def adicionar_produto(produto):
    st.session_state['produtos'].append(produto)

# Função para extrair texto da imagem usando OpenAI Vision (GPT-4o)
def extrair_texto_imagem_openai(image_bytes):
    image_base64 = base64.b64encode(image_bytes).decode()
    headers = {
        "Authorization": f"Bearer {openai_api_key}",
        "Content-Type": "application/json"
    }
    prompt = (
        "Extraia todos os textos legíveis da imagem de embalagem de produto alimentício. "
        "Se possível, identifique: nome do produto, unidade, marca, validade, lote, preço. "
        "Responda apenas com o texto extraído, sem explicações."
    )
    data = {
        "model": "gpt-4o",
        "messages": [
            {"role": "system", "content": "Você é um extrator de texto de imagens de embalagens."},
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

# Função para parsing inteligente dos campos extraídos
def extrair_campos_automaticamente(texto_extraido):
    import re
    descricao = ''
    unidade = ''
    volume = ''
    preco = 0.0
    marca = ''
    validade = ''
    lote = ''
    
    linhas = texto_extraido.split('\n')
    for linha in linhas:
        l = linha.lower()
        if not descricao and len(linha.strip()) > 3 and not re.match(r'^\d+$', linha.strip()):
            descricao = linha.strip()
        
        # Busca por volume (capacidade do produto)
        volume_match = re.search(r'(\d+[\.,]?\d*)\s*(kg|g|ml|l|lt|ml)', l)
        if volume_match:
            volume = volume_match.group(0)
        
        # Busca por unidade de medida
        unidade_match = re.search(r'\b(kg|g|ml|l|lt|unid|unidade|unidades|metros|cm)\b', l)
        if unidade_match:
            unidade = unidade_match.group(1)
        
        # Busca por preço
        preco_match = re.search(r'(r\$\s*\d+[\.,]?\d*)', l)
        if preco_match:
            preco_str = preco_match.group(0).replace('r$', '').replace(' ', '').replace(',', '.')
            try:
                preco = float(preco_str)
            except:
                pass
        
        # Busca por marca
        if 'marca' in l:
            marca = linha.split(':')[-1].strip()
        
        # Busca por validade
        if 'validade' in l:
            validade = linha.split(':')[-1].strip()
        
        # Busca por lote
        if 'lote' in l:
            lote = linha.split(':')[-1].strip()
    
    return {
        'descricao': descricao,
        'unidade': unidade,
        'volume': volume,
        'preco': preco,
        'marca': marca,
        'validade': validade,
        'lote': lote
    }

# Interface principal
st.subheader("Adicionar Produto com Foto")

# Botão para ativar a captura
if st.button("📷 CAPTURAR"):
    st.session_state['capturar'] = True
    st.session_state['foto_bytes'] = None
    st.session_state['foto_hash'] = None
    st.session_state['texto_original'] = ''
    st.session_state['debug_info'] = None
    st.session_state['campos_extraidos'] = {
        'descricao': '',
        'unidade': '',
        'volume': '',
        'preco': 0.0,
        'marca': '',
        'validade': '',
        'lote': ''
    }

# Mostra mensagem quando a câmera não está ativa
if not st.session_state['capturar']:
    st.info("📷 Clique em 'CAPTURAR' para ativar a câmera e tirar uma foto do produto.")

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
            st.session_state['campos_extraidos'] = extrair_campos_automaticamente(texto_extraido)
        else:
            # Se a foto não mudou, apenas armazena os bytes
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
    quantidade = st.number_input("Quantidade utilizada na receita:", min_value=0.0, step=0.01, format="%.2f")
    unidade = st.text_input("Unidade de medida (kg, g, ml, l, unid, etc):", value=st.session_state['campos_extraidos']['unidade'])
    volume = st.text_input("Volume/Capacidade do produto (1lt, 350g, 2kg, etc):", value=st.session_state['campos_extraidos']['volume'])
    preco = st.number_input("Preço médio de mercado (R$):", min_value=0.0, step=0.01, format="%.2f", value=st.session_state['campos_extraidos']['preco'])

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
            'quantidade': quantidade,
            'unidade_medida': unidade,
            'volume_capacidade': volume,
            'preco_medio_mercado': preco,
            'marca': marca,
            'validade': validade,
            'lote': lote,
            'texto_original': st.session_state['texto_original']
        }
        adicionar_produto(produto)
        st.success("✅ Produto adicionado com sucesso!")
        
        # Limpa estado da foto e campos
        st.session_state['foto_bytes'] = None
        st.session_state['foto_hash'] = None
        st.session_state['texto_original'] = ''
        st.session_state['debug_info'] = None
        st.session_state['campos_extraidos'] = {
            'descricao': '',
            'unidade': '',
            'volume': '',
            'preco': 0.0,
            'marca': '',
            'validade': '',
            'lote': ''
        }
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
        
        # Adiciona linha de total
        rodape = pd.DataFrame({
            'timestamp': [''],
            'descricao_produto': ['TOTAL'],
            'quantidade': [total_qtd],
            'unidade_medida': [''],
            'volume_capacidade': [''],
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
        
        # Limpa a lista de produtos após salvar
        st.session_state['produtos'] = []
        st.rerun()
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
=======
import streamlit as st
import pandas as pd
import os
from datetime import datetime
from PIL import Image
import io
import requests
import base64

# Configuração da página
st.set_page_config(page_title="Cadastro de Insumos com Foto", layout="wide")
st.title("📸 Cadastro de Insumos para Receita")

# Lê a chave da OpenAI do secrets.toml
openai_api_key = st.secrets["openai"]["api_key"]
OPENAI_URL = "https://api.openai.com/v1/chat/completions"

# Função para inicializar lista de produtos na sessão
if 'produtos' not in st.session_state:
    st.session_state['produtos'] = []
if 'nome_receita' not in st.session_state:
    st.session_state['nome_receita'] = ''
if 'rendimento' not in st.session_state:
    st.session_state['rendimento'] = ''
if 'observacoes' not in st.session_state:
    st.session_state['observacoes'] = ''
# Estados para controle da captura
if 'capturar' not in st.session_state:
    st.session_state['capturar'] = False
if 'foto_bytes' not in st.session_state:
    st.session_state['foto_bytes'] = None
if 'foto_hash' not in st.session_state:
    st.session_state['foto_hash'] = None
if 'texto_extraido' not in st.session_state:
    st.session_state['texto_extraido'] = ''
if 'debug_info' not in st.session_state:
    st.session_state['debug_info'] = None
if 'campos_auto' not in st.session_state:
    st.session_state['campos_auto'] = ('', '', 0.0, '', '', '')

# Função para gerar hash da foto
def get_foto_hash(foto_bytes):
    import hashlib
    return hashlib.md5(foto_bytes).hexdigest()

# Função para adicionar produto à lista
def adicionar_produto(produto):
    st.session_state['produtos'].append(produto)

# Função para extrair texto da imagem usando OpenAI Vision (GPT-4o)
def extrair_texto_imagem_openai(image_bytes):
    image_base64 = base64.b64encode(image_bytes).decode()
    headers = {
        "Authorization": f"Bearer {openai_api_key}",
        "Content-Type": "application/json"
    }
    prompt = (
        "Extraia todos os textos legíveis da imagem de embalagem de produto alimentício. "
        "Se possível, identifique: nome do produto, unidade, marca, validade, lote, preço. "
        "Responda apenas com o texto extraído, sem explicações."
    )
    data = {
        "model": "gpt-4o",
        "messages": [
            {"role": "system", "content": "Você é um extrator de texto de imagens de embalagens."},
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

# Função para parsing inteligente dos campos extraídos
def preencher_campos_automaticamente(texto_extraido):
    import re
    descricao = ''
    unidade = ''
    preco = 0.0
    marca = ''
    validade = ''
    lote = ''
    linhas = texto_extraido.split('\n')
    for linha in linhas:
        l = linha.lower()
        if not descricao and len(linha.strip()) > 3 and not re.match(r'^\d+$', linha.strip()):
            descricao = linha.strip()
        unidade_match = re.search(r'(\d+[\.,]?\d*)\s*(kg|g|ml|l|unid|unidade|unidades|metros|cm)', l)
        if unidade_match:
            unidade = unidade_match.group(0)
        preco_match = re.search(r'(r\$\s*\d+[\.,]?\d*)', l)
        if preco_match:
            preco_str = preco_match.group(0).replace('r$', '').replace(' ', '').replace(',', '.')
            try:
                preco = float(preco_str)
            except:
                pass
        if 'marca' in l:
            marca = linha.split(':')[-1].strip()
        if 'validade' in l:
            validade = linha.split(':')[-1].strip()
        if 'lote' in l:
            lote = linha.split(':')[-1].strip()
    return descricao, unidade, preco, marca, validade, lote

# Interface principal
st.subheader("Adicionar Produto com Foto")
col1, col2 = st.columns([2, 2])

with col1:
    # Botão para ativar a captura
    if st.button("CAPTURAR"):
        st.session_state['capturar'] = True
        st.session_state['foto_bytes'] = None
        st.session_state['foto_hash'] = None
        st.session_state['texto_extraido'] = ''
        st.session_state['debug_info'] = None
        st.session_state['campos_auto'] = ('', '', 0.0, '', '', '')

    # Mostra mensagem quando a câmera não está ativa
    if not st.session_state['capturar']:
        st.info("📷 Clique em 'CAPTURAR' para ativar a câmera e tirar uma foto do produto.")
    
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
                st.session_state['texto_extraido'] = texto_extraido
                st.session_state['debug_info'] = debug_info
                st.session_state['campos_auto'] = preencher_campos_automaticamente(texto_extraido)
            else:
                # Se a foto não mudou, apenas armazena os bytes
                st.session_state['foto_bytes'] = foto_bytes
                st.session_state['capturar'] = False

    # Exibe a imagem capturada, se houver
    if st.session_state['foto_bytes']:
        st.image(st.session_state['foto_bytes'], caption="Foto capturada", width=200)
    # Exibe o texto extraído, se houver
    if st.session_state['texto_extraido']:
        st.text_area("Texto extraído da embalagem:", value=st.session_state['texto_extraido'], height=100)
    elif st.session_state['foto_bytes']:
        st.warning("Nenhum texto extraído da embalagem. Confira a qualidade da foto e se há texto visível.")
    # Debug
    if st.session_state['debug_info']:
        with st.expander("🔎 Debug IA (clique para ver detalhes)"):
            st.write(st.session_state['debug_info'])
    # Preenche os campos automáticos
    descricao_auto, unidade_auto, preco_auto, marca_auto, validade_auto, lote_auto = st.session_state['campos_auto']

# Inicialização padrão dos campos automáticos caso não estejam definidos
if 'campos_auto' not in st.session_state or not st.session_state['campos_auto']:
    descricao_auto = ''
    unidade_auto = ''
    preco_auto = 0.0
    marca_auto = ''
    validade_auto = ''
    lote_auto = ''
else:
    descricao_auto, unidade_auto, preco_auto, marca_auto, validade_auto, lote_auto = st.session_state['campos_auto']

with col2:
    descricao = st.text_input("Descrição do produto:", value=descricao_auto)
    quantidade = st.number_input("Quantidade utilizada na receita:", min_value=0.0, step=0.01, format="%.2f")
    unidade = st.text_input("Unidade de medida:", value=unidade_auto)
    preco = st.number_input("Preço médio de mercado (R$):", min_value=0.0, step=0.01, format="%.2f", value=preco_auto)
    marca = st.text_input("Marca (opcional):", value=marca_auto)
    validade = st.text_input("Validade (opcional):", value=validade_auto)
    lote = st.text_input("Lote (opcional):", value=lote_auto)

# Botão para adicionar produto com foto
if st.button("Adicionar Produto com Foto"):
    if descricao and unidade:
        produto = {
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'imagem_base64': '',  # Não salva imagem
            'descricao_produto': descricao,
            'quantidade': quantidade,  # Pode ficar em branco
            'unidade_medida': unidade,
            'preco_medio_mercado': preco,
            'marca': marca,
            'validade': validade,
            'lote': lote,
            'tamanho_arquivo_bytes': ''
        }
        adicionar_produto(produto)
        st.success("Produto adicionado!")
        # Limpa estado da foto e campos automáticos
        st.session_state['foto_bytes'] = None
        st.session_state['foto_hash'] = None
        st.session_state['texto_extraido'] = ''
        st.session_state['debug_info'] = None
        st.session_state['campos_auto'] = ('', '', 0.0, '', '', '')
    else:
        st.warning("Preencha ao menos a descrição e unidade!")

st.divider()
st.subheader("Adicionar Produto Manualmente (sem foto)")
col3, col4 = st.columns([2, 2])

with col3:
    descricao_m = st.text_input("Descrição do produto (manual):", key="desc_manual")
    quantidade_m = st.number_input("Quantidade utilizada na receita (manual):", min_value=0.0, step=0.01, format="%.2f", key="qtd_manual")
    unidade_m = st.text_input("Unidade de medida (manual):", key="unid_manual")
    preco_m = st.number_input("Preço médio de mercado (manual) (R$):", min_value=0.0, step=0.01, format="%.2f", key="preco_manual")
    marca_m = st.text_input("Marca (manual, opcional):", key="marca_manual")
    validade_m = st.text_input("Validade (manual, opcional):", key="validade_manual")
    lote_m = st.text_input("Lote (manual, opcional):", key="lote_manual")

# Botão para adicionar produto manualmente
if st.button("INSERIR PRODUTO MANUALMENTE"):
    if descricao_m and unidade_m:
        produto = {
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'imagem_base64': '',
            'descricao_produto': descricao_m,
            'quantidade': quantidade_m,
            'unidade_medida': unidade_m,
            'preco_medio_mercado': preco_m,
            'marca': marca_m,
            'validade': validade_m,
            'lote': lote_m,
            'tamanho_arquivo_bytes': ''
        }
        adicionar_produto(produto)
        st.success("Produto manual adicionado!")
    else:
        st.warning("Preencha ao menos a descrição e unidade!")

st.divider()
st.subheader("Produtos Cadastrados")
if st.session_state['produtos']:
    df = pd.DataFrame(st.session_state['produtos'])
    st.dataframe(df.drop(columns=['imagem_base64']), use_container_width=True)
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

if st.button("Finalizar e Salvar Receita"):
    if st.session_state['produtos'] and st.session_state['nome_receita']:
        df = pd.DataFrame(st.session_state['produtos'])
        df['nome_receita'] = st.session_state['nome_receita']
        df['rendimento_total'] = st.session_state['rendimento']
        df['observacoes'] = st.session_state['observacoes']
        total_custo = df['preco_medio_mercado'].sum()
        total_qtd = df['quantidade'].sum()
        rodape = pd.DataFrame({
            'timestamp': [''],
            'imagem_base64': [''],
            'descricao_produto': ['TOTAL'],
            'quantidade': [total_qtd],
            'unidade_medida': [''],
            'preco_medio_mercado': [total_custo],
            'marca': [''],
            'validade': [''],
            'lote': [''],
            'tamanho_arquivo_bytes': [''],
            'nome_receita': [''],
            'rendimento_total': [''],
            'observacoes': ['']
        })
        df_final = pd.concat([df, rodape], ignore_index=True)
        nome_csv = gerar_nome_csv(st.session_state['nome_receita'])
        df_final.to_csv(nome_csv, sep=';', index=False)
        st.success(f"Receita salva em {nome_csv}!")
        st.download_button(
            label="📥 Baixar CSV da Receita",
            data=df_final.to_csv(sep=';', index=False),
            file_name=nome_csv,
            mime="text/csv"
        )
        st.session_state['produtos'] = []
    else:
        st.warning("Cadastre ao menos um produto e informe o nome da receita!")

st.divider()
with st.expander("ℹ️ Estrutura das Colunas do CSV"):
    st.write("""
    - timestamp: Data e hora do cadastro
    - descricao_produto: Descrição do produto
    - quantidade: Quantidade utilizada na receita
    - unidade_medida: Unidade de medida
    - preco_medio_mercado: Preço médio de mercado
    - marca: Marca do produto
    - validade: Validade
    - lote: Lote
    - nome_receita: Nome da receita
    - rendimento_total: Rendimento total informado
    - observacoes: Observações gerais da receita
>>>>>>> a85f5c058de5153fb3f507837184042f7b164944
    """)