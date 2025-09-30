# 🎓 SGN Automação - Sistema Inteligente de Lançamento de Conceitos

API completa para automatizar o lançamento de conceitos no sistema SGN (SESI/SENAI) com **modo inteligente** baseado em avaliações e habilidades.

## ✨ Funcionalidades

### 🤖 Modo Inteligente
- ✅ **Análise automática** de avaliações cadastradas
- ✅ **Mapeamento de habilidades** vinculadas a cada avaliação
- ✅ **Cálculo inteligente** de conceitos por habilidade baseado nas notas
- ✅ **Seleção automática** de trimestre de referência
- ✅ **Preenchimento automático** de atitudes e observações
- ✅ **Salvamento automático** via AJAX do PrimeFaces

### 📊 Recursos Avançados
- ✅ Coleta de avaliações (AV1, AV2, AV3, AV4, etc.)
- ✅ Coleta de recuperações paralelas (RP1, RP2, etc.)
- ✅ Análise de média de referência por avaliação
- ✅ Mapeamento de competências e habilidades
- ✅ Logs detalhados de todo o processo
- ✅ Tratamento robusto de erros

## 🚀 Como Usar

### 1. Instalar Dependências
```bash
pip install -r requirements.txt
```

### 2. Executar a API
```bash
uvicorn main:app --reload
```

A API estará disponível em: `http://localhost:8000`

### 3. Acessar Documentação
```
http://localhost:8000/docs
```

## 📡 Endpoints

### POST /lancar-conceito-inteligente
Lança conceitos de forma inteligente baseado nas avaliações cadastradas.

**Body:**
```json
{
  "username": "seu_usuario",
  "password": "sua_senha",
  "codigo_turma": "369528",
  "trimestre_referencia": "TR2",
  "conceito_padrao": "A",
  "atitude_padrao": "Excelente participação"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Processados: 39/39 alunos"
}
```

### POST /close-browser
Fecha o navegador.

### GET /docs
Documentação Swagger interativa.

## 📁 Estrutura do Projeto

```
antitoga/
├── src/
│   ├── __init__.py           # Pacote principal
│   ├── api.py               # Rotas FastAPI
│   ├── models.py            # Modelos Pydantic
│   ├── selenium_config.py   # Configuração Selenium
│   └── sgn_automation.py    # Automação SGN (2700+ linhas)
├── main.py                  # Ponto de entrada
├── requirements.txt        # Dependências
└── README.md              # Documentação
```

## 🔄 Fluxo do Modo Inteligente

### 1. Login e Navegação
- Acessa `https://sgn.sesisenai.org.br/login.html`
- Faz login com usuário e senha
- Navega para o diário da turma

### 2. Coleta de Avaliações
- Acessa aba **Aulas/Avaliações**
- Expande painel de Avaliação
- Coleta dados de todas as avaliações:
  - Identificador (AV1, AV2, AV3, AV4)
  - Data da avaliação
  - Título
  - Formato (Prova, Trabalho, etc.)
  - Peso
  - **Média de Referência** (TR1, TR2, TR3)
  - **Habilidades vinculadas**

### 3. Mapeamento de Habilidades
Para cada avaliação:
- Abre modal da avaliação
- Lê média de referência
- Expande painel de Habilidades
- Coleta competências e habilidades vinculadas
- Fecha modal

### 4. Seleção de Trimestre
- Navega para aba **Conceitos**
- Seleciona trimestre de referência (TR1, TR2 ou TR3)
- Aguarda AJAX carregar tabela de conceitos
- Valida seleção

### 5. Lançamento de Conceitos
Para cada aluno:
- Abre modal de conceitos/atitudes
- Coleta notas das avaliações do trimestre
- **Calcula conceito por habilidade** baseado nas notas
- Preenche observações de atitudes
- Preenche conceitos de habilidades
- Salvamento automático via AJAX

## 🎯 Algoritmo Inteligente

### Cálculo de Conceitos por Habilidade

```python
# Para cada habilidade:
# 1. Identificar avaliações que a contemplam
# 2. Coletar notas dessas avaliações
# 3. Calcular conceito baseado nas notas:

if todas_notas >= 8.0:
    conceito = "A"  # Ótimo
elif todas_notas >= 6.0:
    conceito = "B"  # Bom
elif todas_notas >= 4.0:
    conceito = "C"  # Regular
else:
    conceito = "NE"  # Não Atingido
```

### Exemplo de Mapeamento

**Avaliações Cadastradas:**
- AV1 (TR1): H8, H7, H6, H4
- AV2 (TR1): H7
- AV3 (TR2): H5, H3
- AV4 (TR2): H2, H1, H4

**Para TR2:**
- H5 → Baseado em AV3
- H3 → Baseado em AV3
- H2 → Baseado em AV4
- H1 → Baseado em AV4
- H4 → Baseado em AV4

## 🔧 Exemplo de Uso

```python
import requests

data = {
    "username": "natan.rubenich",
    "password": "sua_senha",
    "codigo_turma": "369528",
    "trimestre_referencia": "TR2",
    "conceito_padrao": "A",
    "atitude_padrao": "Excelente participação e comprometimento"
}

response = requests.post(
    "http://localhost:8000/lancar-conceito-inteligente",
    json=data
)
print(response.json())
```

## 📊 Logs Detalhados

O sistema fornece logs completos de todo o processo:

```
1. Iniciando processo de login...
✅ Login realizado com sucesso

2. Navegando para o diário da turma...

3. Coletando avaliações cadastradas...
   ✓ Encontradas 4 avaliações na tabela
   
   🔍 Abrindo modal da AV1...
   ✓ Média de Referência: TR1
   ✓ Encontradas 4 habilidades vinculadas

================================================================================
📊 RESUMO DAS AVALIAÇÕES COLETADAS
================================================================================
✅ Total: 4 avaliações | 10 habilidades vinculadas

4. Navegando para aba Conceitos...

5. Selecionando trimestre de referência...
   📋 Opções disponíveis: ['TR1', 'TR2']
   ✓ Opção clicada via JavaScript
   ✅ Trimestre selecionado com sucesso!

6. Iniciando lançamento INTELIGENTE de conceitos...
   👤 Processando aluno 1/39: Ana Carolina Will
   ✅ Conceitos aplicados para Ana Carolina Will

✅ Lançamento concluído: Processados: 39/39 alunos
```

## ⚙️ Configurações

### Selenium
- **Navegador**: Chrome (headless opcional)
- **Timeout padrão**: 10 segundos
- **Estratégia**: JavaScript para cliques em PrimeFaces

### Performance
- Login otimizado: ~4s
- Coleta de avaliações: ~2s por avaliação
- Lançamento por aluno: ~3-5s
- **Total estimado**: ~5-10 minutos para turma de 40 alunos

## 🛠️ Tecnologias

- **FastAPI**: Framework web assíncrono
- **Selenium**: Automação de navegador
- **Pydantic**: Validação de dados
- **Uvicorn**: Servidor ASGI
- **Chrome WebDriver**: Controle do navegador

## 📝 Notas Importantes

1. **Avaliações obrigatórias**: O modo inteligente requer que as avaliações estejam cadastradas no SGN
2. **Habilidades vinculadas**: Cada avaliação deve ter habilidades vinculadas
3. **Trimestre de referência**: Deve corresponder às avaliações cadastradas
4. **Salvamento automático**: O sistema usa AJAX do PrimeFaces (sem botão Salvar)

## 🔒 Segurança

- Credenciais não são armazenadas
- Sessão do navegador é isolada
- Logs não expõem senhas
- Conexão HTTPS com SGN

## 📄 Licença

Projeto interno SESI/SENAI
