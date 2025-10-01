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
import time
import re
import unicodedata

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
                aba_conceitos = self.driver.find_element(By.XPATH, "//a[contains(text(), 'Conceitos')]")
                aba_conceitos.click()
                time.sleep(2)
                print("   ✓ Aba Conceitos acessada")
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

            # 8. Lançar conceitos INTELIGENTES para todos os alunos
            print("\n8. Iniciando lançamento INTELIGENTE de conceitos...")
            print(f"🔧 Usando valores mapeados:")
            print(f"   - Atitude: {atitude_mapeada}")
            print(f"   - Conceito (fallback): {conceito_mapeado}")
            
            success, message = self._lancar_conceitos_inteligente(
                atitude_observada=atitude_mapeada,
                conceito_habilidade=conceito_mapeado,
                trimestre_referencia=trimestre_referencia,
                mapeamentos_prontos=mapeamentos  # Passar mapeamentos já coletados
            )
            
            return success, message
            
        except Exception as e:
            error_msg = f"Erro ao lançar conceitos inteligentes: {str(e)}"
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
    
    def _open_conceitos_tab(self):
        """
        Abre a aba de Conceitos no diário da turma
        
        Este método:
        1. Localiza a aba/link de "Conceitos" na página do diário
        2. Aguarda até que o elemento seja clicável
        3. Clica na aba para abri-la
        4. Aguarda o carregamento do conteúdo da aba
        
        O XPath usado procura por elementos que contenham o texto "Conceitos"
        ou que tenham "conceito" no atributo href, para maior flexibilidade.
        
        Raises:
            TimeoutException: Se a aba de Conceitos não for encontrada no tempo limite
        """
        print("6. Abrindo aba de Conceitos...")
        
        try:
            # Usar o XPath específico fornecido pelo usuário
            print("   🔍 Procurando aba de Conceitos com XPath específico...")
            conceitos_tab = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "/html/body/div[3]/div[3]/div[2]/div[2]/div/div/ul/li[7]"))
            )
            
            # Scroll até o elemento para garantir que está visível
            self.driver.execute_script("arguments[0].scrollIntoView(true);", conceitos_tab)
            time.sleep(0.5)
            
            conceitos_tab.click()
            print("   ✅ Aba de Conceitos clicada com XPath específico")
            
            # Aguardar mais tempo para a aba carregar completamente
            print("   ⏳ Aguardando aba de Conceitos carregar completamente...")
            time.sleep(5)  # Aumentado para garantir carregamento
            
            # Forçar clique duplo para garantir que a aba seja ativada
            try:
                print("   🔄 Garantindo que a aba está ativa com clique duplo...")
                conceitos_tab.click()  # Segundo clique
                time.sleep(2)
            except:
                pass
            
            # Verifica se a aba foi aberta corretamente
            current_url = self.driver.current_url
            print(f"   URL após clicar na aba: {current_url}")
            
            # Verificar se estamos realmente na aba de Conceitos
            self._verificar_aba_conceitos_ativa()
            
            # Verificar se a tabela de alunos está presente
            try:
                tabela_xpath = "/html/body/div[3]/div[3]/div[2]/div[2]/div/div/div/div[7]/form/div/div/span/span/div[2]/div/div[2]/table/tbody"
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, tabela_xpath))
                )
                print("   ✅ Tabela de alunos encontrada - aba carregada corretamente")
            except:
                print("   ⚠️ Tabela de alunos não encontrada - tentando aguardar mais...")
                time.sleep(5)
                try:
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, tabela_xpath))
                    )
                    print("   ✅ Tabela de alunos encontrada após segunda tentativa")
                except:
                    print("   ❌ Tabela de alunos ainda não encontrada")
                    # Verificar se a aba está realmente ativa
                    self._verificar_aba_conceitos_ativa()
                    # Tira screenshot para debug
                    self.driver.save_screenshot("debug_conceitos_tab_loaded.png")
                    print("   📸 Screenshot salvo como 'debug_conceitos_tab_loaded.png'")
            
            print("✅ Aba de Conceitos aberta com sucesso")
            
        except Exception as e:
            print(f"   ❌ Erro com XPath específico: {str(e)}")
            print("   🔄 Tentando seletores alternativos...")
            
            # Tenta seletores alternativos como fallback
            alternative_selectors = [
                "//a[contains(text(), 'Conceitos')]",
                "//li[contains(text(), 'Conceitos')]",
                "//a[contains(@href, 'conceito')]",
                "//li[7]//a",  # 7º item da lista
                "/html/body/div[3]/div[3]/div[2]/div[2]/div/div/ul/li[7]/a",  # XPath mais específico
                "//ul//li[7]",  # Qualquer 7º item de lista
                "//div[contains(@class, 'tab')]//li[7]"  # 7º item em div de tabs
            ]
            
            for i, selector in enumerate(alternative_selectors, 1):
                try:
                    print(f"   Tentativa {i}: {selector}")
                    element = WebDriverWait(self.driver, 3).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    
                    # Scroll até o elemento
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
                    time.sleep(0.5)  # Reduzido de 1 para 0.5 segundos
                    
                    element.click()
                    print(f"   ✅ Aba encontrada com seletor: {selector}")
                    time.sleep(2)  # Reduzido de 5 para 2 segundos
                    
                    # Se chegou até aqui, funcionou
                    print("✅ Aba de Conceitos aberta com seletor alternativo")
                    return
                    
                except Exception as e2:
                    print(f"   ❌ Falhou: {str(e2)}")
                    continue
            
            # Se chegou até aqui, nenhum seletor funcionou
            print("   📸 Tirando screenshot para debug...")
            self.driver.save_screenshot("debug_conceitos_tab.png")
            print("   📸 Screenshot salvo como 'debug_conceitos_tab.png'")
            
            # Tenta listar todos os elementos li para debug
            try:
                print("   🔍 Listando elementos <li> disponíveis para debug...")
                li_elements = self.driver.find_elements(By.XPATH, "//li")
                for i, li in enumerate(li_elements[:10], 1):  # Mostra apenas os primeiros 10
                    try:
                        text = li.text.strip()[:50]  # Primeiros 50 caracteres
                        if text:
                            print(f"     Li {i}: {text}")
                    except:
                        print(f"     Li {i}: [sem texto]")
            except:
                print("   ❌ Não foi possível listar elementos li")
            
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
        
        Este é o método SIMPLES/ANTIGO que aplica o conceito padrão para todos.
        Para lançamento inteligente baseado nas avaliações, use _lancar_conceitos_inteligente().
        """
        print("7. Iniciando lançamento de conceitos para todos os alunos (MODO SIMPLES)...")
        print(f"   📋 Atitude observada: '{atitude_observada}'")
        print(f"   📋 Conceito de habilidade: '{conceito_habilidade}' (aplicado para TODAS as habilidades)")
        
        try:
            alunos = self._obter_lista_alunos()
            total_alunos = len(alunos)
            
            if total_alunos == 0:
                return False, "Nenhum aluno encontrado na tabela"
            
            print(f"   📋 Encontrados {total_alunos} alunos na turma")
            
            alunos_processados = 0
            alunos_com_erro = 0
            
            for i, aluno_info in enumerate(alunos, 1):
                try:
                    print(f"\n   👤 Processando aluno {i}/{total_alunos}: {aluno_info['nome']}")
                    
                    success = self._acessar_aba_notas_aluno(aluno_info)
                    if not success:
                        print(f"   ❌ Erro ao acessar aba de notas do aluno {aluno_info['nome']}")
                        alunos_com_erro += 1
                        continue
                    
                    success = self._preencher_observacoes_atitudes(atitude_observada)
                    if not success:
                        print(f"   ⚠️ Erro ao preencher observações de atitudes para {aluno_info['nome']}")
                    
                    success = self._preencher_conceitos_habilidades(conceito_habilidade)
                    if not success:
                        print(f"   ⚠️ Erro ao preencher conceitos de habilidades para {aluno_info['nome']}")
                    
                    print(f"   ✅ Conceitos aplicados para {aluno_info['nome']} (salvamento automático)")
                    alunos_processados += 1
                    
                    self._fechar_modal_conceitos()
                    print("")
                    
                except Exception as e:
                    print(f"   ❌ Erro ao processar aluno {aluno_info.get('nome', 'desconhecido')}: {str(e)}")
                    alunos_com_erro += 1
                    try:
                        self._fechar_modal_conceitos()
                    except:
                        pass
            
            message = f"Processados: {alunos_processados}/{total_alunos} alunos"
            if alunos_com_erro > 0:
                message += f", {alunos_com_erro} com erro"
            
            success = alunos_processados > 0
            print(f"\n✅ Lançamento concluído: {message}")
            
            return success, message
            
        except Exception as e:
            error_msg = f"Erro durante lançamento de conceitos: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg
    
    def _lancar_conceitos_inteligente(
        self,
        atitude_observada="Raramente",
        conceito_habilidade="B",
        trimestre_referencia=None,
        mapeamentos_prontos=None,
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
            alunos = self._obter_lista_alunos(mapa_colunas=mapeamentos["colunas"])
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

                    # 4️⃣ PREENCHER HABILIDADES BASEADO NAS NOTAS
                    if not self._preencher_conceitos_habilidades_por_notas(notas, mapeamentos):
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
    
    def _obter_lista_alunos(self, mapa_colunas=None):
        """
        Obtém a lista de todos os alunos na tabela de conceitos
        
        Args:
            mapa_colunas (dict, optional): Mapeamento de colunas de avaliações
                                           Se fornecido, coleta as notas junto
        
        Returns:
            list: Lista de dicionários com informações dos alunos
                  [{"nome": str, "linha": int, "xpath_aba_notas": str, "notas_preview": dict}, ...]
        """
        print("   🔍 Identificando alunos na tabela...")
        
        try:
            # XPath base da tabela de alunos
            tabela_xpath = "/html/body/div[3]/div[3]/div[2]/div[2]/div/div/div/div[7]/form/div/div/span/span/div[2]/div/div[2]/table/tbody"
            
            print(f"   🔍 Procurando tabela de alunos: {tabela_xpath}")
            
            # Aguardar tabela carregar com múltiplas tentativas
            tabela_encontrada = False
            
            # Primeira tentativa com XPath específico
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, tabela_xpath))
                )
                tabela_encontrada = True
                print("   ✅ Tabela encontrada com XPath específico")
            except:
                print("   ⚠️ Tabela não encontrada com XPath específico, tentando alternativas...")
                
                # Tentar XPaths alternativos
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
                        tabela_xpath = alt_xpath
                        tabela_encontrada = True
                        print(f"   ✅ Tabela encontrada com XPath alternativo: {alt_xpath}")
                        break
                    except:
                        continue
            
            if not tabela_encontrada:
                print("   ❌ Nenhuma tabela de alunos encontrada")
                # Tira screenshot para debug
                self.driver.save_screenshot("debug_tabela_alunos.png")
                print("   📸 Screenshot salvo como 'debug_tabela_alunos.png'")
                return []
            
            # Obter todas as linhas da tabela (máximo 50 alunos)
            alunos = []
            for linha in range(1, 51):  # tr[1] até tr[50]
                try:
                    # XPath da linha do aluno
                    linha_xpath = f"{tabela_xpath}/tr[{linha}]"
                    
                    # Verificar se a linha existe
                    linha_element = self.driver.find_element(By.XPATH, linha_xpath)
                    
                    # Obter data-ri
                    data_ri = linha_element.get_attribute("data-ri")
                    if data_ri is None or data_ri == "":
                        data_ri = str(linha - 1)
                    
                    # Obter nome do aluno (coluna 3 - estudante)
                    nome_xpath = f"{linha_xpath}/td[3]"
                    nome_element = self.driver.find_element(By.XPATH, nome_xpath)
                    nome_aluno = nome_element.text.strip()
                    
                    if nome_aluno:  # Se tem nome, é um aluno válido
                        # XPath do botão de aba de notas (coluna 2, 3º link)
                        aba_notas_xpath = f"{linha_xpath}/td[2]/a[3]"
                        
                        aluno_info = {
                            "nome": nome_aluno,
                            "linha": linha,
                            "xpath_aba_notas": aba_notas_xpath,
                            "linha_xpath": linha_xpath,
                            "data_ri": data_ri
                        }
                        
                        # Se mapa_colunas foi fornecido, coletar notas
                        if mapa_colunas:
                            notas_preview = self._coletar_notas_preview(data_ri, mapa_colunas)
                            aluno_info["notas_preview"] = notas_preview
                            
                            # Formatar notas para exibição
                            notas_str = ", ".join([f"{k}={v if v else '∅'}" for k, v in notas_preview.items()])
                            print(f"     👤 Aluno {linha}: {nome_aluno} (data-ri={data_ri}) → {notas_str}")
                        else:
                            print(f"     👤 Aluno {linha}: {nome_aluno} (data-ri={data_ri})")
                        
                        alunos.append(aluno_info)
                    
                except:
                    # Linha não existe ou está vazia, parar busca
                    break
            
            return alunos
            
        except Exception as e:
            print(f"   ❌ Erro ao obter lista de alunos: {str(e)}")
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
            
            # Clicar no botão da aba de notas
            aba_notas_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, aluno_info["xpath_aba_notas"]))
            )
            
            # Scroll até o elemento
            self.driver.execute_script("arguments[0].scrollIntoView(true);", aba_notas_button)
            time.sleep(0.5)
            
            aba_notas_button.click()
            
            # Aguardar modal/aba carregar
            time.sleep(2)
            
            print(f"     ✅ Aba de notas acessada")
            return True
            
        except Exception as e:
            print(f"     ❌ Erro ao acessar aba de notas: {str(e)}")
            return False
    
    def _preencher_observacoes_atitudes(self, opcao_atitude="Raramente"):
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
                
                for i, linha_element in enumerate(linhas):
                    try:
                        data_ri = linha_element.get_attribute("data-ri")
                        print(f"       📝 Processando linha {i+1} (data-ri={data_ri})")
                        
                        # Procurar select nativo diretamente usando o ID específico
                        select_id = f"formAtitudes:panelAtitudes:dataTableAtitudes:{data_ri}:observacaoAtitude_input"
                        select_xpath = f"//select[@id='{select_id}']"
                        
                        try:
                            select_element = self.driver.find_element(By.XPATH, select_xpath)
                            
                            # Scroll até o elemento
                            self.driver.execute_script("arguments[0].scrollIntoView(true);", select_element)
                            time.sleep(0.2)
                            
                            # Verificar valor atual usando JavaScript (select está oculto)
                            valor_atual = self.driver.execute_script("return arguments[0].value;", select_element)
                            print(f"       📋 Valor atual: {valor_atual}")
                            
                            # Mapear opção para o valor exato esperado no select
                            opcoes_mapeadas = {
                                "Sempre": "Sempre",
                                "Às vezes": "Às vezes",
                                "As vezes": "Às vezes",  # Tolerância a erros de acentuação
                                "Vezes": "Às vezes",     # Tolerância a variações
                                "Raramente": "Raramente",
                                "Nunca": "Nunca",
                                "Não conseguiu observar": "Não conseguiu observar",
                                "Nao conseguiu observar": "Não conseguiu observar",
                                "Não se aplica": "Não se aplica",
                                "Nao se aplica": "Não se aplica"
                            }
                            
                            # Obter valor mapeado ou usar o valor original
                            valor_para_preencher = opcoes_mapeadas.get(opcao_atitude, opcao_atitude)
                            
                            if valor_atual != valor_para_preencher:
                                # Usar JavaScript para alterar o valor do select oculto
                                self.driver.execute_script(f"arguments[0].value = '{valor_para_preencher}';", select_element)
                                
                                # Disparar evento change para atualizar a interface
                                self.driver.execute_script("""
                                    var event = new Event('change', { bubbles: true });
                                    arguments[0].dispatchEvent(event);
                                """, select_element)
                                
                                print(f"       ✓ Atitude {i+1}: '{opcao_atitude}' selecionado (JavaScript)")
                                atitudes_preenchidas += 1
                                time.sleep(0.5)  # Aguardar processamento
                            else:
                                print(f"       ✓ Atitude {i+1}: Já estava '{opcao_atitude}'")
                                atitudes_preenchidas += 1
                            
                        except Exception as select_error:
                            print(f"       ❌ Erro ao selecionar '{opcao_atitude}' na linha {i+1}: {str(select_error)}")
                    
                    except Exception as linha_error:
                        print(f"       ❌ Erro ao processar linha {i+1}: {str(linha_error)}")
                        continue
                        
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
        
        Args:
            opcao_conceito (str): Opção a ser selecionada para todos os conceitos
        
        Este método:
        1. Expande a seção de Conceitos de Habilidades
        2. Preenche cada conceito com a opção escolhida
        
        Returns:
            bool: True se conseguiu preencher, False caso contrário
        """
        try:
            print(f"     📝 Preenchendo conceitos de habilidades com '{opcao_conceito}'...")
            
            # As seções já estão expandidas no modal, não precisa expandir
            print(f"     📝 Processando conceitos de habilidades (seções já expandidas)...")
            
            # XPath base da tabela de conceitos de habilidades (ui-datatable-data)
            tabela_habilidades_xpath = "//tbody[@id='formAtitudes:panelAtitudes:dataTableHabilidades_data']"
            
            # Aguardar tabela carregar após expansão
            print(f"     🔍 Procurando tabela de conceitos de habilidades...")
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, tabela_habilidades_xpath))
            )
            print(f"     ✅ Tabela de conceitos encontrada")
            
            # Processar cada linha de conceito de habilidade usando data-ri
            habilidades_preenchidas = 0
            
            # Obter todas as linhas da tabela
            try:
                linhas = self.driver.find_elements(By.XPATH, f"{tabela_habilidades_xpath}/tr[@data-ri]")
                total_linhas = len(linhas)
                print(f"     📊 Encontradas {total_linhas} linhas de conceitos de habilidades")
                
                for i, linha_element in enumerate(linhas):
                    try:
                        data_ri = linha_element.get_attribute("data-ri")
                        print(f"       📝 Processando linha {i+1} (data-ri={data_ri})")
                        
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
                            print(f"       📋 Valor atual: {valor_atual}")
                            
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
                                
                                print(f"       ✓ Habilidade {i+1}: '{valor_para_preencher}' selecionado (JavaScript)")
                                habilidades_preenchidas += 1
                                time.sleep(0.5)  # Aguardar processamento
                            else:
                                print(f"       ✓ Habilidade {i+1}: Já estava '{valor_para_preencher}'")
                                habilidades_preenchidas += 1
                            
                        except Exception as select_error:
                            print(f"       ❌ Erro ao selecionar '{opcao_conceito}' na linha {i+1}: {str(select_error)}")
                    
                    except Exception as linha_error:
                        print(f"       ❌ Erro ao processar linha {i+1}: {str(linha_error)}")
                        continue
                        
            except Exception as tabela_error:
                print(f"     ❌ Erro ao processar tabela de habilidades: {str(tabela_error)}")
            
            print(f"     ✅ {habilidades_preenchidas} conceitos de habilidades preenchidos")
            return habilidades_preenchidas > 0
            
        except Exception as e:
            print(f"     ❌ Erro ao preencher conceitos de habilidades: {str(e)}")
            return False
    
    def _fechar_modal_conceitos(self):
        """
        Fecha a modal de conceitos/atitudes usando ESC
        O sistema salva automaticamente, então só precisa fechar a modal
        
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
                print(f"     ✅ Modal fechada com ESC (salvamento automático)")
                time.sleep(1)
                return True
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
        habilidades = {}  # {identificador_cabecalho: [habilidades]}
        av_original_para_cabecalho = {}  # {AV4: AV1, AV5: AV2}
        
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
                habilidades[ident_cabecalho_match] = habilidades_coletadas
                
                # AVISO: Se não há habilidades, o conceito padrão será usado
                if not habilidades_coletadas or len(habilidades_coletadas) == 0:
                    print(f"   ⚠️ {ident_original} não tem habilidades vinculadas - usará conceito padrão")
            else:
                print(f"   ⚠️ {ident_original} ({data_av} - {titulo_av}) não encontrado nos cabeçalhos (trimestre diferente)")
                continue
        
        # Mapear recuperações para cabeçalhos
        recuperacao_por_av = {}  # {identificador_cabecalho_av: identificador_cabecalho_rp}
        
        for rec_id, rec_info in dados_recuperacoes.items():
            data_rec = rec_info.get("data", "")
            titulo_rec = rec_info.get("titulo", "")
            origem = rec_info.get("origem")  # Ex: "AV5"
            
            # Buscar match pelo (data, titulo)
            ident_cabecalho_rec = None
            for ident_cabecalho, (data_cab, titulo_cab) in tooltip_map.items():
                if data_rec == data_cab and titulo_rec == titulo_cab:
                    ident_cabecalho_rec = ident_cabecalho
                    break
            
            if ident_cabecalho_rec:
                idx_coluna = cabecalhos["identificadores"].index(ident_cabecalho_rec)
                colunas[ident_cabecalho_rec] = idx_coluna
                print(f"   ✓ Match: {rec_id} ({titulo_rec}) → {ident_cabecalho_rec} (coluna {idx_coluna})")
                
                # Mapear recuperação para a avaliação de origem
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

    def _coletar_notas_aluno(self, aluno_info, mapa_colunas):
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
            print(f"     📋 Avaliações/Recuperações a coletar: {list(mapa_colunas.keys())}")

            # Iterar sobre cada avaliação/recuperação mapeada
            for ident, idx in sorted(mapa_colunas.items(), key=lambda x: x[1]):
                indice_coluna = idx + 3  # +3: #, Ação, Estudante
                
                # XPATH para o <select> oculto
                select_xpath = f"//tbody[@id='tabViewDiarioClasse:formAbaConceitos:dataTableConceitos_data']/tr[@data-ri='{data_ri}']/td[{indice_coluna + 1}]//select[contains(@id, '_input')]"
                
                try:
                    select = self.driver.find_element(By.XPATH, select_xpath)
                    
                    # Verificar se está disabled
                    if select.get_attribute("disabled"):
                        notas[ident] = ""
                        print(f"        🔒 {ident}: desabilitado (evadido/transferido)")
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
                            notas[ident] = ""
                            print(f"        ⚪ {ident}: (vazio)")
                    except:
                        # Se não tem option selected, está vazio
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
        
        Para cada habilidade na modal:
        1. Identifica a qual avaliação ela pertence
        2. Busca a nota do aluno naquela avaliação
        3. Se tem recuperação, usa a nota da recuperação
        4. Se não encontrou mapeamento, deixa vazio
        """
        preenchidos = 0

        try:
            print(f"     📝 Preenchendo conceitos de habilidades baseado nas notas...")
            
            # Re-localizar a tabela para evitar stale element
            tabela_xpath = "//tbody[@id='formAtitudes:panelAtitudes:dataTableHabilidades_data']/tr[@data-ri]"
            linhas = WebDriverWait(self.driver, 5).until(
                EC.presence_of_all_elements_located((By.XPATH, tabela_xpath))
            )
            
            print(f"     📋 Total de habilidades encontradas: {len(linhas)}")

            for idx, linha in enumerate(linhas):
                try:
                    # Re-localizar a linha para evitar stale element
                    linhas_atualizadas = self.driver.find_elements(By.XPATH, tabela_xpath)
                    if idx >= len(linhas_atualizadas):
                        continue
                    linha = linhas_atualizadas[idx]
                    
                    data_ri = linha.get_attribute("data-ri")
                    cols = linha.find_elements(By.TAG_NAME, "td")
                    
                    if len(cols) < 3:
                        continue
                        
                    competencia_texto = cols[1].text.strip()
                    habilidade_texto = cols[2].text.strip()
                    
                except Exception as e:
                    print(f"       ⚠️ Erro ao ler linha {idx}: {e}")
                    continue

                conceito = ""  # Vazio por padrão
                av_utilizada = None
                tipo_origem = None
                
                # Procurar em qual avaliação esta habilidade está vinculada
                for av, habilidades_av in mapeamentos["habilidades"].items():
                    if any(self._texto_corresponde(habilidade_texto, h["habilidade"]) for h in habilidades_av):
                        # Encontrou! Esta habilidade pertence a esta avaliação
                        conceito_av = notas_aluno.get(av, "")
                        if conceito_av:
                            conceito = conceito_av
                            av_utilizada = av
                            tipo_origem = "avaliação"

                        # Verificar se tem recuperação para esta avaliação
                        recuperacao = mapeamentos["recuperacao_por_avaliacao"].get(av)
                        if recuperacao:
                            conceito_rec = notas_aluno.get(recuperacao, "")
                            if conceito_rec:
                                conceito = conceito_rec
                                av_utilizada = recuperacao
                                tipo_origem = "recuperação"

                        break

                # Preparar mensagem detalhada
                habilidade_curta = habilidade_texto[:50] if len(habilidade_texto) > 50 else habilidade_texto
                
                if av_utilizada and conceito:
                    print(f"       📌 Habilidade: {habilidade_curta}")
                    print(f"          🔗 Vinculada à: {av_utilizada} ({tipo_origem})")
                    print(f"          📊 Nota do aluno: '{conceito}'")
                elif av_utilizada and not conceito:
                    print(f"       📌 Habilidade: {habilidade_curta}")
                    print(f"          🔗 Vinculada à: {av_utilizada}")
                    print(f"          ⚪ Aluno não tem nota (deixando vazio)")
                    continue  # Pula, não preenche nada
                else:
                    print(f"       📌 Habilidade: {habilidade_curta}")
                    print(f"          ⚠️ Não encontrada em nenhuma avaliação (deixando vazio)")
                    continue  # Pula, não preenche nada

                # Aplicar o conceito
                select_id = f"formAtitudes:panelAtitudes:dataTableHabilidades:{data_ri}:notaConceito_input"
                try:
                    # Re-localizar o select para evitar stale element
                    select_element = WebDriverWait(self.driver, 3).until(
                        EC.presence_of_element_located((By.ID, select_id))
                    )
                    valor_atual = select_element.get_attribute("value") or ""
                    
                    if valor_atual != conceito:
                        self.driver.execute_script("arguments[0].value = arguments[1];", select_element, conceito)
                        self.driver.execute_script(
                            "arguments[0].dispatchEvent(new Event('change', { bubbles: true }));",
                            select_element,
                        )
                        print(f"          ✅ Conceito '{conceito}' aplicado!")
                        preenchidos += 1
                        time.sleep(0.2)
                    else:
                        print(f"          ℹ️ Conceito '{conceito}' já estava aplicado")
                        preenchidos += 1
                        
                except Exception as select_error:
                    print(f"          ❌ Erro ao aplicar conceito: {select_error}")

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
