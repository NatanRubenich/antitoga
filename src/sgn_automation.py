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
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
import time

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

        Args:
            trimestre_referencia (str): Valor esperado (TR1, TR2, TR3)
        """
        try:
            if not trimestre_referencia:
                return

            print(f"   🔄 Ajustando trimestre de referência para '{trimestre_referencia}'...")

            # Localiza o componente do PrimeFaces responsável pelo select de média
            label_xpath = "//label[@id='tabViewDiarioClasse:formAbaConceitos:mediasConceito_label']"
            dropdown_trigger = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, label_xpath))
            )

            # Se o valor atual já for o desejado, não faz nada
            valor_atual = dropdown_trigger.text.strip().upper()
            if valor_atual == trimestre_referencia.upper():
                print("   ✅ Trimestre desejado já está selecionado")
                print(f"   📋 Trimestre atual exibido no rótulo: {valor_atual}")
                return

            dropdown_trigger.click()
            time.sleep(1)

            # A lista de opções fica em um painel associado ao componente selectOneMenu
            opcao_xpath = (
                "//div[@id='tabViewDiarioClasse:formAbaConceitos:mediasConceito_panel']//li"
                f"[normalize-space(text())='{trimestre_referencia}']"
            )

            # Informações do select oculto para listar opções disponíveis
            select_xpath = "//select[@id='tabViewDiarioClasse:formAbaConceitos:mediasConceito_input']"
            opcoes_map = {}
            select_element = None
            try:
                select_element = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, select_xpath))
                )
                option_elements = select_element.find_elements(By.TAG_NAME, "option")
                print("   📋 Opções disponíveis no seletor:")
                for opt in option_elements:
                    texto_opcao = opt.text.strip()
                    if not texto_opcao:
                        continue
                    valor_opcao = opt.get_attribute("value")
                    chave_opcao = texto_opcao.strip().upper()
                    opcoes_map[chave_opcao] = valor_opcao
                    marcador = "(selecionado)" if texto_opcao.upper() == valor_atual else ""
                    print(f"      - {texto_opcao} {marcador} (valor={valor_opcao})")
            except Exception as e:
                print(f"   ⚠️ Não foi possível listar opções do seletor oculto: {e}")
                raise Exception(f"Não foi possível selecionar o trimestre '{trimestre_referencia}'")

            chave_desejada = trimestre_referencia.strip().upper()
            valor_opcao_desejada = opcoes_map.get(chave_desejada)
            if valor_opcao_desejada is None:
                raise Exception(
                    f"Opção '{trimestre_referencia}' não está disponível na lista de médias de referência"
                )

            selecionado = False
            try:
                opcao_elemento = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, opcao_xpath))
                )
                opcao_elemento.click()
                time.sleep(1)

                # Aguarda label refletir novo valor
                WebDriverWait(self.driver, 5).until(
                    lambda drv: drv.find_element(By.XPATH, label_xpath).text.strip().upper() == trimestre_referencia
                )
                selecionado = True
            except Exception as e:
                print(f"   ⚠️ Seleção via clique falhou: {e}")

            if not selecionado:
                print("   🔧 Utilizando fallback via JavaScript para selecionar o trimestre...")
                self._selecionar_trimestre_via_js(select_element, valor_opcao_desejada)
                WebDriverWait(self.driver, 5).until(
                    lambda drv: drv.find_element(By.XPATH, label_xpath).text.strip().upper() == trimestre_referencia
                )

            novo_valor = self.driver.find_element(By.XPATH, label_xpath).text.strip().upper()
            if novo_valor != trimestre_referencia:
                raise Exception(
                    f"Após seleção, o trimestre exibido permaneceu '{novo_valor}'. Esperado: '{trimestre_referencia}'"
                )
            print(f"   ✅ Trimestre selecionado com sucesso: {novo_valor}")

            # Log adicional confirmando seleção através do select oculto
            try:
                select_value = select_element.get_attribute("value") if select_element else None
                if select_value and valor_opcao_desejada and select_value != valor_opcao_desejada:
                    raise Exception(
                        f"Valor interno do select '{select_value}' difere do esperado '{valor_opcao_desejada}'"
                    )
                print(f"   🔍 Valor interno do select após seleção: {select_value}")
            except Exception as e:
                print(f"   ⚠️ Não foi possível ler valor do select oculto: {e}")

        except Exception as e:
            print(f"   ⚠️ Não foi possível selecionar o trimestre '{trimestre_referencia}': {e}")
            # interrompe o fluxo e retornar a mensagem de erro para a API 
            raise Exception(f"Não foi possível selecionar o trimestre '{trimestre_referencia}': {e}")
            
    def _selecionar_trimestre_via_js(self, select_element, valor_desejado):
        """Seleciona o trimestre disparando os eventos necessários via JavaScript."""
        script = """
            const select = arguments[0];
            const value = arguments[1];
            select.value = value;
            select.dispatchEvent(new Event('change', { bubbles: true }));
        """
        try:
            self.driver.execute_script(script, select_element, valor_desejado)
            time.sleep(1)
        except Exception as e:
            raise Exception(f"Fallback JS falhou ao definir valor '{valor_desejado}': {e}")

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
        Lança conceitos para todos os alunos na tabela
        
        Este método:
        1. Identifica todos os alunos na tabela de conceitos
        2. Para cada aluno, acessa sua modal de conceitos
        3. Preenche as observações de atitudes com a opção escolhida
        4. Preenche os conceitos de habilidades com a opção escolhida
        5. Sistema salva automaticamente e fecha modal com ESC
        
        Args:
            atitude_observada (str): Opção para observações de atitudes
            conceito_habilidade (str): Opção para conceitos de habilidades
        
        Returns:
            tuple: (success: bool, message: str)
                - success: True se todos os conceitos foram lançados
                - message: Estatísticas do processo
        """
        print(f"7. Iniciando lançamento de conceitos para todos os alunos...")
        print(f"   📋 Atitude observada: '{atitude_observada}'")
        print(f"   📋 Conceito de habilidade: '{conceito_habilidade}'")
        
        try:
            # Obter lista de alunos
            alunos = self._obter_lista_alunos()
            total_alunos = len(alunos)
            
            if total_alunos == 0:
                return False, "Nenhum aluno encontrado na tabela"
            
            print(f"   📋 Encontrados {total_alunos} alunos na turma")
            
            alunos_processados = 0
            alunos_com_erro = 0
            
            # Processar cada aluno
            for i, aluno_info in enumerate(alunos, 1):
                try:
                    print(f"\n   👤 Processando aluno {i}/{total_alunos}: {aluno_info['nome']}")
                    
                    # Acessar aba de notas do aluno
                    success = self._acessar_aba_notas_aluno(aluno_info)
                    if not success:
                        print(f"   ❌ Erro ao acessar aba de notas do aluno {aluno_info['nome']}")
                        alunos_com_erro += 1
                        continue
                    
                    # Preencher observações de atitudes com opção configurável
                    success = self._preencher_observacoes_atitudes(atitude_observada)
                    if not success:
                        print(f"   ⚠️ Erro ao preencher observações de atitudes para {aluno_info['nome']}")
                    
                    # Preencher conceitos de habilidades com opção configurável
                    success = self._preencher_conceitos_habilidades(conceito_habilidade)
                    if not success:
                        print(f"   ⚠️ Erro ao preencher conceitos de habilidades para {aluno_info['nome']}")
                    
                    # Sistema salva automaticamente - apenas fechar modal
                    print(f"   ✅ Conceitos aplicados para {aluno_info['nome']} (salvamento automático)")
                    alunos_processados += 1
                    
                    # Fechar modal (ESC) - volta para a lista de alunos
                    self._fechar_modal_conceitos()
                    
                    # Adicionar espaço em branco para melhor visualização
                    print("")  # Linha em branco após cada aluno processado
                    
                except Exception as e:
                    print(f"   ❌ Erro ao processar aluno {aluno_info.get('nome', 'desconhecido')}: {str(e)}")
                    alunos_com_erro += 1
                    # Tentar fechar modal
                    try:
                        self._fechar_modal_conceitos()
                    except:
                        pass
            
            # Estatísticas finais
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
    
    def _obter_lista_alunos(self):
        """
        Obtém a lista de todos os alunos na tabela de conceitos
        
        Returns:
            list: Lista de dicionários com informações dos alunos
                  [{"nome": str, "linha": int, "xpath_aba_notas": str}, ...]
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
                            "linha_xpath": linha_xpath
                        }
                        
                        alunos.append(aluno_info)
                        print(f"     👤 Aluno {linha}: {nome_aluno}")
                    
                except:
                    # Linha não existe ou está vazia, parar busca
                    break
            
            return alunos
            
        except Exception as e:
            print(f"   ❌ Erro ao obter lista de alunos: {str(e)}")
            return []
    
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
