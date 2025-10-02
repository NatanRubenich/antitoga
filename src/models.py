"""
Modelos de dados para a API de automação SGN

Este módulo define as estruturas de dados usadas para validação
e documentação da API de lançamento de conceitos.
"""
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum
from fastapi import UploadFile

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


class TrimestreReferencia(str, Enum):
    """Opções de trimestre para lançamento de conceitos"""
    TR1 = "TR1"
    TR2 = "TR2"
    TR3 = "TR3"

class LoginRequest(BaseModel):
    """
    Modelo para requisição de lançamento de conceitos
    
    Attributes:
        username (str): Nome de usuário para login no SGN (3-100 caracteres)
        password (str): Senha do usuário (3-100 caracteres)
        codigo_turma (str): Código identificador da turma (ex: "369528")
        atitude_observada (AtitudeObservada): Opção para observações de atitudes (padrão: "Raramente")
        conceito_habilidade (ConceitoHabilidade): Opção para conceitos de habilidades (padrão: "B")
        trimestre_referencia (TrimestreReferencia): Trimestre em que os conceitos serão lançados
    """
    username: str = Field(
        ..., 
        min_length=3, 
        max_length=100,
        description="Nome de usuário do SGN (3-100 caracteres)",
        example="natan.rubenich"
    )
    password: str = Field(
        ..., 
        min_length=3,
        max_length=100,
        description="Senha do usuário (3-100 caracteres)",
        example="sua_senha_secreta"
    )
    codigo_turma: str = Field(
        ..., 
        min_length=1,
        max_length=20,
        pattern=r'^\d+$',
        description="Código numérico da turma (apenas dígitos)",
        example="369528"
    )
    atitude_observada: AtitudeObservada = Field(
        default=AtitudeObservada.RARAMENTE,
        description="Opção que será aplicada a TODAS as observações de atitudes",
        example="Raramente"
    )
    conceito_habilidade: ConceitoHabilidade = Field(
        default=ConceitoHabilidade.B,
        description="Opção que será aplicada a TODOS os conceitos de habilidades",
        example="B"
    )
    trimestre_referencia: TrimestreReferencia = Field(
        default=TrimestreReferencia.TR2,
        description="Trimestre de referência utilizado para lançamento dos conceitos",
        example="TR2",
        json_schema_extra={"widget": "select"}
    )

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "username": "natan.rubenich",
                    "password": "sua_senha_secreta",
                    "codigo_turma": "369528",
                    "trimestre_referencia": "TR2"
                },
                {
                    "username": "natan.rubenich",
                    "password": "sua_senha_secreta",
                    "codigo_turma": "369528",
                    "atitude_observada": "Sempre",
                    "conceito_habilidade": "A",
                    "trimestre_referencia": "TR1"
                }
            ]
        }

class LoginRequestRA(BaseModel):
    """
    Modelo para requisição de lançamento de conceitos COM Recomposição de Aprendizagem (RA)
    
    Attributes:
        username (str): Nome de usuário para login no SGN
        password (str): Senha do usuário
        codigo_turma (str): Código identificador da turma
        atitude_observada (AtitudeObservada): Opção para observações de atitudes (padrão: "Raramente")
        conceito_habilidade (ConceitoHabilidade): Opção para conceitos de habilidades (padrão: "B")
        trimestre_referencia (TrimestreReferencia): Trimestre em que os conceitos serão lançados
        inicio_ra (str): Data de início da RA (formato: DD/MM/YYYY)
        termino_ra (str): Data de término da RA (formato: DD/MM/YYYY)
        descricao_ra (str): Descrição da RA (O quê/Por quê/Como)
        nome_arquivo_ra (str): Nome do arquivo PDF da RA
    """
    username: str = Field(..., min_length=3, max_length=100, description="Nome de usuário do SGN")
    password: str = Field(..., min_length=3, max_length=100, description="Senha do usuário")
    codigo_turma: str = Field(..., min_length=1, max_length=20, pattern=r'^\d+$', description="Código da turma")
    atitude_observada: AtitudeObservada = Field(default=AtitudeObservada.RARAMENTE, description="Opção para atitudes")
    conceito_habilidade: ConceitoHabilidade = Field(default=ConceitoHabilidade.B, description="Conceito padrão (fallback)")
    trimestre_referencia: TrimestreReferencia = Field(default=TrimestreReferencia.TR2, description="Trimestre de referência")
    inicio_ra: str = Field(..., pattern=r'^\d{2}/\d{2}/\d{4}$', description="Data início RA (DD/MM/YYYY)", example="01/10/2025")
    termino_ra: str = Field(..., pattern=r'^\d{2}/\d{2}/\d{4}$', description="Data término RA (DD/MM/YYYY)", example="31/10/2025")
    descricao_ra: str = Field(..., min_length=10, max_length=5000, description="Descrição da RA", example="Reforço em programação orientada a objetos")
    nome_arquivo_ra: str = Field(..., min_length=1, max_length=80, description="Nome do arquivo PDF", example="RA_Turma_369528_TR2.pdf")

class ParecerRequest(BaseModel):
    """
    Modelo para requisição de lançamento de pareceres baseados em notas
    
    Attributes:
        username (str): Nome de usuário para login no SGN
        password (str): Senha do usuário
        codigo_turma (str): Código identificador da turma
        trimestre_referencia (TrimestreReferencia): Trimestre de referência
    """
    username: str = Field(
        ..., 
        min_length=3, 
        max_length=100,
        description="Nome de usuário do SGN (3-100 caracteres)",
        example="natan.rubenich"
    )
    password: str = Field(
        ..., 
        min_length=3,
        max_length=100,
        description="Senha do usuário (3-100 caracteres)",
        example="sua_senha_secreta"
    )
    codigo_turma: str = Field(
        ..., 
        min_length=1,
        max_length=20,
        pattern=r'^\d+$',
        description="Código numérico da turma (apenas dígitos)",
        example="369528"
    )
    trimestre_referencia: TrimestreReferencia = Field(
        default=TrimestreReferencia.TR2,
        description="Trimestre de referência utilizado para lançamento dos pareceres",
        example="TR2"
    )

class AutomationResponse(BaseModel):
    """
    Modelo para resposta da automação
    
    Attributes:
        success (bool): Indica se a operação foi bem-sucedida
        message (str): Mensagem descritiva do resultado
    """
    success: bool = Field(..., description="Status da operação (true/false)")
    message: str = Field(..., description="Mensagem descritiva do resultado")
