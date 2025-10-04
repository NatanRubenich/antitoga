"""
API de Automação de Lançamento de Notas - SGN

Este módulo fornece o endpoint principal para lançamento de conceitos trimestrais
de forma automatizada no sistema SGN.
"""
from fastapi import FastAPI, Body, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from .models import LoginRequest, LoginRequestRA, ParecerRequest, AutomationResponse, AtitudeObservada, ConceitoHabilidade, TrimestreReferencia
from .selenium_config import SeleniumManager
from .sgn_automation import SGNAutomation
import tempfile
import os

# Instâncias globais compartilhadas
selenium_manager = SeleniumManager()
sgn_automation = SGNAutomation(selenium_manager)

def create_app():
    """
    Cria e configura a aplicação FastAPI com o endpoint principal
    
    Returns:
        FastAPI: Instância configurada da aplicação
    """
    app = FastAPI(
        title="SGN Automação de Notas",
        description="API para automação de lançamento de notas no sistema SGN",
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    # Configurar CORS para permitir requisições do frontend
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Em produção, especifique os domínios permitidos
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    @app.post("/lancar-conceito-trimestre", response_model=AutomationResponse)
    async def lancar_conceito_trimestre(
        request: LoginRequest = Body(
            ...,
            examples={
                "padrao": {
                    "summary": "Padrão (Raramente/B)",
                    "description": "Usa os padrões: Raramente para atitudes e B para conceitos",
                    "value": {
                        "username": "seu.usuario",
                        "password": "sua.senha",
                        "codigo_turma": "369528",
                        "trimestre_referencia": "TR2"
                    },
                },
                "excelente": {
                    "summary": "Excelente desempenho (Sempre/A)",
                    "value": {
                        "username": "seu.usuario",
                        "password": "sua.senha",
                        "codigo_turma": "369528",
                        "atitude_observada": "Sempre",
                        "conceito_habilidade": "A",
                        "trimestre_referencia": "TR1"
                    },
                },
                "basico": {
                    "summary": "Desempenho básico (Às vezes/C)",
                    "value": {
                        "username": "seu.usuario",
                        "password": "sua.senha",
                        "codigo_turma": "369528",
                        "atitude_observada": "Às vezes",
                        "conceito_habilidade": "C",
                        "trimestre_referencia": "TR3"
                    },
                },
            },
        )
    ):
        """
        Executa login e lança conceitos para todos os alunos da turma
        
        Este endpoint realiza o fluxo completo de lançamento de conceitos:
        1. Faz login no sistema SGN usando as credenciais fornecidas
        2. Navega diretamente para o diário da turma especificada
        3. Abre a aba de Conceitos
        4. Para cada aluno na turma:
           - Acessa a modal de conceitos do aluno
           - Aplica a opção escolhida em todas as Observações de Atitudes
           - Aplica a opção escolhida em todos os Conceitos de Habilidades
        
        Exemplos de uso:
        - Padrão (Raramente/B): {"username": "usuario", "password": "senha", "codigo_turma": "12345"}
        - Excelente (Sempre/A): {"username": "usuario", "password": "senha", "codigo_turma": "12345", "atitude_observada": "Sempre", "conceito_habilidade": "A"}
        - Básico (Às vezes/C): {"username": "usuario", "password": "senha", "codigo_turma": "12345", "atitude_observada": "Às vezes", "conceito_habilidade": "C"}
        
        Args:
            request (LoginRequest): Dados de login, código da turma e opções de conceitos
            
        Returns:
            AutomationResponse: Resultado da automação com estatísticas
            
        Example:
            POST /lancar-conceito-trimestre
            {
                "username": "natan.rubenich",
                "password": "Barning123",
                "codigo_turma": "369528",
                "atitude_observada": "Sempre",
                "conceito_habilidade": "A",
                "trimestre_referencia": "TR1"
            }
            
        Response:
                "success": true,
                "message": "Lançamento de conceitos concluído com sucesso! Processados: 25/25 alunos"
            }
        """
        try:
            # Log da requisição recebida (sem a senha por segurança)
            request_dict = request.dict()
            if 'password' in request_dict:
                request_dict['password'] = '***'  # Ofuscar senha nos logs
            
            print("\n" + "="*80)
            print(" NOVA REQUISIÇÃO RECEBIDA")
            print("-"*80)
            print(f"Dados da requisição: {request_dict}")
            
            # Extrair valores dos Enums (usar None para que o método lance exceção se os valores forem inválidos)
            atitude_val = request.atitude_observada.value if hasattr(request, 'atitude_observada') and request.atitude_observada else None
            conceito_val = request.conceito_habilidade.value if hasattr(request, 'conceito_habilidade') and request.conceito_habilidade else None
            
            print(f"🔧 Parâmetros recebidos:")
            print(f"   - Usuário: {request.username}")
            print(f"   - Código da turma: {request.codigo_turma}")
            print(f"   - Atitude observada: {atitude_val or 'Padrão (Raramente)'}")
            print(f"   - Conceito habilidade: {conceito_val or 'Padrão (B)'}")
            print(f"   - Trimestre referência: {request.trimestre_referencia}")
            print("-"*80 + "\n")

            # Executar lançamento de conceitos com opções configuráveis
            success, message = sgn_automation.lancar_conceito_trimestre(
                username=request.username,
                password=request.password,
                codigo_turma=request.codigo_turma,
                atitude_observada=atitude_val,
                conceito_habilidade=conceito_val,
                trimestre_referencia=request.trimestre_referencia
            )
            
            return AutomationResponse(
                success=success,
                message=message
            )
            
        except Exception as e:
            # Captura qualquer erro não tratado pela automação
            error_msg = f"Erro na API: {str(e)}"
            print(f"❌ {error_msg}")
            
            return AutomationResponse(
                success=False,
                message=error_msg
            )
    
    @app.post("/lancar-conceito-inteligente", response_model=AutomationResponse)
    async def lancar_conceito_inteligente(
        request: LoginRequest = Body(
            ...,
            examples={
                "padrao": {
                    "summary": "Padrão (Raramente/B)",
                    "description": "Aplica conceitos baseados nas avaliações cadastradas",
                    "value": {
                        "username": "seu.usuario",
                        "password": "sua.senha",
                        "codigo_turma": "369528",
                        "trimestre_referencia": "TR2"
                    },
                },
                "excelente": {
                    "summary": "Com fallback para A",
                    "description": "Se não houver mapeamento, usa A como padrão",
                    "value": {
                        "username": "seu.usuario",
                        "password": "sua.senha",
                        "codigo_turma": "369528",
                        "atitude_observada": "Sempre",
                        "conceito_habilidade": "A",
                        "trimestre_referencia": "TR1"
                    },
                },
            },
        )
    ):
        """
        🆕 NOVO: Lança conceitos INTELIGENTES baseados nas avaliações cadastradas
        
        Este endpoint realiza o fluxo INTELIGENTE de lançamento de conceitos:
        1. Faz login no sistema SGN
        2. Navega para aba "Aulas/Avaliações" e coleta todas as avaliações cadastradas
        3. Coleta recuperações paralelas e mapeia para suas avaliações de origem
        4. Abre cada modal de avaliação e extrai as habilidades vinculadas
        5. Para cada aluno:
           - Lê as notas da tabela principal (AV1=B, RP1=A, etc.)
           - Abre modal de conceitos
           - Aplica atitudes com o padrão escolhido
           - Para cada habilidade, aplica o conceito da avaliação correspondente
           - Se existe recuperação (RP), usa RP em vez de AV
           - Se não há mapeamento, usa o conceito padrão
        
        Diferença do endpoint anterior:
        - Endpoint anterior: Aplica o MESMO conceito para TODAS as habilidades
        - Este endpoint: Aplica conceitos DIFERENTES baseados nas avaliações de cada habilidade
        
        Exemplo:
        - Aluno tem AV1=B e RP1=A
        - Habilidade H1 está vinculada à AV1
        - Sistema aplica conceito "A" (da RP1) para H1
        
        Args:
            request (LoginRequest): Dados de login, código da turma e opções de conceitos
            
        Returns:
            AutomationResponse: Resultado da automação com estatísticas
        """
        try:
            request_dict = request.dict()
            if 'password' in request_dict:
                request_dict['password'] = '***'
            
            print("\n" + "="*80)
            print(" 🆕 NOVA REQUISIÇÃO - MODO INTELIGENTE")
            print("-"*80)
            print(f"Dados da requisição: {request_dict}")
            
            atitude_val = request.atitude_observada.value if hasattr(request, 'atitude_observada') and request.atitude_observada else None
            conceito_val = request.conceito_habilidade.value if hasattr(request, 'conceito_habilidade') and request.conceito_habilidade else None
            
            print(f"🔧 Parâmetros recebidos:")
            print(f"   - Usuário: {request.username}")
            print(f"   - Código da turma: {request.codigo_turma}")
            print(f"   - Atitude observada: {atitude_val or 'Padrão (Raramente)'}")
            print(f"   - Conceito habilidade (fallback): {conceito_val or 'Padrão (B)'}")
            print(f"   - Trimestre referência: {request.trimestre_referencia}")
            print(f"   - Modo: INTELIGENTE (baseado em avaliações)")
            print("-"*80 + "\n")

            # Executar lançamento INTELIGENTE de conceitos
            success, message = sgn_automation.lancar_conceito_inteligente(
                username=request.username,
                password=request.password,
                codigo_turma=request.codigo_turma,
                atitude_observada=atitude_val,
                conceito_habilidade=conceito_val,
                trimestre_referencia=request.trimestre_referencia
            )
            
            return AutomationResponse(
                success=success,
                message=message
            )
            
        except Exception as e:
            error_msg = f"Erro na API: {str(e)}"
            print(f"❌ {error_msg}")
            
            return AutomationResponse(
                success=False,
                message=error_msg
            )
    
    
    @app.post("/lancar-conceito-inteligente-RA", response_model=AutomationResponse)
    async def lancar_conceito_inteligente_ra(
        username: str = Form(..., description="Nome de usuário do SGN"),
        password: str = Form(..., description="Senha do usuário"),
        codigo_turma: str = Form(..., description="Código da turma"),
        inicio_ra: str = Form(..., description="Data início RA (DD/MM/YYYY)", example="01/10/2025"),
        termino_ra: str = Form(..., description="Data término RA (DD/MM/YYYY)", example="31/10/2025"),
        descricao_ra: str = Form(..., description="Descrição da RA"),
        nome_arquivo_ra: str = Form(..., description="Nome do arquivo PDF"),
        arquivo_ra: UploadFile = File(..., description="Arquivo PDF da RA"),
        atitude_observada: str = Form(default="Raramente", description="Atitude observada"),
        conceito_habilidade: str = Form(default="B", description="Conceito padrão (fallback)"),
        trimestre_referencia: str = Form(default="TR2", description="Trimestre de referência"),
    ):
        """
        🆕 NOVO: Lança conceitos INTELIGENTES com cadastro de Recomposição de Aprendizagem (RA)
        
        Este endpoint realiza o fluxo INTELIGENTE com RA:
        1. Faz login no sistema SGN
        2. Navega para aba "Aulas/Avaliações" e coleta todas as avaliações cadastradas
        3. Coleta recuperações paralelas e mapeia para suas avaliações de origem
        4. Abre cada modal de avaliação e extrai as habilidades vinculadas
        5. Para cada aluno:
           - Lê as notas da tabela principal (AV1=B, RP1=A, etc.)
           - Abre modal de conceitos
           - Aplica atitudes com o padrão escolhido
           - Para cada habilidade, aplica o conceito da avaliação correspondente
           - **DIFERENÇA**: Se conceito = C, MANTÉM o C (não troca por NE)
           - Se existe recuperação (RP), usa RP em vez de AV
           - **NOVO**: Se aluno tem algum C, cadastra RA para CADA habilidade com C
        
        Diferenças do /lancar-conceito-inteligente:
        - Endpoint anterior: Conceito C vira NE automaticamente
        - Este endpoint: Conceito C é mantido e RA é cadastrada
        
        Fluxo de cadastro de RA:
        1. Detecta habilidades com conceito C
        2. Para cada habilidade C:
           - Clica em "Adicionar" na seção de RA
           - Seleciona a habilidade
           - Preenche data início e término
           - Preenche descrição
           - Clica na aba "Anexo"
           - Faz upload do PDF
           - Salva o anexo
           - Salva a RA
        
        Args:
            username: Nome de usuário do SGN
            password: Senha do usuário
            codigo_turma: Código da turma
            inicio_ra: Data de início da RA (DD/MM/YYYY)
            termino_ra: Data de término da RA (DD/MM/YYYY)
            descricao_ra: Descrição da RA (O quê/Por quê/Como)
            nome_arquivo_ra: Nome do arquivo PDF
            arquivo_ra: Arquivo PDF da RA (upload)
            atitude_observada: Atitude padrão (default: "Raramente")
            conceito_habilidade: Conceito padrão fallback (default: "B")
            trimestre_referencia: Trimestre (default: "TR2")
            
        Returns:
            AutomationResponse: Resultado da automação com estatísticas
        """
        try:
            print("\n" + "="*80)
            print(" 🆕 NOVA REQUISIÇÃO - MODO INTELIGENTE COM RA")
            print("-"*80)
            print(f"🔧 Parâmetros recebidos:")
            print(f"   - Usuário: {username}")
            print(f"   - Código da turma: {codigo_turma}")
            print(f"   - Atitude observada: {atitude_observada}")
            print(f"   - Conceito habilidade (fallback): {conceito_habilidade}")
            print(f"   - Trimestre referência: {trimestre_referencia}")
            print(f"   - Início RA: {inicio_ra}")
            print(f"   - Término RA: {termino_ra}")
            print(f"   - Nome arquivo RA: {nome_arquivo_ra}")
            print(f"   - Arquivo RA: {arquivo_ra.filename} ({arquivo_ra.content_type})")
            print(f"   - Modo: INTELIGENTE COM RA (C mantido + cadastro de RA)")
            print("-"*80 + "\n")
            
            # Salvar arquivo temporariamente
            temp_dir = tempfile.gettempdir()
            temp_file_path = os.path.join(temp_dir, arquivo_ra.filename)
            
            with open(temp_file_path, "wb") as buffer:
                content = await arquivo_ra.read()
                buffer.write(content)
            
            print(f"📁 Arquivo salvo temporariamente em: {temp_file_path}")
            
            # Executar lançamento INTELIGENTE com RA
            success, message = sgn_automation.lancar_conceito_inteligente_com_ra(
                username=username,
                password=password,
                codigo_turma=codigo_turma,
                atitude_observada=atitude_observada,
                conceito_habilidade=conceito_habilidade,
                trimestre_referencia=trimestre_referencia,
                inicio_ra=inicio_ra,
                termino_ra=termino_ra,
                descricao_ra=descricao_ra,
                nome_arquivo_ra=nome_arquivo_ra,
                caminho_arquivo_ra=temp_file_path
            )
            
            # Limpar arquivo temporário
            try:
                os.remove(temp_file_path)
                print(f"🗑️ Arquivo temporário removido: {temp_file_path}")
            except Exception as e:
                print(f"⚠️ Não foi possível remover arquivo temporário: {e}")
            
            return AutomationResponse(
                success=success,
                message=message
            )
            
        except Exception as e:
            error_msg = f"Erro na API: {str(e)}"
            print(f"❌ {error_msg}")
            
            # Tentar limpar arquivo temporário em caso de erro
            try:
                if 'temp_file_path' in locals():
                    os.remove(temp_file_path)
            except:
                pass
            
            return AutomationResponse(
                success=False,
                message=error_msg
            )
    
    @app.post("/lancar-pareceres-por-nota", response_model=AutomationResponse)
    async def lancar_pareceres_por_nota(request: ParecerRequest = Body(...)):
        """
        🆕 NOVO: Lança pareceres pedagógicos baseados na moda dos conceitos
        
        Este endpoint coleta os conceitos de cada aluno e calcula a moda (nota mais frequente)
        para gerar pareceres por trimestre.
        
        Fluxo:
        1. Faz login no sistema SGN
        2. Navega para o diário da turma
        3. Abre aba de Conceitos
        4. Seleciona o trimestre de referência
        5. Para cada aluno:
           - Abre modal individual
           - Coleta todos os conceitos das habilidades
           - Calcula a moda (conceito mais frequente)
           - Limpa o nome do aluno (remove sufixos como [PCD], [MENOR])
        6. Navega para aba Pedagógico
        7. Para cada aluno:
           - Seleciona o aluno no dropdown
           - Lança o parecer baseado no conceito predominante
        
        Args:
            request (ParecerRequest): Dados de login, código da turma e trimestre
            
        Returns:
            AutomationResponse: Resultado da automação com estatísticas
        """
        try:
            request_dict = request.dict()
            if 'password' in request_dict:
                request_dict['password'] = '***'
            
            print("\n" + "="*80)
            print(" 📝 NOVA REQUISIÇÃO - LANÇAMENTO DE PARECERES POR NOTA")
            print("-"*80)
            print(f"Dados da requisição: {request_dict}")
            
            print(f"🔧 Parâmetros recebidos:")
            print(f"   - Usuário: {request.username}")
            print(f"   - Código da turma: {request.codigo_turma}")
            print(f"   - Trimestre referência: {request.trimestre_referencia}")
            print("-"*80 + "\n")

            # Executar lançamento de pareceres
            success, message = sgn_automation.lancar_pareceres_por_nota(
                username=request.username,
                password=request.password,
                codigo_turma=request.codigo_turma,
                trimestre_referencia=request.trimestre_referencia
            )
            
            return AutomationResponse(
                success=success,
                message=message
            )
            
        except Exception as e:
            error_msg = f"Erro na API: {str(e)}"
            print(f"❌ {error_msg}")
            
            return AutomationResponse(
                success=False,
                message=error_msg
            )
    
    @app.get("/")
    async def root():
        """
        Endpoint raiz com informações da API
        
        Fornece informações básicas sobre a API e lista os endpoints
        disponíveis. Útil para descoberta da API e verificação rápida.
        
        Returns:
            dict: Informações da API e endpoints disponíveis
            
        Example:
            GET /
            
        Response:
            {
                "message": "SGN Automação de Notas API",
                "version": "1.0.0",
                "endpoints": {...}
            }
        """
        return {
            "message": "SGN Automação de Notas API",
            "version": "4.0.0",
            "endpoints": {
                "lancar_conceito_trimestre": "POST /lancar-conceito-trimestre - 📝 SIMPLES: Aplica o MESMO conceito para TODAS as habilidades",
                "lancar_conceito_inteligente": "POST /lancar-conceito-inteligente - 🧠 INTELIGENTE: Aplica conceitos baseados nas avaliações de cada habilidade",
                "lancar_conceito_inteligente_RA": "POST /lancar-conceito-inteligente-RA - 🎓 INTELIGENTE COM RA: Igual ao inteligente mas mantém C e cadastra RA",
                "lancar_pareceres_por_nota": "POST /lancar-pareceres-por-nota - 📊 PARECERES: Coleta conceitos e lança pareceres baseados na moda",
                "health": "GET /health - Health check da API",
                "docs": "GET /docs - Documentação Swagger",
                "redoc": "GET /redoc - Documentação ReDoc"
            },
            "modos": {
                "simples": "Aplica o mesmo conceito (ex: B) para todas as habilidades de todos os alunos",
                "inteligente": "Lê as avaliações cadastradas e aplica o conceito específico de cada avaliação para sua habilidade correspondente",
                "inteligente_com_ra": "Igual ao inteligente, mas mantém conceito C (não troca por NE) e cadastra Recomposição de Aprendizagem para cada habilidade C",
                "pareceres_por_nota": "Coleta conceitos de cada aluno, calcula a moda (nota mais frequente) e lança pareceres pedagógicos"
            }
        }
    
    @app.get("/health")
    async def health():
        """
        Health check da API
        
        Endpoint simples para verificar se a API está funcionando.
        Usado por sistemas de monitoramento e load balancers.
        
        Returns:
            dict: Status da API
            
        Example:
            GET /health
            
        Response:
            {
                "status": "healthy",
                "service": "SGN Automation API"
            }
        """
        return {
            "status": "healthy",
            "service": "SGN Automation API"
        }
    
    return app
