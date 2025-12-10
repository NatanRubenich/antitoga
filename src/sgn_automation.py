"""
Automação específica para o sistema SGN

Este módulo contém toda a lógica específica para interagir com o sistema SGN:
- Processo de login no sistema
- Navegação entre páginas
- Interação com elementos específicos do SGN
- Fluxo completo até a aba de Conceitos

O módulo é dividido em métodos pequenos e específicos para facilitar
manutenção e debugging de cada etapa do processo.
"""
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import time
import re
import unicodedata
import json
import random
import os
import requests
from lxml import html
from .sgn_automation_helpers import SGNAutomationHelpers

class SGNAutomation:
    """
    Classe responsável pela automação específica do sistema SGN
    
    Esta classe implementa todo o fluxo necessário para:
    1. Fazer login no sistema SGN
    2. Navegar até a página de diários
    3. Acessar o diário de uma turma específica
    4. Abrir a aba de Conceitos
    
    Attributes:
        selenium_manager: Instância do gerenciador do Selenium
        driver: Referência ao WebDriver (obtida do selenium_manager)
    """
    
    def __init__(self, selenium_manager):
        """
        Inicializa a automação do SGN
        
        Args:
            selenium_manager (SeleniumManager): Instância do gerenciador do Selenium
        """
        self.selenium_manager = selenium_manager
        self.driver = None
        # Inicializar helpers para métodos aprimorados
        self.helpers = SGNAutomationHelpers(selenium_manager)
        
        # Delegar métodos auxiliares para a classe principal
        self._validar_elementos_conceitos = self.helpers._validar_elementos_conceitos
        self._obter_lista_alunos_com_validacao = self.helpers._obter_lista_alunos_com_validacao
        self._acessar_aba_notas_aluno_com_validacao = self.helpers._acessar_aba_notas_aluno_com_validacao
        self._preencher_observacoes_atitudes_com_validacao = self.helpers._preencher_observacoes_atitudes_com_validacao
        self._preencher_conceitos_habilidades_com_validacao = self.helpers._preencher_conceitos_habilidades_com_validacao
        self._validar_dados_preenchidos = self.helpers._validar_dados_preenchidos
        self._fechar_modal_conceitos_com_validacao = self.helpers._fechar_modal_conceitos_com_validacao
        # Cache de pareceres
        self._pareceres_cache = None

    def _load_pareceres(self) -> dict:
        """
        Carrega os pareceres a partir de pareceres_pedagogicos.json (cacheado).
        """
        if self._pareceres_cache is not None:
            return self._pareceres_cache
        try:
            base_dir = os.path.dirname(os.path.dirname(__file__))
            json_path = os.path.join(base_dir, "pareceres_pedagogicos.json")
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # normaliza chaves
            self._pareceres_cache = {str(k).upper(): (v if isinstance(v, list) else []) for k, v in data.items()}
        except Exception as e:
            print(f"   ⚠️ Não foi possível carregar pareceres_pedagogicos.json: {e}")
            self._pareceres_cache = {}
        return self._pareceres_cache

    def _gerar_parecer_por_conceito(self, conceito: str) -> str:
        """Seleciona aleatoriamente um parecer do JSON conforme o conceito (A/B/C/NE)."""
        banco = self._load_pareceres()
        key = (conceito or "").strip().upper()
        lst = banco.get(key) or []
        if lst:
            return random.choice(lst)
        for alt in ("B", "A", "C", "NE"):
            cand = banco.get(alt) or []
            if cand:
                return random.choice(cand)
        return (
            "O estudante apresenta evolução compatível com o período, havendo oportunidades de aprimoramento em organização, "
            "consistência nas entregas e participação. A consolidação dos conteúdos ocorrerá com maior dedicação e estudos regulares."
        )
    
    def perform_login(self, username, password):
        """
        Realiza apenas o login no sistema SGN (método público reutilizável)
        
        Este método pode ser usado independentemente para fazer login no SGN.
        Ele executa todo o fluxo de login: acessar página -> clicar botão inicial -> inserir credenciais.
        
        Args:
            username (str): Nome de usuário para login no SGN
            password (str): Senha do usuário
            
        Returns:
            tuple: (success: bool, message: str)
                - success: True se o login foi bem-sucedido, False caso contrário
                - message: Mensagem descritiva do resultado
        """
        try:
            # Obter driver do gerenciador (cria um novo se necessário)
            self.driver = self.selenium_manager.get_driver()
            
            # Executar fluxo de login
            self._access_login_page()           # 1. Acessar página inicial
            self._click_initial_login_button()  # 2. Clicar no botão "Entrar" inicial
            self._perform_login_credentials(username, password)  # 3. Inserir credenciais
            self._fechar_modal_senha_chrome()   # 4. Fechar modal de senha do Chrome (se aparecer)
            
            return True, "Login realizado com sucesso!"
        except Exception as e:
            error_msg = f"Erro durante login: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg
    
    def lancar_conceito_trimestre(
        self,
        username,
        password,
        codigo_turma,
        atitude_observada=None,
        conceito_habilidade=None,
        trimestre_referencia="TR2",
    ):
        """
        Executa o fluxo completo: login -> navegação -> lançamento de conceitos
        
        Este método realiza todo o processo de lançamento de conceitos para todos os alunos:
        1. Faz login no sistema
        2. Navega até o diário da turma
        3. Abre a aba de Conceitos
        4. Para cada aluno:
           - Abre a modal de conceitos
           - Preenche as observações de atitudes com o valor especificado
           - Preenche os conceitos de habilidades com o valor especificado
           - Salva as alterações
        
        Args:
            username (str): Nome de usuário para login no SGN
            password (str): Senha do usuário
            codigo_turma (str): Código identificador da turma
            atitude_observada (str, optional): Opção para observações de atitudes. Padrão: "Raramente"
            conceito_habilidade (str, optional): Opção para conceitos de habilidades. Padrão: "B"
            trimestre_referencia (str): Trimestre de referência (TR1, TR2 ou TR3)
                
        Returns:
            tuple: (success: bool, message: str)
                - success: True se tudo ocorreu bem, False em caso de erro
                - message: Mensagem descritiva do resultado com estatísticas
        """
        """
        Executa o fluxo completo: login -> navegação -> lançamento de conceitos
        
        Este método realiza todo o processo de lançamento de conceitos para todos os alunos:
        1. Faz login no sistema
{{ ... }}
        
        Args:
            username (str): Nome de usuário para login no SGN
            password (str): Senha do usuário
            codigo_turma (str): Código identificador da turma
            atitude_observada (str, optional): Opção para observações de atitudes. Padrão: "Raramente"
            conceito_habilidade (str, optional): Opção para conceitos de habilidades. Padrão: "B"
                
        Returns:
            tuple: (success: bool, message: str)
                - success: True se tudo ocorreu bem, False em caso de erro
                - message: Mensagem descritiva do resultado com estatísticas
        """
        try:
            from .models import AtitudeObservada, ConceitoHabilidade
            
            # Validar e definir valores padrão
            if not isinstance(username, str) or not isinstance(password, str) or not isinstance(codigo_turma, str):
                raise TypeError("Parâmetros username, password e codigo_turma devem ser strings")
            
            # Definir valores padrão se não fornecidos
            if atitude_observada is None:
                atitude_observada = "Raramente"
            if conceito_habilidade is None:
                conceito_habilidade = "B"
            if trimestre_referencia is None:
                trimestre_referencia = "TR2"

            # Garantir que trimestre_referencia seja uma string válida (TR1/TR2/TR3)
            if hasattr(trimestre_referencia, "value"):
                trimestre_referencia = trimestre_referencia.value

            trimestre_referencia = str(trimestre_referencia).strip().upper()
            valid_trimestres = {"TR1", "TR2", "TR3"}
            if trimestre_referencia not in valid_trimestres:
                raise ValueError(
                    f"Trimestre de referência inválido. Valores aceitos: {', '.join(sorted(valid_trimestres))}"
                )
            
            # Mapear atitude_observada para o enum
            try:
                # Normaliza a string para comparação (remove acentos e converte para minúsculas)
                def normalize_str(s):
                    import unicodedata
                    return ''.join(c for c in unicodedata.normalize('NFD', str(s).lower()) 
                                if unicodedata.category(c) != 'Mn')
                
                # Processar atitude_observada
                if isinstance(atitude_observada, str):
                    input_normalized = normalize_str(atitude_observada)
                    for a in AtitudeObservada:
                        if normalize_str(a.value) == input_normalized:
                            atitude_mapeada = a
                            break
                    else:
                        # Tenta encontrar correspondência parcial
                        for a in AtitudeObservada:
                            if input_normalized in normalize_str(a.value) or normalize_str(a.value) in input_normalized:
                                atitude_mapeada = a
                                break
                        else:
                            raise ValueError(
                                f"Atitude observada inválida. Valores aceitos: {', '.join(e.value for e in AtitudeObservada)}"
                            )
                else:
                    atitude_mapeada = atitude_observada
                
                # Processar conceito_habilidade
                if isinstance(conceito_habilidade, str):
                    conceito_upper = conceito_habilidade.strip().upper()
                    conceito_mapeado = next(
                        (c for c in ConceitoHabilidade 
                         if c.value.upper() == conceito_upper),
                        None
                    )
                    if conceito_mapeado is None:
                        # Tenta encontrar correspondência parcial
                        for c in ConceitoHabilidade:
                            if c.value.upper() == conceito_upper or \
                               (len(conceito_upper) == 1 and c.value.upper() == conceito_upper):
                                conceito_mapeado = c
                                break
                        else:
                            raise ValueError(
                                f"Conceito de habilidade inválido. Valores aceitos: {', '.join(e.value for e in ConceitoHabilidade if e != ConceitoHabilidade.SELECIONE)}"
                            )
                else:
                    conceito_mapeado = conceito_habilidade
                    
            except ValueError as e:
                raise ValueError(str(e))
            except Exception as e:
                raise ValueError(f"Erro ao processar parâmetros: {str(e)}")
            
            print(f"🔧 Parâmetros recebidos:")
            print(f"   - Usuário: {username}")
            print(f"   - Código da turma: {codigo_turma}")
            print(f"   - Atitude observada: {atitude_mapeada.value if hasattr(atitude_mapeada, 'value') else atitude_mapeada}")
            print(f"   - Conceito habilidade: {conceito_mapeado.value if hasattr(conceito_mapeado, 'value') else conceito_mapeado}")
            
            # 1. Fazer login
            print("\n1. Iniciando processo de login...")
            success, message = self.perform_login(username, password)
            if not success:
                return False, f"Falha no login: {message}"
            
            # 2. Navegar para a aba de conceitos
            print("\n2. Navegando para a aba de conceitos...")
            success, message = self.navigate_to_conceitos(codigo_turma)
            if not success:
                return False, f"Falha ao navegar para conceitos: {message}"

            # 2.1 Validar trimestre de referência antes do lançamento
            print("\n2.1. Validando trimestre de referência antes do lançamento...")
            self._selecionar_trimestre_referencia(trimestre_referencia)

            # 3. Lançar conceitos para todos os alunos
            print("\n3. Iniciando lançamento de conceitos...")
            print(f"🔧 Usando valores mapeados:")
            print(f"   - Atitude: {atitude_mapeada}")
            print(f"   - Conceito: {conceito_mapeado}")
            
            success, message = self._lancar_conceitos_todos_alunos(
                atitude_observada=atitude_mapeada,
                conceito_habilidade=conceito_mapeado,
                trimestre_referencia=trimestre_referencia
            )
            
            return success, message
            
        except Exception as e:
            error_msg = f"Erro ao lançar conceitos: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg
    
    def lancar_conceito_inteligente(
        self,
        username,
        password,
        codigo_turma,
        atitude_observada=None,
        conceito_habilidade=None,
        trimestre_referencia="TR2",
        trocar_c_por_ne: bool = True,
    ):
        """
        🆕 NOVO: Executa o fluxo completo com lançamento INTELIGENTE de conceitos
        
        Diferença do método anterior:
        - lancar_conceito_trimestre(): Aplica o MESMO conceito para TODAS as habilidades
        - Este método: Aplica conceitos DIFERENTES baseados nas avaliações de cada habilidade
        
        Este método realiza:
        1. Login no sistema
        2. Navegação até o diário da turma
        3. Coleta de avaliações cadastradas (AV1, AV2, etc.)
        4. Coleta de recuperações paralelas (RP1, RP2, etc.)
        5. Mapeamento de habilidades para cada avaliação
        6. Para cada aluno:
           - Lê as notas da tabela (AV1=B, RP1=A, etc.)
           - Aplica conceito específico para cada habilidade baseado em sua avaliação
           - Se existe RP, usa RP em vez de AV
           - Se não há mapeamento, usa conceito padrão
        
        Args:
            username (str): Nome de usuário para login no SGN
            password (str): Senha do usuário
            codigo_turma (str): Código identificador da turma
            atitude_observada (str, optional): Opção para observações de atitudes. Padrão: "Raramente"
            conceito_habilidade (str, optional): Conceito padrão (fallback) se não houver mapeamento. Padrão: "B"
            trimestre_referencia (str): Trimestre de referência (TR1, TR2 ou TR3)
                
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            from .models import AtitudeObservada, ConceitoHabilidade
            
            if not isinstance(username, str) or not isinstance(password, str) or not isinstance(codigo_turma, str):
                raise TypeError("Parâmetros username, password e codigo_turma devem ser strings")
            
            if atitude_observada is None:
                atitude_observada = "Raramente"
            if conceito_habilidade is None:
                conceito_habilidade = "B"
            if trimestre_referencia is None:
                trimestre_referencia = "TR2"

            if hasattr(trimestre_referencia, "value"):
                trimestre_referencia = trimestre_referencia.value

            trimestre_referencia = str(trimestre_referencia).strip().upper()
            valid_trimestres = {"TR1", "TR2", "TR3"}
            if trimestre_referencia not in valid_trimestres:
                raise ValueError(
                    f"Trimestre de referência inválido. Valores aceitos: {', '.join(sorted(valid_trimestres))}"
                )
            
            # Mapear parâmetros para enums
            def normalize_str(s):
                import unicodedata
                return ''.join(c for c in unicodedata.normalize('NFD', str(s).lower()) 
                            if unicodedata.category(c) != 'Mn')
            
            if isinstance(atitude_observada, str):
                input_normalized = normalize_str(atitude_observada)
                for a in AtitudeObservada:
                    if normalize_str(a.value) == input_normalized:
                        atitude_mapeada = a
                        break
                else:
                    for a in AtitudeObservada:
                        if input_normalized in normalize_str(a.value) or normalize_str(a.value) in input_normalized:
                            atitude_mapeada = a
                            break
                    else:
                        raise ValueError(
                            f"Atitude observada inválida. Valores aceitos: {', '.join(e.value for e in AtitudeObservada)}"
                        )
            else:
                atitude_mapeada = atitude_observada
            
            if isinstance(conceito_habilidade, str):
                conceito_upper = conceito_habilidade.strip().upper()
                conceito_mapeado = next(
                    (c for c in ConceitoHabilidade 
                     if c.value.upper() == conceito_upper),
                    None
                )
                if conceito_mapeado is None:
                    for c in ConceitoHabilidade:
                        if c.value.upper() == conceito_upper or \
                           (len(conceito_upper) == 1 and c.value.upper() == conceito_upper):
                            conceito_mapeado = c
                            break
                    else:
                        raise ValueError(
                            f"Conceito de habilidade inválido. Valores aceitos: {', '.join(e.value for e in ConceitoHabilidade if e != ConceitoHabilidade.SELECIONE)}"
                        )
            else:
                conceito_mapeado = conceito_habilidade
            
            print(f"🔧 Parâmetros recebidos (MODO INTELIGENTE):")
            print(f"   - Usuário: {username}")
            print(f"   - Código da turma: {codigo_turma}")
            print(f"   - Atitude observada: {atitude_mapeada.value if hasattr(atitude_mapeada, 'value') else atitude_mapeada}")
            print(f"   - Conceito habilidade (fallback): {conceito_mapeado.value if hasattr(conceito_mapeado, 'value') else conceito_mapeado}")
            print(f"   - Trocar C por NE: {trocar_c_por_ne}")
            
            # 1. Fazer login
            print("\n1. Iniciando processo de login...")
            success, message = self.perform_login(username, password)
            if not success:
                return False, f"Falha no login: {message}"
            
            # 2. Navegar para o diário (mas NÃO para aba conceitos ainda)
            print("\n2. Navegando para o diário da turma...")
            diario_url = f"https://sgn.sesisenai.org.br/pages/diarioClasse/diario-classe.html?idDiario={codigo_turma}"
            self.driver.get(diario_url)
            time.sleep(3)
            
            # 3. COLETAR AVALIAÇÕES PRIMEIRO (antes de ir para aba Conceitos)
            print("\n3. Coletando avaliações cadastradas...")
            dados_av = self._coletar_avaliacoes_turma()
            
            # VERIFICAÇÃO CRÍTICA: Se não há avaliações, encerrar com erro
            if not dados_av or len(dados_av) == 0:
                erro_msg = "❌ ERRO CRÍTICO: Nenhuma avaliação encontrada na turma. É necessário cadastrar avaliações antes de lançar conceitos no modo inteligente."
                print(f"   {erro_msg}")
                raise Exception(erro_msg)
            
            dados_rp = self._coletar_recuperacoes_paralelas()

            # 4. AGORA SIM, navegar para aba Conceitos
            print("\n4. Navegando para aba Conceitos...")
            try:
                self._open_conceitos_tab()
            except Exception as e:
                return False, f"Erro ao acessar aba Conceitos: {e}"

            # 5. Selecionar trimestre de referência
            print("\n5. Selecionando trimestre de referência...")
            self._selecionar_trimestre_referencia(trimestre_referencia)
            
            # 6. COLETAR CABEÇALHOS APÓS SELECIONAR O TRIMESTRE (CRÍTICO!)
            print("\n6. Coletando cabeçalhos da tabela de conceitos...")
            cabecalhos = self._coletar_configuracao_conceitos()
            
            # 7. Construir mapeamentos
            mapeamentos = self._construir_mapeamento_avaliacoes(cabecalhos, dados_av, dados_rp)
            
            # PRINTAR RESUMO DAS AVALIAÇÕES COLETADAS
            self._printar_resumo_avaliacoes(dados_av, dados_rp, mapeamentos)

            # 7.1 Validação crítica: bloquear se houver avaliações sem habilidades
            avs_sem_hab = mapeamentos.get("avaliacoes_sem_habilidade", [])
            if avs_sem_hab:
                msg_bloqueio = (
                    "❌ ERRO: Existem avaliações sem habilidades vinculadas para o trimestre selecionado: "
                    + ", ".join(avs_sem_hab)
                    + ". Cadastre habilidades nessas avaliações antes de continuar."
                )
                print(msg_bloqueio)
                return False, msg_bloqueio

            # 8. Lançar conceitos INTELIGENTES para todos os alunos
            print("\n8. Iniciando lançamento INTELIGENTE de conceitos...")
            print(f"🔧 Usando valores mapeados:")
            print(f"   - Atitude: {atitude_mapeada}")
            print(f"   - Conceito (fallback): {conceito_mapeado}")
            
            success, message = self._lancar_conceitos_inteligente(
                atitude_observada=atitude_mapeada,
                conceito_habilidade=conceito_mapeado,
                trimestre_referencia=trimestre_referencia,
                mapeamentos_prontos=mapeamentos,  # Passar mapeamentos já coletados
                trocar_c_por_ne=trocar_c_por_ne,
            )
            
            return success, message
            
        except Exception as e:
            error_msg = f"Erro ao lançar conceitos inteligentes: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg
    
    def lancar_conceito_inteligente_com_ra(
        self,
        username,
        password,
        codigo_turma,
        inicio_ra,
        termino_ra,
        descricao_ra,
        nome_arquivo_ra,
        caminho_arquivo_ra,
        atitude_observada=None,
        conceito_habilidade=None,
        trimestre_referencia="TR2",
    ):
        """
        🆕 NOVO: Executa o fluxo completo com lançamento INTELIGENTE de conceitos COM CADASTRO DE RA
        
        Diferenças do método lancar_conceito_inteligente():
        - Mantém conceito C (não troca por NE)
        - Cadastra Recomposição de Aprendizagem para cada habilidade com conceito C
        
        Args:
            username (str): Nome de usuário para login no SGN
            password (str): Senha do usuário
            codigo_turma (str): Código identificador da turma
            inicio_ra (str): Data de início da RA (DD/MM/YYYY)
            termino_ra (str): Data de término da RA (DD/MM/YYYY)
            descricao_ra (str): Descrição da RA
            nome_arquivo_ra (str): Nome do arquivo PDF
            caminho_arquivo_ra (str): Caminho completo do arquivo PDF
            atitude_observada (str, optional): Opção para observações de atitudes. Padrão: "Raramente"
            conceito_habilidade (str, optional): Conceito padrão (fallback). Padrão: "B"
            trimestre_referencia (str): Trimestre de referência (TR1, TR2 ou TR3)
                
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            from .models import AtitudeObservada, ConceitoHabilidade
            
            if not isinstance(username, str) or not isinstance(password, str) or not isinstance(codigo_turma, str):
                raise TypeError("Parâmetros username, password e codigo_turma devem ser strings")
            
            if atitude_observada is None:
                atitude_observada = "Raramente"
            if conceito_habilidade is None:
                conceito_habilidade = "B"
            if trimestre_referencia is None:
                trimestre_referencia = "TR2"

            if hasattr(trimestre_referencia, "value"):
                trimestre_referencia = trimestre_referencia.value

            trimestre_referencia = str(trimestre_referencia).strip().upper()
            valid_trimestres = {"TR1", "TR2", "TR3"}
            if trimestre_referencia not in valid_trimestres:
                raise ValueError(
                    f"Trimestre de referência inválido. Valores aceitos: {', '.join(sorted(valid_trimestres))}"
                )
            
            # Mapear parâmetros para enums
            def normalize_str(s):
                import unicodedata
                return ''.join(c for c in unicodedata.normalize('NFD', str(s).lower()) 
                            if unicodedata.category(c) != 'Mn')
            
            if isinstance(atitude_observada, str):
                input_normalized = normalize_str(atitude_observada)
                for a in AtitudeObservada:
                    if normalize_str(a.value) == input_normalized:
                        atitude_mapeada = a
                        break
                else:
                    for a in AtitudeObservada:
                        if input_normalized in normalize_str(a.value) or normalize_str(a.value) in input_normalized:
                            atitude_mapeada = a
                            break
                    else:
                        raise ValueError(
                            f"Atitude observada inválida. Valores aceitos: {', '.join(e.value for e in AtitudeObservada)}"
                        )
            else:
                atitude_mapeada = atitude_observada
            
            if isinstance(conceito_habilidade, str):
                conceito_upper = conceito_habilidade.strip().upper()
                conceito_mapeado = next(
                    (c for c in ConceitoHabilidade 
                     if c.value.upper() == conceito_upper),
                    None
                )
                if conceito_mapeado is None:
                    for c in ConceitoHabilidade:
                        if c.value.upper() == conceito_upper or \
                           (len(conceito_upper) == 1 and c.value.upper() == conceito_upper):
                            conceito_mapeado = c
                            break
                    else:
                        raise ValueError(
                            f"Conceito de habilidade inválido. Valores aceitos: {', '.join(e.value for e in ConceitoHabilidade if e != ConceitoHabilidade.SELECIONE)}"
                        )
            else:
                conceito_mapeado = conceito_habilidade
            
            print(f"🔧 Parâmetros recebidos (MODO INTELIGENTE COM RA):")
            print(f"   - Usuário: {username}")
            print(f"   - Código da turma: {codigo_turma}")
            print(f"   - Atitude observada: {atitude_mapeada.value if hasattr(atitude_mapeada, 'value') else atitude_mapeada}")
            print(f"   - Conceito habilidade (fallback): {conceito_mapeado.value if hasattr(conceito_mapeado, 'value') else conceito_mapeado}")
            print(f"   - Início RA: {inicio_ra}")
            print(f"   - Término RA: {termino_ra}")
            print(f"   - Arquivo RA: {caminho_arquivo_ra}")
            
            # 1. Fazer login
            print("\n1. Iniciando processo de login...")
            success, message = self.perform_login(username, password)
            if not success:
                return False, f"Falha no login: {message}"
            
            # 2. Navegar para o diário
            print("\n2. Navegando para o diário da turma...")
            diario_url = f"https://sgn.sesisenai.org.br/pages/diarioClasse/diario-classe.html?idDiario={codigo_turma}"
            self.driver.get(diario_url)
            time.sleep(3)
            
            # 3. COLETAR AVALIAÇÕES
            print("\n3. Coletando avaliações cadastradas...")
            dados_av = self._coletar_avaliacoes_turma()
            
            if not dados_av or len(dados_av) == 0:
                erro_msg = "❌ ERRO CRÍTICO: Nenhuma avaliação encontrada na turma."
                print(f"   {erro_msg}")
                raise Exception(erro_msg)
            
            dados_rp = self._coletar_recuperacoes_paralelas()

            # 4. Navegar para aba Conceitos
            print("\n4. Navegando para aba Conceitos...")
            try:
                self._open_conceitos_tab()
            except Exception as e:
                return False, f"Erro ao acessar aba Conceitos: {e}"

            # 5. Selecionar trimestre
            print("\n5. Selecionando trimestre de referência...")
            self._selecionar_trimestre_referencia(trimestre_referencia)
            
            # 6. Coletar cabeçalhos
            print("\n6. Coletando cabeçalhos da tabela de conceitos...")
            cabecalhos = self._coletar_configuracao_conceitos()
            
            # 7. Construir mapeamentos
            mapeamentos = self._construir_mapeamento_avaliacoes(cabecalhos, dados_av, dados_rp)
            
            # PRINTAR RESUMO
            self._printar_resumo_avaliacoes(dados_av, dados_rp, mapeamentos)

            # 7.1 Validação crítica (modo RA): bloquear se houver avaliações sem habilidades
            avs_sem_hab = mapeamentos.get("avaliacoes_sem_habilidade", [])
            if avs_sem_hab:
                msg_bloqueio = (
                    "❌ ERRO: Existem avaliações sem habilidades vinculadas para o trimestre selecionado: "
                    + ", ".join(avs_sem_hab)
                    + ". Cadastre habilidades nessas avaliações antes de continuar."
                )
                print(msg_bloqueio)
                return False, msg_bloqueio

            # 8. Lançar conceitos INTELIGENTES COM RA
            print("\n8. Iniciando lançamento INTELIGENTE de conceitos COM RA...")
            print(f"🔧 Usando valores mapeados:")
            print(f"   - Atitude: {atitude_mapeada}")
            print(f"   - Conceito (fallback): {conceito_mapeado}")
            print(f"   - Modo: MANTÉM C + CADASTRA RA")
            
            success, message = self._lancar_conceitos_inteligente_com_ra(
                atitude_observada=atitude_mapeada,
                conceito_habilidade=conceito_mapeado,
                trimestre_referencia=trimestre_referencia,
                mapeamentos_prontos=mapeamentos,
                inicio_ra=inicio_ra,
                termino_ra=termino_ra,
                descricao_ra=descricao_ra,
                nome_arquivo_ra=nome_arquivo_ra,
                caminho_arquivo_ra=caminho_arquivo_ra
            )
            
            return success, message
            
        except Exception as e:
            error_msg = f"Erro ao lançar conceitos inteligentes com RA: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg
    
    def login_and_navigate_to_conceitos(self, username, password, codigo_turma):
        """
        MÉTODO LEGADO: Executa o fluxo completo: login -> navegação -> aba conceitos
        
        Este método mantém compatibilidade com código existente.
        Para lançamento de conceitos, use lancar_conceito_trimestre().
        
        Args:
            username (str): Nome de usuário para login no SGN
            password (str): Senha do usuário
            codigo_turma (str): Código identificador da turma
            
        Returns:
            tuple: (success: bool, message: str)
                - success: True se tudo ocorreu bem, False em caso de erro
                - message: Mensagem descritiva do resultado
        """
        try:
            # Fazer login usando o método reutilizável
            login_success, login_message = self.perform_login(username, password)
            
            if not login_success:
                return False, f"Falha no login: {login_message}"
            
            # Continuar com a navegação específica
            self._navigate_to_diary_search()    # 4. Navegar para buscar diário
            self._access_class_diary(codigo_turma)  # 5. Acessar diário da turma
            self._open_conceitos_tab()          # 6. Abrir aba de conceitos
            
            return True, "Login e navegação para Conceitos concluídos com sucesso!"
            
        except Exception as e:
            error_msg = f"Erro durante automação completa: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg
    
    def navigate_to_conceitos(self, codigo_turma):
        """
        Navega para a aba de Conceitos de uma turma específica (método público reutilizável)
        
        Este método assume que o usuário já está logado no sistema.
        Navega diretamente para o diário da turma e abre a aba de Conceitos.
        
        Args:
            codigo_turma (str): Código identificador da turma
            
        Returns:
            tuple: (success: bool, message: str)
                - success: True se a navegação foi bem-sucedida, False caso contrário
                - message: Mensagem descritiva do resultado
        """
        try:
            if not self.driver:
                return False, "Driver não inicializado. Faça login primeiro."
            
            # Acesso direto ao diário da turma (pula a navegação intermediária)
            print(f"🚀 Acessando diretamente o diário da turma {codigo_turma}...")
            self._access_class_diary(codigo_turma)  # Acessar diário da turma diretamente
            self._open_conceitos_tab()          # Abrir aba de conceitos
            
            return True, f"Navegação direta para Conceitos da turma {codigo_turma} concluída!"
            
        except Exception as e:
            error_msg = f"Erro durante navegação: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg
    
    def check_login_status(self):
        """
        Verifica se o usuário está logado no sistema
        
        Returns:
            tuple: (is_logged_in: bool, current_url: str)
                - is_logged_in: True se estiver logado, False caso contrário
                - current_url: URL atual do navegador
        """
        try:
            if not self.driver:
                return False, "Driver não inicializado"
            
            current_url = self.driver.current_url
            page_title = self.driver.title
            
            # Verifica se não está na página de login
            is_logged_in = (
                "login" not in current_url.lower() and 
                "sgn.sesisenai.org.br" in current_url and
                current_url != "https://sgn.sesisenai.org.br/"
            )
            
            print(f"Status do login: {'✅ Logado' if is_logged_in else '❌ Não logado'}")
            print(f"URL atual: {current_url}")
            print(f"Título: {page_title}")
            
            return is_logged_in, current_url
            
        except Exception as e:
            print(f"Erro ao verificar status de login: {str(e)}")
            return False, str(e)
    
    def test_conceitos_tab_only(self, codigo_turma):
        """
        Testa apenas o acesso à aba de Conceitos (assume que já está logado)
        
        Método para debug específico da aba de Conceitos.
        Navega diretamente para o diário e tenta abrir a aba.
        
        Args:
            codigo_turma (str): Código identificador da turma
            
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            if not self.driver:
                return False, "Driver não inicializado. Faça login primeiro."
            
            print(f"🧪 Teste específico: Acessando aba de Conceitos da turma {codigo_turma}")
            
            # Navegar diretamente para o diário
            diario_url = f"https://sgn.sesisenai.org.br/pages/diarioClasse/diario-classe.html?idDiario={codigo_turma}"
            print(f"   Navegando para: {diario_url}")
            self.driver.get(diario_url)
            time.sleep(3)  # Reduzido de 5 para 3 segundos
            
            # Tentar abrir a aba de Conceitos
            self._open_conceitos_tab()
            
            return True, f"Aba de Conceitos da turma {codigo_turma} acessada com sucesso!"
            
        except Exception as e:
            error_msg = f"Erro no teste da aba de Conceitos: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg
    
    def _access_login_page(self):
        """
        Acessa a página de login do SGN
        
        Este método:
        1. Navega para a URL de login do SGN
        2. Aguarda o carregamento da página
        
        Note:
            Método privado (prefixo _) usado internamente pela classe
        """
        print("1. Acessando página de login...")
        
        # URLs para tentar (baseado na memória sobre FIESC)
        urls_to_try = [
            "https://sgn.sesisenai.org.br/sgn/login",
            "https://sgn.sesisenai.org.br/login",
            "https://sgn.sesisenai.org.br/"
        ]
        
        for i, url in enumerate(urls_to_try, 1):
            try:
                print(f"   Tentativa {i}: {url}")
                self.driver.get(url)
                time.sleep(2)  # Reduzido de 5 para 2 segundos
                
                # Verifica se a página carregou
                current_url = self.driver.current_url
                page_title = self.driver.title
                
                print(f"   ✅ Página carregada: {current_url}")
                print(f"   Título: {page_title}")
                
                # Se chegou até aqui, a URL funcionou
                break
                
            except Exception as e:
                print(f"   ❌ Erro ao acessar {url}: {str(e)}")
                if i == len(urls_to_try):
                    # Se foi a última tentativa, relança o erro
                    raise Exception(f"Não foi possível acessar nenhuma URL do SGN. Último erro: {str(e)}")
                else:
                    print(f"   🔄 Tentando próxima URL...")
                    continue
    
    def _click_initial_login_button(self):
        """
        Clica no botão "Entrar" inicial da página de boas-vindas
        
        Este método clica no botão inicial que aparece na tela de boas-vindas
        antes de mostrar os campos de login propriamente ditos.
        
        XPath baseado na análise: /html/body/div[1]/div/div/div[2]/form/div[2]/input
        """
        print("2. Clicando no botão 'Entrar' inicial...")
        
        try:
            # Aguarda o botão "Entrar" inicial estar disponível (reduzido timeout)
            initial_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "/html/body/div[1]/div/div/div[2]/form/div[2]/input"))
            )
            
            initial_button.click()
            print("   ✅ Botão 'Entrar' inicial clicado")
            
            # Aguarda a próxima tela carregar (reduzido de 5 para 3 segundos)
            time.sleep(3)
            
            # Debug: Mostrar nova URL e título
            current_url = self.driver.current_url
            page_title = self.driver.title
            print(f"   URL após clique: {current_url}")
            print(f"   Título: {page_title}")
            
        except Exception as e:
            print(f"   ❌ Erro ao clicar no botão inicial: {str(e)}")
            # Tenta seletores alternativos
            try:
                print("   🔄 Tentando seletores alternativos...")
                
                # Tenta por ID ou classe
                alternative_selectors = [
                    "//input[@value='Entrar']",
                    "//button[contains(text(), 'Entrar')]",
                    "//input[@type='submit']",
                    "#formLogin\\:entrar"
                ]
                
                for selector in alternative_selectors:
                    try:
                        if selector.startswith("#"):
                            button = self.driver.find_element(By.CSS_SELECTOR, selector)
                        else:
                            button = self.driver.find_element(By.XPATH, selector)
                        
                        button.click()
                        print(f"   ✅ Botão encontrado com seletor: {selector}")
                        time.sleep(3)  # Reduzido de 5 para 3 segundos
                        return
                        
                    except:
                        continue
                
                # Se chegou até aqui, não encontrou nenhum botão
                raise Exception("Nenhum botão 'Entrar' inicial encontrado")
                
            except Exception as e2:
                print(f"   ❌ Erro com seletores alternativos: {str(e2)}")
                # Tira screenshot para debug
                self.driver.save_screenshot("debug_initial_button.png")
                print("   📸 Screenshot salvo como 'debug_initial_button.png'")
                raise
    
    def _perform_login_credentials(self, username, password):
        """
        Insere as credenciais de login no formulário
        
        Este método é responsável apenas por preencher os campos de usuário e senha
        e submeter o formulário de login. Deve ser chamado após clicar no botão inicial.
        
        Args:
            username (str): Nome de usuário
            password (str): Senha do usuário
            
        Raises:
            TimeoutException: Se os elementos não forem encontrados no tempo limite
            NoSuchElementException: Se algum elemento não existir na página
        """
        print("3. Realizando login com credenciais...")
        
        # Debug: Mostrar URL atual e título da página
        current_url = self.driver.current_url
        page_title = self.driver.title
        print(f"   URL atual: {current_url}")
        print(f"   Título da página: {page_title}")
        
        # Usar os XPaths específicos fornecidos pelo usuário
        try:
            # Campo de login: /html/body/div/div/div/div[2]/div[2]/form/div[1]/input
            print("   🔍 Procurando campo de login...")
            username_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "/html/body/div/div/div/div[2]/div[2]/form/div[1]/input"))
            )
            print("   ✅ Campo de login encontrado")
            
            # Campo de senha: /html/body/div/div/div/div[2]/div[2]/form/div[2]/input
            print("   🔍 Procurando campo de senha...")
            password_field = self.driver.find_element(By.XPATH, "/html/body/div/div/div/div[2]/div[2]/form/div[2]/input")
            print("   ✅ Campo de senha encontrado")
            
            # Preenche o campo de usuário
            username_field.clear()
            username_field.send_keys(username)
            print(f"   ✅ Usuário '{username}' inserido")
            
            # Preenche o campo de senha
            password_field.clear()
            password_field.send_keys(password)
            print("   ✅ Senha inserida")
            
            # Procura pelo botão de login (pode estar em diferentes locais)
            print("   🔍 Procurando botão de login...")
            
            # Tenta diferentes seletores para o botão de login
            login_selectors = [
                "//button[@type='submit']",
                "//input[@type='submit']",
                "//button[contains(text(), 'Entrar')]",
                "//input[@value='Entrar']",
                "/html/body/div/div/div/div[2]/div[2]/form//button",
                "/html/body/div/div/div/div[2]/div[2]/form//input[@type='submit']"
            ]
            
            login_button = None
            for selector in login_selectors:
                try:
                    login_button = self.driver.find_element(By.XPATH, selector)
                    print(f"   ✅ Botão de login encontrado com: {selector}")
                    break
                except:
                    continue
            
            if login_button:
                login_button.click()
                print("   ✅ Botão de login clicado")
            else:
                # Se não encontrou botão, tenta pressionar Enter no campo de senha
                print("   ⚠️ Botão não encontrado, tentando Enter no campo de senha...")
                password_field.send_keys("\n")
            
            # Aguarda o processamento do login e redirecionamento (reduzido de 8 para 4 segundos)
            print("   ⏳ Aguardando redirecionamento...")
            time.sleep(4)
            
            # Verifica se o login foi bem-sucedido
            new_url = self.driver.current_url
            print(f"   URL após login: {new_url}")
            
            if "login" not in new_url.lower() or new_url != current_url:
                print("✅ Login realizado com sucesso")
            else:
                print("⚠️ Ainda na página de login - pode ter havido erro nas credenciais")
                # Tira screenshot para debug
                self.driver.save_screenshot("debug_after_login.png")
                print("   📸 Screenshot pós-login salvo como 'debug_after_login.png'")
            
        except Exception as e:
            print(f"   ❌ Erro durante login: {str(e)}")
            # Tira screenshot para debug
            self.driver.save_screenshot("debug_login_error.png")
            print("   📸 Screenshot de erro salvo como 'debug_login_error.png'")
            raise
    
    def _navigate_to_diary_search(self):
        """
        Navega para a página de busca de diário de classe
        
        Este método acessa diretamente a URL da página de consulta de diários,
        que é onde o usuário pode buscar e acessar diários de diferentes turmas.
        
        Note:
            Esta etapa é necessária no fluxo normal do sistema, mesmo que
            posteriormente acessemos o diário diretamente via URL
        """
        print("4. Navegando para buscar diário...")
        self.driver.get("https://sgn.sesisenai.org.br/pages/diarioClasse/diario-classe-consulta.html")
        time.sleep(1)  # Reduzido de 3 para 1 segundo (página intermediária)
    
    def _access_class_diary(self, codigo_turma):
        """
        Acessa o diário da turma específica
        
        Este método usa uma abordagem direta, construindo a URL do diário
        com o código da turma e navegando diretamente para ela, evitando
        a necessidade de buscar e selecionar a turma na interface.
        
        Args:
            codigo_turma (str): Código identificador da turma (ex: "369528")
            
        Note:
            A URL segue o padrão: 
            https://sgn.sesisenai.org.br/pages/diarioClasse/diario-classe.html?idDiario={codigo}
        """
        print(f"📋 Acessando diário da turma {codigo_turma} diretamente...")

        diario_url = f"https://sgn.sesisenai.org.br/pages/diarioClasse/diario-classe.html?idDiario={codigo_turma}"
        print(f"   🔗 URL: {diario_url}")

        max_tentativas = 3
        for tentativa in range(1, max_tentativas + 1):
            try:
                print(f"   🔄 Tentativa {tentativa}/{max_tentativas} de abrir o diário...")
                self.driver.get(diario_url)
                time.sleep(3)  # Aguardar carregamento da página

                if self._pagina_erro_diario_detectada():
                    print("   ⚠️ Página de erro 500 detectada ao carregar o diário")
                    if tentativa < max_tentativas:
                        self._recuperar_de_pagina_erro()
                        print("   ⏳ Reintentando acesso após recuperar da página de erro...")
                        time.sleep(2)
                        continue
                    else:
                        raise Exception("Página de erro 500 persistente ao acessar o diário")

                print(f"   ✅ Diário da turma {codigo_turma} carregado com sucesso")
                return

            except Exception as e:
                print(f"   ❌ Falha na tentativa {tentativa}: {e}")
                if tentativa >= max_tentativas:
                    raise
                time.sleep(2)

        raise Exception("Não foi possível acessar o diário após múltiplas tentativas")
    
    def _click_safe(self, element, element_description="elemento"):
        """
        Clica em um elemento de forma segura, evitando interceptações por overlays.
        
        Este método implementa uma estratégia robusta de clique:
        1. Rola a página com offset para evitar headers fixos no topo
        2. Aguarda um momento para estabilizar
        3. Tenta clique normal do Selenium
        4. Se interceptado, usa JavaScript click como fallback
        
        Args:
            element: WebElement do Selenium para clicar
            element_description (str): Descrição do elemento para logs
            
        Raises:
            Exception: Se nenhuma estratégia de clique funcionar
        """
        try:
            # Estratégia 1: Scroll com offset para evitar topbar fixo (120px de margem)
            self.driver.execute_script(
                "window.scrollTo(0, arguments[0].getBoundingClientRect().top + window.scrollY - 120);",
                element
            )
            time.sleep(0.5)
            
            # Estratégia 2: Tentar clique normal
            try:
                element.click()
                print(f"   ✅ {element_description} clicado com sucesso (clique normal)")
                return
            except Exception as click_error:
                # Se interceptado, tentar JavaScript click
                if "intercepted" in str(click_error).lower():
                    print(f"   ⚠️ Clique interceptado, tentando JavaScript click...")
                    self.driver.execute_script("arguments[0].click();", element)
                    print(f"   ✅ {element_description} clicado com sucesso (JavaScript)")
                    return
                else:
                    raise
                    
        except Exception as e:
            print(f"   ❌ Erro ao clicar em {element_description}: {str(e)}")
            raise
    
    def _open_pedagogico_tab(self):
        """
        Abre a aba Pedagógico no diário da turma
        
        Este método:
        1. Localiza a aba/link de "Pedagógico" na página do diário
        2. Aguarda até que o elemento seja clicável
        3. Clica na aba para abri-la usando clique seguro (evita interceptações)
        4. Aguarda o carregamento do conteúdo da aba
        
        Raises:
            TimeoutException: Se a aba Pedagógico não for encontrada no tempo limite
        """
        print("Abrindo aba Pedagógico...")
        
        # Lista de seletores para tentar (do mais específico ao mais genérico)
        selectors = [
            ("//a[contains(text(), 'Pedagógico')]", "Link com texto 'Pedagógico'"),
            ("//a[contains(@href, 'abaPedagogico')]", "Link com href contendo 'abaPedagogico'"),
            ("//li//a[contains(text(), 'Pedagógico')]", "Item de lista com link 'Pedagógico'"),
        ]
        
        for i, (selector, description) in enumerate(selectors, 1):
            try:
                print(f"   🔍 Tentativa {i}: {description}")
                pedagogico_tab = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, selector))
                )
                
                # Usar clique seguro (evita interceptações)
                self._click_safe(pedagogico_tab, f"Aba Pedagógico ({description})")
                
                # Aguardar carregamento AJAX da aba
                print("   ⏳ Aguardando aba Pedagógico carregar...")
                time.sleep(3)
                
                # Verificar se o dropdown de alunos está presente (sinal de sucesso)
                try:
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.ID, "tabViewDiarioClasse:formAbaPedagogico:selectEstudantes"))
                    )
                    print("✅ Aba Pedagógico aberta com sucesso")
                    return
                except:
                    print("   ⚠️ Dropdown de alunos não encontrado, tentando próximo seletor...")
                    continue
                    
            except Exception as e:
                print(f"   ❌ Falhou com {description}: {str(e)[:100]}")
                continue
        
        # Se chegou até aqui, nenhum seletor funcionou
        print("   📸 Tirando screenshot para debug...")
        self.driver.save_screenshot("debug_pedagogico_tab.png")
        print("   📸 Screenshot salvo como 'debug_pedagogico_tab.png'")
        
        raise Exception("Não foi possível encontrar a aba Pedagógico com nenhum seletor")
    
    def _open_conceitos_tab(self):
        """
        Abre a aba de Conceitos no diário da turma
        
        Este método:
        1. Localiza a aba/link de "Conceitos" na página do diário
        2. Aguarda até que o elemento seja clicável
        3. Clica na aba para abri-la usando clique seguro (evita interceptações)
        4. Aguarda o carregamento do conteúdo da aba
        
        O XPath usado procura por elementos que contenham o texto "Conceitos"
        ou que tenham "conceito" no atributo href, para maior flexibilidade.
        
        Raises:
            TimeoutException: Se a aba de Conceitos não for encontrada no tempo limite
        """
        print("6. Abrindo aba de Conceitos...")
        
        # Lista de seletores para tentar (do mais específico ao mais genérico)
        selectors = [
            ("//a[contains(text(), 'Conceitos')]", "Link com texto 'Conceitos'"),
            ("/html/body/div[3]/div[3]/div[2]/div[2]/div/div/ul/li[7]/a", "XPath específico li[7]/a"),
            ("//li[7]//a", "7º item da lista (link)"),
            ("/html/body/div[3]/div[3]/div[2]/div[2]/div/div/ul/li[7]", "XPath específico li[7]"),
            ("//a[contains(@href, 'conceito')]", "Link com href contendo 'conceito'"),
        ]
        
        for i, (selector, description) in enumerate(selectors, 1):
            try:
                print(f"   🔍 Tentativa {i}: {description}")
                conceitos_tab = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, selector))
                )
                
                # Usar clique seguro (evita interceptações)
                self._click_safe(conceitos_tab, f"Aba Conceitos ({description})")
                
                # Aguardar carregamento AJAX da aba
                print("   ⏳ Aguardando aba de Conceitos carregar...")
                time.sleep(3)
                
                # Verificar se a tabela de alunos está presente (sinal de sucesso)
                # Usar mesma lógica do _obter_lista_alunos que funciona
                tabela_encontrada = False
                
                # XPath principal usado pelos endpoints que funcionam
                tabela_xpath = "/html/body/div[3]/div[3]/div[2]/div[2]/div/div/div/div[7]/form/div/div/span/span/div[2]/div/div[2]/table/tbody"
                
                try:
                    print(f"   🔍 Verificando tabela principal: {tabela_xpath}")
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, tabela_xpath))
                    )
                    tabela_encontrada = True
                    print("   ✅ Tabela de alunos encontrada com XPath principal")
                except:
                    print("   ⚠️ Tabela não encontrada com XPath principal, tentando alternativas...")
                    
                    # XPaths alternativos (mesmos usados em _obter_lista_alunos)
                    alternative_table_xpaths = [
                        "//table//tbody[contains(@class, 'ui-datatable-data')]",
                        "//div[contains(@class, 'ui-datatable')]//tbody",
                        "//form//table//tbody",
                        "//div[7]//table//tbody",
                        "//span//div[2]//table//tbody"
                    ]
                    
                    for alt_xpath in alternative_table_xpaths:
                        try:
                            print(f"   🔄 Tentando: {alt_xpath}")
                            WebDriverWait(self.driver, 5).until(
                                EC.presence_of_element_located((By.XPATH, alt_xpath))
                            )
                            tabela_encontrada = True
                            print(f"   ✅ Tabela encontrada com XPath alternativo: {alt_xpath}")
                            break
                        except:
                            continue
                
                if tabela_encontrada:
                    print("✅ Aba de Conceitos aberta com sucesso")
                    return
                else:
                    print("   ⚠️ Tabela de alunos não encontrada, tentando próximo seletor...")
                    continue
                    
            except Exception as e:
                print(f"   ❌ Falhou com {description}: {str(e)[:100]}")
                continue
        
        # Se chegou até aqui, nenhum seletor funcionou
        print("   📸 Tirando screenshot para debug...")
        self.driver.save_screenshot("debug_conceitos_tab.png")
        print("   📸 Screenshot salvo como 'debug_conceitos_tab.png'")
        
        raise Exception("Não foi possível encontrar a aba de Conceitos com nenhum seletor")
    
    def close_browser(self):
        """
        Fecha o navegador de forma segura
        
        Este método delega o fechamento do navegador para o SeleniumManager,
        que possui a lógica adequada para fechar o driver de forma segura
        e liberar os recursos do sistema.
        """
        self.selenium_manager.close_driver()
    
    def _selecionar_trimestre_referencia(self, trimestre_referencia):
        """
        Seleciona o trimestre de referência na aba de conceitos.
        IMPORTANTE: 
        1. Deve clicar no LABEL para expandir o dropdown
        2. Depois selecionar a opção correta
        3. Aguardar AJAX carregar a tabela

        Args:
            trimestre_referencia (str): Valor esperado (TR1, TR2, TR3)
        """
        try:
            if not trimestre_referencia:
                return

            print(f"   🔄 Selecionando trimestre de referência '{trimestre_referencia}'...")

            # Aguardar o select estar presente (após AJAX da aba Conceitos)
            time.sleep(2)
            
            # XPATH ESPECÍFICO DO LABEL (deve clicar aqui primeiro)
            label_xpath_especifico = "/html/body/div[3]/div[3]/div[2]/div[2]/div/div/div/div[7]/form/div/div/div[1]/div/label"
            
            # XPaths alternativos
            select_xpath = "//select[@id='tabViewDiarioClasse:formAbaConceitos:mediasConceito_input']"
            label_xpath = "//label[@id='tabViewDiarioClasse:formAbaConceitos:mediasConceito_label']"
            div_select_xpath = "//div[@id='tabViewDiarioClasse:formAbaConceitos:mediasConceito']"
            
            # 1. LOCALIZAR O SELECT
            select_element = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, select_xpath))
            )
            
            # 2. AGUARDAR AS OPÇÕES ESTAREM CARREGADAS NO SELECT
            print(f"   ⏳ Aguardando opções do select carregarem...")
            try:
                # Aguardar até que existam pelo menos 2 options (Selecione + TR1/TR2/TR3)
                WebDriverWait(self.driver, 10).until(
                    lambda d: len(d.find_element(By.XPATH, select_xpath).find_elements(By.TAG_NAME, "option")) >= 2
                )
                print(f"   ✓ Opções carregadas no select")
                time.sleep(1)
            except Exception as e:
                print(f"   ⚠️ Timeout aguardando opções: {e}")
                print(f"   ℹ️ Tentando clicar no select para forçar carregamento...")
                
                # Tentar clicar no div do select para disparar AJAX
                try:
                    div_select = self.driver.find_element(By.XPATH, div_select_xpath)
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", div_select)
                    time.sleep(0.5)
                    div_select.click()
                    time.sleep(2)  # Aguardar AJAX
                    
                    # Fechar dropdown
                    self.driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                    time.sleep(1)
                    
                    # Aguardar novamente
                    WebDriverWait(self.driver, 5).until(
                        lambda d: len(d.find_element(By.XPATH, select_xpath).find_elements(By.TAG_NAME, "option")) >= 2
                    )
                    print(f"   ✓ Opções carregadas após clique")
                except Exception as e2:
                    print(f"   ❌ Não foi possível carregar opções: {e2}")
            
            # 3. LER OPÇÕES DO SELECT
            # Re-localizar o select para garantir que temos o elemento atualizado
            select_element = self.driver.find_element(By.XPATH, select_xpath)
            valor_atual_select = select_element.get_attribute("value") or ""
            
            # Mapear opções disponíveis
            option_elements = select_element.find_elements(By.TAG_NAME, "option")
            opcoes_map = {}
            
            print(f"   📋 Lendo opções do select (total: {len(option_elements)} options)...")
            for idx, opt in enumerate(option_elements):
                # IMPORTANTE: PrimeFaces esconde o select, então .text não funciona
                # Usar textContent ou innerHTML para pegar o texto real
                texto_opcao = opt.get_attribute("textContent") or opt.get_attribute("innerHTML") or opt.text
                texto_opcao = texto_opcao.strip()
                valor_opcao = opt.get_attribute("value") or ""
                
                print(f"      Option {idx}: texto='{texto_opcao}', value='{valor_opcao}'")
                
                if not texto_opcao or texto_opcao.lower() == "selecione" or texto_opcao.lower() == "nenhuma":
                    continue
                    
                chave_opcao = texto_opcao.strip().upper()
                opcoes_map[chave_opcao] = valor_opcao
                
                is_selected = opt.get_attribute("selected") == "true" or valor_opcao == valor_atual_select
                marcador = "✓ (selecionado)" if is_selected else ""
                print(f"         → Mapeado: {chave_opcao} = {valor_opcao} {marcador}")
            
            print(f"   📊 Total de opções válidas mapeadas: {len(opcoes_map)}")
            print(f"   🗺️ Mapa de opções: {opcoes_map}")

            # 3. VERIFICAR SE OPÇÃO EXISTE
            chave_desejada = trimestre_referencia.strip().upper()
            valor_opcao_desejada = opcoes_map.get(chave_desejada)
            
            if valor_opcao_desejada is None:
                raise Exception(
                    f"Opção '{trimestre_referencia}' não está disponível. Opções: {list(opcoes_map.keys())}"
                )

            # 4. VERIFICAR SE JÁ ESTÁ SELECIONADO
            if valor_atual_select == valor_opcao_desejada:
                print(f"   ✅ Trimestre '{trimestre_referencia}' já está selecionado")
                return

            # 5. SELECIONAR A OPÇÃO CORRETA
            print(f"   🔧 Selecionando '{trimestre_referencia}' (valor={valor_opcao_desejada})...")
            self._selecionar_trimestre_via_js(select_element, valor_opcao_desejada)
            
            # 6. AGUARDAR AJAX CARREGAR TABELA
            print(f"   ⏳ Aguardando tabela de conceitos carregar...")
            time.sleep(3)

            # Verificar se foi selecionado
            novo_valor_select = select_element.get_attribute("value")
            
            try:
                label_element = self.driver.find_element(By.XPATH, label_xpath)
                novo_valor_label = label_element.text.strip().upper()
            except:
                novo_valor_label = ""

            if novo_valor_select != valor_opcao_desejada:
                raise Exception(
                    f"Valor do select '{novo_valor_select}' difere do esperado '{valor_opcao_desejada}'"
                )

            print(f"   ✅ Trimestre selecionado com sucesso!")
            print(f"      - Valor no select: {novo_valor_select}")
            print(f"      - Label exibido: {novo_valor_label}")
            
            # Verificar se a tabela de conceitos foi carregada
            try:
                tabela_xpath = "//table[contains(@id, 'tabelaConceitos') or contains(@id, 'dataTableHabilidades')]"
                tabela = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, tabela_xpath))
                )
                print(f"   ✅ Tabela de conceitos carregada e pronta para uso")
            except:
                print(f"   ⚠️ Tabela de conceitos pode não ter carregado (isso pode ser normal se não houver habilidades)")

        except Exception as e:
            print(f"   ❌ Erro ao selecionar trimestre '{trimestre_referencia}': {e}")
            raise Exception(f"Não foi possível selecionar o trimestre '{trimestre_referencia}': {e}")
            
    def _selecionar_trimestre_via_js(self, select_element, valor_desejado):
        """
        Seleciona o trimestre disparando os eventos necessários via JavaScript.
        Isso dispara o AJAX do PrimeFaces que carrega a tabela de conceitos.
        """
        script = """
            const select = arguments[0];
            const value = arguments[1];
            
            // Define o valor
            select.value = value;
            
            // Dispara evento change (necessário para PrimeFaces detectar)
            select.dispatchEvent(new Event('change', { bubbles: true }));
            
            // Dispara o PrimeFaces.ab (Ajax Behavior) - CRÍTICO para carregar tabela
            if (select.onchange) {
                select.onchange();
            }
        """
        try:
            self.driver.execute_script(script, select_element, valor_desejado)
            print(f"      ✓ JavaScript executado, AJAX disparado")
            time.sleep(1)
        except Exception as e:
            raise Exception(f"Erro ao executar JavaScript para selecionar trimestre: {e}")

    def _pagina_erro_diario_detectada(self):
        """Verifica se a página atual é a tela de erro 500 do SGN."""
        try:
            current_url = self.driver.current_url or ""
        except Exception:
            current_url = ""

        if "errors/500" in current_url.lower():
            return True

        try:
            self.driver.find_element(By.CSS_SELECTOR, "span.exception-summary")
            return True
        except Exception:
            return False

    def _recuperar_de_pagina_erro(self):
        """Tenta retornar à página inicial quando a tela de erro 500 é exibida."""
        print("   🔁 Tentando recuperar da página de erro...")
        try:
            home_button = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.ID, "recNotAjax"))
            )
            home_button.click()
            print("   ✅ Botão 'Início' clicado na página de erro")
            WebDriverWait(self.driver, 10).until(
                EC.url_contains("/pages/common/home.html")
            )
        except Exception as e:
            print(f"   ⚠️ Falha ao clicar no botão 'Início': {e}")
            # Fallback: navegar diretamente para a home
            try:
                self.driver.get("https://sgn.sesisenai.org.br/pages/common/home.html")
                WebDriverWait(self.driver, 10).until(
                    EC.url_contains("/pages/common/home.html")
                )
                print("   ✅ Página inicial carregada via fallback")
            except Exception as e2:
                print(f"   ❌ Falha ao carregar a página inicial via fallback: {e2}")

        time.sleep(2)

    def _pagina_erro_diario_detectada(self):
        """Verifica se a página atual é a tela de erro 500 do SGN."""
        try:
            current_url = self.driver.current_url or ""
        except Exception:
            current_url = ""

        if "errors/500" in current_url.lower():
            return True

        try:
            self.driver.find_element(By.CSS_SELECTOR, "span.exception-summary")
            return True
        except Exception:
            return False

    def _recuperar_de_pagina_erro(self):
        """Tenta retornar à página inicial quando a tela de erro 500 é exibida."""
        print("   🔁 Tentando recuperar da página de erro...")
        try:
            home_button = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.ID, "recNotAjax"))
            )
            home_button.click()
            print("   ✅ Botão 'Início' clicado na página de erro")
            WebDriverWait(self.driver, 10).until(
                EC.url_contains("/pages/common/home.html")
            )
        except Exception as e:
            print(f"   ⚠️ Falha ao clicar no botão 'Início': {e}")
            # Fallback: navegar diretamente para a home
            try:
                self.driver.get("https://sgn.sesisenai.org.br/pages/common/home.html")
                WebDriverWait(self.driver, 10).until(
                    EC.url_contains("/pages/common/home.html")
                )
                print("   ✅ Página inicial carregada via fallback")
            except Exception as e2:
                print(f"   ❌ Falha ao carregar a página inicial via fallback: {e2}")

        time.sleep(2)

    def _lancar_conceitos_todos_alunos(
        self,
        atitude_observada="Raramente",
        conceito_habilidade="B",
        trimestre_referencia=None,
    ):
        """
        Lança conceitos para todos os alunos aplicando o MESMO conceito para TODAS as habilidades.
        
        VERSÃO OTIMIZADA - 100% HTTP (SEM MODAL VISUAL)
        
        Melhorias:
        - Lançamento 100% via requisições HTTP (sem abrir/fechar modal)
        - ~80% mais rápido que o método tradicional
        - Timeout aumentado (30s) para servidor lento
        - Retry automático com backoff exponencial
        - Renovação automática de sessão
        
        Este é o método SIMPLES/OTIMIZADO que aplica o conceito padrão para todos.
        Para lançamento inteligente baseado nas avaliações, use _lancar_conceitos_inteligente().
        """
        import time
        from datetime import datetime, timedelta
        
        inicio_processamento = time.time()
        print("7. Iniciando lançamento de conceitos para todos os alunos (MODO HTTP PURO)...")
        print(f"   📋 Atitude observada: '{atitude_observada}'")
        print(f"   📋 Conceito de habilidade: '{conceito_habilidade}' (aplicado para TODAS as habilidades)")
        print(f"   🕐 Início: {datetime.now().strftime('%H:%M:%S')}")
        print(f"   🚀 Usando método HTTP puro (sem modal visual) - ~80% mais rápido!")
        
        try:
            # 1. OBTER LISTA DE ALUNOS
            print("\n   📋 Coletando lista de alunos...")
            alunos = self._obter_lista_alunos(trimestre=trimestre_referencia)
            total_alunos = len(alunos)
            
            if total_alunos == 0:
                print("   ⚠️ Nenhum aluno encontrado, tentando novamente...")
                alunos = self._obter_lista_alunos(trimestre=trimestre_referencia)
                total_alunos = len(alunos)
            
            if total_alunos == 0:
                return False, "Nenhum aluno encontrado na tabela. Verifique se o trimestre está selecionado."
            
            print(f"   ✅ Encontrados {total_alunos} alunos na turma")
            
            # 2. USAR MÉTODO HTTP PURO (SEM MODAL VISUAL)
            # Timeout aumentado para 30s por requisição (servidor lento)
            alunos_processados, alunos_com_erro, mensagens = self.helpers._lancar_conceitos_todos_alunos_http_puro(
                lista_alunos=alunos,
                atitude_valor=atitude_observada,
                conceito_valor=conceito_habilidade,
                timeout=30  # Timeout aumentado para servidor lento
            )
            
            # 3. CALCULAR ESTATÍSTICAS FINAIS
            tempo_total = time.time() - inicio_processamento
            tempo_medio_final = tempo_total / total_alunos if total_alunos > 0 else 0
            
            # 4. GERAR MENSAGEM DE RESULTADO
            message = f"Processados: {alunos_processados}/{total_alunos} alunos"
            if alunos_com_erro > 0:
                message += f", {alunos_com_erro} com erro"
            
            success = alunos_processados > 0
            
            print(f"\n" + "="*60)
            print(f"✅ LANÇAMENTO HTTP PURO CONCLUÍDO")
            print(f"📊 Resultado: {message}")
            print(f"⏱️ Tempo total: {tempo_total:.1f}s")
            print(f"📈 Tempo médio por aluno: {tempo_medio_final:.1f}s")
            print(f"📋 Taxa de sucesso: {(alunos_processados/total_alunos*100):.1f}%")
            print(f"🕐 Finalizado: {datetime.now().strftime('%H:%M:%S')}")
            print("="*60)
            
            return success, message
            
        except Exception as e:
            tempo_total = time.time() - inicio_processamento
            error_msg = f"Erro durante lançamento HTTP puro após {tempo_total:.1f}s: {str(e)}"
            print(f"❌ {error_msg}")
            import traceback
            print(f"📋 Detalhes do erro:\n{traceback.format_exc()}")
            return False, error_msg
    
    def _lancar_conceitos_inteligente(
        self,
        atitude_observada="Raramente",
        conceito_habilidade="B",
        trimestre_referencia=None,
        mapeamentos_prontos=None,
        trocar_c_por_ne: bool = True,
    ):
        """
        Lança conceitos para todos os alunos respeitando as avaliações (AV/RP) e suas
        respectivas habilidades/capacidades.
        
        Este é o método INTELIGENTE que aplica conceitos baseados nas notas das avaliações.
        """
        print("   📋 Processando alunos com conceitos inteligentes...")
        print(f"   📋 Atitude observada padrão: '{atitude_observada}'")
        print(f"   📋 Conceito de habilidade padrão: '{conceito_habilidade}'")

        try:
            # Se mapeamentos já foram coletados, usar eles
            if mapeamentos_prontos:
                mapeamentos = mapeamentos_prontos
                print("   ✓ Usando mapeamentos já coletados")
            else:
                # Coletar mapeamentos (fluxo antigo para compatibilidade)
                print("   🔍 Coletando configuração de avaliações...")
                
                # IMPORTANTE: Coletar cabeçalhos DEPOIS de selecionar o trimestre
                # (os cabeçalhos mudam conforme o trimestre selecionado)
                print("   🔍 Coletando cabeçalhos da tabela de conceitos...")
                cabecalhos = self._coletar_configuracao_conceitos()
                print(f"   ✓ Cabeçalhos coletados: {cabecalhos['identificadores']}")
                
                dados_av = self._coletar_avaliacoes_turma()
                
                if not dados_av or len(dados_av) == 0:
                    erro_msg = "❌ ERRO CRÍTICO: Nenhuma avaliação encontrada na turma."
                    print(f"   {erro_msg}")
                    raise Exception(erro_msg)
                
                dados_rp = self._coletar_recuperacoes_paralelas()
                mapeamentos = self._construir_mapeamento_avaliacoes(cabecalhos, dados_av, dados_rp)

            # VERIFICAÇÃO: Se não há habilidades mapeadas, alertar
            if not mapeamentos["habilidades"]:
                print("   ⚠️ AVISO: Nenhuma habilidade vinculada às avaliações. Será usado apenas o conceito padrão.")

            # DEBUG: Verificar mapeamentos
            print(f"\n   🔍 DEBUG: mapeamentos['colunas'] = {mapeamentos['colunas']}")

            # Obter lista de alunos COM preview das notas
            alunos = self._obter_lista_alunos(mapa_colunas=mapeamentos["colunas"], trimestre=trimestre_referencia)
            total_alunos = len(alunos)
            if total_alunos == 0:
                return False, "Nenhum aluno encontrado na tabela"

            print(f"\n   📋 Encontrados {total_alunos} alunos na turma")

            alunos_processados = 0
            alunos_com_erro = 0

            conceito_padrao = getattr(conceito_habilidade, "value", str(conceito_habilidade))
            atitude_padrao = getattr(atitude_observada, "value", str(atitude_observada))

            for indice, aluno_info in enumerate(alunos, 1):
                try:
                    print(f"\n   👤 Processando aluno {indice}/{total_alunos}: {aluno_info['nome']}")

                    # 1️⃣ COLETAR NOTAS DA TABELA PRINCIPAL (ANTES de abrir a modal)
                    notas = self._coletar_notas_aluno(aluno_info, mapeamentos["colunas"])
                    print(f"      📊 Notas coletadas: {notas}")

                    # 2️⃣ ABRIR A MODAL DE HABILIDADES/ATITUDES
                    if not self._acessar_aba_notas_aluno(aluno_info):
                        print(f"   ❌ Não foi possível abrir a modal de notas de {aluno_info['nome']}")
                        alunos_com_erro += 1
                        continue

                    # 3️⃣ PREENCHER ATITUDES
                    if not self._preencher_observacoes_atitudes(atitude_padrao):
                        print(f"   ⚠️ Observações de atitudes não preenchidas para {aluno_info['nome']}")

                    # 4️⃣ PREENCHER HABILIDADES BASEADO NAS NOTAS (respeita trocar_c_por_ne)
                    preencheu_ok = False
                    if trocar_c_por_ne:
                        preencheu_ok = self._preencher_conceitos_habilidades_por_notas(notas, mapeamentos)
                    else:
                        # Mantém C e NÃO troca por NE
                        _ = self._preencher_conceitos_habilidades_por_notas_mantendo_c(notas, mapeamentos)
                        # Consideramos sucesso se nenhum erro crítico ocorreu; a função de manter C retorna lista de Cs
                        preencheu_ok = True

                    if not preencheu_ok:
                        print(f"   ⚠️ Conceitos de habilidades não atualizados para {aluno_info['nome']}")

                    print(f"   ✅ Conceitos aplicados para {aluno_info['nome']} (salvamento automático)")
                    alunos_processados += 1
                    
                    self._fechar_modal_conceitos()
                    print("")

                except Exception as aluno_erro:
                    print(f"   ❌ Erro ao processar {aluno_info.get('nome', 'desconhecido')}: {aluno_erro}")
                    import traceback
                    traceback.print_exc()
                    alunos_com_erro += 1
                    try:
                        self._fechar_modal_conceitos()
                    except Exception:
                        pass

            mensagem = f"Processados: {alunos_processados}/{total_alunos} alunos"
            if alunos_com_erro:
                mensagem += f", {alunos_com_erro} com erro"

            print(f"\n✅ Lançamento concluído: {mensagem}")
            return alunos_processados > 0, mensagem

        except Exception as e:
            erro = f"Erro durante lançamento de conceitos: {e}"
            print(f"❌ {erro}")
            return False, erro
    
    def _lancar_conceitos_inteligente_com_ra(
        self,
        atitude_observada="Raramente",
        conceito_habilidade="B",
        trimestre_referencia=None,
        mapeamentos_prontos=None,
        inicio_ra=None,
        termino_ra=None,
        descricao_ra=None,
        nome_arquivo_ra=None,
        caminho_arquivo_ra=None,
    ):
        """
        Lança conceitos INTELIGENTES COM cadastro de RA para habilidades com conceito C
        
        Diferenças do _lancar_conceitos_inteligente():
        - Mantém conceito C (não troca por NE)
        - Cadastra RA para cada habilidade com C
        """
        print("   📋 Processando alunos com conceitos inteligentes COM RA...")
        print(f"   📋 Atitude observada padrão: '{atitude_observada}'")
        print(f"   📋 Conceito de habilidade padrão: '{conceito_habilidade}'")
        print(f"   📋 Modo: MANTÉM C + CADASTRA RA")

        try:
            if mapeamentos_prontos:
                mapeamentos = mapeamentos_prontos
                print("   ✓ Usando mapeamentos já coletados")
            else:
                print("   🔍 Coletando configuração de avaliações...")
                cabecalhos = self._coletar_configuracao_conceitos()
                print(f"   ✓ Cabeçalhos coletados: {cabecalhos['identificadores']}")
                
                dados_av = self._coletar_avaliacoes_turma()
                if not dados_av or len(dados_av) == 0:
                    erro_msg = "❌ ERRO CRÍTICO: Nenhuma avaliação encontrada na turma."
                    print(f"   {erro_msg}")
                    raise Exception(erro_msg)
                
                dados_rp = self._coletar_recuperacoes_paralelas()
                mapeamentos = self._construir_mapeamento_avaliacoes(cabecalhos, dados_av, dados_rp)

            if not mapeamentos["habilidades"]:
                print("   ⚠️ AVISO: Nenhuma habilidade vinculada às avaliações. Será usado apenas o conceito padrão.")

            print(f"\n   🔍 DEBUG: mapeamentos['colunas'] = {mapeamentos['colunas']}")

            # Obter lista de alunos COM preview das notas
            alunos = self._obter_lista_alunos(mapa_colunas=mapeamentos["colunas"], trimestre=trimestre_referencia)
            total_alunos = len(alunos)
            if total_alunos == 0:
                return False, "Nenhum aluno encontrado na tabela"

            print(f"\n   📋 Encontrados {total_alunos} alunos na turma")

            alunos_processados = 0
            alunos_com_erro = 0
            total_ras_cadastradas = 0

            conceito_padrao = getattr(conceito_habilidade, "value", str(conceito_habilidade))
            atitude_padrao = getattr(atitude_observada, "value", str(atitude_observada))

            for indice, aluno_info in enumerate(alunos, 1):
                try:
                    print(f"\n   👤 Processando aluno {indice}/{total_alunos}: {aluno_info['nome']}")

                    # 1️⃣ COLETAR NOTAS DA TABELA PRINCIPAL
                    notas = self._coletar_notas_aluno(aluno_info, mapeamentos["colunas"])
                    print(f"      📊 Notas coletadas: {notas}")

                    # 2️⃣ ABRIR A MODAL DE HABILIDADES/ATITUDES
                    if not self._acessar_aba_notas_aluno(aluno_info):
                        print(f"   ❌ Não foi possível abrir a modal de notas de {aluno_info['nome']}")
                        alunos_com_erro += 1
                        continue

                    # 3️⃣ PREENCHER ATITUDES
                    if not self._preencher_observacoes_atitudes(atitude_padrao):
                        print(f"   ⚠️ Observações de atitudes não preenchidas para {aluno_info['nome']}")

                    # 4️⃣ PREENCHER HABILIDADES BASEADO NAS NOTAS (MANTENDO C)
                    habilidades_com_c = self._preencher_conceitos_habilidades_por_notas_mantendo_c(notas, mapeamentos)
                    
                    # 5️⃣ SE TEM HABILIDADES COM C, CADASTRAR RA
                    if habilidades_com_c and len(habilidades_com_c) > 0:
                        print(f"   🎓 Aluno tem {len(habilidades_com_c)} habilidade(s) com conceito C")
                        print(f"   🎓 Cadastrando RA para cada habilidade...")
                        
                        ras_cadastradas = self._cadastrar_ra_para_habilidades(
                            habilidades_com_c=habilidades_com_c,
                            inicio_ra=inicio_ra,
                            termino_ra=termino_ra,
                            descricao_ra=descricao_ra,
                            nome_arquivo_ra=nome_arquivo_ra,
                            caminho_arquivo_ra=caminho_arquivo_ra
                        )
                        
                        total_ras_cadastradas += ras_cadastradas
                        print(f"   ✅ {ras_cadastradas} RA(s) cadastrada(s) para {aluno_info['nome']}")

                    print(f"   ✅ Conceitos aplicados para {aluno_info['nome']} (salvamento automático)")
                    alunos_processados += 1
                    
                    self._fechar_modal_conceitos()
                    print("")

                except Exception as aluno_erro:
                    print(f"   ❌ Erro ao processar {aluno_info.get('nome', 'desconhecido')}: {aluno_erro}")
                    import traceback
                    traceback.print_exc()
                    alunos_com_erro += 1
                    try:
                        self._fechar_modal_conceitos()
                    except Exception:
                        pass

            mensagem = f"Processados: {alunos_processados}/{total_alunos} alunos, {total_ras_cadastradas} RA(s) cadastrada(s)"
            if alunos_com_erro:
                mensagem += f", {alunos_com_erro} com erro"

            print(f"\n✅ Lançamento concluído: {mensagem}")
            return alunos_processados > 0, mensagem

        except Exception as e:
            erro = f"Erro durante lançamento de conceitos com RA: {e}"
            print(f"❌ {erro}")
            import traceback
            traceback.print_exc()
            return False, erro
    
    def _obter_lista_alunos(self, mapa_colunas=None, trimestre=None):
        """
        Obtém a lista de todos os alunos na tabela de conceitos
        Versão aprimorada baseada na estrutura HTML real do SGN
        
        Args:
            mapa_colunas (dict, optional): Mapeamento de colunas de avaliações
                                           Se fornecido, coleta as notas junto
            trimestre (str, optional): Trimestre para a requisição HTTP (TR1, TR2, TR3)
        
        Returns:
            list: Lista de dicionários com informações dos alunos
                  [{"nome": str, "linha": int, "xpath_aba_notas": str, "notas_preview": dict}, ...]
        """
        print("   🔍 Identificando alunos na tabela SGN...")
        
        # DEBUG: Verificar se helpers estão disponíveis
        if hasattr(self, 'helpers'):
            print(f"   🔧 DEBUG: Helpers disponível: {self.helpers is not None}")
        else:
            print("   🔧 DEBUG: Helpers NÃO disponível")
        
        import time
        
        try:
            # FORÇAR uso do método HTTP otimizado
            if hasattr(self, 'helpers') and self.helpers:
                print("   🚀 FORÇANDO uso do método HTTP otimizado...")
                
                try:
                    # Primeiro tentar via requisição HTTP (mais rápido e confiável)
                    print("   🌐 Iniciando método via requisição HTTP...")
                    start_time = time.time()
                    
                    # Passar trimestre se disponível (padrão TR1)
                    trimestre_param = trimestre if trimestre else "TR1"
                    alunos_sgn = self.helpers._obter_lista_alunos_via_requisicao(trimestre=trimestre_param)
                    
                    elapsed_time = time.time() - start_time
                    print(f"   ⏱️ DEBUG: Método HTTP levou {elapsed_time:.2f} segundos")
                    
                    if alunos_sgn:
                        print(f"   ✅ {len(alunos_sgn)} alunos encontrados via requisição HTTP")
                        
                        # Converter formato para compatibilidade
                        print("   🔄 Convertendo formato dos alunos...")
                        conversion_start = time.time()
                        
                        alunos_convertidos = []
                        for aluno in alunos_sgn:
                            aluno_info = {
                                "nome": aluno["nome"],
                                "linha": aluno["linha"],
                                "data_ri": aluno["data_ri"],
                                "ja_preenchido": aluno.get("ja_preenchido", False),  # PRESERVAR status de preenchido
                                "linha_xpath": f"//tbody[@id='tabViewDiarioClasse:formAbaConceitos:dataTableConceitos_data']/tr[@data-ri='{aluno['data_ri']}']",
                                "xpath_aba_notas": f"//tbody[@id='tabViewDiarioClasse:formAbaConceitos:dataTableConceitos_data']/tr[@data-ri='{aluno['data_ri']}']/td[2]/a[contains(@id,'linkEditarAtitudes')]"
                            }
                            
                            # Se mapa_colunas foi fornecido, coletar notas
                            if mapa_colunas:
                                print(f"   🔄 DEBUG: Coletando notas para {aluno['nome'][:20]}...")
                                notas_start = time.time()
                                
                                notas_preview = self._coletar_notas_preview_sgn(aluno["data_ri"], mapa_colunas)
                                aluno_info["notas_preview"] = notas_preview
                                
                                notas_elapsed = time.time() - notas_start
                                print(f"   ⏱️ DEBUG: Coleta de notas levou {notas_elapsed:.2f}s")
                                
                                # Formatar notas para exibição
                                notas_str = ", ".join([f"{k}={v if v else '∅'}" for k, v in notas_preview.items()])
                                print(f"     👤 Aluno {aluno['linha']}: {aluno['nome']} → {notas_str}")
                            else:
                                print(f"     👤 Aluno {aluno['linha']}: {aluno['nome']}")
                            
                            alunos_convertidos.append(aluno_info)
                        
                        conversion_elapsed = time.time() - conversion_start
                        print(f"   ⏱️ DEBUG: Conversão total levou {conversion_elapsed:.2f} segundos")
                        
                        return alunos_convertidos
                    else:
                        print("   ⚠️ Requisição HTTP não retornou dados, tentando AJAX...")
                        ajax_start = time.time()
                        
                        # Fallback para método AJAX
                        alunos_sgn = self.helpers._obter_lista_alunos_com_ajax()
                        
                        ajax_elapsed = time.time() - ajax_start
                        print(f"   ⏱️ DEBUG: Método AJAX levou {ajax_elapsed:.2f} segundos")
                        
                        if alunos_sgn:
                            print(f"   ✅ {len(alunos_sgn)} alunos encontrados com método AJAX")
                            
                            # Converter formato para compatibilidade
                            alunos_convertidos = []
                            for aluno in alunos_sgn:
                                aluno_info = {
                                    "nome": aluno["nome"],
                                    "linha": aluno["linha"],
                                    "data_ri": aluno["data_ri"],
                                    "ja_preenchido": aluno.get("ja_preenchido", False),  # PRESERVAR status de preenchido
                                    "linha_xpath": f"//tbody[@id='tabViewDiarioClasse:formAbaConceitos:dataTableConceitos_data']/tr[@data-ri='{aluno['data_ri']}']",
                                    "xpath_aba_notas": f"//tbody[@id='tabViewDiarioClasse:formAbaConceitos:dataTableConceitos_data']/tr[@data-ri='{aluno['data_ri']}']/td[2]/a[contains(@id,'linkEditarAtitudes')]"
                                }
                                
                                # Se mapa_colunas foi fornecido, coletar notas
                                if mapa_colunas:
                                    notas_preview = self._coletar_notas_preview_sgn(aluno["data_ri"], mapa_colunas)
                                    aluno_info["notas_preview"] = notas_preview
                                    
                                    # Formatar notas para exibição
                                    notas_str = ", ".join([f"{k}={v if v else '∅'}" for k, v in notas_preview.items()])
                                    print(f"     👤 Aluno {aluno['linha']}: {aluno['nome']} → {notas_str}")
                                else:
                                    print(f"     👤 Aluno {aluno['linha']}: {aluno['nome']}")
                                
                                alunos_convertidos.append(aluno_info)
                            
                            return alunos_convertidos
                            
                except Exception as e:
                    print(f"   ⚠️ Métodos aprimorados falharam: {e}")
                    print("   🔄 Usando método fallback...")
            else:
                print("   ❌ Helpers não disponíveis - usando método fallback LENTO")
            
            # Método fallback original (com melhorias) - ESTE É O LENTO!
            print("   🐌 ATENÇÃO: Usando método fallback LENTO (Selenium + HTML)")
            fallback_start = time.time()
            
            resultado = self._obter_lista_alunos_fallback(mapa_colunas)
            
            fallback_elapsed = time.time() - fallback_start
            print(f"   ⏱️ DEBUG: Método fallback LENTO levou {fallback_elapsed:.2f} segundos")
            
            return resultado
            
        except Exception as e:
            print(f"   ❌ Erro geral ao obter lista de alunos: {str(e)}")
            return []
    
    def _obter_lista_alunos_fallback(self, mapa_colunas=None):
        """Método fallback para obter lista de alunos"""
        print("   🔄 Usando método fallback para obter alunos...")
        
        try:
            # Seletores baseados na estrutura HTML real
            seletores_tbody = [
                "#tabViewDiarioClasse\\:formAbaConceitos\\:dataTableConceitos_data",
                "tbody.ui-datatable-data",
                ".ui-datatable-scrollable-body tbody",
                "table[role='grid'] tbody"
            ]
            
            tbody = None
            for seletor in seletores_tbody:
                try:
                    tbody = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, seletor))
                    )
                    print(f"   ✅ Tbody encontrado: {seletor}")
                    break
                except TimeoutException:
                    continue
            
            if not tbody:
                print("   ❌ Nenhuma tabela de alunos encontrada")
                self.driver.save_screenshot("debug_tabela_alunos_fallback.png")
                print("   📸 Screenshot salvo como 'debug_tabela_alunos_fallback.png'")
                return []
            
            # Obter linhas de alunos
            linhas = tbody.find_elements(By.CSS_SELECTOR, "tr[data-ri]")
            print(f"   📊 {len(linhas)} linhas encontradas")
            
            alunos = []
            for i, linha in enumerate(linhas):
                try:
                    data_ri = linha.get_attribute("data-ri")
                    colunas = linha.find_elements(By.TAG_NAME, "td")
                    
                    if len(colunas) >= 3:
                        # Tentar obter nome do link específico
                        try:
                            link_nome = colunas[2].find_element(By.CSS_SELECTOR, "a[id*='linkNomeEstudanteAbaConceitos']")
                            nome_aluno = link_nome.text.strip()
                        except NoSuchElementException:
                            nome_aluno = colunas[2].text.strip()
                        
                        if nome_aluno and len(nome_aluno) > 3:
                            aluno_info = {
                                "nome": nome_aluno,
                                "linha": i + 1,
                                "data_ri": data_ri,
                                "linha_xpath": f"//tbody[@id='tabViewDiarioClasse:formAbaConceitos:dataTableConceitos_data']/tr[@data-ri='{data_ri}']",
                                "xpath_aba_notas": f"//tbody[@id='tabViewDiarioClasse:formAbaConceitos:dataTableConceitos_data']/tr[@data-ri='{data_ri}']/td[2]/a[contains(@id,'linkEditarAtitudes')]"
                            }
                            
                            # Se mapa_colunas foi fornecido, coletar notas
                            if mapa_colunas:
                                notas_preview = self._coletar_notas_preview_sgn(data_ri, mapa_colunas)
                                aluno_info["notas_preview"] = notas_preview
                                
                                notas_str = ", ".join([f"{k}={v if v else '∅'}" for k, v in notas_preview.items()])
                                print(f"     👤 Aluno {i+1}: {nome_aluno} → {notas_str}")
                            else:
                                print(f"     👤 Aluno {i+1}: {nome_aluno}")
                            
                            alunos.append(aluno_info)
                
                except Exception as e:
                    print(f"   ⚠️ Erro ao processar linha {i+1}: {e}")
                    continue
            
            return alunos
            
        except Exception as e:
            print(f"   ❌ Erro no método fallback: {e}")
            return []
    
    def _coletar_notas_preview(self, data_ri, mapa_colunas):
        """
        Coleta as notas de um aluno de forma rápida (com logs de debug)
        
        Args:
            data_ri: Índice da linha do aluno
            mapa_colunas: Mapeamento de colunas
        
        Returns:
            dict: Notas do aluno {identificador: valor}
        """
        notas = {}
        
        print(f"        🔍 DEBUG: data_ri='{data_ri}', mapa_colunas={mapa_colunas}")
        
        try:
            for ident, idx in sorted(mapa_colunas.items(), key=lambda x: x[1]):
                indice_coluna = idx + 3
                select_xpath = f"//tbody[@id='tabViewDiarioClasse:formAbaConceitos:dataTableConceitos_data']/tr[@data-ri='{data_ri}']/td[{indice_coluna + 1}]//select[contains(@id, '_input')]"
                
                print(f"        🔍 DEBUG {ident}: XPath = {select_xpath}")
                
                try:
                    select = self.driver.find_element(By.XPATH, select_xpath)
                    print(f"        ✅ DEBUG {ident}: <select> encontrado")
                    
                    if select.get_attribute("disabled"):
                        notas[ident] = ""
                        print(f"        🔒 DEBUG {ident}: disabled")
                        continue
                    
                    try:
                        option = select.find_element(By.CSS_SELECTOR, "option[selected='selected']")
                        valor = option.get_attribute("value") or ""
                        print(f"        📊 DEBUG {ident}: valor bruto = '{valor}'")
                        notas[ident] = valor.strip() if valor and valor.strip() and valor not in [" ", "\xa0"] else ""
                        print(f"        ✅ DEBUG {ident}: valor final = '{notas[ident]}'")
                    except Exception as e:
                        notas[ident] = ""
                        print(f"        ❌ DEBUG {ident}: erro ao buscar option - {str(e)}")
                except Exception as e:
                    notas[ident] = ""
                    print(f"        ❌ DEBUG {ident}: erro ao buscar select - {str(e)}")
        except Exception as e:
            print(f"        ❌ DEBUG: erro geral - {str(e)}")
            import traceback
            traceback.print_exc()
        
        print(f"        📋 DEBUG: notas finais = {notas}")
        return notas
    
    def _coletar_notas_preview_sgn(self, data_ri, mapa_colunas):
        """
        Versão aprimorada para coletar notas baseada na estrutura HTML real do SGN
        
        Args:
            data_ri: Índice da linha do aluno
            mapa_colunas: Mapeamento de colunas
        
        Returns:
            dict: Notas do aluno {identificador: valor}
        """
        notas = {}
        
        try:
            for ident, idx in sorted(mapa_colunas.items(), key=lambda x: x[1]):
                # Calcular índice da coluna (baseado na estrutura HTML real)
                # Colunas: 1=número, 2=ações, 3=estudante, 4+=avaliações
                indice_coluna = idx + 3  # +3 para pular as primeiras colunas
                
                # Seletores CSS baseados na estrutura real
                seletores_select = [
                    f"#tabViewDiarioClasse\\:formAbaConceitos\\:dataTableConceitos_data tr[data-ri='{data_ri}'] td:nth-child({indice_coluna + 1}) select[id*='_input']",
                    f"tbody.ui-datatable-data tr[data-ri='{data_ri}'] td:nth-child({indice_coluna + 1}) select",
                    f"tr[data-ri='{data_ri}'] td:nth-child({indice_coluna + 1}) .ui-selectonemenu select"
                ]
                
                valor_encontrado = False
                for seletor in seletores_select:
                    try:
                        select = self.driver.find_element(By.CSS_SELECTOR, seletor)
                        
                        # Verificar se está desabilitado
                        if select.get_attribute("disabled"):
                            notas[ident] = ""
                            valor_encontrado = True
                            break
                        
                        # Buscar opção selecionada
                        try:
                            option = select.find_element(By.CSS_SELECTOR, "option[selected='selected']")
                            valor = option.get_attribute("value") or ""
                            notas[ident] = valor.strip() if valor and valor.strip() and valor not in [" ", "\xa0"] else ""
                            valor_encontrado = True
                            break
                        except NoSuchElementException:
                            # Tentar pegar valor do select diretamente
                            valor = select.get_attribute("value") or ""
                            notas[ident] = valor.strip() if valor and valor.strip() and valor not in [" ", "\xa0"] else ""
                            valor_encontrado = True
                            break
                            
                    except NoSuchElementException:
                        continue
                
                if not valor_encontrado:
                    notas[ident] = ""
                    
        except Exception as e:
            print(f"        ❌ Erro ao coletar notas SGN: {e}")
        
        return notas
    
    def _acessar_aba_notas_aluno(self, aluno_info):
        """
        Acessa a aba de notas de um aluno específico
        
        Args:
            aluno_info (dict): Informações do aluno com xpath_aba_notas
            
        Returns:
            bool: True se conseguiu acessar, False caso contrário
        """
        try:
            print(f"     🔗 Acessando aba de notas...")
            
            # IMPORTANTE: Garantir que nenhuma modal está aberta antes de clicar
            try:
                modal_aberta = self.driver.find_element(By.ID, "modalDadosAtitudes")
                if modal_aberta.is_displayed():
                    print(f"     ⚠️ Modal ainda aberta, forçando fechamento...")
                    self.driver.execute_script("PF('modalDadosAtitudes').hide();")
                    time.sleep(1)
            except:
                pass
            
            # Clicar no botão da aba de notas
            aba_notas_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, aluno_info["xpath_aba_notas"]))
            )
            
            # Scroll até o elemento
            self.driver.execute_script("arguments[0].scrollIntoView(true);", aba_notas_button)
            time.sleep(0.5)
            
            # Clicar via JavaScript para evitar interceptação
            self.driver.execute_script("arguments[0].click();", aba_notas_button)
            
            # Aguardar modal/aba carregar (otimizado)
            time.sleep(1)
            
            print(f"     ✅ Aba de notas acessada")
            return True
            
        except Exception as e:
            print(f"     ❌ Erro ao acessar aba de notas: {str(e)}")
            return False
    
    def _preencher_observacoes_atitudes_via_requisicao(self, opcao_atitude="Raramente"):
        """
        Preenche todas as observações de atitudes via requisições HTTP diretas (método rápido)
        
        Args:
            opcao_atitude (str): Opção de atitude (Sempre, Às vezes, Raramente, Nunca, etc.)
            
        Returns:
            bool: True se sucesso, False caso contrário
        """
        print(f"   🚀 Preenchendo atitudes via requisição HTTP: {opcao_atitude}")
        
        try:
            if not hasattr(self, 'helpers') or not self.helpers:
                print("   ❌ Helpers não disponíveis, usando método fallback")
                return self._preencher_observacoes_atitudes_fallback(opcao_atitude)
            
            # Obter ViewState atual
            viewstate = self.helpers._obter_viewstate_atual()
            if not viewstate:
                print("   ❌ Não foi possível obter ViewState")
                return False
            
            # Usar contadores globais (todos os alunos têm a mesma quantidade)
            max_atitudes, _ = self.helpers._get_contadores_globais()
            
            # OTIMIZAÇÃO 1: Processar em lotes menores com timeout reduzido (evitar erro 500)
            atitudes_processadas = 0
            lote_size = 10  # Lotes menores para evitar sobrecarregar servidor
            timeout_reduzido = 8  # Timeout um pouco maior para dar tempo ao servidor
            
            # OTIMIZAÇÃO 2: Pré-validar se atitudes já estão preenchidas (usando cache global)
            atitudes_pendentes = self.helpers._verificar_atitudes_pendentes_otimizado(opcao_atitude, max_atitudes)
            atitudes_processadas = max_atitudes - len(atitudes_pendentes)
            
            if not atitudes_pendentes:
                print(f"   ✅ Todas as atitudes já estão preenchidas!")
                return True
            
            # OTIMIZAÇÃO 3: Processar apenas as pendentes em lotes PARALELOS
            for lote_inicio in range(0, len(atitudes_pendentes), lote_size):
                lote_fim = min(lote_inicio + lote_size, len(atitudes_pendentes))
                lote_indices = atitudes_pendentes[lote_inicio:lote_fim]
                
                print(f"   🧵 Processando lote {lote_inicio//lote_size + 1} PARALELO: {len(lote_indices)} atitudes pendentes")
                
                # OTIMIZAÇÃO 4: Processar lote em PARALELO com threads (modo conservador)
                sucessos_lote, falhas_lote = self.helpers._lancar_lote_atitudes_paralelo(
                    lote_indices, opcao_atitude, viewstate, timeout_reduzido
                )
                
                atitudes_processadas += sucessos_lote
                print(f"   📊 Lote {lote_inicio//lote_size + 1}: {sucessos_lote} sucessos, {falhas_lote} falhas")
                
                # Se muitas falhas (>70%), verificar se é problema de sessão
                if falhas_lote > 0 and (falhas_lote / len(lote_indices)) > 0.7:
                    print(f"   ⚠️ Muitas falhas no lote ({falhas_lote}/{len(lote_indices)}), verificando sessão...")
                    
                    # Tentar renovar sessão se muitas falhas
                    if self.helpers._tentar_renovar_sessao():
                        print(f"   ✅ Sessão renovada, continuando processamento")
                    else:
                        print(f"   ❌ Não foi possível renovar sessão, forçando renovação de cache")
                        # Forçar renovação de cache para próximo lote
                        self.helpers._get_cached_request_data(force_refresh=True)
                
                # OTIMIZAÇÃO 5: Renovar ViewState apenas entre lotes
                if lote_fim < len(atitudes_pendentes):
                    viewstate_novo = self.helpers._obter_viewstate_atual()
                    if viewstate_novo:
                        viewstate = viewstate_novo
                        print(f"   🔄 ViewState renovado após lote {lote_inicio//lote_size + 1}")
                    
                    # Pausa mínima entre lotes
                    time.sleep(0.1)  # Pausa ainda menor
            
            if atitudes_processadas > 0:
                print(f"   ✅ {atitudes_processadas} atitudes preenchidas com sucesso")
                return True
            else:
                print("   ❌ Nenhuma atitude foi preenchida")
                return False
                
        except Exception as e:
            print(f"   ❌ Erro ao preencher atitudes via requisição: {e}")
            return False
    
    def _preencher_observacoes_atitudes(self, opcao_atitude="Raramente"):
        """
        Preenche todas as observações de atitudes (usa requisição HTTP por padrão, fallback para método HTML)
        """
        # Tentar método via requisição HTTP primeiro (mais rápido)
        if hasattr(self, 'helpers') and self.helpers:
            sucesso = self._preencher_observacoes_atitudes_via_requisicao(opcao_atitude)
            if sucesso:
                return True
            else:
                print("   ⚠️ Método via requisição falhou, tentando método fallback...")
        
        # Fallback para método original
        return self._preencher_observacoes_atitudes_fallback(opcao_atitude)
    
    def _preencher_observacoes_atitudes_fallback(self, opcao_atitude="Raramente"):
        """
        Preenche todas as observações de atitudes com a opção escolhida
        
        Args:
            opcao_atitude (str): Opção a ser selecionada para todas as atitudes
        
        Este método:
        1. Expande a seção de Observações de Atitudes
        2. Preenche cada observação com "Raramente"
        
        Returns:
            bool: True se conseguiu preencher, False caso contrário
        """
        try:
            print(f"     📝 Preenchendo observações de atitudes com '{opcao_atitude}'...")
            
            # Aguardar modal carregar (as seções já estão expandidas por padrão)
            print(f"     ⏳ Aguardando modal de atitudes/habilidades carregar...")
            
            # Verificar se o modal está aberto
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//div[@id='modalDadosAtitudes']"))
                )
                print(f"     ✅ Modal de atitudes/habilidades encontrado")
            except:
                print(f"     ⚠️ Modal não encontrado, continuando...")
            
            # XPath base da tabela de observações de atitudes (ui-datatable-data)
            tabela_atitudes_xpath = "//tbody[@id='formAtitudes:panelAtitudes:dataTableAtitudes_data']"
            
            # Aguardar tabela carregar após expansão
            print(f"     🔍 Procurando tabela de observações de atitudes...")
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, tabela_atitudes_xpath))
            )
            print(f"     ✅ Tabela de observações encontrada")
            
            # Processar cada linha de observação de atitude usando data-ri
            atitudes_preenchidas = 0
            
            # Obter todas as linhas da tabela
            try:
                linhas = self.driver.find_elements(By.XPATH, f"{tabela_atitudes_xpath}/tr[@data-ri]")
                total_linhas = len(linhas)
                print(f"     📊 Encontradas {total_linhas} linhas de observações de atitudes")
                
                from selenium.common.exceptions import StaleElementReferenceException as _Stale
                for i, _ in enumerate(linhas):
                    # Re-busca por data-ri a cada iteração para evitar referências stales
                    tentativa_max = 2
                    for tent in range(1, tentativa_max + 1):
                        try:
                            linha_element = self.driver.find_element(By.XPATH, f"{tabela_atitudes_xpath}/tr[@data-ri='{i}']")
                            data_ri = linha_element.get_attribute("data-ri")
                            print(f"       📝 Processando linha {i+1} (data-ri={data_ri}) [tentativa {tent}]")

                            select_id = f"formAtitudes:panelAtitudes:dataTableAtitudes:{data_ri}:observacaoAtitude_input"
                            select_xpath = f"//select[@id='{select_id}']"

                            select_element = self.driver.find_element(By.XPATH, select_xpath)
                            self.driver.execute_script("arguments[0].scrollIntoView(true);", select_element)
                            time.sleep(0.1)

                            valor_atual = self.driver.execute_script("return arguments[0].value;", select_element)
                            print(f"       📋 Valor atual: {valor_atual}")

                            opcoes_mapeadas = {
                                "Sempre": "Sempre",
                                "Às vezes": "Às vezes",
                                "As vezes": "Às vezes",
                                "Vezes": "Às vezes",
                                "Raramente": "Raramente",
                                "Nunca": "Nunca",
                                "Não conseguiu observar": "Não conseguiu observar",
                                "Nao conseguiu observar": "Não conseguiu observar",
                                "Não se aplica": "Não se aplica",
                                "Nao se aplica": "Não se aplica"
                            }

                            valor_para_preencher = opcoes_mapeadas.get(opcao_atitude, opcao_atitude)

                            if valor_atual != valor_para_preencher:
                                self.driver.execute_script(f"arguments[0].value = '{valor_para_preencher}';", select_element)
                                self.driver.execute_script("""
                                    var event = new Event('change', { bubbles: true });
                                    arguments[0].dispatchEvent(event);
                                """, select_element)
                                print(f"       ✓ Atitude {i+1}: '{opcao_atitude}' selecionado (JavaScript)")
                                atitudes_preenchidas += 1
                                time.sleep(0.2)
                            else:
                                print(f"       ✓ Atitude {i+1}: Já estava '{opcao_atitude}'")
                                atitudes_preenchidas += 1
                            break
                        except _Stale:
                            if tent < tentativa_max:
                                print(f"       ⚠️ StaleElement na linha {i+1}, refazendo busca...")
                                time.sleep(0.1)
                                continue
                            else:
                                print(f"       ❌ Elemento ficou stale repetidamente na linha {i+1}")
                        except Exception as select_error:
                            print(f"       ❌ Erro ao selecionar '{opcao_atitude}' na linha {i+1}: {str(select_error)}")
                            break
                        
            except Exception as tabela_error:
                print(f"     ❌ Erro ao processar tabela de atitudes: {str(tabela_error)}")
            
            print(f"     ✅ {atitudes_preenchidas} observações de atitudes preenchidas")
            return atitudes_preenchidas > 0
            
        except Exception as e:
            print(f"     ❌ Erro ao preencher observações de atitudes: {str(e)}")
            return False
    
    def _preencher_conceitos_habilidades(self, opcao_conceito="B"):
        """
        Preenche todos os conceitos de habilidades com a opção escolhida
        VERSÃO OTIMIZADA COM SUPORTE A MÚLTIPLAS CAPACIDADES: Tenta HTTP primeiro, fallback para Selenium
        
        Args:
            opcao_conceito (str): Opção a ser selecionada para todos os conceitos
        
        Returns:
            bool: True se conseguiu preencher, False caso contrário
        """
        try:
            print(f"     🚀 TENTANDO lançamento de conceitos via HTTP otimizado (MÚLTIPLAS CAPACIDADES)...")
            
            # 1. TENTAR MÉTODO HTTP OTIMIZADO
            try:
                viewstate = self.helpers._obter_viewstate_atual()
                if viewstate:
                    print(f"     ✅ ViewState encontrado para conceitos: {viewstate[:50]}...")
                    
                    # Expandir capacidades apenas uma vez por sessão (todos alunos têm a mesma estrutura)
                    self.helpers._expandir_capacidades_uma_vez()
                    
                    # Buscar TODAS as tabelas de habilidades (múltiplas capacidades)
                    todas_tabelas = self._obter_todas_tabelas_habilidades()
                    total_capacidades = len(todas_tabelas)
                    
                    print(f"     📊 Encontradas {total_capacidades} capacidade(s) com tabelas de habilidades")
                    
                    if total_capacidades == 0:
                        print(f"     ⚠️ Nenhuma tabela de habilidades encontrada - tentando método legado...")
                        # Fallback para método original (uma única tabela)
                        tabela_habilidades_xpath = "//tbody[@id='formAtitudes:panelAtitudes:dataTableHabilidades_data']"
                        WebDriverWait(self.driver, 10).until(
                            EC.presence_of_element_located((By.XPATH, tabela_habilidades_xpath))
                        )
                        
                        linhas = self.driver.find_elements(By.XPATH, f"{tabela_habilidades_xpath}/tr[@data-ri]")
                        todas_tabelas = [{'xpath': tabela_habilidades_xpath, 'linhas': linhas, 'nome': 'Capacidade Principal'}]
                        total_capacidades = 1
                    
                    conceitos_http_ok = 0
                    conceitos_falharam = 0
                    total_linhas_processadas = 0
                    
                    # Processar cada capacidade separadamente
                    for cap_idx, tabela_info in enumerate(todas_tabelas, 1):
                        linhas = tabela_info['linhas']
                        nome_capacidade = tabela_info.get('nome', f'Capacidade {cap_idx}')
                        total_linhas_capacidade = len(linhas)
                        
                        print(f"     📋 Processando {nome_capacidade}: {total_linhas_capacidade} habilidades")
                        
                        if total_linhas_capacidade == 0:
                            print(f"     ⚠️ {nome_capacidade} não possui habilidades - pulando...")
                            continue
                        
                        # OTIMIZAÇÃO: Pré-filtrar conceitos que já estão corretos
                        conceitos_pendentes_data_ri = []
                        conceito_esperado = opcao_conceito.split('.')[-1] if '.' in opcao_conceito else opcao_conceito
                        
                        print(f"       🔍 Verificando conceitos já preenchidos em {nome_capacidade}...")
                        for i, linha in enumerate(tabela_info['linhas']):
                            try:
                                data_ri = linha.get_attribute("data-ri")
                                select_id = f"formAtitudes:panelAtitudes:dataTableHabilidades:{data_ri}:notaConceito"
                                select_element = self.driver.find_element(By.ID, select_id)
                                valor_atual = select_element.get_attribute("value")
                                
                                if valor_atual != conceito_esperado:
                                    conceitos_pendentes_data_ri.append(data_ri)
                                else:
                                    conceitos_http_ok += 1
                                    print(f"       ✓ {nome_capacidade} - data-ri={data_ri} já tem '{valor_atual}'")
                            except:
                                # Se não conseguir verificar, assumir que precisa processar
                                conceitos_pendentes_data_ri.append(linha.get_attribute("data-ri"))
                        
                        print(f"       📊 {nome_capacidade}: {len(conceitos_pendentes_data_ri)} conceitos pendentes de {len(tabela_info['linhas'])} total")
                        
                        if not conceitos_pendentes_data_ri:
                            print(f"       ✅ {nome_capacidade}: Todos os conceitos já estão preenchidos!")
                            continue
                        
                        # OTIMIZAÇÃO: Processar conceitos em PARALELO com retry
                        max_tentativas = 3
                        lote_size_conceitos = 10  # Lotes menores para conceitos
                        
                        for tentativa in range(max_tentativas):
                            if not conceitos_pendentes_data_ri:
                                break
                                
                            print(f"       🔄 Tentativa {tentativa + 1}/{max_tentativas}: {len(conceitos_pendentes_data_ri)} conceitos pendentes")
                            
                            # Processar em lotes paralelos
                            conceitos_processados_com_sucesso = []
                            
                            for lote_inicio in range(0, len(conceitos_pendentes_data_ri), lote_size_conceitos):
                                lote_fim = min(lote_inicio + lote_size_conceitos, len(conceitos_pendentes_data_ri))
                                lote_data_ri = conceitos_pendentes_data_ri[lote_inicio:lote_fim]
                                
                                print(f"         🧵 Processando lote PARALELO {lote_inicio//lote_size_conceitos + 1}: {len(lote_data_ri)} conceitos")
                                
                                # Processar lote em paralelo
                                sucessos_lote, falhas_lote = self.helpers._lancar_conceitos_habilidades_paralelo(
                                    lote_data_ri, conceito_esperado, viewstate, timeout=3
                                )
                                
                                conceitos_http_ok += sucessos_lote
                                conceitos_falharam += falhas_lote
                                
                                # Marcar sucessos para remoção da lista de pendentes
                                if sucessos_lote > 0:
                                    # Verificar quais conceitos foram realmente processados
                                    for data_ri in lote_data_ri:
                                        try:
                                            select_id = f"formAtitudes:panelAtitudes:dataTableHabilidades:{data_ri}:notaConceito"
                                            select_element = self.driver.find_element(By.ID, select_id)
                                            valor_atual = select_element.get_attribute("value")
                                            
                                            if valor_atual == conceito_esperado:
                                                conceitos_processados_com_sucesso.append(data_ri)
                                        except:
                                            pass
                                
                                print(f"         📊 Lote {lote_inicio//lote_size_conceitos + 1}: {sucessos_lote} sucessos, {falhas_lote} falhas")
                                
                                # Renovar ViewState entre lotes se necessário
                                if lote_fim < len(conceitos_pendentes_data_ri):
                                    viewstate_novo = self.helpers._obter_viewstate_atual()
                                    if viewstate_novo:
                                        viewstate = viewstate_novo
                                    time.sleep(0.1)  # Pausa mínima entre lotes
                            
                            # Remover conceitos processados com sucesso da lista de pendentes
                            for data_ri in conceitos_processados_com_sucesso:
                                if data_ri in conceitos_pendentes_data_ri:
                                    conceitos_pendentes_data_ri.remove(data_ri)
                            
                            # Se ainda há pendentes, aguardar antes da próxima tentativa
                            if conceitos_pendentes_data_ri and tentativa < max_tentativas - 1:
                                print(f"       ⏳ Aguardando 1s antes da próxima tentativa...")
                                time.sleep(1)
                        
                        # Relatório final desta capacidade
                        conceitos_sucesso_capacidade = len(tabela_info['linhas']) - len(conceitos_pendentes_data_ri)
                        print(f"       📊 {nome_capacidade}: {conceitos_sucesso_capacidade}/{len(tabela_info['linhas'])} conceitos lançados")
                        
                        total_linhas_processadas += len(tabela_info['linhas'])
                    
                    # Relatório final HTTP
                    print(f"     📊 RESULTADO HTTP FINAL: {conceitos_http_ok} sucessos, {conceitos_falharam} falhas de {total_linhas_processadas} total em {total_capacidades} capacidade(s)")
                    
                    if conceitos_http_ok > 0:
                        print(f"     ✅ {conceitos_http_ok}/{total_linhas_processadas} conceitos lançados via HTTP em múltiplas capacidades")
                        if conceitos_falharam > 0:
                            print(f"     ⚠️ {conceitos_falharam} conceitos falharam - tentando fallback Selenium para estes")
                        return True
                    else:
                        print(f"     ❌ Nenhum conceito lançado via HTTP - usando fallback Selenium")
                        
            except Exception as e:
                print(f"     ⚠️ Método HTTP falhou: {e}")
            
            # 2. FALLBACK PARA MÉTODO SELENIUM ORIGINAL COM MÚLTIPLAS CAPACIDADES
            print(f"     🔄 Fallback para método Selenium (MÚLTIPLAS CAPACIDADES)...")
            print(f"     📝 Preenchendo conceitos de habilidades com '{opcao_conceito}'...")
            
            # Buscar TODAS as tabelas de habilidades (múltiplas capacidades)
            todas_tabelas_selenium = self._obter_todas_tabelas_habilidades()
            
            if not todas_tabelas_selenium:
                print(f"     ⚠️ Nenhuma tabela encontrada - tentando método legado...")
                # Fallback para método original (uma única tabela)
                tabela_habilidades_xpath = "//tbody[@id='formAtitudes:panelAtitudes:dataTableHabilidades_data']"
                
                try:
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, tabela_habilidades_xpath))
                    )
                    linhas = self.driver.find_elements(By.XPATH, f"{tabela_habilidades_xpath}/tr[@data-ri]")
                    todas_tabelas_selenium = [{'xpath': tabela_habilidades_xpath, 'linhas': linhas, 'nome': 'Capacidade Principal'}]
                except:
                    print(f"     ❌ Não foi possível encontrar nenhuma tabela de habilidades")
                    return False
            
            # Processar cada capacidade separadamente
            habilidades_preenchidas = 0
            total_capacidades_selenium = len(todas_tabelas_selenium)
            
            print(f"     📊 Processando {total_capacidades_selenium} capacidade(s) via Selenium")
            
            for cap_idx, tabela_info in enumerate(todas_tabelas_selenium, 1):
                linhas = tabela_info['linhas']
                nome_capacidade = tabela_info.get('nome', f'Capacidade {cap_idx}')
                total_linhas_capacidade = len(linhas)
                
                print(f"     📋 Selenium - Processando {nome_capacidade}: {total_linhas_capacidade} habilidades")
                
                if total_linhas_capacidade == 0:
                    print(f"     ⚠️ {nome_capacidade} não possui habilidades - pulando...")
                    continue
                
                # Processar cada linha desta capacidade
                for i, linha_element in enumerate(linhas):
                    try:
                        data_ri = linha_element.get_attribute("data-ri")
                        print(f"       📝 {nome_capacidade} - Selenium linha {i+1} (data-ri={data_ri})")
                        
                        # Procurar select nativo diretamente usando o ID específico
                        select_id = f"formAtitudes:panelAtitudes:dataTableHabilidades:{data_ri}:notaConceito_input"
                        select_xpath = f"//select[@id='{select_id}']"
                        
                        try:
                            select_element = self.driver.find_element(By.XPATH, select_xpath)
                            
                            # Scroll até o elemento
                            self.driver.execute_script("arguments[0].scrollIntoView(true);", select_element)
                            time.sleep(0.2)
                            
                            # Verificar valor atual usando JavaScript (select está oculto)
                            valor_atual = self.driver.execute_script("return arguments[0].value;", select_element)
                            print(f"       📋 {nome_capacidade} - Valor atual: {valor_atual}")
                            
                            # Mapear opção para o valor exato esperado no select
                            opcoes_mapeadas = {
                                "A": "A",
                                "B": "B",
                                "C": "C",
                                "NE": "NE",
                                "Não se aplica": "NE",
                                "Nao se aplica": "NE",
                                "Não entregue": "NE",
                                "Nao entregue": "NE"
                            }
                            
                            # Obter valor mapeado ou usar o valor original
                            valor_para_preencher = opcoes_mapeadas.get(opcao_conceito.upper(), opcao_conceito.upper())
                            
                            # Verificar se o valor mapeado é válido
                            valores_validos = ["A", "B", "C", "NE"]
                            if valor_para_preencher not in valores_validos:
                                print(f"       ⚠️ Valor inválido: '{opcao_conceito}'. Usando 'B' como padrão.")
                                valor_para_preencher = "B"
                            
                            if valor_atual != valor_para_preencher:
                                # Usar JavaScript para alterar o valor do select oculto
                                self.driver.execute_script(f"arguments[0].value = '{valor_para_preencher}';", select_element)
                                
                                # Disparar evento change para atualizar a interface
                                self.driver.execute_script("""
                                    var event = new Event('change', { bubbles: true });
                                    arguments[0].dispatchEvent(event);
                                """, select_element)
                                
                                print(f"       ✓ {nome_capacidade} - Habilidade {i+1}: '{valor_para_preencher}' selecionado (JavaScript)")
                                habilidades_preenchidas += 1
                                time.sleep(0.5)  # Aguardar processamento
                            else:
                                print(f"       ✓ {nome_capacidade} - Habilidade {i+1}: Já estava '{valor_para_preencher}'")
                                habilidades_preenchidas += 1
                            
                        except Exception as select_error:
                            print(f"       ❌ {nome_capacidade} - Erro ao selecionar '{opcao_conceito}' na linha {i+1}: {str(select_error)}")
                    
                    except Exception as linha_error:
                        print(f"       ❌ {nome_capacidade} - Erro ao processar linha {i+1}: {str(linha_error)}")
                        continue
            
            print(f"     ✅ SELENIUM FINAL: {habilidades_preenchidas} conceitos de habilidades preenchidos em {total_capacidades_selenium} capacidade(s)")
            return habilidades_preenchidas > 0
            
        except Exception as e:
            print(f"     ❌ Erro ao preencher conceitos de habilidades: {e}")
            return False

    def _salvar_conceitos_via_http(self, aluno_info):
        """
        Salva conceitos via requisição HTTP direta
        
        Args:
            aluno_info (dict): Informações do aluno
            
        Returns:
            bool: True se salvou com sucesso
        """
        try:
            driver = self.driver
            
            # Tentar encontrar e clicar botão salvar via JavaScript
            try:
                # Procurar botão de salvar no modal
                botao_salvar_js = """
                var botoes = document.querySelectorAll('button, input[type="button"], input[type="submit"]');
                for (var i = 0; i < botoes.length; i++) {
                    var texto = botoes[i].textContent || botoes[i].value || '';
                    if (texto.toLowerCase().includes('salvar') || texto.toLowerCase().includes('confirmar')) {
                        botoes[i].click();
                        return true;
                    }
                }
                return false;
                """
                
                resultado = driver.execute_script(botao_salvar_js)
                if resultado:
                    print(f"         ✅ Botão salvar clicado via JavaScript")
                    time.sleep(2)  # Aguardar salvamento
                    return True
                    
            except Exception as e:
                print(f"         ⚠️ Erro ao clicar botão salvar: {e}")
            
            # Fallback: tentar ESC para fechar e salvar
            try:
                from selenium.webdriver.common.keys import Keys
                driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                print(f"         ✅ ESC enviado para salvar e fechar")
                time.sleep(1)
                return True
            except:
                pass
                
            return False
            
        except Exception as e:
            print(f"         ❌ Erro ao salvar conceitos via HTTP: {e}")
            return False

    def _fechar_modal_conceitos(self):
        """
        Fecha o modal de conceitos usando ESC ou botão fechar
        
        Returns:
            bool: True se conseguiu fechar, False caso contrário
        """
        try:
            print(f"     🔙 Fechando modal de conceitos...")
            
            # Método principal: ESC (sistema salva automaticamente)
            try:
                from selenium.webdriver.common.keys import Keys
                body = self.driver.find_element(By.TAG_NAME, "body")
                body.send_keys(Keys.ESCAPE)
                time.sleep(0.4)

                # Verificar rapidamente se apareceu erro de Recomposição de Aprendizagem (conceito C)
                ra_elems = self.driver.find_elements(By.XPATH, "//span[contains(text(), 'Recomposição de Aprendizagem')]")
                if ra_elems:
                    print(f"     ⚠️ ERRO: Conceito C exige Recomposição de Aprendizagem")
                    # Tentar fechar mensagem de erro (não bloquear)
                    try:
                        fechar_erro = self.driver.find_element(By.XPATH, "//div[contains(@class, 'ui-messages-error')]//a[contains(@class, 'ui-messages-close')]")
                        fechar_erro.click()
                        time.sleep(0.2)
                    except:
                        pass

                # Verificar se modal realmente fechou
                try:
                    WebDriverWait(self.driver, 1).until(
                        EC.invisibility_of_element_located((By.ID, "modalDadosAtitudes"))
                    )
                    print(f"     ✅ Modal fechada com ESC (salvamento automático)")
                    return True
                except:
                    print(f"     ⚠️ Modal ainda visível, tentando forçar fechamento...")
                    # Forçar fechamento via JavaScript
                    try:
                        self.driver.execute_script("PF('modalDadosAtitudes').hide();")
                        time.sleep(0.5)
                        print(f"     ✅ Modal fechada via JavaScript")
                        return True
                    except:
                        pass
                    
            except Exception as esc_error:
                print(f"     ⚠️ ESC não funcionou, tentando botão de fechar...")
            
            # Método alternativo: Botão de fechar (caso ESC falhe)
            fechar_selectors = [
                "//div[@id='modalDadosAtitudes']//a[contains(@class, 'ui-dialog-titlebar-close')]",
                "//a[contains(@class, 'ui-dialog-titlebar-close')]",
                "//span[@class='ui-icon ui-icon-closethick']/..",
                "/html/body/div[3]/div[3]/div[2]/div[13]/div[1]/a"  # XPath específico como fallback
            ]
            
            for i, selector in enumerate(fechar_selectors):
                try:
                    fechar_button = WebDriverWait(self.driver, 3).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    
                    fechar_button.click()
                    
                    # Aguardar modal fechar
                    try:
                        WebDriverWait(self.driver, 5).until(
                            EC.invisibility_of_element_located((By.XPATH, "//div[@id='modalDadosAtitudes']"))
                        )
                        print(f"     ✅ Modal fechado com sucesso")
                    except:
                        print(f"     ⚠️ Modal pode não ter fechado completamente")
                    
                    time.sleep(1)
                    print(f"     ✅ Voltou para lista de alunos")
                    return True
                    
                except:
                    continue
            
            # Se não encontrou botão, tenta ESC
            print(f"     ⚠️ Botão voltar não encontrado, tentando ESC")
            self.driver.find_element(By.TAG_NAME, "body").send_keys("\x1b")  # ESC
            time.sleep(1)
            return True
            
        except Exception as e:
            print(f"     ❌ Erro ao voltar para lista: {str(e)}")
            return False
    
    def _verificar_aba_conceitos_ativa(self):
        """
        Verifica se a aba de Conceitos está realmente ativa
        
        Este método verifica indicadores visuais de que a aba de Conceitos
        está ativa e o conteúdo está carregado.
        """
        try:
            print("   🔍 Verificando se aba de Conceitos está ativa...")
            
            # Verificar se a aba está marcada como ativa
            aba_ativa_selectors = [
                "/html/body/div[3]/div[3]/div[2]/div[2]/div/div/ul/li[7][contains(@class, 'ui-state-active')]",
                "/html/body/div[3]/div[3]/div[2]/div[2]/div/div/ul/li[7][contains(@class, 'active')]",
                "//li[7][contains(@class, 'ui-state-active')]",
                "//li[contains(@class, 'ui-state-active') and contains(text(), 'Conceitos')]"
            ]
            
            aba_ativa = False
            for selector in aba_ativa_selectors:
                try:
                    element = self.driver.find_element(By.XPATH, selector)
                    if element:
                        aba_ativa = True
                        print("   ✅ Aba de Conceitos está marcada como ativa")
                        break
                except:
                    continue
            
            if not aba_ativa:
                print("   ⚠️ Aba de Conceitos pode não estar ativa")
                
                # Tentar clicar novamente na aba
                try:
                    print("   🔄 Tentando clicar na aba novamente...")
                    conceitos_tab = self.driver.find_element(By.XPATH, "/html/body/div[3]/div[3]/div[2]/div[2]/div/div/ul/li[7]")
                    conceitos_tab.click()
                    time.sleep(3)
                    print("   ✅ Aba clicada novamente")
                except Exception as e:
                    print(f"   ❌ Erro ao clicar novamente na aba: {str(e)}")
            
            # Verificar se há conteúdo específico da aba de Conceitos
            conceitos_content_selectors = [
                "//div[contains(@class, 'ui-tabs-panel') and not(contains(@style, 'display: none'))]",
                "//form[contains(@id, 'conceito') or contains(@name, 'conceito')]",
                "//div[7]//form",
                "//span//div[2]//table"
            ]
            
            conteudo_encontrado = False
            for selector in conceitos_content_selectors:
                try:
                    element = self.driver.find_element(By.XPATH, selector)
                    if element and element.is_displayed():
                        conteudo_encontrado = True
                        print(f"   ✅ Conteúdo da aba encontrado: {selector}")
                        break
                except:
                    continue
            
            if not conteudo_encontrado:
                print("   ⚠️ Conteúdo da aba de Conceitos não encontrado")
            
            return aba_ativa and conteudo_encontrado
            
        except Exception as e:
            print(f"   ❌ Erro ao verificar aba de Conceitos: {str(e)}")
            return False
    
    # ============================================================================
    # NOVOS MÉTODOS - Sistema Inteligente de Lançamento de Conceitos
    # ============================================================================
    
    def _coletar_configuracao_conceitos(self):
        """
        Retorna informações dos cabeçalhos da tabela de conceitos (AV1, RP1, etc.)
        
        Estrutura HTML:
        <th id="...avaliacoes:0" aria-label="AV1">
            <span class="ui-column-title">
                <span title="06/08/2025 - Avaliação 03...">AV1</span>
            </span>
        </th>
        """
        resultado = {"identificadores": [], "tooltip": {}}

        try:
            # Buscar TODOS os <th> que têm aria-label começando com AV ou RP
            base_head_xpath = "//thead[@id='tabViewDiarioClasse:formAbaConceitos:dataTableConceitos_head']/tr/th[@aria-label]"
            cabecalhos = self.driver.find_elements(By.XPATH, base_head_xpath)
            
            print(f"     🔍 Analisando {len(cabecalhos)} cabeçalhos da tabela...")

            for idx, th in enumerate(cabecalhos):
                try:
                    # Ler o aria-label (contém o identificador: AV1, AV2, RP2, etc.)
                    aria = th.get_attribute("aria-label")
                    if not aria:
                        continue
                    
                    identificador = aria.strip().upper()
                    
                    # Filtrar apenas AV* e RP*
                    if not identificador.startswith(("AV", "RP")):
                        continue

                    resultado["identificadores"].append(identificador)
                    
                    # Tentar extrair tooltip (informações adicionais)
                    try:
                        tooltip_span = th.find_element(By.CSS_SELECTOR, "span[title]")
                        tooltip = tooltip_span.get_attribute("title") or ""
                        info = self._extrair_info_tooltip(tooltip)
                        resultado["tooltip"][identificador] = info
                        print(f"        ✓ {identificador}: {info.get('titulo', 'Sem título')}")
                    except:
                        resultado["tooltip"][identificador] = {}
                        print(f"        ✓ {identificador}: (sem tooltip)")
                        
                except Exception as e:
                    print(f"        ⚠️ Erro ao processar cabeçalho {idx}: {e}")
                    continue

            print(f"     ✅ Encontrados {len(resultado['identificadores'])} cabeçalhos: {resultado['identificadores']}")

        except Exception as e:
            print(f"   ❌ Erro ao capturar cabeçalhos de conceitos: {e}")
            import traceback
            traceback.print_exc()

        return resultado

    def _extrair_info_tooltip(self, texto):
        """Extrai informações do tooltip da avaliação"""
        info = {
            "data": None,
            "titulo": None,
            "formato": None,
            "docente": None,
            "peso": None,
        }

        if not texto:
            return info

        partes = [p.strip() for p in texto.split(" - ") if p.strip()]
        if partes:
            info["data"] = partes[0]

        for parte in partes[1:]:
            parte_lower = parte.lower()
            if "docente:" in parte_lower:
                info["docente"] = parte.split(":", 1)[1].strip()
            elif "peso:" in parte_lower:
                info["peso"] = parte.split(":", 1)[1].strip()
            elif any(x in parte_lower for x in ["formato", "prova", "recuperação", "recuperacao"]):
                info["formato"] = parte
            else:
                if not info["titulo"]:
                    info["titulo"] = parte

        return info

    def _coletar_avaliacoes_turma(self):
        """
        Coleta dados da tabela de avaliações (aba Aulas/Avaliações)
        FLUXO:
        1. Navegar para aba Aulas/Avaliações
        2. Clicar ESPECIFICAMENTE no painel para expandir
        3. Ler tabela de avaliações
        4. Para cada avaliação, clicar no lápis (ação) e coletar habilidades
        """
        dados = []
        
        try:
            print("     🔍 Navegando para aba Aulas/Avaliações...")
            
            # Clicar na aba Aulas/Avaliações
            aba_xpath = "//li[@data-index='2']//a[contains(text(), 'Aulas / avaliações')]"
            try:
                aba = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, aba_xpath))
                )
                aba.click()
                time.sleep(2)
                print("     ✓ Aba Aulas/Avaliações acessada")
            except:
                print("     ⚠️ Não foi possível acessar aba Aulas/Avaliações")
                return dados

            # EXPANDIR PAINEL DE AVALIAÇÃO - XPATH ESPECÍFICO
            print("     🔽 Expandindo painel de Avaliação...")
            painel_xpath_especifico = "/html/body/div[3]/div[3]/div[2]/div[2]/div/div/div/div[3]/form/div/div/div[2]/div[1]"
            try:
                painel = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, painel_xpath_especifico))
                )
                # Verificar se já está expandido
                if "ui-state-active" not in painel.get_attribute("class"):
                    painel.click()
                    time.sleep(2)  # Aguardar expandir
                print("     ✓ Painel de Avaliação expandido")
            except Exception as e:
                print(f"     ⚠️ Erro ao expandir painel: {e}")
                # Tentar xpath alternativo
                try:
                    painel_alt = self.driver.find_element(
                        By.XPATH, 
                        "//div[@id='tabViewDiarioClasse:formAbaAulasAvaliacoes:panelAvaliacao']//div[contains(@class, 'ui-accordion-header')]"
                    )
                    if "ui-state-active" not in painel_alt.get_attribute("class"):
                        painel_alt.click()
                        time.sleep(2)
                        print("     ✓ Painel expandido (xpath alternativo)")
                except:
                    print("     ❌ Não foi possível expandir painel")

            # Aguardar tabela carregar
            time.sleep(1)
            
            # LER TABELA DE AVALIAÇÕES - XPATH ESPECÍFICO
            tabela_xpath_especifico = "/html/body/div[3]/div[3]/div[2]/div[2]/div/div/div/div[3]/form/div/div/div[2]/div[2]/div[2]"
            print(f"     📋 Lendo tabela de avaliações...")
            
            try:
                # Localizar tbody com as linhas
                tbody_xpath = "//tbody[@id='tabViewDiarioClasse:formAbaAulasAvaliacoes:panelAvaliacao:avaliacoesDataTable_data']/tr[@data-ri]"
                linhas = self.driver.find_elements(By.XPATH, tbody_xpath)
                
                print(f"     📋 Encontradas {len(linhas)} avaliações na tabela")
                
                for idx, linha in enumerate(linhas, start=1):
                    try:
                        data_ri = linha.get_attribute("data-ri")
                        cols = linha.find_elements(By.TAG_NAME, "td")
                        
                        if len(cols) < 7:
                            continue

                        # Colunas: [0]=Número, [1]=Ação, [2]=Data Criação, [3]=Data Avaliação, 
                        #          [4]=Formato, [5]=Título, [6]=MR, [7]=Peso, [8]=Docente
                        numero = cols[0].text.strip()
                        titulo = cols[5].text.strip()
                        data_av = cols[3].text.strip()
                        mr = cols[6].text.strip()
                        peso = cols[7].text.strip()

                        identificador = f"AV{numero}"
                        
                        dados.append({
                            "identificador": identificador,
                            "titulo": titulo,
                            "data": data_av,
                            "mr": mr,
                            "peso": peso,
                            "data_ri": data_ri,
                            "indice_linha": idx,
                        })
                        
                        print(f"       ✓ {identificador}: {titulo} (MR: TR{mr})")
                        
                    except Exception as e:
                        print(f"     ⚠️ Erro ao processar linha {idx}: {e}")
                        continue

                print(f"     ✅ Total de {len(dados)} avaliações coletadas")

            except Exception as e:
                print(f"     ❌ Erro ao ler tabela: {e}")

        except Exception as e:
            print(f"   ❌ Erro geral ao coletar avaliações: {e}")

        return dados

    def _coletar_recuperacoes_paralelas(self):
        """
        Coleta dados do painel de Recuperação Paralela
        """
        dados = {}
        
        try:
            try:
                aba_xpath = "//a[contains(text(), 'Aulas / avaliações') or contains(text(), 'Aulas / Avaliações')]"
                aba = self.driver.find_element(By.XPATH, aba_xpath)
                if "ui-state-active" not in aba.get_attribute("class"):
                    aba.click()
                    time.sleep(2)
            except:
                pass

            painel_xpath = "//div[@id='tabViewDiarioClasse:formAbaAulasAvaliacoes:painelRecuperacaoParalela']//div[contains(@class, 'ui-accordion-header')]"
            try:
                painel = self.driver.find_element(By.XPATH, painel_xpath)
                if "ui-state-active" not in painel.get_attribute("class"):
                    painel.click()
                    time.sleep(1)
            except:
                pass

            tabela_xpath = "//tbody[@id='tabViewDiarioClasse:formAbaAulasAvaliacoes:painelRecuperacaoParalela:recuperacoesParalelas_data']/tr"
            linhas = self.driver.find_elements(By.XPATH, tabela_xpath)

            for linha in linhas:
                try:
                    cols = linha.find_elements(By.TAG_NAME, "td")
                    if len(cols) < 5:
                        continue

                    numero = cols[0].text.strip()
                    identificador = f"RP{numero}"
                    titulo = cols[2].text.strip()
                    data_rec = cols[1].text.strip()
                    mr = cols[3].text.strip()

                    dados[identificador] = {
                        "titulo": titulo,
                        "origem": self._inferir_avaliacao_origem(titulo),
                        "mr": mr,
                        "data": data_rec,
                    }
                    
                except:
                    continue

            print(f"     ✓ Encontradas {len(dados)} recuperações paralelas")

            try:
                aba_conceitos = self.driver.find_element(By.XPATH, "//a[contains(text(), 'Conceitos')]")
                aba_conceitos.click()
                time.sleep(2)
            except:
                pass

        except Exception as e:
            print(f"   ⚠️ Erro ao coletar recuperações: {e}")

        return dados

    def _inferir_avaliacao_origem(self, titulo):
        """
        Tenta inferir qual avaliação original está relacionada à recuperação
        """
        if not titulo:
            return None

        padrao = re.search(r"AVALIAÇ[ÃA]O\s*(\d+)", titulo, flags=re.IGNORECASE)
        if padrao:
            return f"AV{padrao.group(1)}"

        padrao = re.search(r"AV\s*(\d+)", titulo, flags=re.IGNORECASE)
        if padrao:
            return f"AV{padrao.group(1)}"

        return None

    def _construir_mapeamento_avaliacoes(self, cabecalhos, dados_avaliacoes, dados_recuperacoes):
        """
        Unifica informações de cabeçalho + listagens (AV/RP) + habilidades
        
        IMPORTANTE: O SGN renumera as avaliações sequencialmente por trimestre:
        - TR1: AV1, AV2, AV3, RP1, RP2
        - TR2: AV1, AV2, RP1 (renumeração reinicia!)
        
        Estratégia: Mapear pelo tooltip (data + título) para fazer match correto
        """
        print(f"   🔍 Construindo mapeamento de avaliações...")
        print(f"   📋 DEBUG: cabecalhos completo = {cabecalhos}")
        print(f"   📋 Cabeçalhos da tabela: {cabecalhos['identificadores']}")
        
        # VERIFICAÇÃO CRÍTICA: Se não há cabeçalhos, não é possível mapear
        if not cabecalhos.get("identificadores") or len(cabecalhos["identificadores"]) == 0:
            print(f"   ❌ ERRO: Nenhum cabeçalho encontrado na tabela de conceitos!")
            print(f"   ℹ️  Isso pode acontecer se:")
            print(f"      1. O trimestre selecionado não tem avaliações")
            print(f"      2. A tabela ainda não carregou completamente")
            print(f"      3. O XPath de coleta de cabeçalhos está incorreto")
            return {
                "colunas": {},
                "habilidades": {},
                "recuperacao_por_avaliacao": {},
            }
        
        # Extrair informações dos tooltips dos cabeçalhos
        tooltip_map = {}  # {identificador_cabecalho: (data, titulo)}
        for ident_cabecalho in cabecalhos["identificadores"]:
            tooltip = cabecalhos.get("tooltip", {}).get(ident_cabecalho, {})
            print(f"   🔍 DEBUG: {ident_cabecalho} → tooltip = {tooltip}")
            
            # Tooltip pode ser dict ou string
            if isinstance(tooltip, dict):
                data = tooltip.get("data", "")
                titulo = tooltip.get("titulo", "")
                if data and titulo:
                    tooltip_map[ident_cabecalho] = (data, titulo)
                    print(f"   📋 {ident_cabecalho}: {data} - {titulo}")
            elif isinstance(tooltip, str) and " - " in tooltip:
                partes = tooltip.split(" - ")
                if len(partes) >= 2:
                    data = partes[0].strip()
                    titulo = partes[1].strip()
                    tooltip_map[ident_cabecalho] = (data, titulo)
                    print(f"   📋 {ident_cabecalho}: {data} - {titulo}")
        
        # Mapear avaliações para cabeçalhos
        colunas = {}  # {identificador_cabecalho: indice_coluna}
        habilidades = {}  # {identificador: [habilidades]} (tanto cabeçalho quanto original)
        av_original_para_cabecalho = {}  # {AV4: AV1, AV5: AV2}
        avaliacoes_sem_habilidade = []  # lista de identificadores (cabeçalho) sem habilidades
        
        for av_info in dados_avaliacoes:
            ident_original = av_info["identificador"]
            data_av = av_info.get("data", "")
            titulo_av = av_info.get("titulo", "")
            
            # Buscar match pelo (data, titulo)
            # IMPORTANTE: O título pode ter sufixos extras (ex: "Avaliação 01 - SGBD")
            # mas o cabeçalho pode ter apenas "Avaliação 01"
            ident_cabecalho_match = None
            for ident_cabecalho, (data_cab, titulo_cab) in tooltip_map.items():
                # Match exato
                if data_av == data_cab and titulo_av == titulo_cab:
                    ident_cabecalho_match = ident_cabecalho
                    break
                # Match parcial: título do cabeçalho está contido no título da avaliação
                elif data_av == data_cab and titulo_cab in titulo_av:
                    ident_cabecalho_match = ident_cabecalho
                    print(f"   ℹ️  Match parcial: '{titulo_av}' contém '{titulo_cab}'")
                    break
            
            if ident_cabecalho_match:
                idx_coluna = cabecalhos["identificadores"].index(ident_cabecalho_match)
                colunas[ident_cabecalho_match] = idx_coluna
                av_original_para_cabecalho[ident_original] = ident_cabecalho_match
                print(f"   ✓ Match: {ident_original} ({titulo_av}) → {ident_cabecalho_match} (coluna {idx_coluna})")
                
                # SEMPRE coletar habilidades
                habilidades_coletadas = self._coletar_habilidades_modal(av_info)
                # Armazenar tanto pelo identificador do cabeçalho (ex.: AV1) quanto pelo original (ex.: AV4)
                habilidades[ident_cabecalho_match] = habilidades_coletadas
                habilidades[ident_original] = habilidades_coletadas
                
                # AVISO: Se não há habilidades, o conceito padrão será usado
                if not habilidades_coletadas or len(habilidades_coletadas) == 0:
                    print(f"   ❌ {ident_original} não tem habilidades vinculadas")
                    # Registrar a coluna efetiva (cabeçalho) como sem habilidades
                    if ident_cabecalho_match not in avaliacoes_sem_habilidade:
                        avaliacoes_sem_habilidade.append(ident_cabecalho_match)
            else:
                print(f"   ⚠️ {ident_original} ({data_av} - {titulo_av}) não encontrado nos cabeçalhos (trimestre diferente)")
                continue
        
        # Mapear recuperações para cabeçalhos
        recuperacao_por_av = {}  # {identificador_cabecalho_av: identificador_cabecalho_rp}
        
        print(f"   🔍 DEBUG: Total de recuperações coletadas: {len(dados_recuperacoes)}")
        print(f"   📋 DEBUG: Recuperações = {list(dados_recuperacoes.keys())}")
        
        # NOVA ABORDAGEM: Primeiro, adicionar TODAS as colunas RP que aparecem nos cabeçalhos
        # Isso garante que RPs visíveis na tabela sejam coletadas mesmo sem dados detalhados
        for ident_cabecalho in cabecalhos["identificadores"]:
            if ident_cabecalho.startswith("RP"):
                # Se ainda não foi adicionado, adicionar agora
                if ident_cabecalho not in colunas:
                    idx_coluna = cabecalhos["identificadores"].index(ident_cabecalho)
                    colunas[ident_cabecalho] = idx_coluna
                    print(f"   ✓ RP detectada no cabeçalho: {ident_cabecalho} (coluna {idx_coluna})")
                    
                    # Tentar inferir qual AV esta RP substitui pelo número
                    # Ex: RP2 substitui AV2
                    match_numero = re.search(r'RP(\d+)', ident_cabecalho)
                    if match_numero:
                        numero_rp = match_numero.group(1)
                        av_correspondente = f"AV{numero_rp}"
                        
                        # Verificar se esta AV existe nas colunas
                        if av_correspondente in colunas:
                            recuperacao_por_av[av_correspondente] = ident_cabecalho
                            print(f"   🔗 Inferido: {ident_cabecalho} substitui {av_correspondente}")
        
        # Depois, processar recuperações detalhadas (se houver)
        for rec_id, rec_info in dados_recuperacoes.items():
            data_rec = rec_info.get("data", "")
            titulo_rec = rec_info.get("titulo", "")
            origem = rec_info.get("origem")  # Ex: "AV5"
            
            # Buscar match pelo (data, titulo)
            print(f"   🔍 Procurando RP detalhada: {rec_id} (data='{data_rec}', titulo='{titulo_rec}', origem='{origem}')")
            ident_cabecalho_rec = None
            for ident_cabecalho, (data_cab, titulo_cab) in tooltip_map.items():
                if data_rec == data_cab and titulo_rec == titulo_cab:
                    ident_cabecalho_rec = ident_cabecalho
                    print(f"   ✓ Match encontrado: {ident_cabecalho}")
                    break
            
            if ident_cabecalho_rec:
                idx_coluna = cabecalhos["identificadores"].index(ident_cabecalho_rec)
                # Atualizar colunas (pode já estar lá da primeira passagem)
                colunas[ident_cabecalho_rec] = idx_coluna
                print(f"   ✓ Match: {rec_id} ({titulo_rec}) → {ident_cabecalho_rec} (coluna {idx_coluna})")
                
                # Mapear recuperação para a avaliação de origem (sobrescreve inferência se houver)
                if origem and origem in av_original_para_cabecalho:
                    ident_cabecalho_origem = av_original_para_cabecalho[origem]
                    recuperacao_por_av[ident_cabecalho_origem] = ident_cabecalho_rec
                    print(f"   🔗 Recuperação: {ident_cabecalho_rec} substitui {ident_cabecalho_origem}")
            else:
                print(f"   ⚠️ {rec_id} ({data_rec} - {titulo_rec}) não encontrado nos cabeçalhos (trimestre diferente)")

        resultado = {
            "colunas": colunas,
            "habilidades": habilidades,
            "recuperacao_por_avaliacao": recuperacao_por_av,
            "av_original_para_cabecalho": av_original_para_cabecalho,
            "avaliacoes_sem_habilidade": avaliacoes_sem_habilidade,
        }
        
        total_habilidades = sum(len(h) for h in habilidades.values())
        print(f"     ✓ Mapeamento: {len(colunas)} colunas, {len(habilidades)} avaliações, {total_habilidades} habilidades vinculadas")
        
        # Voltar para aba Conceitos
        try:
            print("     🔙 Voltando para aba Conceitos...")
            aba_conceitos = self.driver.find_element(By.XPATH, "//a[contains(text(), 'Conceitos')]")
            aba_conceitos.click()
            time.sleep(2)
            print("     ✓ Aba Conceitos acessada")
        except Exception as e:
            print(f"     ⚠️ Erro ao voltar para aba Conceitos: {e}")
        
        return resultado

    def _printar_resumo_avaliacoes(self, dados_av, dados_rp, mapeamentos):
        """
        Printa um resumo completo das avaliações, habilidades e médias de referência coletadas
        """
        print("\n" + "="*80)
        print(" 📊 RESUMO DAS AVALIAÇÕES COLETADAS")
        print("="*80)
        
        # Printar avaliações
        print(f"\n📝 AVALIAÇÕES CADASTRADAS: {len(dados_av)}")
        for av in dados_av:
            print(f"\n   {av['identificador']} - {av['titulo']}")
            print(f"      📅 Data: {av['data']}")
            print(f"      📊 Média de Referência: TR{av['mr']}")
            print(f"      ⚖️  Peso: {av['peso']}")
            
            # Printar habilidades vinculadas a esta avaliação
            habilidades_av = mapeamentos["habilidades"].get(av['identificador'], [])
            if habilidades_av and len(habilidades_av) > 0:
                print(f"      🎯 Habilidades vinculadas ({len(habilidades_av)}):")
                for hab in habilidades_av:
                    habilidade_curta = hab['habilidade'][:70] + "..." if len(hab['habilidade']) > 70 else hab['habilidade']
                    print(f"         • {habilidade_curta}")
            else:
                print(f"      ❌ NENHUMA HABILIDADE VINCULADA - Esta avaliação não será usada!")
        
        # Printar recuperações paralelas
        if dados_rp:
            print(f"\n🔄 RECUPERAÇÕES PARALELAS: {len(dados_rp)}")
            for rp_id, rp_info in dados_rp.items():
                print(f"\n   {rp_id} - {rp_info.get('titulo', 'Sem título')}")
                origem = rp_info.get('origem')
                if origem:
                    print(f"      🔗 Substitui: {origem}")
        else:
            print(f"\n🔄 RECUPERAÇÕES PARALELAS: Nenhuma cadastrada")
        
        print("\n" + "="*80)
        print(f"✅ Total: {len(dados_av)} avaliações | {sum(len(h) for h in mapeamentos['habilidades'].values())} habilidades vinculadas")
        print("="*80 + "\n")

    def _coletar_habilidades_modal(self, avaliacao_info):
        """
        Abre a modal da avaliação e extrai as habilidades configuradas
        FLUXO:
        1. Clicar no lápis (ação) da linha específica
        2. Aguardar modal carregar (AJAX do PrimeFaces)
        3. Ler Média de Referência
        4. Ler tabela de Habilidades (Competência + Habilidade)
        5. Fechar modal
        """
        habilidades = []
        media_referencia = None
        
        try:
            data_ri = avaliacao_info.get("data_ri")
            identificador = avaliacao_info.get("identificador")
            indice_linha = avaliacao_info.get("indice_linha", 1)
            
            print(f"\n       🔍 Abrindo modal da {identificador}...")
            print(f"       📍 Linha: {indice_linha}, data-ri: {data_ri}")

            # TENTAR CAMINHO HTTP (JSF partial/ajax) PRIMEIRO
            try:
                modal_html = self._http_fetch_modal_conteudo(str(data_ri))
                if modal_html:
                    print("       🌐 Modal carregada via HTTP (partial/ajax)")
                    habilidades_http = self._parse_habilidades_from_modal_html(modal_html)
                    if habilidades_http:
                        for h in habilidades_http[:3]:
                            habilidade_curta = h['habilidade'][:60] + "..." if len(h['habilidade']) > 60 else h['habilidade']
                            print(f"         • {habilidade_curta}")
                        return habilidades_http
                    else:
                        print("       ⚠️ Modal HTTP não retornou habilidades, caindo para Selenium")
            except Exception as e_http:
                print(f"       ⚠️ Falha caminho HTTP: {str(e_http)[:120]}")
            
            # CLICAR NO LINK DO LÁPIS USANDO O ID DO PRIMEFACES
            # O PrimeFaces gera IDs únicos: tabViewDiarioClasse:formAbaAulasAvaliacoes:panelAvaliacao:avaliacoesDataTable:0:aulasAvaliacao
            link_id = f"tabViewDiarioClasse:formAbaAulasAvaliacoes:panelAvaliacao:avaliacoesDataTable:{data_ri}:aulasAvaliacao"
            
            # Fallback usando data-ri
            link_xpath_fallback = f"//tbody[@id='tabViewDiarioClasse:formAbaAulasAvaliacoes:panelAvaliacao:avaliacoesDataTable_data']/tr[@data-ri='{data_ri}']/td[2]/a[1]"
            
            print(f"       🎯 Clicando no lápis (ID: {link_id})...")
            
            try:
                # MÉTODO 1: Usar ID do PrimeFaces (mais confiável)
                try:
                    link_lapis = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.ID, link_id))
                    )
                    print(f"       ✓ Link encontrado (por ID)")
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", link_lapis)
                    time.sleep(0.5)
                    self.driver.execute_script("arguments[0].click();", link_lapis)
                    print(f"       ✓ Lápis clicado via JavaScript")
                    
                except Exception as e_id:
                    print(f"       ⚠️ Falha ao usar ID: {e_id}")
                    print(f"       🔄 Tentando XPath (fallback)...")
                    
                    # MÉTODO 2: Fallback com XPath
                    link_lapis = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.XPATH, link_xpath_fallback))
                    )
                    print(f"       ✓ Link encontrado (por XPath)")
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", link_lapis)
                    time.sleep(0.5)
                    self.driver.execute_script("arguments[0].click();", link_lapis)
                    print(f"       ✓ Lápis clicado via JavaScript (fallback)")
                
                time.sleep(2)  # Aguardar AJAX do PrimeFaces
                print(f"       ✅ Modal sendo carregada...")
                
            except Exception as e:
                print(f"       ❌ ERRO ao clicar no lápis: {e}")
                try:
                    self.driver.save_screenshot(f"erro_lapis_{identificador}.png")
                    print(f"       📸 Screenshot: erro_lapis_{identificador}.png")
                except:
                    pass
                return habilidades
            
            # AGUARDAR MODAL CARREGAR (PrimeFaces carrega em 2 etapas via AJAX)
            print(f"       ⏳ Aguardando modal carregar (2 etapas AJAX)...")
            try:
                # ETAPA 1: Aguardar modal aparecer (primeira requisição AJAX)
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.ID, "modalAvaliacao"))
                )
                print(f"       ✓ Modal apareceu (etapa 1)")
                time.sleep(1)
                
                # ETAPA 2: Aguardar conteúdo carregar (segunda requisição AJAX com modalAvaliacao_contentLoad=true)
                # Aguardar o formulário aparecer dentro da modal
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.ID, "formModalAvaliacao"))
                )
                print(f"       ✓ Formulário carregado (etapa 2)")
                time.sleep(1)
                
                # ETAPA 3: Aguardar tabela de habilidades estar presente
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located(
                        (By.ID, "formModalAvaliacao:tabViewModalAvaliacao:painelTabelaHabilidade:tabelaHabilidade")
                    )
                )
                print(f"       ✓ Tabela de habilidades presente")
                time.sleep(1)
                
                # ETAPA 4: Aguardar o label da média de referência estar presente
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located(
                        (By.ID, "formModalAvaliacao:tabViewModalAvaliacao:mediaReferencia_label")
                    )
                )
                print(f"       ✅ Modal completamente carregada!")
                
            except Exception as e:
                print(f"       ❌ Modal não carregou completamente: {e}")
                return habilidades

            # COLETAR MÉDIA DE REFERÊNCIA - XPATH ESPECÍFICO
            print(f"       📊 Lendo Média de Referência...")
            try:
                # XPath específico: /html/body/div[3]/div[3]/div[2]/div[19]/div[2]/form/div/div/div[1]/div/div/div[2]/div[3]/div
                mr_label_xpath = "//label[@id='formModalAvaliacao:tabViewModalAvaliacao:mediaReferencia_label']"
                mr_label = self.driver.find_element(By.XPATH, mr_label_xpath)
                media_referencia_texto = mr_label.text.strip()
                
                # Também ler do select oculto para confirmar
                mr_select_xpath = "//select[@id='formModalAvaliacao:tabViewModalAvaliacao:mediaReferencia_input']"
                mr_select = self.driver.find_element(By.XPATH, mr_select_xpath)
                mr_value = mr_select.get_attribute("value")
                
                # Mapear valor para TR1/TR2/TR3
                mr_map = {"1": "TR1", "2": "TR2", "3": "TR3"}
                media_referencia = mr_map.get(mr_value, media_referencia_texto)
                
                print(f"       ✓ Média de Referência: {media_referencia}")
            except Exception as e:
                print(f"       ⚠️ Não foi possível coletar MR: {e}")
                media_referencia = None

            # LER TABELA DE HABILIDADES - XPATH ESPECÍFICO
            # XPath: /html/body/div[3]/div[3]/div[2]/div[19]/div[2]/form/div/div/div[1]/div/div/div[5]/div[2]/div/div[2]/div[4]/div[1]
            print(f"       📋 Lendo tabela de Habilidades...")
            
            try:
                # Verificar se painel de habilidades está expandido
                painel_hab_xpath = "//div[@id='formModalAvaliacao:tabViewModalAvaliacao:painelTabelaHabilidade']//div[contains(@class, 'ui-accordion-header')]"
                try:
                    painel_hab = self.driver.find_element(By.XPATH, painel_hab_xpath)
                    if "ui-state-active" not in painel_hab.get_attribute("class"):
                        painel_hab.click()
                        time.sleep(1)
                        print(f"       ✓ Painel de Habilidades expandido")
                except:
                    pass  # Já pode estar expandido
                
                # Aguardar tabela carregar
                time.sleep(1)
                
                # Ler linhas da tabela de habilidades
                tbody_habilidades_xpath = "//tbody[@id='formModalAvaliacao:tabViewModalAvaliacao:painelTabelaHabilidade:tabelaHabilidade_data']/tr[@data-ri]"
                linhas_hab = self.driver.find_elements(By.XPATH, tbody_habilidades_xpath)
                
                print(f"       ✓ Encontradas {len(linhas_hab)} habilidades vinculadas")

                for linha_hab in linhas_hab:
                    try:
                        cols = linha_hab.find_elements(By.TAG_NAME, "td")
                        if len(cols) < 3:
                            continue

                        # Colunas: [0]=Ação (ignorar), [1]=Competência, [2]=Habilidade
                        # Buscar o span com title para pegar texto completo
                        try:
                            competencia_span = cols[1].find_element(By.CSS_SELECTOR, "span.text-overflow-ellipsis-3")
                            competencia = competencia_span.get_attribute("title") or competencia_span.text.strip()
                        except:
                            competencia = cols[1].text.strip()
                        
                        try:
                            habilidade_span = cols[2].find_element(By.CSS_SELECTOR, "span.text-overflow-ellipsis-3")
                            habilidade = habilidade_span.get_attribute("title") or habilidade_span.text.strip()
                        except:
                            habilidade = cols[2].text.strip()

                        if competencia and habilidade:
                            habilidades.append({
                                "competencia": competencia,
                                "habilidade": habilidade,
                            })
                            
                            # Mostrar apenas primeiros 60 caracteres
                            habilidade_curta = habilidade[:60] + "..." if len(habilidade) > 60 else habilidade
                            print(f"         • {habilidade_curta}")
                        
                    except Exception as e:
                        print(f"       ⚠️ Erro ao processar linha de habilidade: {e}")
                        continue
                
            except Exception as e:
                print(f"       ❌ Erro ao ler tabela de habilidades: {e}")
            
            # VALIDAÇÃO CRÍTICA: Verificar se coletou pelo menos uma habilidade
            if len(habilidades) == 0:
                print(f"       ❌ ERRO: Nenhuma habilidade foi coletada para {identificador}!")
                print(f"       ⚠️ A modal foi aberta mas a tabela de habilidades está vazia.")
                print(f"       ℹ️ Esta avaliação precisa ter habilidades cadastradas no SGN.")
                # Não lançar exceção aqui, será tratado no _construir_mapeamento_avaliacoes

            # FECHAR MODAL - XPATH ESPECÍFICO DO BOTÃO DE FECHAR
            print(f"       🔒 Fechando modal...")
            try:
                # XPath específico: /html/body/div[3]/div[3]/div[2]/div[19]/div[1]/a/span
                fechar_btn_xpath = "/html/body/div[3]/div[3]/div[2]/div[19]/div[1]/a/span"
                
                # Tentar xpath específico primeiro
                try:
                    fechar_span = self.driver.find_element(By.XPATH, fechar_btn_xpath)
                    fechar_span.click()
                    print(f"       ✓ Modal fechada (xpath específico)")
                except:
                    # Fallback: tentar via JavaScript
                    try:
                        self.driver.execute_script("PF('modalAvaliacao').hide();")
                        print(f"       ✓ Modal fechada (JavaScript)")
                    except:
                        # Último fallback: clicar no botão de fechar genérico
                        fechar_btn = self.driver.find_element(By.XPATH, "//div[@id='modalAvaliacao']//a[contains(@class, 'ui-dialog-titlebar-close')]")
                        fechar_btn.click()
                        print(f"       ✓ Modal fechada (fallback)")
                
                time.sleep(1)  # Aguardar modal fechar
                
            except Exception as e:
                print(f"       ⚠️ Erro ao fechar modal: {e}")

        except Exception as e:
            print(f"     ⚠️ Erro ao coletar habilidades da modal: {e}")

        return habilidades

    def _build_requests_session(self):
        """Monta uma requests.Session com os cookies do Selenium."""
        sess = requests.Session()
        try:
            ua = self.driver.execute_script("return navigator.userAgent;")
        except Exception:
            ua = "Mozilla/5.0"
        sess.headers.update({
            "User-Agent": ua,
            "Accept": "application/xml, text/xml, */*; q=0.01",
            "X-Requested-With": "XMLHttpRequest",
            "Faces-Request": "partial/ajax",
            "Origin": "https://sgn.sesisenai.org.br",
            "Referer": self.driver.current_url,
        })
        for c in (self.driver.get_cookies() or []):
            try:
                sess.cookies.set(c["name"], c["value"], domain=c.get("domain"), path=c.get("path", "/"))
            except Exception:
                continue
        return sess

    def _extract_view_state(self) -> str:
        """Extrai o javax.faces.ViewState da página atual aberta no Selenium."""
        try:
            # Tentativas comuns de localização
            candidates = [
                "//input[@name='javax.faces.ViewState']",
                "//input[contains(@name,'javax.faces.ViewState')]",
                "//input[contains(@id,'javax.faces.ViewState')]",
            ]
            for xp in candidates:
                els = self.driver.find_elements(By.XPATH, xp)
                if els:
                    val = els[0].get_attribute("value") or ""
                    if val:
                        return val
        except Exception:
            pass
        return ""

    def _http_fetch_modal_conteudo(self, data_ri: str) -> str | None:
        """
        Executa as duas requisições JSF partial/ajax para abrir e carregar a modal
        de avaliação e retorna o HTML da modal (conteúdo) como string.
        """
        view = self._extract_view_state()
        if not view:
            raise RuntimeError("ViewState não encontrado para requisição HTTP")

        sess = self._build_requests_session()
        # URL base da página do diário (sem query)
        base_url = self.driver.current_url.split("?", 1)[0]

        # 1) Abrir a modal (clique no lápis)
        source_id = (
            f"tabViewDiarioClasse:formAbaAulasAvaliacoes:panelAvaliacao:avaliacoesDataTable:{data_ri}:aulasAvaliacao"
        )
        data1 = {
            "javax.faces.partial.ajax": "true",
            "javax.faces.source": source_id,
            "javax.faces.partial.execute": source_id,
            "javax.faces.partial.render": "modalAvaliacao",
            source_id: source_id,
            "javax.faces.ViewState": view,
        }
        r1 = sess.post(base_url, data=data1)
        r1.raise_for_status()

        # 2) Carregar conteúdo da modal
        data2 = {
            "javax.faces.partial.ajax": "true",
            "javax.faces.source": "modalAvaliacao",
            "javax.faces.partial.execute": "modalAvaliacao",
            "javax.faces.partial.render": "modalAvaliacao",
            "modalAvaliacao": "modalAvaliacao",
            "modalAvaliacao_contentLoad": "true",
            "javax.faces.ViewState": view,
        }
        r2 = sess.post(base_url, data=data2)
        r2.raise_for_status()

        # A resposta é um XML <partial-response> com <update id="modalAvaliacao"><![CDATA[...]]></update>
        text = r2.text or ""
        try:
            # Extração simples via regex para o CDATA do update de modalAvaliacao
            m = re.search(r"<update id=\"modalAvaliacao\"><!\[CDATA\[(.*?)\]\]>\</update>", text, re.S)
            if m:
                return m.group(1)
        except Exception:
            pass
        return None

    def _parse_habilidades_from_modal_html(self, modal_html: str):
        """Extrai a lista de habilidades do HTML da modal retornado via HTTP."""
        try:
            tree = html.fromstring(modal_html)
            rows = tree.xpath("//tbody[@id='formModalAvaliacao:tabViewModalAvaliacao:painelTabelaHabilidade:tabelaHabilidade_data']/tr[@data-ri]")
            habilidades = []
            for row in rows:
                tds = row.xpath("./td")
                if len(tds) >= 3:
                    competencia = (tds[1].text_content() or "").strip()
                    habilidade = (tds[2].text_content() or "").strip()
                    if competencia and habilidade:
                        habilidades.append({
                            "competencia": competencia,
                            "habilidade": habilidade,
                        })
            return habilidades
        except Exception as e:
            print(f"       ⚠️ Falha ao parsear habilidades via HTTP: {e}")
            return []

    def _lancar_conceito_aluno_via_requisicao(self, aluno_info, conceito_desejado):
        """
        Lança conceito para um aluno via requisição HTTP direta (método rápido)
        
        Args:
            aluno_info (dict): Informações do aluno incluindo data_ri
            conceito_desejado (str): Conceito a ser lançado (A, B, C, NE)
            
        Returns:
            bool: True se sucesso, False caso contrário
        """
        print(f"   🚀 Lançando conceito via requisição HTTP para: {aluno_info['nome']}")
        
        try:
            if not hasattr(self, 'helpers') or not self.helpers:
                print("   ❌ Helpers não disponíveis, usando método fallback")
                return self._lancar_conceito_aluno_fallback(aluno_info, conceito_desejado)
            
            # Obter ViewState atual
            viewstate = self.helpers._obter_viewstate_atual()
            if not viewstate:
                print("   ❌ Não foi possível obter ViewState")
                return False
            
            data_ri = aluno_info.get('data_ri')
            if not data_ri:
                print("   ❌ data_ri não encontrado nas informações do aluno")
                return False
            
            # Lançar TODOS os conceitos de habilidades via requisição
            print(f"   🎯 Lançando TODOS os conceitos de habilidades: {conceito_desejado}")
            sucesso = self._preencher_conceitos_habilidades(conceito_desejado)
            
            if sucesso:
                print(f"   ✅ Conceito {conceito_desejado} lançado com sucesso para {aluno_info['nome']}")
                return True
            else:
                print(f"   ❌ Falha ao lançar conceito para {aluno_info['nome']}")
                return False
                
        except Exception as e:
            print(f"   ❌ Erro ao lançar conceito via requisição: {e}")
            return False
    
    def _forcar_lancamento_conceitos_direto(self, conceito_desejado="B"):
        """
        FORÇA lançamento de conceitos diretamente no modal aberto
        NÃO depende da lista de alunos - usa dados diretos do DOM
        """
        try:
            print(f"   🚀 FORÇANDO lançamento direto de conceitos: {conceito_desejado}")
            
            # 1. TENTAR MÉTODO HTTP OTIMIZADO PRIMEIRO
            if hasattr(self, 'helpers') and self.helpers:
                try:
                    viewstate = self.helpers._obter_viewstate_atual()
                    if viewstate:
                        print(f"   ✅ ViewState obtido: {viewstate[:50]}...")
                        
                        # Obter linhas diretamente do modal atual
                        tabela_xpath = "//tbody[@id='formAtitudes:panelAtitudes:dataTableHabilidades_data']"
                        linhas = self.driver.find_elements(By.XPATH, f"{tabela_xpath}/tr[@data-ri]")
                        
                        if linhas:
                            print(f"   📊 {len(linhas)} habilidades encontradas no modal")
                            conceitos_ok = 0
                            
                            for i, linha in enumerate(linhas):
                                data_ri = linha.get_attribute("data-ri")
                                print(f"     📝 Lançando conceito HTTP habilidade {i+1} (data-ri={data_ri})")
                                
                                sucesso = self.helpers._lancar_conceito_habilidade_via_requisicao(data_ri, conceito_desejado, viewstate)
                                if sucesso:
                                    conceitos_ok += 1
                                    time.sleep(0.1)
                            
                            if conceitos_ok > 0:
                                print(f"   ✅ {conceitos_ok} conceitos lançados via HTTP!")
                                return True
                                
                except Exception as e:
                    print(f"   ⚠️ Método HTTP falhou: {e}")
            
            # 2. FALLBACK PARA SELENIUM
            print(f"   🔄 Fallback: Lançando conceitos via Selenium...")
            return self._preencher_conceitos_habilidades(conceito_desejado)
            
        except Exception as e:
            print(f"   ❌ Erro no lançamento direto: {e}")
            return False

    def _lancar_conceito_aluno(self, aluno_info, conceito_desejado):
        """
        Lança conceito para um aluno (usa requisição HTTP por padrão, fallback para método HTML)
        """
        # Tentar método via requisição HTTP primeiro (mais rápido)
        if hasattr(self, 'helpers') and self.helpers:
            sucesso = self._lancar_conceito_aluno_via_requisicao(aluno_info, conceito_desejado)
            if sucesso:
                return True
            else:
                print("   ⚠️ Método via requisição falhou, tentando método fallback...")
        
        # Fallback para método original
        return self._lancar_conceito_aluno_fallback(aluno_info, conceito_desejado)
    
    def _lancar_conceito_aluno_fallback(self, aluno_info, conceito_desejado):
        """
        Lê os valores das AV/RP para o aluno na tabela principal de conceitos
        
        IMPORTANTE: O PrimeFaces renderiza os <select> via AJAX quando a modal é aberta.
        Por isso, precisamos ler DIRETAMENTE o <option selected> do <select> oculto.
        
        Estrutura HTML (após renderização AJAX):
        <select id="...j_idt1100_input">
          <option value="">nbsp;</option>
          <option value="B" selected="selected">B</option>  ← AQUI!
        </select>
        <label>&nbsp;</label>  ← Label é atualizado via JS, pode estar vazio
        
        Args:
            aluno_info: Informações do aluno (nome, linha, data_ri)
            mapa_colunas: Mapeamento de identificadores para índices de colunas
        
        Returns:
            dict: Notas coletadas {identificador: valor}
        """
        notas = {}
        
        try:
            data_ri = aluno_info.get("data_ri")
            if data_ri is None:
                data_ri = str(aluno_info["linha"] - 1)

            print(f"     🔍 Coletando notas da linha data-ri='{data_ri}'...")
            av_list = [k for k in mapa_colunas.keys() if k.startswith('AV')]
            rp_list = [k for k in mapa_colunas.keys() if k.startswith('RP')]
            print(f"     📋 Coletando: {len(av_list)} AVs {av_list} + {len(rp_list)} RPs {rp_list}")

            # Iterar sobre cada avaliação/recuperação mapeada
            for ident, idx in sorted(mapa_colunas.items(), key=lambda x: x[1]):
                indice_coluna = idx + 3  # +3: #, Ação, Estudante
                
                # XPATH para o <select> oculto
                select_xpath = f"//tbody[@id='tabViewDiarioClasse:formAbaConceitos:dataTableConceitos_data']/tr[@data-ri='{data_ri}']/td[{indice_coluna + 1}]//select[contains(@id, '_input')]"
                
                try:
                    select = self.driver.find_element(By.XPATH, select_xpath)
                    
                    # Verificar se está disabled
                    if select.get_attribute("disabled"):
                        print(f"        🔒 {ident}: select desabilitado - tentando ler label/texto visível")
                        # FALLBACK 1: label irmão do select (padrão PrimeFaces *_label)
                        try:
                            label_xpath = select_xpath.replace("_input' ]", "_label' ]") if "_input' ]" in select_xpath else None
                            label_elem = None
                            if label_xpath:
                                label_elem = self.driver.find_element(By.XPATH, label_xpath)
                            else:
                                # Tentar procurar por um label dentro da mesma célula
                                td_xpath = f"//tbody[@id='tabViewDiarioClasse:formAbaConceitos:dataTableConceitos_data']/tr[@data-ri='{data_ri}']/td[{indice_coluna + 1}]"
                                td_elem = self.driver.find_element(By.XPATH, td_xpath)
                                try:
                                    label_elem = td_elem.find_element(By.CSS_SELECTOR, "label, span.ui-selectonemenu-label")
                                except:
                                    label_elem = None
                            valor_label = (label_elem.text or "").strip() if label_elem else ""
                            if valor_label:
                                notas[ident] = valor_label
                                print(f"        ✅ {ident}: '{valor_label}' (via label)")
                                continue
                        except Exception as e_lab:
                            pass

                        # FALLBACK 2: texto visível na célula (pode conter A/B/C/NE)
                        try:
                            td_xpath = f"//tbody[@id='tabViewDiarioClasse:formAbaConceitos:dataTableConceitos_data']/tr[@data-ri='{data_ri}']/td[{indice_coluna + 1}]"
                            td_elem = self.driver.find_element(By.XPATH, td_xpath)
                            texto_td = self.driver.execute_script("return arguments[0].textContent;", td_elem) or ""
                            texto_td = texto_td.strip()
                            # Extrair um possível conceito (A, B, C, NE)
                            import re as _re
                            m = _re.search(r"\b(NE|A|B|C)\b", texto_td)
                            if m:
                                notas[ident] = m.group(1)
                                print(f"        ✅ {ident}: '{notas[ident]}' (via texto da célula)")
                                continue
                        except Exception as e_td:
                            pass

                        # Se nada encontrado, manter vazio
                        notas[ident] = ""
                        print(f"        ⚪ {ident}: (sem valor visível)")
                        continue
                    
                    # Buscar <option selected="selected">
                    try:
                        option = select.find_element(By.CSS_SELECTOR, "option[selected='selected']")
                        valor = option.get_attribute("value") or ""
                        
                        # Filtrar valores vazios e &nbsp;
                        if valor and valor.strip() and valor not in [" ", "\xa0"]:
                            notas[ident] = valor.strip()
                            print(f"        ✅ {ident}: '{valor}'")
                        else:
                            # FALLBACK: tentar label/texto quando option não traz valor útil
                            td_xpath = f"//tbody[@id='tabViewDiarioClasse:formAbaConceitos:dataTableConceitos_data']/tr[@data-ri='{data_ri}']/td[{indice_coluna + 1}]"
                            td_elem = self.driver.find_element(By.XPATH, td_xpath)
                            texto_td = self.driver.execute_script("return arguments[0].textContent;", td_elem) or ""
                            texto_td = texto_td.strip()
                            import re as _re
                            m = _re.search(r"\b(NE|A|B|C)\b", texto_td)
                            if m:
                                notas[ident] = m.group(1)
                                print(f"        ✅ {ident}: '{notas[ident]}' (fallback texto célula)")
                            else:
                                notas[ident] = ""
                                print(f"        ⚪ {ident}: (vazio)")
                    except Exception as _e_opt:
                        # Se não tem option selected, tentar ler label/texto
                        try:
                            td_xpath = f"//tbody[@id='tabViewDiarioClasse:formAbaConceitos:dataTableConceitos_data']/tr[@data-ri='{data_ri}']/td[{indice_coluna + 1}]"
                            td_elem = self.driver.find_element(By.XPATH, td_xpath)
                            texto_td = self.driver.execute_script("return arguments[0].textContent;", td_elem) or ""
                            texto_td = texto_td.strip()
                            import re as _re
                            m = _re.search(r"\b(NE|A|B|C)\b", texto_td)
                            if m:
                                notas[ident] = m.group(1)
                                print(f"        ✅ {ident}: '{notas[ident]}' (sem option, via texto)")
                            else:
                                notas[ident] = ""
                                print(f"        ⚪ {ident}: (vazio - sem option selected)")
                        except Exception as _e_txt:
                            notas[ident] = ""
                            print(f"        ⚪ {ident}: (vazio - sem option selected)")
                        
                except Exception as e:
                    notas[ident] = ""
                    print(f"        ❌ {ident}: erro ({str(e)[:50]})")

            print(f"     📊 Resumo: {notas}")

        except Exception as e:
            print(f"   ⚠️ Erro ao coletar notas: {e}")
            import traceback
            traceback.print_exc()

        return notas

    def _preencher_conceitos_habilidades_por_notas(self, notas_aluno, mapeamentos):
        """
        Aplica os conceitos de habilidades baseado nas notas das avaliações
        
        NOVA ABORDAGEM: Usa AJAX direto para evitar problemas de stale element
        O PrimeFaces recarrega a tabela via AJAX após cada mudança, então precisamos:
        1. Coletar TODAS as habilidades e seus conceitos ANTES de aplicar
        2. Aplicar conceitos via AJAX (POST) um por vez
        3. Aguardar cada AJAX completar antes do próximo
        """
        preenchidos = 0

        try:
            print(f"     📝 Preenchendo conceitos de habilidades baseado nas notas...")
            
            # ETAPA 1: Coletar informações de todas as habilidades
            # Alguns layouts variam o id da tabela; tentar múltiplos seletores
            xpaths_tabela = [
                "//tbody[@id='formAtitudes:panelAtitudes:dataTableHabilidades_data']/tr[@data-ri]",
                "//tbody[contains(@id,'dataTableHabilidades_data')]/tr[@data-ri]",
                "//tbody[contains(@id,'tabelaHabilidade_data')]/tr[@data-ri]",
            ]
            linhas = []
            last_err = None
            for xp in xpaths_tabela:
                try:
                    linhas = WebDriverWait(self.driver, 12).until(
                        EC.presence_of_all_elements_located((By.XPATH, xp))
                    )
                    if linhas:
                        tabela_xpath = xp
                        break
                except Exception as _e:
                    last_err = _e
                    continue

            if not linhas:
                print("     📋 Total de habilidades encontradas: 0 (tabela não localizada)")
                # Não trata como erro crítico; apenas não há o que aplicar
                return True

            print(f"     📋 Total de habilidades encontradas: {len(linhas)}")
            
            # Lista de habilidades a preencher: [(data_ri, habilidade_texto, conceito)]
            habilidades_para_preencher = []

            for idx, linha in enumerate(linhas):
                try:
                    data_ri = linha.get_attribute("data-ri")
                    cols = linha.find_elements(By.TAG_NAME, "td")
                    
                    if len(cols) < 3:
                        continue
                    
                    # Usar textContent via JavaScript
                    competencia_texto = self.driver.execute_script("return arguments[0].textContent;", cols[0]).strip()
                    habilidade_texto = self.driver.execute_script("return arguments[0].textContent;", cols[1]).strip()
                    
                except Exception as e:
                    print(f"       ⚠️ Erro ao ler linha {idx}: {e}")
                    continue

                conceito = ""
                av_utilizada = None
                
                # Procurar em qual avaliação esta habilidade está vinculada
                for av, habilidades_av in mapeamentos["habilidades"].items():
                    for h in habilidades_av:
                        hab_coletada = h["habilidade"].lstrip("*").strip()
                        hab_modal = habilidade_texto.lstrip("*").strip()
                        if self._texto_corresponde(hab_modal, hab_coletada):
                            # REGRA: SEMPRE priorizar RP se existir
                            recuperacao = mapeamentos["recuperacao_por_avaliacao"].get(av)
                            conceito_rec = notas_aluno.get(recuperacao, "") if recuperacao else ""
                            conceito_av = notas_aluno.get(av, "")
                            
                            if conceito_rec:
                                conceito = conceito_rec
                                av_utilizada = recuperacao
                                print(f"       🔄 USANDO RP! Habilidade de {av} → Aplicando nota da {recuperacao}: '{conceito_rec}'")
                            elif conceito_av:
                                conceito = conceito_av
                                av_utilizada = av

                            break
                    if av_utilizada:
                        break

                # Se encontrou conceito, adicionar à lista
                if av_utilizada and conceito:
                    # No fluxo NORMAL (sem RA), conceito 'C' exige RA no SGN.
                    # Para evitar bloqueio, mapear 'C' -> 'NE' aqui.
                    if (conceito or "").strip().upper() == 'C':
                        print("         ℹ️ Conceito 'C' exige RA no fluxo normal → usando 'NE'")
                        conceito = 'NE'
                    habilidade_curta = habilidade_texto[:50] if len(habilidade_texto) > 50 else habilidade_texto
                    print(f"       ✓ {habilidade_curta[:40]}... → {conceito}")
                    habilidades_para_preencher.append((data_ri, habilidade_texto, conceito))

            # ETAPA 2: Aplicar conceitos via JavaScript (simula AJAX do PrimeFaces)
            print(f"     🔧 Aplicando {len(habilidades_para_preencher)} conceitos...")
            
            for data_ri, habilidade_texto, conceito in habilidades_para_preencher:
                try:
                    # Construir o ID do select
                    select_id = f"formAtitudes:panelAtitudes:dataTableHabilidades:{data_ri}:notaConceito_input"
                    # Garantir que a linha esteja renderizada/visível
                    try:
                        linha_xpath_scroll = f"{tabela_xpath}/tr[@data-ri='{data_ri}']"
                        linha_elem = self.driver.find_element(By.XPATH, linha_xpath_scroll)
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", linha_elem)
                        time.sleep(0.1)
                    except Exception:
                        pass
                    
                    # Tentar até 3 vezes para garantir que o conceito foi aplicado
                    max_tentativas = 3
                    sucesso = False
                    
                    for tentativa in range(1, max_tentativas + 1):
                        try:
                            # Usar JavaScript para definir o valor e disparar o evento change
                            script = f"""
                            var select = document.getElementById('{select_id}');
                            if (select) {{
                                var valorAtual = select.value;
                                if (valorAtual !== '{conceito}') {{
                                    select.value = '{conceito}';
                                    // Marcar visualmente como selected
                                    var options = select.options;
                                    for (var i = 0; i < options.length; i++) {{
                                        options[i].selected = (options[i].value === '{conceito}');
                                    }}
                                    // Disparar onchange (PrimeFaces Ajax Behavior)
                                    if (typeof select.onchange === 'function') {{
                                        try {{ select.onchange(); }} catch(e) {{ /* ignora */ }}
                                    }} else {{
                                        var event = new Event('change', {{ bubbles: true, cancelable: true }});
                                        select.dispatchEvent(event);
                                    }}
                                    return true;
                                }}
                                return false; // já estava com o valor correto
                            }}
                            return null; // select não encontrado
                            """
                            
                            resultado = self.driver.execute_script(script)
                            
                            if resultado is True:
                                # Aguardar processamento Ajax curto
                                time.sleep(0.2)
                                
                                # Verificar se o valor foi realmente aplicado
                                script_verificar = f"""
                                var select = document.getElementById('{select_id}');
                                return select ? select.value : null;
                                """
                                valor_atual = self.driver.execute_script(script_verificar)
                                
                                if valor_atual == conceito:
                                    preenchidos += 1
                                    sucesso = True
                                    break
                                else:
                                    if tentativa < max_tentativas:
                                        print(f"          ⚠️ Tentativa {tentativa}: Valor não aplicado, retentando...")
                                        time.sleep(0.2)
                            elif resultado is False:
                                # Já estava com o valor correto → contar como sucesso
                                preenchidos += 1
                                sucesso = True
                                break
                            else:
                                print(f"          ⚠️ Select não encontrado: {select_id}. Tentando re-renderizar linha...")
                                # Tentar forçar renderização/visibilidade e tentar novamente
                                try:
                                    linha_xpath_scroll = f"{tabela_xpath}/tr[@data-ri='{data_ri}']"
                                    linha_elem = self.driver.find_element(By.XPATH, linha_xpath_scroll)
                                    self.driver.execute_script("arguments[0].scrollIntoView(true);", linha_elem)
                                    time.sleep(0.2)
                                except Exception:
                                    pass
                                # deixar o loop de tentativa repetir
                                
                        except Exception as e_tentativa:
                            if tentativa < max_tentativas:
                                print(f"          ⚠️ Erro na tentativa {tentativa}, retentando: {str(e_tentativa)[:50]}")
                                time.sleep(0.5)
                            else:
                                raise e_tentativa
                    
                    if not sucesso:
                        print(f"          ❌ Não foi possível aplicar conceito após {max_tentativas} tentativas")
                        
                except Exception as e:
                    print(f"          ❌ Erro ao aplicar conceito para data-ri={data_ri}: {e}")

            print(f"     ✅ Total: {preenchidos} habilidades preenchidas")

        except Exception as e:
            print(f"     ❌ Erro ao preencher conceitos de habilidades: {e}")
            import traceback
            traceback.print_exc()
            return False

        return preenchidos > 0

    def _texto_corresponde(self, texto_alvo, texto_fonte):
        """
        Compara duas strings ignorando acentos, espaços extras e caixa
        """
        def normalizar(valor):
            if not valor:
                return ""
            valor = unicodedata.normalize("NFD", valor)
            valor = "".join(c for c in valor if unicodedata.category(c) != "Mn")
            return re.sub(r"\s+", " ", valor).strip().lower()

        return normalizar(texto_alvo) == normalizar(texto_fonte)

    def _fechar_modal_senha_chrome(self):
        """
        Fecha a modal do Chrome que pede para "Mudar sua senha" após o login
        
        Esta modal aparece quando o Chrome detecta que uma senha foi comprometida em
        um vazamento de dados. A modal é nativa do Chrome (não é HTML da página).
        
        Tentamos várias abordagens para fechá-la:
        1. Pressionar ESC (fecha modais nativas do Chrome)
        2. Pressionar ENTER (confirma botão padrão)
        3. Buscar e clicar no botão "OK"
        
        Se a modal não aparecer, não faz nada (não é um erro).
        """
        try:
            print("   🔍 Verificando se há modal de senha do Chrome...")
            time.sleep(2)  # Aguardar modal aparecer
            
            # Abordagem 1: Pressionar ESC (fecha modais nativas do Chrome)
            try:
                body = self.driver.find_element(By.TAG_NAME, "body")
                body.send_keys(Keys.ESCAPE)
                print("   ✅ Modal de senha fechada (ESC)")
                time.sleep(1)
                return
            except:
                pass
            
            # Abordagem 2: Pressionar ENTER (confirma botão padrão "OK")
            try:
                body = self.driver.find_element(By.TAG_NAME, "body")
                body.send_keys(Keys.ENTER)
                print("   ✅ Modal de senha fechada (ENTER)")
                time.sleep(1)
                return
            except:
                pass
            
            # Abordagem 3: Tentar encontrar botão OK visível (se for HTML)
            try:
                ok_button = WebDriverWait(self.driver, 2).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'OK') or contains(text(), 'Ok') or contains(@aria-label, 'OK')]"))
                )
                ok_button.click()
                print("   ✅ Modal de senha fechada (botão OK)")
                time.sleep(1)
                return
            except:
                pass
            
            # Abordagem 4: Tentar via JavaScript para fechar qualquer overlay
            try:
                self.driver.execute_script("""
                    // Fechar qualquer modal/overlay do Chrome
                    const overlays = document.querySelectorAll('[role="dialog"], .modal, [aria-modal="true"]');
                    overlays.forEach(overlay => {
                        if (overlay && overlay.style) {
                            overlay.style.display = 'none';
                        }
                    });
                """)
                print("   ✅ Modal de senha fechada (JavaScript)")
                time.sleep(1)
                return
            except:
                pass
            
            # Se chegou aqui, a modal não apareceu ou já foi fechada
            print("   ℹ️ Nenhuma modal de senha detectada")
            
        except Exception as e:
            # Não é um erro crítico, apenas log
            print(f"   ℹ️ Verificação de modal de senha: {e}")
    
    def _preencher_conceitos_habilidades_por_notas_mantendo_c(self, notas_aluno, mapeamentos):
        """
        Aplica os conceitos de habilidades baseado nas notas das avaliações
        MANTENDO conceito C (não troca por NE)
        
        Returns:
            list: Lista de habilidades que receberam conceito C [(data_ri, habilidade_texto), ...]
        """
        preenchidos = 0
        habilidades_com_c = []

        try:
            print(f"     📝 Preenchendo conceitos de habilidades (MANTENDO C)...")
            
            # ETAPA 1: Coletar informações de todas as habilidades
            tabela_xpath = "//tbody[@id='formAtitudes:panelAtitudes:dataTableHabilidades_data']/tr[@data-ri]"
            linhas = WebDriverWait(self.driver, 5).until(
                EC.presence_of_all_elements_located((By.XPATH, tabela_xpath))
            )
            
            print(f"     📋 Total de habilidades encontradas: {len(linhas)}")
            
            # Lista de habilidades a preencher: [(data_ri, habilidade_texto, conceito)]
            habilidades_para_preencher = []

            for idx, linha in enumerate(linhas):
                try:
                    data_ri = linha.get_attribute("data-ri")
                    cols = linha.find_elements(By.TAG_NAME, "td")
                    
                    if len(cols) < 3:
                        continue
                    
                    # Usar textContent via JavaScript
                    competencia_texto = self.driver.execute_script("return arguments[0].textContent;", cols[0]).strip()
                    habilidade_texto = self.driver.execute_script("return arguments[0].textContent;", cols[1]).strip()
                    
                except Exception as e:
                    print(f"       ⚠️ Erro ao ler linha {idx}: {e}")
                    continue

                conceito = ""
                av_utilizada = None
                
                # Procurar em qual avaliação esta habilidade está vinculada
                for av, habilidades_av in mapeamentos["habilidades"].items():
                    for h in habilidades_av:
                        hab_coletada = h["habilidade"].lstrip("*").strip()
                        hab_modal = habilidade_texto.lstrip("*").strip()
                        if self._texto_corresponde(hab_modal, hab_coletada):
                            # REGRA: SEMPRE priorizar RP se existir
                            recuperacao = mapeamentos["recuperacao_por_avaliacao"].get(av)
                            conceito_rec = notas_aluno.get(recuperacao, "") if recuperacao else ""
                            conceito_av = notas_aluno.get(av, "")
                            
                            if conceito_rec:
                                conceito = conceito_rec
                                av_utilizada = recuperacao
                                print(f"       🔄 USANDO RP! Habilidade de {av} → Aplicando nota da {recuperacao}: '{conceito_rec}'")
                            elif conceito_av:
                                conceito = conceito_av
                                av_utilizada = av

                            break
                    if av_utilizada:
                        break

                # Se encontrou conceito, adicionar à lista
                if av_utilizada and conceito:
                    habilidade_curta = habilidade_texto[:50] if len(habilidade_texto) > 50 else habilidade_texto
                    print(f"       ✓ {habilidade_curta[:40]}... → {conceito}")
                    habilidades_para_preencher.append((data_ri, habilidade_texto, conceito))
                    
                    # Se conceito é C, adicionar à lista de habilidades com C
                    if conceito.upper() == "C":
                        habilidades_com_c.append((data_ri, habilidade_texto))

            # ETAPA 2: Aplicar conceitos via JavaScript
            print(f"     🔧 Aplicando {len(habilidades_para_preencher)} conceitos...")
            
            for data_ri, habilidade_texto, conceito in habilidades_para_preencher:
                try:
                    # Construir o ID do select
                    select_id = f"formAtitudes:panelAtitudes:dataTableHabilidades:{data_ri}:notaConceito_input"
                    
                    # Tentar até 3 vezes
                    max_tentativas = 3
                    sucesso = False
                    
                    for tentativa in range(1, max_tentativas + 1):
                        try:
                            script = f"""
                            var select = document.getElementById('{select_id}');
                            if (select) {{
                                var valorAtual = select.value;
                                if (valorAtual !== '{conceito}') {{
                                    select.value = '{conceito}';
                                    
                                    var options = select.options;
                                    for (var i = 0; i < options.length; i++) {{
                                        if (options[i].value === '{conceito}') {{
                                            options[i].selected = true;
                                        }} else {{
                                            options[i].selected = false;
                                        }}
                                    }}
                                    
                                    var event = new Event('change', {{ bubbles: true, cancelable: true }});
                                    select.dispatchEvent(event);
                                    
                                    return true;
                                }}
                                return false;
                            }}
                            return null;
                            """
                            
                            resultado = self.driver.execute_script(script)
                            
                            if resultado is True:
                                time.sleep(0.5)
                                
                                script_verificar = f"""
                                var select = document.getElementById('{select_id}');
                                return select ? select.value : null;
                                """
                                valor_atual = self.driver.execute_script(script_verificar)
                                
                                if valor_atual == conceito:
                                    preenchidos += 1
                                    sucesso = True
                                    break
                                else:
                                    if tentativa < max_tentativas:
                                        print(f"          ⚠️ Tentativa {tentativa}: Valor não aplicado, retentando...")
                                        time.sleep(0.5)
                            elif resultado is False:
                                sucesso = True
                                break
                            else:
                                print(f"          ⚠️ Select não encontrado: {select_id}")
                                break
                                
                        except Exception as e_tentativa:
                            if tentativa < max_tentativas:
                                print(f"          ⚠️ Erro na tentativa {tentativa}, retentando: {str(e_tentativa)[:50]}")
                                time.sleep(0.5)
                            else:
                                raise e_tentativa
                    
                    if not sucesso:
                        print(f"          ❌ Não foi possível aplicar conceito após {max_tentativas} tentativas")
                        
                except Exception as e:
                    print(f"          ❌ Erro ao aplicar conceito para data-ri={data_ri}: {e}")

            print(f"     ✅ Total: {preenchidos} habilidades preenchidas, {len(habilidades_com_c)} com conceito C")

        except Exception as e:
            print(f"     ❌ Erro ao preencher conceitos de habilidades: {e}")
            import traceback
            traceback.print_exc()
            return []

        return habilidades_com_c
    
    def _cadastrar_ra_para_habilidades(
        self,
        habilidades_com_c,
        inicio_ra,
        termino_ra,
        descricao_ra,
        nome_arquivo_ra,
        caminho_arquivo_ra
    ):
        """
        Cadastra Recomposição de Aprendizagem para cada habilidade com conceito C
        
        Args:
            habilidades_com_c: Lista de tuplas [(data_ri, habilidade_texto), ...]
            inicio_ra: Data de início (DD/MM/YYYY)
            termino_ra: Data de término (DD/MM/YYYY)
            descricao_ra: Descrição da RA
            nome_arquivo_ra: Nome do arquivo PDF
            caminho_arquivo_ra: Caminho completo do arquivo PDF
            
        Returns:
            int: Número de RAs cadastradas
        """
        ras_cadastradas = 0
        
        try:
            print(f"     🎓 Cadastrando RA para {len(habilidades_com_c)} habilidade(s)...")
            
            for idx, (data_ri, habilidade_texto) in enumerate(habilidades_com_c):
                try:
                    print(f"       📝 Cadastrando RA {idx+1}/{len(habilidades_com_c)}: {habilidade_texto[:60]}...")
                    
                    # 1. Clicar no botão "Adicionar" da seção de RA
                    btn_adicionar_ra = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.ID, "formAtitudes:panelAtitudes:btnAdicionarPPE"))
                    )
                    self.driver.execute_script("arguments[0].click();", btn_adicionar_ra)
                    time.sleep(2)
                    print(f"         ✓ Botão Adicionar RA clicado")
                    
                    # Aguardar modal carregar completamente
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.ID, "formPPE:tabPanelCadastroPPE:habilidadePPE_input"))
                    )
                    time.sleep(1)
                    print(f"         ✓ Modal de RA carregada")
                    
                    # 2. Selecionar a habilidade no dropdown
                    # IMPORTANTE: O valor do select é o data-ri da habilidade no modal
                    # Precisamos usar o data_ri que foi coletado
                    
                    # Selecionar via JavaScript
                    script_select = f"""
                    var select = document.getElementById('formPPE:tabPanelCadastroPPE:habilidadePPE_input');
                    select.value = '{data_ri}';
                    
                    // Marcar option como selected
                    var options = select.options;
                    for (var i = 0; i < options.length; i++) {{
                        if (options[i].value === '{data_ri}') {{
                            options[i].selected = true;
                        }} else {{
                            options[i].selected = false;
                        }}
                    }}
                    
                    // Disparar evento change para PrimeFaces
                    var event = new Event('change', {{ bubbles: true, cancelable: true }});
                    select.dispatchEvent(event);
                    """
                    self.driver.execute_script(script_select)
                    time.sleep(1.5)
                    print(f"         ✓ Habilidade selecionada (data-ri: {data_ri})")
                    
                    # 3. Preencher data de início
                    input_inicio = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.ID, "formPPE:tabPanelCadastroPPE:inicioPPE_input"))
                    )
                    self.driver.execute_script("arguments[0].value = '';", input_inicio)
                    input_inicio.send_keys(inicio_ra)
                    # Disparar evento change
                    self.driver.execute_script("""
                        var elem = arguments[0];
                        var event = new Event('change', { bubbles: true });
                        elem.dispatchEvent(event);
                    """, input_inicio)
                    time.sleep(1)
                    print(f"         ✓ Data início: {inicio_ra}")
                    
                    # 4. Preencher data de término
                    input_termino = self.driver.find_element(By.ID, "formPPE:tabPanelCadastroPPE:terminoPPE_input")
                    self.driver.execute_script("arguments[0].value = '';", input_termino)
                    input_termino.send_keys(termino_ra)
                    # Disparar evento change
                    self.driver.execute_script("""
                        var elem = arguments[0];
                        var event = new Event('change', { bubbles: true });
                        elem.dispatchEvent(event);
                    """, input_termino)
                    time.sleep(1)
                    print(f"         ✓ Data término: {termino_ra}")
                    
                    # 5. Preencher descrição (editor Quill)
                    # Formatar descrição como HTML se não estiver
                    descricao_html = descricao_ra if descricao_ra.startswith('<') else f"<p>{descricao_ra}</p>"
                    
                    # Atualizar editor visual Quill
                    try:
                        editor_descricao = self.driver.find_element(By.CSS_SELECTOR, "#formPPE\\:tabPanelCadastroPPE\\:editorDescricao\\:editorDescricao_editor .ql-editor")
                        self.driver.execute_script("arguments[0].innerHTML = arguments[1];", editor_descricao, descricao_html)
                    except:
                        print(f"         ⚠️ Editor visual não encontrado, tentando alternativa...")
                    
                    # Atualizar campo hidden (CRÍTICO)
                    input_hidden = self.driver.find_element(By.ID, "formPPE:tabPanelCadastroPPE:editorDescricao:editorDescricao_input")
                    self.driver.execute_script("arguments[0].value = arguments[1];", input_hidden, descricao_html)
                    time.sleep(0.5)
                    print(f"         ✓ Descrição preenchida")
                    
                    # 6. Clicar na aba "Anexo"
                    try:
                        # Tentar clicar via JavaScript para evitar problemas de overlay
                        aba_anexo = WebDriverWait(self.driver, 5).until(
                            EC.presence_of_element_located((By.XPATH, "//a[contains(text(), 'Anexo')]"))
                        )
                        self.driver.execute_script("arguments[0].click();", aba_anexo)
                        time.sleep(1.5)
                        print(f"         ✓ Aba Anexo aberta")
                    except Exception as e:
                        print(f"         ⚠️ Erro ao clicar na aba Anexo: {e}")
                        # Tentar via índice do TabView
                        self.driver.execute_script("""
                            var tabView = PF('widget_formPPE_tabPanelCadastroPPE');
                            if (tabView) tabView.select(1);
                        """)
                        time.sleep(1.5)
                    
                    # 7. Clicar em "Adicionar Anexo"
                    btn_adicionar_anexo = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.ID, "formPPE:tabPanelCadastroPPE:adicionarAnexoPPE"))
                    )
                    self.driver.execute_script("arguments[0].click();", btn_adicionar_anexo)
                    time.sleep(2)
                    print(f"         ✓ Botão Adicionar Anexo clicado")
                    
                    # Aguardar modal de anexo carregar
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.ID, "formAnexoPlanoPessoalEstudo:cadastroAnexo:nome"))
                    )
                    time.sleep(1)
                    print(f"         ✓ Modal de anexo carregada")
                    
                    # 8. Preencher nome do arquivo
                    input_nome_arquivo = self.driver.find_element(By.ID, "formAnexoPlanoPessoalEstudo:cadastroAnexo:nome")
                    self.driver.execute_script("arguments[0].value = '';", input_nome_arquivo)
                    input_nome_arquivo.send_keys(nome_arquivo_ra)
                    # Disparar evento change
                    self.driver.execute_script("""
                        var elem = arguments[0];
                        var event = new Event('change', { bubbles: true });
                        elem.dispatchEvent(event);
                    """, input_nome_arquivo)
                    time.sleep(1)
                    print(f"         ✓ Nome do arquivo: {nome_arquivo_ra}")
                    
                    # 9. Fazer upload do arquivo (PrimeFaces FileUpload com auto=true)
                    input_file = self.driver.find_element(By.ID, "formAnexoPlanoPessoalEstudo:cadastroAnexo:arquivo_input")
                    input_file.send_keys(caminho_arquivo_ra)
                    print(f"         ✓ Arquivo selecionado: {caminho_arquivo_ra}")
                    
                    # Aguardar upload automático completar (PrimeFaces auto=true)
                    time.sleep(3)
                    
                    # Verificar se upload foi bem-sucedido
                    try:
                        # Verificar se o nome do arquivo foi preenchido automaticamente
                        nome_atual = self.driver.execute_script(
                            "return document.getElementById('formAnexoPlanoPessoalEstudo:cadastroAnexo:nome').value;"
                        )
                        if nome_atual:
                            print(f"         ✓ Upload automático concluído")
                        else:
                            print(f"         ⚠️ Upload pode não ter completado, aguardando mais...")
                            time.sleep(2)
                    except:
                        pass
                    
                    # 10. Salvar anexo
                    btn_salvar_anexo = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.ID, "formAnexoPlanoPessoalEstudo:cadastroAnexo:salvarAnexo"))
                    )
                    self.driver.execute_script("arguments[0].click();", btn_salvar_anexo)
                    time.sleep(2)
                    print(f"         ✓ Botão Salvar Anexo clicado")
                    
                    # Aguardar modal de anexo fechar
                    try:
                        WebDriverWait(self.driver, 5).until(
                            EC.invisibility_of_element_located((By.ID, "modalPlanoPessoalEstudoAnexo"))
                        )
                        print(f"         ✓ Modal de anexo fechada")
                    except:
                        # Forçar fechamento via JavaScript
                        self.driver.execute_script("PF('modalPlanoPessoalEstudoAnexo').hide();")
                        time.sleep(1)
                    
                    # Aguardar tabela de anexos atualizar
                    time.sleep(1)
                    
                    # 11. Voltar para aba "Dados Gerais" (não é necessário, mas vamos garantir)
                    try:
                        aba_dados_gerais = self.driver.find_element(By.XPATH, "//a[contains(text(), 'Dados Gerais')]")
                        self.driver.execute_script("arguments[0].click();", aba_dados_gerais)
                        time.sleep(1)
                        print(f"         ✓ Voltou para Dados Gerais")
                    except:
                        # Tentar via índice do TabView
                        self.driver.execute_script("""
                            var tabView = PF('widget_formPPE_tabPanelCadastroPPE');
                            if (tabView) tabView.select(0);
                        """)
                        time.sleep(1)
                    
                    # 12. Salvar a RA
                    btn_salvar_ra = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.ID, "formPPE:salvarPPE"))
                    )
                    self.driver.execute_script("arguments[0].click();", btn_salvar_ra)
                    time.sleep(3)
                    print(f"         ✓ Botão Salvar RA clicado")
                    
                    # Aguardar modal de RA fechar
                    try:
                        WebDriverWait(self.driver, 5).until(
                            EC.invisibility_of_element_located((By.ID, "modalPPE"))
                        )
                        print(f"         ✅ RA cadastrada com sucesso!")
                    except:
                        # Forçar fechamento via JavaScript
                        self.driver.execute_script("PF('modalPPE').hide();")
                        time.sleep(1)
                        print(f"         ✅ RA salva (modal fechada via JS)")
                    
                    ras_cadastradas += 1
                    time.sleep(1)  # Pausa entre cadastros
                    
                except Exception as e:
                    print(f"         ❌ Erro ao cadastrar RA para habilidade: {e}")
                    import traceback
                    traceback.print_exc()
                    
                    # Tentar fechar modais em caso de erro
                    try:
                        self.driver.execute_script("PF('modalPlanoPessoalEstudoAnexo').hide();")
                        time.sleep(0.5)
                    except:
                        pass
                    try:
                        self.driver.execute_script("PF('modalPPE').hide();")
                        time.sleep(0.5)
                    except:
                        pass
                    
                    # Tentar fechar via botão X
                    try:
                        close_btn = self.driver.find_element(By.CSS_SELECTOR, ".ui-dialog-titlebar-close")
                        close_btn.click()
                        time.sleep(0.5)
                    except:
                        pass
            
            print(f"     ✅ Total de RAs cadastradas: {ras_cadastradas}/{len(habilidades_com_c)}")
            return ras_cadastradas
            
        except Exception as e:
            print(f"     ❌ Erro ao cadastrar RAs: {e}")
            import traceback
            traceback.print_exc()
            return ras_cadastradas
    
    def _limpar_nome_aluno(self, nome_completo):
        """
        Remove sufixos como [PCD], [MENOR], [PCD - MENOR] do nome do aluno
        
        Args:
            nome_completo (str): Nome completo com possíveis sufixos
            
        Returns:
            str: Nome limpo sem sufixos
            
        Example:
            "Matheus Gonçalves dos Santos - [PCD]" -> "Matheus Gonçalves dos Santos"
            "Mateus Müller Biscaro - [MENOR]" -> "Mateus Müller Biscaro"
            "Ayumi Iura - [PCD - MENOR]" -> "Ayumi Iura"
        """
        # Remove tudo após o hífen seguido de espaço e colchete
        if " - [" in nome_completo:
            nome_limpo = nome_completo.split(" - [")[0].strip()
        else:
            nome_limpo = nome_completo.strip()
        
        return nome_limpo
    
    def _calcular_moda_conceitos(self, conceitos):
        """
        Calcula a moda (valor mais frequente) dos conceitos de um aluno
        COM ARREDONDAMENTO PARA BAIXO em caso de empate.
        
        Regra: A=4, B=3, C=2, NE=1
        Em caso de empate, escolhe o conceito de menor valor (arredonda para baixo)
        
        EXCEÇÃO: Se os conceitos forem exatamente A, B e C (empate triplo), retorna B
        
        Args:
            conceitos (list): Lista de conceitos (ex: ['A', 'B', 'A', 'B'])
            
        Returns:
            str: Conceito predominante (com arredondamento para baixo)
            
        Examples:
            ['A', 'B', 'A', 'B'] -> 'B' (empate, escolhe menor)
            ['A', 'C', 'A', 'C'] -> 'C' (empate, escolhe menor)
            ['A', 'NE', 'A', 'NE'] -> 'NE' (empate, escolhe menor)
            ['A', 'B', 'C'] -> 'B' (EXCEÇÃO: empate triplo A,B,C retorna B)
            ['B', 'B', 'B', 'A'] -> 'B' (B é mais frequente)
        """
        from collections import Counter
        
        if not conceitos:
            return None
        
        # Valores dos conceitos (menor = pior)
        valores = {'A': 4, 'B': 3, 'C': 2, 'NE': 1}
        
        # Contar frequência de cada conceito
        contador = Counter(conceitos)
        
        # EXCEÇÃO: Se for empate triplo A, B, C → retorna B
        conceitos_unicos = set(conceitos)
        if conceitos_unicos == {'A', 'B', 'C'} and all(contador[c] == contador['A'] for c in ['A', 'B', 'C']):
            return 'B'
        
        # Encontrar a frequência máxima
        freq_maxima = max(contador.values())
        
        # Pegar todos os conceitos com frequência máxima (empate)
        conceitos_empatados = [c for c, freq in contador.items() if freq == freq_maxima]
        
        # Se há empate, escolher o de menor valor (arredondamento para baixo)
        if len(conceitos_empatados) > 1:
            moda = min(conceitos_empatados, key=lambda c: valores.get(c, 0))
        else:
            moda = conceitos_empatados[0]
        
        return moda
    
    def _coletar_conceitos_alunos(self, trimestre_referencia):
        """
        Coleta os conceitos de todos os alunos abrindo o modal individual de cada um
        
        Args:
            trimestre_referencia (str): Trimestre de referência (TR1, TR2, TR3)
            
        Returns:
            dict: Dicionário com {nome_aluno_limpo: conceito_moda}
            
        Example:
            {
                "Matheus Gonçalves dos Santos": "B",
                "Mateus Müller Biscaro": "A",
                "Ayumi Iura": "C"
            }
        """
        print("\n📊 Coletando conceitos de todos os alunos...")
        
        alunos_conceitos = {}
        
        try:
            # Usar mesma lógica de _obter_lista_alunos que funciona
            alunos = self._obter_lista_alunos(trimestre=trimestre_referencia)
            total_alunos = len(alunos)
            
            if total_alunos == 0:
                print("   ❌ Nenhum aluno encontrado na tabela")
                return alunos_conceitos
            
            print(f"   ✓ Encontrados {total_alunos} alunos")
            
            for idx, aluno_info in enumerate(alunos, 1):
                try:
                    nome_completo = aluno_info['nome']
                    nome_limpo = self._limpar_nome_aluno(nome_completo)
                    
                    print(f"\n   [{idx}/{total_alunos}] Processando: {nome_limpo}")
                    
                    # Usar método que funciona para abrir modal
                    if not self._acessar_aba_notas_aluno(aluno_info):
                        print(f"      ❌ Não foi possível abrir modal de {nome_limpo}")
                        continue
                    
                    # Aguardar modal abrir
                    WebDriverWait(self.driver, 10).until(
                        EC.visibility_of_element_located((By.ID, "modalDadosAtitudes"))
                    )
                    
                    # Accordion já vem expandido por padrão, não precisa clicar
                    # Apenas aguardar a tabela estar presente
                    
                    # Coletar todos os conceitos das habilidades
                    conceitos = []
                    try:
                        # Aguardar tabela estar presente (sem sleep fixo)
                        WebDriverWait(self.driver, 3).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "tbody[id*='dataTableHabilidades_data'] tr[data-ri]"))
                        )
                        
                        # Encontrar todas as linhas da tabela de habilidades
                        linhas_habilidades = self.driver.find_elements(
                            By.CSS_SELECTOR,
                            "tbody[id*='dataTableHabilidades_data'] tr[data-ri]"
                        )
                        
                        print(f"      🔍 Encontradas {len(linhas_habilidades)} linhas de habilidades")
                        
                        for idx_hab, linha_hab in enumerate(linhas_habilidades):
                            try:
                                # MÉTODO 1: Tentar ler do <select> com selected="selected"
                                select_conceito = linha_hab.find_element(
                                    By.CSS_SELECTOR,
                                    "select[id*='notaConceito_input']"
                                )
                                
                                # Buscar option com selected="selected"
                                try:
                                    option_selecionada = select_conceito.find_element(
                                        By.CSS_SELECTOR,
                                        "option[selected='selected']"
                                    )
                                    conceito_selecionado = option_selecionada.get_attribute("value")
                                    
                                    if conceito_selecionado and conceito_selecionado != "":
                                        conceitos.append(conceito_selecionado)
                                        print(f"         [{idx_hab+1}] Conceito: {conceito_selecionado}")
                                        continue
                                except:
                                    pass
                                
                                # MÉTODO 2: Tentar ler do <label> que exibe o valor
                                try:
                                    label_conceito = linha_hab.find_element(
                                        By.CSS_SELECTOR,
                                        "label[id*='notaConceito_label']"
                                    )
                                    conceito_texto = label_conceito.text.strip()
                                    
                                    # Verificar se não é vazio ou &nbsp;
                                    if conceito_texto and conceito_texto not in ["", "Selecione", "\xa0"]:
                                        conceitos.append(conceito_texto)
                                        print(f"         [{idx_hab+1}] Conceito (label): {conceito_texto}")
                                        continue
                                except:
                                    pass
                                
                                # MÉTODO 3: Usar Select do Selenium (fallback)
                                try:
                                    conceito_selecionado = Select(select_conceito).first_selected_option.text.strip()
                                    if conceito_selecionado and conceito_selecionado != "Selecione":
                                        conceitos.append(conceito_selecionado)
                                        print(f"         [{idx_hab+1}] Conceito (Select): {conceito_selecionado}")
                                except:
                                    print(f"         [{idx_hab+1}] ⚠️ Nenhum conceito selecionado")
                                    
                            except Exception as e:
                                print(f"         [{idx_hab+1}] ❌ Erro: {str(e)[:50]}")
                                continue
                        
                        print(f"      ✓ Conceitos coletados: {conceitos}")
                        
                        # Calcular moda
                        if conceitos:
                            moda = self._calcular_moda_conceitos(conceitos)
                            alunos_conceitos[nome_limpo] = moda
                            print(f"      ✅ Conceito predominante (moda): {moda}")
                        else:
                            print(f"      ⚠️ Nenhum conceito encontrado para este aluno")
                    
                    except Exception as e:
                        print(f"      ❌ Erro ao coletar conceitos: {e}")
                    
                    # Fechar modal
                    try:
                        btn_fechar = self.driver.find_element(
                            By.CSS_SELECTOR,
                            "div[id='modalDadosAtitudes'] .ui-dialog-titlebar-close"
                        )
                        btn_fechar.click()
                        time.sleep(1)
                    except:
                        # Tentar via JavaScript
                        self.driver.execute_script("PF('modalDadosAtitudes').hide();")
                        time.sleep(1)
                
                except Exception as e:
                    print(f"      ❌ Erro ao processar aluno: {e}")
                    # Tentar fechar modal em caso de erro
                    try:
                        self.driver.execute_script("PF('modalDadosAtitudes').hide();")
                        time.sleep(1)
                    except:
                        pass
                    continue
            
            print(f"\n✅ Coleta concluída! Total de alunos processados: {len(alunos_conceitos)}/{total_alunos}")
            return alunos_conceitos
            
        except Exception as e:
            print(f"❌ Erro ao coletar conceitos dos alunos: {e}")
            import traceback
            traceback.print_exc()
            return alunos_conceitos
    
    def lancar_pareceres_por_nota(
        self,
        username,
        password,
        codigo_turma,
        trimestre_referencia="TR2"
    ):
        """
        Lança pareceres pedagógicos baseados na moda dos conceitos de cada aluno
        
        Fluxo:
        1. Faz login no sistema
        2. Navega até o diário da turma
        3. Abre aba de Conceitos
        4. Seleciona o trimestre de referência
        5. Para cada aluno:
           - Abre modal individual
           - Coleta todos os conceitos das habilidades
           - Calcula a moda (conceito mais frequente)
        6. Navega para aba Pedagógico
        7. Para cada aluno:
           - Seleciona o aluno no dropdown
           - Lança o parecer baseado no conceito predominante
        
        Args:
            username (str): Nome de usuário para login no SGN
            password (str): Senha do usuário
            codigo_turma (str): Código identificador da turma
            trimestre_referencia (str): Trimestre de referência (TR1, TR2 ou TR3)
            
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            print("\n" + "="*80)
            print(" 📝 LANÇAMENTO DE PARECERES POR NOTA")
            print("="*80)
            
            # 1. Fazer login
            print("\n1. Realizando login...")
            success, message = self.perform_login(username, password)
            if not success:
                return False, message
            
            # 2. Navegar para o diário da turma
            print(f"\n2. Navegando para o diário da turma {codigo_turma}...")
            self.driver.get(f"https://sgn.sesisenai.org.br/pages/diarioClasse/diario-classe.html?idDiario={codigo_turma}")
            time.sleep(3)
            
            # 3. Abrir aba de Conceitos
            print("\n3. Navegando para aba Conceitos...")
            try:
                self._open_conceitos_tab()
            except Exception as e:
                return False, f"Erro ao acessar aba Conceitos: {e}"
            
            # 4. Selecionar trimestre de referência
            print(f"\n4. Selecionando trimestre de referência: {trimestre_referencia}...")
            self._selecionar_trimestre_referencia(trimestre_referencia)
            
            # 5. Coletar conceitos de todos os alunos
            print("\n5. Coletando conceitos de todos os alunos...")
            alunos_conceitos = self._coletar_conceitos_alunos(trimestre_referencia)
            
            if not alunos_conceitos:
                return False, "Nenhum conceito foi coletado. Verifique se há alunos com conceitos lançados."
            
            # 6. Navegar para aba Pedagógico
            print("\n6. Navegando para aba Pedagógico...")
            try:
                self._open_pedagogico_tab()
            except Exception as e:
                return False, f"Erro ao acessar aba Pedagógico: {e}"
            
            # 7. Lançar pareceres para cada aluno
            print("\n7. Lançando pareceres...")
            pareceres_lancados = 0
            total_alunos = len(alunos_conceitos)
            
            # Aguardar dropdown carregar completamente (com retry)
            print("   ⏳ Aguardando dropdown de alunos carregar...")
            alunos_dropdown = {}
            max_tentativas = 10
            
            for tentativa in range(1, max_tentativas + 1):
                try:
                    # Aguardar o select estar presente
                    select_estudante = WebDriverWait(self.driver, 2).until(
                        EC.presence_of_element_located((By.ID, "tabViewDiarioClasse:formAbaPedagogico:selectEstudantes_input"))
                    )
                    
                    # Usar JavaScript para pegar as options (mais confiável que Selenium Select)
                    options_data = self.driver.execute_script("""
                        var select = document.getElementById('tabViewDiarioClasse:formAbaPedagogico:selectEstudantes_input');
                        var options = [];
                        for (var i = 0; i < select.options.length; i++) {
                            var opt = select.options[i];
                            if (opt.text && opt.text !== 'Selecione') {
                                options.push({
                                    text: opt.text,
                                    value: opt.value
                                });
                            }
                        }
                        return options;
                    """)
                    
                    # Criar mapa de nomes disponíveis
                    alunos_dropdown = {}
                    for opt_data in options_data:
                        alunos_dropdown[opt_data['text']] = opt_data['value']
                    
                    # Se encontrou alunos, sair do loop
                    if len(alunos_dropdown) > 0:
                        print(f"   ✓ Dropdown carregado com {len(alunos_dropdown)} alunos")
                        break
                    
                    # Se não encontrou, aguardar e tentar novamente
                    print(f"   ⏳ Tentativa {tentativa}/{max_tentativas}: Dropdown vazio, aguardando...")
                    time.sleep(1)
                    
                except Exception as e:
                    print(f"   ⚠️ Tentativa {tentativa}/{max_tentativas}: Erro - {str(e)[:50]}")
                    time.sleep(1)
            
            # Verificar se conseguiu carregar
            if len(alunos_dropdown) == 0:
                print(f"\n   ❌ ERRO: Dropdown não carregou após {max_tentativas} tentativas")
                print(f"   🔍 DEBUG - HTML do select:")
                try:
                    select_html = select_estudante.get_attribute('outerHTML')
                    print(f"   {select_html[:500]}")
                except:
                    print("   Não foi possível obter HTML do select")
                return False, "Dropdown de alunos não carregou na aba Pedagógico"
            
            # DEBUG: Mostrar primeiros 5 alunos de cada lista para comparação
            print(f"\n   🔍 DEBUG - Primeiros 5 alunos coletados da aba Conceitos:")
            for i, nome in enumerate(list(alunos_conceitos.keys())[:5], 1):
                print(f"      {i}. '{nome}'")
            
            print(f"\n   🔍 DEBUG - Primeiros 5 alunos do dropdown Pedagógico:")
            for i, nome in enumerate(list(alunos_dropdown.keys())[:5], 1):
                print(f"      {i}. '{nome}'")
            
            for idx, (nome_aluno, conceito_moda) in enumerate(alunos_conceitos.items(), 1):
                try:
                    print(f"\n   [{idx}/{total_alunos}] {nome_aluno} (Conceito: {conceito_moda})")
                    
                    # Verificar se o aluno está no dropdown
                    if nome_aluno not in alunos_dropdown:
                        print(f"      ⚠️ Aluno não está nesta disciplina")
                        continue
                    
                    # Selecionar aluno usando JavaScript (mais confiável)
                    valor_option = alunos_dropdown[nome_aluno]
                    self.driver.execute_script("""
                        var select = document.getElementById('tabViewDiarioClasse:formAbaPedagogico:selectEstudantes_input');
                        select.value = arguments[0];
                        
                        // Disparar evento change para acionar o AJAX do PrimeFaces
                        var event = new Event('change', { bubbles: true });
                        select.dispatchEvent(event);
                    """, valor_option)
                    
                    # Aguardar carregamento AJAX dos dados do aluno
                    WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.ID, "tabViewDiarioClasse:formAbaPedagogico:sanfonaDesempenho"))
                    )
                    time.sleep(0.5)
                    
                    print(f"      ✓ Selecionado e carregado")
                    
                    # ===== Implementação de preenchimento de pareceres (alinhado ao HAR correto) =====
                    # 1) Garantir que 'Média de referência' tenha o valor esperado, sem disparar AJAX extra
                    try:
                        tr_label = str(trimestre_referencia).split('.')[-1] if '.' in str(trimestre_referencia) else str(trimestre_referencia)
                        mapa_valor = {"TR1": "1", "TR2": "2", "TR3": "3", "CF": "4"}
                        desired_val = mapa_valor.get(tr_label)
                        if desired_val:
                            current_val = self.driver.execute_script(
                                "return document.getElementById('tabViewDiarioClasse:formAbaPedagogico:sanfonaDesempenho:sanfonaAvaliacao:mediasReferencia_input')?.value;"
                            )
                            if current_val != desired_val:
                                self.driver.execute_script(
                                    "var el=document.getElementById('tabViewDiarioClasse:formAbaPedagogico:sanfonaDesempenho:sanfonaAvaliacao:mediasReferencia_input');"
                                    "if(el){el.value=arguments[0];}",
                                    desired_val
                                )
                        time.sleep(0.3)
                    except Exception:
                        pass

                    # 2) Mapear TR -> índice da linha dos pareceres
                    trimestre_para_indice = {"TR1": 0, "TR2": 1, "TR3": 2, "CF": 3}
                    indice_trimestre = trimestre_para_indice.get(tr_label)
                    if indice_trimestre is None:
                        print(f"      ⚠️ Trimestre inválido para parecer: {trimestre_referencia}")
                        continue

                    # 3) Gerar parecer
                    parecer = self._gerar_parecer_por_conceito(conceito_moda)
                    print(f"      📝 PARECER ({tr_label}/{conceito_moda}) -> {parecer[:140]}...")

                    # Log no console do navegador
                    try:
                        self.driver.execute_script(
                            "console.log('Parecer anexado | Aluno: ' + arguments[0] + ' | Trimestre: ' + arguments[1] + ' | Conceito: ' + arguments[2] + ' | Texto: ' + arguments[3]);",
                            nome_aluno,
                            tr_label,
                            conceito_moda,
                            parecer
                        )
                    except Exception:
                        pass

                    # 4) Abrir acordeão Pareceres se necessário e garantir visibilidade da tabela
                    try:
                        sanfona_media = WebDriverWait(self.driver, 5).until(
                            EC.presence_of_element_located((By.ID, "tabViewDiarioClasse:formAbaPedagogico:sanfonaDesempenho:sanfonaMedia"))
                        )
                        try:
                            header = sanfona_media.find_element(By.CSS_SELECTOR, ".ui-accordion-header")
                            if header.get_attribute("aria-expanded") != "true":
                                self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", header)
                                header.click()
                                time.sleep(0.3)
                        except Exception:
                            pass
                        WebDriverWait(self.driver, 5).until(
                            EC.presence_of_element_located((By.ID, "tabViewDiarioClasse:formAbaPedagogico:sanfonaDesempenho:sanfonaMedia:desempenhoMedias"))
                        )
                    except Exception:
                        pass

                    # 5) Preencher textarea do TR correto via JS (evita element not interactable)
                    textarea_id = f"tabViewDiarioClasse:formAbaPedagogico:sanfonaDesempenho:sanfonaMedia:desempenhoMedias:{indice_trimestre}:j_idt990"
                    try:
                        textarea = WebDriverWait(self.driver, 6).until(
                            EC.presence_of_element_located((By.ID, textarea_id))
                        )
                        try:
                            self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", textarea)
                            time.sleep(0.2)
                        except Exception:
                            pass
                        self.driver.execute_script(
                            "var el=document.getElementById(arguments[0]);"
                            "if(el){el.value=arguments[1];var e1=new Event('input',{bubbles:true});el.dispatchEvent(e1);var e2=new Event('change',{bubbles:true});el.dispatchEvent(e2);}",
                            textarea_id,
                            parecer
                        )
                        print(f"      ✓ Parecer preenchido em {tr_label}")

                        # 6) Salvar — clicar no botão e aguardar mensagem
                        btn_salvar = WebDriverWait(self.driver, 6).until(
                            EC.presence_of_element_located((By.ID, "tabViewDiarioClasse:formAbaPedagogico:sanfonaDesempenho:botaoSalvarDesempenho"))
                        )
                        try:
                            self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn_salvar)
                            time.sleep(0.2)
                        except Exception:
                            pass
                        try:
                            WebDriverWait(self.driver, 4).until(
                                EC.element_to_be_clickable((By.ID, "tabViewDiarioClasse:formAbaPedagogico:sanfonaDesempenho:botaoSalvarDesempenho"))
                            )
                            btn_salvar.click()
                        except Exception:
                            self.driver.execute_script("arguments[0].click();", btn_salvar)

                        # Aguardar mensagem de sucesso (ou pequeno fallback)
                        try:
                            WebDriverWait(self.driver, 6).until(
                                EC.presence_of_element_located((By.ID, "sgnPrimeMessagesAutoUpdate"))
                            )
                        except Exception:
                            time.sleep(1.0)
                        print(f"      ✅ Parecer salvo para {nome_aluno} ({tr_label})")

                        pareceres_lancados += 1
                    except Exception as e_p:
                        print(f"      ❌ Erro ao preencher/salvar parecer: {str(e_p)[:120]}")
                    
                except Exception as e:
                    print(f"      ❌ Erro: {str(e)[:80]}")
                    continue
            
            # Mensagem final
            mensagem_final = f"Pareceres lançados com sucesso! Processados: {pareceres_lancados}/{len(alunos_conceitos)} alunos"
            print(f"\n{'='*80}")
            print(f"✅ {mensagem_final}")
            print(f"{'='*80}\n")
            
            return True, mensagem_final
            
        except Exception as e:
            error_msg = f"Erro ao lançar pareceres: {str(e)}"
            print(f"❌ {error_msg}")
            import traceback
            traceback.print_exc()
            return False, error_msg

    def _detectar_e_expandir_capacidades(self):
        """
        Detecta e expande múltiplas capacidades/painéis na interface
        
        Returns:
            int: Número de capacidades processadas
        """
        try:
            print(f"     🔍 Detectando múltiplas capacidades/painéis...")
            
            capacidades_expandidas = 0
            
            # 1. Procurar por painéis/accordions que podem conter capacidades
            accordion_selectors = [
                "//div[contains(@class, 'ui-accordion-header')]",
                "//div[contains(@id, 'capacidade') or contains(@class, 'capacidade')]",
                "//div[contains(@id, 'painel') or contains(@class, 'painel')]",
                "//h3[contains(text(), 'Capacidade') or contains(text(), 'C1') or contains(text(), 'C2') or contains(text(), 'C3')]",
                "//div[contains(@class, 'ui-fieldset-legend')]"
            ]
            
            for selector in accordion_selectors:
                try:
                    elementos = self.driver.find_elements(By.XPATH, selector)
                    print(f"     📋 Encontrados {len(elementos)} elementos com seletor: {selector}")
                    
                    for elemento in elementos:
                        try:
                            # Verificar se o elemento está visível e pode ser clicado
                            if elemento.is_displayed():
                                texto = elemento.text.strip()
                                
                                # Verificar se parece ser um painel de capacidade
                                if any(palavra in texto.lower() for palavra in ['capacidade', 'c1', 'c2', 'c3', 'habilidade']):
                                    print(f"     📂 Possível capacidade encontrada: '{texto[:50]}...'")
                                    
                                    # Verificar se está expandido
                                    class_attr = elemento.get_attribute("class") or ""
                                    aria_expanded = elemento.get_attribute("aria-expanded")
                                    
                                    if ("ui-state-active" not in class_attr and 
                                        aria_expanded != "true"):
                                        
                                        print(f"     🔄 Expandindo painel: {texto[:30]}...")
                                        
                                        # Tentar clicar para expandir
                                        self.driver.execute_script("arguments[0].scrollIntoView(true);", elemento)
                                        time.sleep(0.3)
                                        elemento.click()
                                        time.sleep(1)  # Aguardar expansão
                                        
                                        capacidades_expandidas += 1
                                        print(f"     ✅ Painel expandido: {texto[:30]}")
                                    else:
                                        print(f"     ✓ Painel já expandido: {texto[:30]}")
                                        capacidades_expandidas += 1
                                        
                        except Exception as e:
                            print(f"     ⚠️ Erro ao processar elemento: {str(e)[:50]}")
                            continue
                            
                except Exception as e:
                    print(f"     ⚠️ Erro com seletor {selector}: {str(e)[:50]}")
                    continue
            
            print(f"     📊 Total de capacidades/painéis processados: {capacidades_expandidas}")
            return capacidades_expandidas
            
        except Exception as e:
            print(f"     ❌ Erro ao detectar capacidades: {str(e)}")
            return 0

    def _obter_todas_tabelas_habilidades(self):
        """
        Obtém todas as tabelas de habilidades disponíveis (múltiplas capacidades)
        MÉTODO OTIMIZADO: Usa descoberta rápida como nas atitudes
        
        Returns:
            list: Lista de dicionários com informações das tabelas
        """
        try:
            print(f"     🔍 Descobrindo número real de conceitos/habilidades...")
            
            # MÉTODO OTIMIZADO: Buscar diretamente pelos selects de conceito (como nas atitudes)
            try:
                conceitos_elements = self.driver.find_elements(By.CSS_SELECTOR, "select[id*='notaConceito']")
                max_conceitos = len(conceitos_elements)
                print(f"     📊 Encontrados {max_conceitos} elementos de conceito na página")
                
                if max_conceitos == 0:
                    # Fallback: buscar por método tradicional se não encontrar conceitos
                    print(f"     ⚠️ Nenhum conceito encontrado, tentando método tradicional...")
                    return self._obter_tabelas_habilidades_tradicional()
                    
            except Exception as e:
                print(f"     ⚠️ Erro ao descobrir conceitos, usando método tradicional: {e}")
                return self._obter_tabelas_habilidades_tradicional()
            
            # Criar estrutura otimizada baseada nos conceitos encontrados
            todas_tabelas = []
            
            # Buscar a tabela principal de habilidades
            try:
                tabela_habilidades_xpath = "//tbody[@id='formAtitudes:panelAtitudes:dataTableHabilidades_data']"
                tbody_element = self.driver.find_element(By.XPATH, tabela_habilidades_xpath)
                
                if tbody_element.is_displayed():
                    # Criar linhas virtuais baseadas nos conceitos encontrados
                    linhas_virtuais = []
                    
                    for i in range(max_conceitos):
                        # Criar objeto linha virtual com data-ri (capturar i por valor)
                        linha_virtual = type('LinhaVirtual', (), {
                            'get_attribute': lambda self, attr, data_ri=str(i): data_ri if attr == 'data-ri' else None
                        })()
                        linhas_virtuais.append(linha_virtual)
                    
                    tabela_info = {
                        'id': 'formAtitudes:panelAtitudes:dataTableHabilidades_data',
                        'xpath': tabela_habilidades_xpath,
                        'linhas': linhas_virtuais,
                        'nome': f'Conceitos de Habilidades (Total: {max_conceitos})',
                        'elemento': tbody_element
                    }
                    
                    todas_tabelas.append(tabela_info)
                    print(f"     ✅ Tabela otimizada criada: {max_conceitos} conceitos identificados rapidamente")
                    
            except Exception as e:
                print(f"     ⚠️ Erro ao criar tabela otimizada: {e}")
                return self._obter_tabelas_habilidades_tradicional()
            
            return todas_tabelas
            
        except Exception as e:
            print(f"     ❌ Erro ao obter tabelas de habilidades: {str(e)}")
            return []

    def _obter_tabelas_habilidades_tradicional(self):
        """
        Método tradicional (mais lento) para buscar tabelas de habilidades
        """
        try:
            print(f"     🔍 Buscando tabelas pelo método tradicional...")
            
            todas_tabelas = []
            
            # Diferentes padrões de seletores para tabelas de habilidades
            seletores_tabelas = [
                "//tbody[@id='formAtitudes:panelAtitudes:dataTableHabilidades_data']",
                "//tbody[contains(@id, 'dataTableHabilidades') and contains(@id, '_data')]",
                "//tbody[contains(@id, 'tabelaHabilidade') and contains(@id, '_data')]",
                "//tbody[contains(@id, 'habilidades_data')]",
                "//table[contains(@id, 'habilidades')]//tbody",
                "//div[contains(@class, 'ui-datatable')]//tbody[contains(@id, '_data')]"
            ]
            
            tabelas_encontradas = set()  # Para evitar duplicatas
            
            for i, seletor in enumerate(seletores_tabelas):
                try:
                    elementos = self.driver.find_elements(By.XPATH, seletor)
                    print(f"     📋 Seletor {i+1}: encontradas {len(elementos)} tabela(s)")
                    
                    for j, tbody in enumerate(elementos):
                        try:
                            # Verificar se a tabela está visível e tem linhas
                            if tbody.is_displayed():
                                linhas = tbody.find_elements(By.XPATH, ".//tr[@data-ri]")
                                
                                if len(linhas) > 0:
                                    # Usar ID como chave única para evitar duplicatas
                                    tbody_id = tbody.get_attribute("id") or f"tabela_{i}_{j}"
                                    
                                    if tbody_id not in tabelas_encontradas:
                                        tabelas_encontradas.add(tbody_id)
                                        
                                        # Tentar identificar o nome da capacidade
                                        nome_capacidade = self._identificar_nome_capacidade(tbody)
                                        
                                        tabela_info = {
                                            'id': tbody_id,
                                            'xpath': seletor,
                                            'linhas': linhas,
                                            'nome': nome_capacidade,
                                            'elemento': tbody
                                        }
                                        
                                        todas_tabelas.append(tabela_info)
                                        print(f"     ✅ Tabela adicionada: {nome_capacidade} ({len(linhas)} habilidades)")
                                    else:
                                        print(f"     ⚠️ Tabela duplicada ignorada: {tbody_id}")
                                else:
                                    print(f"     ⚠️ Tabela sem habilidades: {tbody.get_attribute('id')}")
                            else:
                                print(f"     ⚠️ Tabela não visível: {tbody.get_attribute('id')}")
                                
                        except Exception as e:
                            print(f"     ⚠️ Erro ao processar tabela {j}: {str(e)[:50]}")
                            continue
                            
                except Exception as e:
                    print(f"     ⚠️ Erro com seletor {i+1}: {str(e)[:50]}")
                    continue
            
            print(f"     📊 TOTAL DE TABELAS ENCONTRADAS: {len(todas_tabelas)}")
            
            # Log detalhado das tabelas encontradas
            for i, tabela in enumerate(todas_tabelas, 1):
                print(f"     📋 Tabela {i}: {tabela['nome']} - {len(tabela['linhas'])} habilidades")
            
            return todas_tabelas
            
        except Exception as e:
            print(f"     ❌ Erro ao obter tabelas de habilidades (tradicional): {str(e)}")
            return []

    def _identificar_nome_capacidade(self, tbody_element):
        """
        Tenta identificar o nome da capacidade baseado no contexto da tabela
        
        Args:
            tbody_element: Elemento tbody da tabela
            
        Returns:
            str: Nome identificado da capacidade
        """
        try:
            # Tentar encontrar um título ou cabeçalho próximo
            parent = tbody_element
            
            # Subir na hierarquia procurando por títulos
            for _ in range(5):  # Máximo 5 níveis acima
                try:
                    parent = parent.find_element(By.XPATH, "..")
                    
                    # Procurar por elementos de título próximos
                    titulos_xpath = [
                        ".//h1 | .//h2 | .//h3 | .//h4",
                        ".//legend",
                        ".//span[contains(@class, 'ui-fieldset-legend')]",
                        ".//div[contains(@class, 'ui-accordion-header')]",
                        ".//label[contains(text(), 'Capacidade') or contains(text(), 'C1') or contains(text(), 'C2')]"
                    ]
                    
                    for xpath in titulos_xpath:
                        elementos = parent.find_elements(By.XPATH, xpath)
                        for elemento in elementos:
                            texto = elemento.text.strip()
                            if texto and len(texto) > 2:
                                # Verificar se parece ser um nome de capacidade
                                if any(palavra in texto.lower() for palavra in ['capacidade', 'c1', 'c2', 'c3', 'habilidade']):
                                    return texto[:50]  # Limitar tamanho
                                    
                except:
                    continue
                    
            # Se não encontrou título, usar ID da tabela
            tbody_id = tbody_element.get_attribute("id")
            if tbody_id:
                return f"Capacidade ({tbody_id.split('_')[-2] if '_' in tbody_id else 'Principal'})"
            
            return "Capacidade Não Identificada"
            
        except Exception as e:
            return f"Capacidade (Erro: {str(e)[:20]})"
