"""
Modelos de dados para a API usando Pydantic

Este módulo define as estruturas de dados que serão usadas para:
- Validar dados de entrada da API
- Documentar automaticamente a API no Swagger
- Garantir tipagem correta dos dados
"""
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum

class AtitudeObservada(str, Enum):
    """Opções disponíveis para observações de atitudes"""
    SELECIONE = "Selecione"
    SEMPRE = "Sempre"
    AS_VEZES = "Às vezes"
    RARAMENTE = "Raramente"
    NUNCA = "Nunca"
    NAO_CONSEGUIU_OBSERVAR = "Não conseguiu observar"
    NAO_SE_APLICA = "Não se aplica"

class ConceitoHabilidade(str, Enum):
    """Opções disponíveis para conceitos de habilidades"""
    SELECIONE = "Selecione"
    A = "A"
    B = "B"
    C = "C"
    NE = "NE"

class LoginRequest(BaseModel):
    """
    Modelo para requisição de login e lançamento de conceitos
    
    Attributes:
        username (str): Nome de usuário para login no SGN
        password (str): Senha do usuário
        codigo_turma (str): Código identificador da turma (ex: "369528")
        atitude_observada (AtitudeObservada, optional): Opção para observações de atitudes (padrão: "Raramente")
        conceito_habilidade (ConceitoHabilidade, optional): Opção para conceitos de habilidades (padrão: "B")
    
    Example:
        {
            "username": "natan.rubenich",
            "password": "Barning123", 
            "codigo_turma": "369528",
            "atitude_observada": "Sempre",
            "conceito_habilidade": "A"
        }
    """
    username: str = Field(..., description="Nome de usuário do SGN", example="natan.rubenich")
    password: str = Field(..., description="Senha do usuário", example="Barning123")
    codigo_turma: str = Field(..., description="Código da turma", example="369528")
    atitude_observada: Optional[AtitudeObservada] = Field(
        default=AtitudeObservada.RARAMENTE, 
        description="Opção para todas as observações de atitudes",
        example="Sempre"
    )
    conceito_habilidade: Optional[ConceitoHabilidade] = Field(
        default=ConceitoHabilidade.B,
        description="Opção para todos os conceitos de habilidades", 
        example="A"
    )

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
