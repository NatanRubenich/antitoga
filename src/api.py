"""
API de Automação de Lançamento de Notas - SGN

Este módulo fornece o endpoint principal para lançamento de conceitos trimestrais
de forma automatizada no sistema SGN.
"""
from fastapi import FastAPI, Body
from .models import LoginRequest, AutomationResponse
from .selenium_config import SeleniumManager
from .sgn_automation import SGNAutomation

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
                "health": "GET /health - Health check da API",
                "docs": "GET /docs - Documentação Swagger",
                "redoc": "GET /redoc - Documentação ReDoc"
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
