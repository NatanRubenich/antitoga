"""
Rotas e endpoints da API FastAPI

Este módulo define todos os endpoints da API REST e integra:
- Modelos de dados (validação de entrada/saída)
- Automação do SGN (execução das tarefas)
- Gerenciamento do Selenium (controle do navegador)

A API fornece endpoints para:
- Executar automação completa (login + navegação)
- Fechar o navegador
- Health check e informações da API
"""
from fastapi import FastAPI, HTTPException, Body
from .models import (
    LoginRequest, 
    AutomationResponse, 
    LoginOnlyRequest, 
    NavigateRequest, 
    LoginStatusResponse, 
    AtitudeObservada, 
    ConceitoHabilidade
)
from .selenium_config import SeleniumManager
from .sgn_automation import SGNAutomation

# Instâncias globais compartilhadas
# Estas instâncias são criadas uma vez e reutilizadas em todas as requisições
selenium_manager = SeleniumManager()
sgn_automation = SGNAutomation(selenium_manager)

def create_app():
    """
    Cria e configura a aplicação FastAPI
    
    Esta função factory cria a aplicação FastAPI com todas as configurações
    necessárias e define todos os endpoints da API.
    
    Returns:
        FastAPI: Instância configurada da aplicação
    """
    app = FastAPI(
        title="SGN Automação de Notas",
        description="API para automação de lançamento de notas no sistema SGN",
        docs_url="/docs",  # Swagger UI
        redoc_url="/redoc"  # ReDoc
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
                        "codigo_turma": "369528"
                    },
                },
                "excelente": {
                    "summary": "Excelente desempenho (Sempre/A)",
                    "value": {
                        "username": "seu.usuario",
                        "password": "sua.senha",
                        "codigo_turma": "369528",
                        "atitude_observada": "Sempre",
                        "conceito_habilidade": "A"
                    },
                },
                "basico": {
                    "summary": "Desempenho básico (Às vezes/C)",
                    "value": {
                        "username": "seu.usuario",
                        "password": "sua.senha",
                        "codigo_turma": "369528",
                        "atitude_observada": "Às vezes",
                        "conceito_habilidade": "C"
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
                "conceito_habilidade": "A"
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
            print("-"*80 + "\n")

            # Executar lançamento de conceitos com opções configuráveis
            success, message = sgn_automation.lancar_conceito_trimestre(
                username=request.username,
                password=request.password,
                codigo_turma=request.codigo_turma,
                atitude_observada=atitude_val,
                conceito_habilidade=conceito_val
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
    
    @app.post("/login", response_model=AutomationResponse)
    async def login_only(request: LoginOnlyRequest):
        """
        Realiza apenas o login no SGN (sem navegação)
        
        Este endpoint executa somente o processo de login, deixando o usuário
        logado no sistema para usar outros endpoints posteriormente.
        
        Args:
            request (LoginOnlyRequest): Credenciais de login
            
        Returns:
            AutomationResponse: Resultado do login
            
        Example:
            POST /login
            {
                "username": "natan.rubenich",
                "password": "Barning123"
            }
            
        Response:
            {
                "success": true,
                "message": "Login realizado com sucesso!"
            }
        """
        try:
            success, message = sgn_automation.perform_login(
                username=request.username,
                password=request.password
            )
            
            return AutomationResponse(
                success=success,
                message=message
            )
            
        except Exception as e:
            error_msg = f"Erro no login: {str(e)}"
            print(f"❌ {error_msg}")
            
            return AutomationResponse(
                success=False,
                message=error_msg
            )
    
    @app.post("/navigate-to-conceitos", response_model=AutomationResponse)
    async def navigate_to_conceitos(request: NavigateRequest):
        """
        Navega para a aba de Conceitos (assume que já está logado)
        
        Este endpoint navega diretamente para a aba de Conceitos de uma turma,
        assumindo que o usuário já fez login anteriormente.
        
        Args:
            request (NavigateRequest): Código da turma
            
        Returns:
            AutomationResponse: Resultado da navegação
            
        Example:
            POST /navigate-to-conceitos
            {
                "codigo_turma": "369528"
            }
            
        Response:
            {
                "success": true,
                "message": "Navegação para Conceitos da turma 369528 concluída!"
            }
        """
        try:
            success, message = sgn_automation.navigate_to_conceitos(
                codigo_turma=request.codigo_turma
            )
            
            return AutomationResponse(
                success=success,
                message=message
            )
            
        except Exception as e:
            error_msg = f"Erro na navegação: {str(e)}"
            print(f"❌ {error_msg}")
            
            return AutomationResponse(
                success=False,
                message=error_msg
            )
    
    @app.get("/login-status", response_model=LoginStatusResponse)
    async def get_login_status():
        """
        Verifica o status atual do login
        
        Este endpoint verifica se o usuário está logado no sistema
        e retorna informações sobre o estado atual da sessão.
        
        Returns:
            LoginStatusResponse: Status do login e URL atual
            
        Example:
            GET /login-status
            
        Response:
            {
                "is_logged_in": true,
                "current_url": "https://sgn.sesisenai.org.br/pages/home",
                "message": "Usuário está logado"
            }
        """
        try:
            is_logged_in, current_url = sgn_automation.check_login_status()
            
            if isinstance(current_url, str) and current_url.startswith("http"):
                message = "Usuário está logado" if is_logged_in else "Usuário não está logado"
            else:
                message = current_url  # É uma mensagem de erro
                current_url = "N/A"
                is_logged_in = False
            
            return LoginStatusResponse(
                is_logged_in=is_logged_in,
                current_url=current_url,
                message=message
            )
            
        except Exception as e:
            error_msg = f"Erro ao verificar status: {str(e)}"
            print(f"❌ {error_msg}")
            
            return LoginStatusResponse(
                is_logged_in=False,
                current_url="N/A",
                message=error_msg
            )
    
    @app.post("/test-conceitos-tab", response_model=AutomationResponse)
    async def test_conceitos_tab(request: NavigateRequest):
        """
        Testa apenas o acesso à aba de Conceitos (para debug)
        
        Este endpoint é específico para testar e debugar o acesso à aba de Conceitos.
        Assume que o usuário já está logado e navega diretamente para o diário da turma.
        
        Args:
            request (NavigateRequest): Código da turma
            
        Returns:
            AutomationResponse: Resultado do teste
            
        Example:
            POST /test-conceitos-tab
            {
                "codigo_turma": "369528"
            }
            
        Response:
            {
                "success": true,
                "message": "Aba de Conceitos da turma 369528 acessada com sucesso!"
            }
        """
        try:
            success, message = sgn_automation.test_conceitos_tab_only(
                codigo_turma=request.codigo_turma
            )
            
            return AutomationResponse(
                success=success,
                message=message
            )
            
        except Exception as e:
            error_msg = f"Erro no teste da aba de Conceitos: {str(e)}"
            print(f"❌ {error_msg}")
            
            return AutomationResponse(
                success=False,
                message=error_msg
            )
    
    @app.post("/close-browser")
    async def close_browser():
        """
        Fecha o navegador de forma segura
        
        Este endpoint permite fechar o navegador manualmente, liberando
        recursos do sistema. Útil para limpeza após testes ou em caso
        de erro que deixe o navegador aberto.
        
        Returns:
            dict: Mensagem de confirmação ou erro
            
        Example:
            POST /close-browser
            
        Response:
            {
                "message": "Navegador fechado com sucesso"
            }
        """
        try:
            sgn_automation.close_browser()
            return {"message": "Navegador fechado com sucesso"}
        except Exception as e:
            return {"message": f"Erro ao fechar navegador: {str(e)}"}
    
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
            "version": "1.0.0",
            "endpoints": {
                "lancar_conceito_trimestre": "POST /lancar-conceito-trimestre - 🎯 PRINCIPAL: Lançar conceitos para todos os alunos",
                "login_and_navigate": "POST /login-and-navigate - Login + navegação (legado)",
                "login": "POST /login - Apenas login (reutilizável)",
                "navigate_to_conceitos": "POST /navigate-to-conceitos - Navegar para Conceitos",
                "test_conceitos_tab": "POST /test-conceitos-tab - Testar aba de Conceitos (debug)",
                "login_status": "GET /login-status - Verificar status do login",
                "close_browser": "POST /close-browser - Fechar navegador",
                "docs": "GET /docs - Documentação Swagger",
                "redoc": "GET /redoc - Documentação ReDoc",
                "health": "GET /health - Health check"
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
