# SGN Automação de Notas - Versão Organizada

API estruturada para automatizar login e navegação no sistema SGN até a aba de Conceitos.

## 🚀 Como Usar

### 1. Instalar Dependências
```bash
pip install -r requirements.txt
```

### 2. Executar a API
```bash
python main.py
```

A API estará disponível em: `http://localhost:8000`

### 3. Testar
```bash
python test_api.py
```

## 📡 Endpoints

### POST /login-and-navigate
Faz login e navega até a aba de Conceitos.

**Body:**
```json
{
  "username": "seu_usuario",
  "password": "sua_senha", 
  "codigo_turma": "369528"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Login realizado e navegação concluída!"
}
```

### POST /close-browser
Fecha o navegador.

### GET /docs
Documentação Swagger da API.

## 📁 Estrutura do Projeto

```
antitoga/
├── src/
│   ├── __init__.py           # Pacote principal
│   ├── api.py               # Rotas FastAPI
│   ├── models.py            # Modelos Pydantic
│   ├── selenium_config.py   # Configuração Selenium
│   └── sgn_automation.py    # Automação SGN
├── main.py                  # Ponto de entrada
├── test_api.py             # Script de teste
├── requirements.txt        # Dependências
└── README.md              # Documentação
```

## 🔄 Fluxo Implementado

1. ✅ Acessa `https://sgn.sesisenai.org.br/login.html`
2. ✅ Faz login com usuário e senha
3. ✅ Navega para buscar diário
4. ✅ Acessa diário da turma diretamente via URL
5. ✅ Abre aba de Conceitos

## 🎯 Próximos Passos

Após testar esta versão, continuaremos implementando:
- Lançamento de notas
- Seleção de alunos
- Validações adicionais

## 🔧 Exemplo de Uso

```python
import requests

data = {
    "username": "natan.rubenich",
    "password": "Barning123", 
    "codigo_turma": "369528"
}

response = requests.post("http://localhost:8000/login-and-navigate", json=data)
print(response.json())
```
