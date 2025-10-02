# 📊 Endpoint: Lançamento de Pareceres por Nota

## Descrição

O endpoint `/lancar-pareceres-por-nota` coleta os conceitos de cada aluno e calcula a **moda** (nota mais frequente) para gerar pareceres pedagógicos por trimestre.

## URL

```
POST http://localhost:8000/lancar-pareceres-por-nota
```

## Parâmetros

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| `username` | string | Sim | Nome de usuário do SGN |
| `password` | string | Sim | Senha do usuário |
| `codigo_turma` | string | Sim | Código da turma (ex: "369528") |
| `trimestre_referencia` | string | Não | Trimestre (TR1, TR2 ou TR3). Padrão: "TR2" |

## Fluxo de Execução

1. **Login** - Faz login no sistema SGN
2. **Navegação** - Acessa o diário da turma especificada
3. **Aba Conceitos** - Abre a aba de Conceitos
4. **Seleção de Trimestre** - Seleciona o trimestre de referência
5. **Coleta de Conceitos** - Para cada aluno:
   - Abre o modal individual
   - Expande o accordion "Conceitos das Habilidades"
   - Coleta todos os conceitos lançados (A, B, C, NE)
   - Calcula a **moda** (conceito mais frequente)
   - Limpa o nome do aluno (remove sufixos como `[PCD]`, `[MENOR]`)
6. **Aba Pedagógico** - Navega para a aba Pedagógico
7. **Lançamento de Pareceres** - Para cada aluno:
   - Seleciona o aluno no dropdown
   - Lança o parecer baseado no conceito predominante

## Limpeza de Nomes

O sistema remove automaticamente sufixos dos nomes dos alunos:

| Nome Original | Nome Limpo |
|---------------|------------|
| `Matheus Gonçalves dos Santos - [PCD]` | `Matheus Gonçalves dos Santos` |
| `Mateus Müller Biscaro - [MENOR]` | `Mateus Müller Biscaro` |
| `Ayumi Iura - [PCD - MENOR]` | `Ayumi Iura` |

## Cálculo da Moda

A **moda** é o conceito que aparece com maior frequência. Exemplos:

| Conceitos do Aluno | Moda Calculada |
|--------------------|----------------|
| `['A', 'B', 'B', 'C', 'B']` | `B` (aparece 3x) |
| `['A', 'A', 'C']` | `A` (aparece 2x) |
| `['B', 'B', 'C', 'C']` | `B` ou `C` (empate, retorna o primeiro) |

## Exemplo de Uso (cURL)

```bash
curl -X POST "http://localhost:8000/lancar-pareceres-por-nota" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "natan.rubenich",
    "password": "sua_senha",
    "codigo_turma": "369528",
    "trimestre_referencia": "TR2"
  }'
```

## Exemplo de Uso (Python)

```python
import requests

url = "http://localhost:8000/lancar-pareceres-por-nota"

payload = {
    "username": "natan.rubenich",
    "password": "sua_senha",
    "codigo_turma": "369528",
    "trimestre_referencia": "TR2"
}

response = requests.post(url, json=payload)
print(response.json())
```

## Resposta de Sucesso

```json
{
  "success": true,
  "message": "Pareceres lançados com sucesso! Processados: 38/38 alunos"
}
```

## Resposta de Erro

```json
{
  "success": false,
  "message": "Erro ao coletar conceitos dos alunos: Timeout ao aguardar modal"
}
```

## Diferenças dos Outros Endpoints

| Endpoint | Função |
|----------|--------|
| `/lancar-conceito-trimestre` | Lança **conceitos** (A, B, C, NE) de forma simples |
| `/lancar-conceito-inteligente` | Lança **conceitos** baseados em avaliações |
| `/lancar-conceito-inteligente-RA` | Lança **conceitos** + cadastra RA para conceito C |
| `/lancar-pareceres-por-nota` | **Coleta** conceitos existentes e lança **pareceres** pedagógicos |

## Casos de Uso

1. **Geração Automática de Pareceres** - Após lançar todos os conceitos, use este endpoint para gerar pareceres baseados no desempenho geral de cada aluno
2. **Análise de Desempenho** - Identifica o conceito predominante de cada aluno para orientar intervenções pedagógicas
3. **Relatórios Pedagógicos** - Facilita a criação de relatórios baseados na moda dos conceitos

## Requisitos

- Conceitos já devem estar lançados na aba de Conceitos
- Alunos devem ter pelo menos um conceito lançado
- O sistema precisa estar acessível e o usuário ter permissões adequadas

## Troubleshooting

### Erro: "Nenhum conceito foi coletado"
**Causa**: Não há conceitos lançados para os alunos no trimestre selecionado.
**Solução**: Lance os conceitos primeiro usando um dos endpoints de lançamento de conceitos.

### Erro: "Aluno não encontrado no dropdown"
**Causa**: O nome do aluno na aba Conceitos não corresponde ao nome na aba Pedagógico.
**Solução**: Verifique se há inconsistências nos nomes dos alunos no sistema.

### Erro: "Timeout ao aguardar modal"
**Causa**: O modal de conceitos demorou muito para abrir.
**Solução**: Verifique a conexão com o sistema SGN e tente novamente.

## Logs de Execução

O endpoint gera logs detalhados durante a execução:

```
================================================================================
 📝 LANÇAMENTO DE PARECERES POR NOTA
================================================================================

1. Realizando login...
   ✓ Login realizado com sucesso!

2. Navegando para o diário da turma 369528...
   ✓ Diário acessado

3. Navegando para aba Conceitos...
   ✓ Aba Conceitos acessada

4. Selecionando trimestre de referência: TR2...
   ✓ Trimestre selecionado

5. Coletando conceitos de todos os alunos...

📊 Coletando conceitos de todos os alunos...
   ✓ Encontrados 38 alunos

   [1/38] Processando: Matheus Gonçalves dos Santos
      ✓ Conceitos coletados: ['B', 'B', 'A', 'B', 'C']
      ✅ Conceito predominante (moda): B

   [2/38] Processando: Mateus Müller Biscaro
      ✓ Conceitos coletados: ['A', 'A', 'A', 'B']
      ✅ Conceito predominante (moda): A

...

✅ Coleta concluída! Total de alunos processados: 38/38

6. Navegando para aba Pedagógico...
   ✓ Aba Pedagógico acessada

7. Lançando pareceres...

   Lançando parecer para: Matheus Gonçalves dos Santos (Conceito: B)
      ✓ Aluno selecionado no dropdown

   Lançando parecer para: Mateus Müller Biscaro (Conceito: A)
      ✓ Aluno selecionado no dropdown

...

================================================================================
✅ Pareceres lançados com sucesso! Processados: 38/38 alunos
================================================================================
```

## Observações Importantes

1. **Tempo de Execução**: O processo pode levar vários minutos dependendo do número de alunos
2. **Navegador Visível**: O navegador Chrome será aberto e você poderá acompanhar a execução
3. **Não Interromper**: Não feche o navegador ou interrompa o processo durante a execução
4. **Conceitos Vazios**: Alunos sem conceitos lançados serão pulados automaticamente
5. **Ordem de Execução**: Os alunos são processados na ordem em que aparecem na tabela

## Próximos Passos

Após a coleta dos conceitos e cálculo da moda, você pode:

1. Implementar lógica adicional para preencher campos de parecer específicos
2. Gerar relatórios em PDF com os conceitos predominantes
3. Enviar notificações para coordenadores sobre alunos com conceito C ou NE predominante
4. Integrar com outros sistemas de gestão escolar
