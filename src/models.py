"""
Modelos de dados para a API usando Pydantic

Este módulo define as estruturas de dados que serão usadas para:
- Validar dados de entrada da API
- Documentar automaticamente a API no Swagger
- Garantir tipagem correta dos dados
"""
from pydantic import BaseModel, Field

class LoginRequest(BaseModel):
    """
    Modelo para requisição de login e navegação
    
    Attributes:
        username (str): Nome de usuário para login no SGN
        password (str): Senha do usuário
        codigo_turma (str): Código identificador da turma (ex: "369528")
    
    Example:
        {
            "username": "natan.rubenich",
            "password": "Barning123", 
            "codigo_turma": "369528"
        }
    """
    username: str = Field(..., description="Nome de usuário do SGN", example="natan.rubenich")
    password: str = Field(..., description="Senha do usuário", example="Barning123")
    codigo_turma: str = Field(..., description="Código da turma", example="369528")

class AutomationResponse(BaseModel):
    """
    Modelo para resposta da automação
    
    Attributes:
        success (bool): Indica se a operação foi bem-sucedida
        message (str): Mensagem descritiva do resultado da operação
    
    Example:
        {
            "success": true,
            "message": "Login realizado e navegação concluída com sucesso!"
        }
    """
    success: bool = Field(..., description="Status da operação (true/false)")
    message: str = Field(..., description="Mensagem descritiva do resultado")

class LoginOnlyRequest(BaseModel):
    """
    Modelo para requisição de login apenas (sem navegação)
    
    Attributes:
        username (str): Nome de usuário para login no SGN
        password (str): Senha do usuário
    
    Example:
        {
            "username": "natan.rubenich",
            "password": "Barning123"
        }
    """
    username: str = Field(..., description="Nome de usuário do SGN", example="natan.rubenich")
    password: str = Field(..., description="Senha do usuário", example="Barning123")

class NavigateRequest(BaseModel):
    """
    Modelo para requisição de navegação (assume que já está logado)
    
    Attributes:
        codigo_turma (str): Código identificador da turma
    
    Example:
        {
            "codigo_turma": "369528"
        }
    """
    codigo_turma: str = Field(..., description="Código da turma", example="369528")

class LoginStatusResponse(BaseModel):
    """
    Modelo para resposta do status de login
    
    Attributes:
        is_logged_in (bool): Indica se está logado
        current_url (str): URL atual do navegador
        message (str): Mensagem adicional
    
    Example:
        {
            "is_logged_in": true,
            "current_url": "https://sgn.sesisenai.org.br/pages/home",
            "message": "Usuário está logado"
        }
    """
    is_logged_in: bool = Field(..., description="Status do login (true/false)")
    current_url: str = Field(..., description="URL atual do navegador")
    message: str = Field(..., description="Mensagem descritiva")
