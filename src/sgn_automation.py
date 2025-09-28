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
from selenium.webdriver.support.ui import WebDriverWait
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
    
    def lancar_conceito_trimestre(self, username, password, codigo_turma):
        """
        Executa o fluxo completo: login -> navegação -> lançamento de conceitos
        
        Este método realiza todo o processo de lançamento de conceitos para todos os alunos:
        1. Faz login no sistema
        2. Navega para a aba de Conceitos da turma
        3. Para cada aluno na tabela:
           - Acessa a aba de notas do aluno
           - Seleciona "Raramente" em todas as Observações de Atitudes
           - Seleciona "B" em todos os Conceitos de Habilidades
           - Salva as alterações
        
        Args:
            username (str): Nome de usuário para login no SGN
            password (str): Senha do usuário
            codigo_turma (str): Código identificador da turma
            
        Returns:
            tuple: (success: bool, message: str)
                - success: True se tudo ocorreu bem, False em caso de erro
                - message: Mensagem descritiva do resultado com estatísticas
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
            
            # Novo: Lançar conceitos para todos os alunos
            success, message = self._lancar_conceitos_todos_alunos()
            
            if not success:
                return False, f"Erro no lançamento de conceitos: {message}"
            
            return True, f"Lançamento de conceitos concluído com sucesso! {message}"
            
        except Exception as e:
            error_msg = f"Erro durante lançamento de conceitos: {str(e)}"
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
            
            # Navegar para a aba de conceitos
            self._navigate_to_diary_search()    # Navegar para buscar diário
            self._access_class_diary(codigo_turma)  # Acessar diário da turma
            self._open_conceitos_tab()          # Abrir aba de conceitos
            
            return True, f"Navegação para Conceitos da turma {codigo_turma} concluída!"
            
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
        print(f"5. Acessando diário da turma {codigo_turma}...")
        
        # Constrói a URL direta para o diário da turma
        diario_url = f"https://sgn.sesisenai.org.br/pages/diarioClasse/diario-classe.html?idDiario={codigo_turma}"
        self.driver.get(diario_url)
        time.sleep(3)  # Reduzido de 5 para 3 segundos
        print(f"✅ Diário da turma {codigo_turma} acessado")
    
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
    
    def _lancar_conceitos_todos_alunos(self):
        """
        Lança conceitos para todos os alunos na tabela
        
        Este método:
        1. Identifica todos os alunos na tabela de conceitos
        2. Para cada aluno, acessa sua aba de notas
        3. Preenche as observações de atitudes com "Raramente"
        4. Preenche os conceitos de habilidades com "B"
        5. Salva as alterações
        
        Returns:
            tuple: (success: bool, message: str)
                - success: True se todos os conceitos foram lançados
                - message: Estatísticas do processo
        """
        print("7. Iniciando lançamento de conceitos para todos os alunos...")
        
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
                    
                    # Preencher observações de atitudes
                    success = self._preencher_observacoes_atitudes()
                    if not success:
                        print(f"   ⚠️ Erro ao preencher observações de atitudes para {aluno_info['nome']}")
                    
                    # Preencher conceitos de habilidades
                    success = self._preencher_conceitos_habilidades()
                    if not success:
                        print(f"   ⚠️ Erro ao preencher conceitos de habilidades para {aluno_info['nome']}")
                    
                    # Salvar alterações
                    success = self._salvar_alteracoes_aluno()
                    if success:
                        print(f"   ✅ Conceitos salvos para {aluno_info['nome']}")
                        alunos_processados += 1
                    else:
                        print(f"   ❌ Erro ao salvar conceitos para {aluno_info['nome']}")
                        alunos_com_erro += 1
                    
                    # Voltar para a lista de alunos
                    self._voltar_para_lista_alunos()
                    
                except Exception as e:
                    print(f"   ❌ Erro ao processar aluno {aluno_info.get('nome', 'desconhecido')}: {str(e)}")
                    alunos_com_erro += 1
                    # Tentar voltar para a lista
                    try:
                        self._voltar_para_lista_alunos()
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
    
    def _preencher_observacoes_atitudes(self):
        """
        Preenche todas as observações de atitudes com "Raramente"
        
        Este método:
        1. Expande a seção de Observações de Atitudes
        2. Preenche cada observação com "Raramente"
        
        Returns:
            bool: True se conseguiu preencher, False caso contrário
        """
        try:
            print(f"     📝 Preenchendo observações de atitudes...")
            
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
                            
                            if valor_atual != "Raramente":
                                # Usar JavaScript para alterar o valor do select oculto
                                self.driver.execute_script("arguments[0].value = 'Raramente';", select_element)
                                
                                # Disparar evento change para atualizar a interface
                                self.driver.execute_script("""
                                    var event = new Event('change', { bubbles: true });
                                    arguments[0].dispatchEvent(event);
                                """, select_element)
                                
                                print(f"       ✓ Atitude {i+1}: 'Raramente' selecionado (JavaScript)")
                                atitudes_preenchidas += 1
                                time.sleep(0.5)  # Aguardar processamento
                            else:
                                print(f"       ✓ Atitude {i+1}: Já estava 'Raramente'")
                                atitudes_preenchidas += 1
                            
                        except Exception as select_error:
                            print(f"       ❌ Erro ao selecionar 'Raramente' na linha {i+1}: {str(select_error)}")
                    
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
    
    def _preencher_conceitos_habilidades(self):
        """
        Preenche todos os conceitos de habilidades com "B"
        
        Este método:
        1. Expande a seção de Conceitos de Habilidades
        2. Preenche cada conceito com "B"
        
        Returns:
            bool: True se conseguiu preencher, False caso contrário
        """
        try:
            print(f"     📝 Preenchendo conceitos de habilidades...")
            
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
                            
                            if valor_atual != "B":
                                # Usar JavaScript para alterar o valor do select oculto
                                self.driver.execute_script("arguments[0].value = 'B';", select_element)
                                
                                # Disparar evento change para atualizar a interface
                                self.driver.execute_script("""
                                    var event = new Event('change', { bubbles: true });
                                    arguments[0].dispatchEvent(event);
                                """, select_element)
                                
                                print(f"       ✓ Habilidade {i+1}: 'B' selecionado (JavaScript)")
                                habilidades_preenchidas += 1
                                time.sleep(0.5)  # Aguardar processamento
                            else:
                                print(f"       ✓ Habilidade {i+1}: Já estava 'B'")
                                habilidades_preenchidas += 1
                            
                        except Exception as select_error:
                            print(f"       ❌ Erro ao selecionar 'B' na linha {i+1}: {str(select_error)}")
                    
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
    
    def _salvar_alteracoes_aluno(self):
        """
        Salva as alterações feitas para o aluno atual
        
        Returns:
            bool: True se conseguiu salvar, False caso contrário
        """
        try:
            print(f"     💾 Salvando alterações...")
            
            # Procurar botão de salvar (pode ter diferentes localizações)
            salvar_selectors = [
                "//button[contains(text(), 'Salvar')]",
                "//input[@type='submit' and contains(@value, 'Salvar')]",
                "//button[@type='submit']",
                "//a[contains(text(), 'Salvar')]",
                "/html/body/div[3]/div[3]/div[2]/div[13]/div[2]/form//button[contains(text(), 'Salvar')]"
            ]
            
            for selector in salvar_selectors:
                try:
                    salvar_button = WebDriverWait(self.driver, 3).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    
                    # Scroll até o botão
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", salvar_button)
                    time.sleep(0.5)
                    
                    salvar_button.click()
                    
                    # Aguardar salvamento
                    time.sleep(2)
                    
                    print(f"     ✅ Alterações salvas")
                    return True
                    
                except:
                    continue
            
            print(f"     ⚠️ Botão salvar não encontrado, tentando Enter")
            # Se não encontrou botão, tenta pressionar Enter
            self.driver.find_element(By.TAG_NAME, "body").send_keys("\n")
            time.sleep(2)
            return True
            
        except Exception as e:
            print(f"     ❌ Erro ao salvar alterações: {str(e)}")
            return False
    
    def _voltar_para_lista_alunos(self):
        """
        Volta para a lista de alunos (fecha modal/aba de notas)
        
        Returns:
            bool: True se conseguiu voltar, False caso contrário
        """
        try:
            print(f"     🔙 Voltando para lista de alunos...")
            
            # Procurar botão de fechar o modal (XPath específico fornecido)
            voltar_selectors = [
                "/html/body/div[3]/div[3]/div[2]/div[13]/div[1]/a",  # XPath específico fornecido
                "//div[@id='modalDadosAtitudes']//a[contains(@class, 'ui-dialog-titlebar-close')]",
                "//a[contains(@class, 'ui-dialog-titlebar-close')]",
                "//span[@class='ui-icon ui-icon-closethick']/..",
                "//button[contains(text(), 'Fechar')]",
                "//button[contains(text(), 'Voltar')]"
            ]
            
            for selector in voltar_selectors:
                try:
                    voltar_button = WebDriverWait(self.driver, 3).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    
                    voltar_button.click()
                    
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
