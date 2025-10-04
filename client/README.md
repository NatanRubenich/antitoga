# 🤖 Bot de Automação SGN - Frontend

Interface web moderna e intuitiva para automação de lançamento de notas no sistema SGN.

## 🎨 Design

- **Fonte:** Space Grotesk
- **Framework CSS:** Tailwind CSS
- **Ícones:** Material Symbols
- **Estilo:** Glassmorphism com gradientes modernos

## 🚀 Como Usar

### 1. Iniciar a API

Primeiro, certifique-se de que a API está rodando:

```bash
# No diretório raiz do projeto
python main.py
```

A API estará disponível em: `http://localhost:8000`

### 2. Abrir o Frontend

Simplesmente abra o arquivo `index.html` no seu navegador:

```bash
# Windows
start index.html

# Ou clique duas vezes no arquivo index.html
```

**Alternativa:** Use um servidor local (recomendado):

```bash
# Python 3
python -m http.server 8080

# Acesse: http://localhost:8080
```

## 📋 Funcionalidades

### 1. **Lançar Conceito Inteligente**
- Analisa o desempenho individual de cada aluno
- Atribui conceitos baseados nas avaliações cadastradas
- Campos obrigatórios marcados com `*` vermelho

### 2. **Lançar um Conceito para Todos**
- Aplica o mesmo conceito para todos os alunos
- Útil para lançamentos rápidos e uniformes

### 3. **Lançar Conceito e RA**
- Lança conceitos inteligentes
- Cadastra Recomposição de Aprendizagem para conceito C
- Requer upload de arquivo PDF

### 4. **Lançar Pareceres**
- Coleta conceitos de cada aluno
- Calcula a moda (nota mais frequente)
- Lança pareceres pedagógicos automaticamente

## 🎯 Campos e Validações

### Campos Obrigatórios (marcados com `*` vermelho)
- Username
- Password
- Código da Turma
- Trimestre de Referência

### Dropdowns Disponíveis

**Trimestre de Referência:**
- TR1
- TR2
- TR3

**Atitude Observada:**
- Sempre
- Às vezes
- Raramente
- Nunca
- Não conseguiu observar
- Não se aplica

**Conceito Habilidade:**
- A
- B
- C
- NE

## 📊 Logs em Tempo Real

Cada painel possui uma área de logs que exibe:
- ✓ Mensagens de sucesso (verde)
- ✗ Mensagens de erro (vermelho)
- ⚠ Avisos (amarelo)
- • Informações gerais (cinza)

## 🎨 Características Visuais

- **Sidebar:** Menu lateral com navegação entre funcionalidades
- **Painéis:** Conteúdo principal com formulários organizados
- **Botão Executar:** Verde com efeito hover e loading spinner
- **Campos Obrigatórios:** Asterisco vermelho após o label
- **Área de Explicação:** Fundo azul claro com descrição da funcionalidade

## 🔧 Estrutura de Arquivos

```
client/
├── index.html          # Estrutura HTML principal
├── app.js             # Lógica JavaScript e comunicação com API
├── README.md          # Este arquivo
└── base_design.png    # Design de referência
```

## 🌐 Comunicação com a API

O frontend se comunica com a API através de requisições HTTP:

- **Base URL:** `http://localhost:8000`
- **Método:** POST
- **Content-Type:** `application/json` ou `multipart/form-data` (para upload de arquivos)

### Endpoints Utilizados

1. `/lancar-conceito-inteligente` - Conceitos inteligentes
2. `/lancar-conceito-trimestre` - Conceito para todos
3. `/lancar-conceito-inteligente-RA` - Conceitos com RA
4. `/lancar-pareceres-por-nota` - Pareceres pedagógicos

## ⚡ Recursos Técnicos

- **Validação de Formulários:** Verifica campos obrigatórios antes de enviar
- **Feedback Visual:** Loading spinner durante execução
- **Tratamento de Erros:** Mensagens claras de erro
- **Scroll Automático:** Logs rolam automaticamente para a última mensagem
- **Conversão de Datas:** Formato DD/MM/YYYY para a API
- **Upload de Arquivos:** Suporte para envio de PDFs

## 🎯 Exemplo de Uso

1. Selecione uma funcionalidade no menu lateral
2. Preencha os campos obrigatórios (marcados com `*`)
3. Configure os parâmetros opcionais
4. Clique em "Executar"
5. Acompanhe o progresso nos logs
6. Aguarde a mensagem de sucesso

## 🐛 Troubleshooting

### Erro de Conexão
```
Erro de conexão: Failed to fetch
Verifique se a API está rodando em http://localhost:8000
```

**Solução:** Certifique-se de que a API está rodando com `python main.py`

### CORS Error
Se aparecer erro de CORS no console do navegador, verifique se o middleware CORS está configurado na API (já está configurado neste projeto).

### Campos Obrigatórios
```
Por favor, preencha todos os campos obrigatórios!
```

**Solução:** Preencha todos os campos marcados com `*` vermelho.

## 📱 Responsividade

O frontend é responsivo e funciona bem em:
- Desktop (1920x1080+)
- Laptop (1366x768+)
- Tablet (768x1024+)

## 🎨 Customização

Para alterar cores ou estilos, edite as classes Tailwind CSS no arquivo `index.html` ou adicione CSS customizado na tag `<style>`.

## 📄 Licença

Este projeto faz parte do sistema de automação SGN.
