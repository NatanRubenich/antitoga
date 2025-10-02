# 🎓 Exemplo de Uso: Endpoint `/lancar-conceito-inteligente-RA`

## 📋 Descrição

Este endpoint é uma extensão do `/lancar-conceito-inteligente` que adiciona funcionalidade de **Recomposição de Aprendizagem (RA)** para alunos com conceito C.

## 🔑 Diferenças Principais

| Característica | `/lancar-conceito-inteligente` | `/lancar-conceito-inteligente-RA` |
|---|---|---|
| **Conceito C** | Troca por NE automaticamente | **Mantém C** |
| **RA** | Não cadastra | **Cadastra para cada habilidade C** |
| **Upload de arquivo** | Não | **Sim (PDF obrigatório)** |
| **Campos adicionais** | Não | **Sim (datas, descrição)** |

## 📝 Exemplo de Uso com cURL

```bash
curl -X POST "http://localhost:8000/lancar-conceito-inteligente-RA" \
  -H "Content-Type: multipart/form-data" \
  -F "username=seu.usuario" \
  -F "password=sua.senha" \
  -F "codigo_turma=369528" \
  -F "inicio_ra=01/10/2025" \
  -F "termino_ra=31/10/2025" \
  -F "descricao_ra=Reforço em programação orientada a objetos. O aluno participará de atividades práticas para desenvolver suas habilidades." \
  -F "nome_arquivo_ra=RA_Turma_369528_TR2.pdf" \
  -F "arquivo_ra=@/caminho/para/arquivo.pdf" \
  -F "atitude_observada=Raramente" \
  -F "conceito_habilidade=B" \
  -F "trimestre_referencia=TR2"
```

## 🐍 Exemplo de Uso com Python (requests)

```python
import requests

url = "http://localhost:8000/lancar-conceito-inteligente-RA"

# Dados do formulário
data = {
    "username": "seu.usuario",
    "password": "sua.senha",
    "codigo_turma": "369528",
    "inicio_ra": "01/10/2025",
    "termino_ra": "31/10/2025",
    "descricao_ra": "Reforço em programação orientada a objetos",
    "nome_arquivo_ra": "RA_Turma_369528_TR2.pdf",
    "atitude_observada": "Raramente",
    "conceito_habilidade": "B",
    "trimestre_referencia": "TR2"
}

# Arquivo PDF
files = {
    "arquivo_ra": open("/caminho/para/arquivo.pdf", "rb")
}

# Fazer requisição
response = requests.post(url, data=data, files=files)

# Verificar resposta
if response.status_code == 200:
    result = response.json()
    print(f"Sucesso: {result['success']}")
    print(f"Mensagem: {result['message']}")
else:
    print(f"Erro: {response.status_code}")
    print(response.text)
```

## 📊 Exemplo de Resposta

### Sucesso

```json
{
  "success": true,
  "message": "Processados: 25/25 alunos, 12 RA(s) cadastrada(s)"
}
```

### Erro

```json
{
  "success": false,
  "message": "Erro ao lançar conceitos inteligentes com RA: Nenhuma avaliação encontrada na turma."
}
```

## 🔍 Fluxo de Execução

1. **Login** no sistema SGN
2. **Coleta de avaliações** cadastradas (AV1, AV2, RP1, etc.)
3. **Navegação** para aba Conceitos
4. **Seleção** do trimestre de referência
5. **Para cada aluno**:
   - Coleta notas da tabela principal
   - Abre modal de conceitos
   - Aplica atitudes
   - Aplica conceitos baseados nas notas (mantendo C)
   - **Se tem habilidade com C**:
     - Para cada habilidade C:
       - Abre modal de RA
       - Seleciona a habilidade
       - Preenche datas (início e término)
       - Preenche descrição
       - Navega para aba Anexo
       - Adiciona anexo (nome + upload PDF)
       - Salva anexo
       - Salva RA
   - Fecha modal

## ⚠️ Requisitos

- **Arquivo PDF**: Obrigatório, máximo 10MB
- **Formato de datas**: DD/MM/YYYY
- **Descrição**: Mínimo 10 caracteres
- **Nome do arquivo**: Máximo 80 caracteres
- **Avaliações cadastradas**: Necessário ter avaliações na turma

## 🎯 Casos de Uso

### Caso 1: Aluno com 2 habilidades C

**Entrada**:
- Aluno: João Silva
- AV1: C (Habilidade H4)
- AV2: C (Habilidade H8)

**Resultado**:
- Conceito C mantido em ambas
- 2 RAs cadastradas (uma para H4, outra para H8)
- Mesmo arquivo PDF usado para ambas
- Mesmas datas e descrição

### Caso 2: Aluno com RP que melhora nota

**Entrada**:
- Aluno: Maria Santos
- AV1: C (Habilidade H4)
- RP1: B (Recuperação da AV1)

**Resultado**:
- Conceito B aplicado (RP sobrescreve AV)
- Nenhuma RA cadastrada (não tem C final)

### Caso 3: Turma mista

**Entrada**:
- 30 alunos na turma
- 10 alunos com pelo menos 1 habilidade C
- Total de 18 habilidades C entre todos

**Resultado**:
- 30 alunos processados
- 18 RAs cadastradas
- Mensagem: "Processados: 30/30 alunos, 18 RA(s) cadastrada(s)"

## 🐛 Troubleshooting

### Erro: "Nenhuma avaliação encontrada"
**Causa**: Não há avaliações cadastradas na turma
**Solução**: Cadastre avaliações antes de usar o endpoint

### Erro: "Tipo de arquivo inválido"
**Causa**: Arquivo não é PDF ou extensão incorreta
**Solução**: Use apenas arquivos .pdf

### Erro: "O arquivo possui tamanho maior que o permitido"
**Causa**: Arquivo PDF maior que 10MB
**Solução**: Reduza o tamanho do PDF

### Erro: "Falha no login"
**Causa**: Credenciais incorretas
**Solução**: Verifique username e password

## 📚 Referências

- Endpoint base: `/lancar-conceito-inteligente`
- Documentação Swagger: `http://localhost:8000/docs`
- Documentação ReDoc: `http://localhost:8000/redoc`
