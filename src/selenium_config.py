"""
Configuração e gerenciamento do Selenium WebDriver

Este módulo é responsável por:
- Configurar o navegador Chrome com as opções adequadas
- Gerenciar o ciclo de vida do WebDriver (criar/fechar)
- Fornecer uma interface simples para obter o driver
- Garantir que apenas uma instância do driver seja criada
"""
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

class SeleniumManager:
    """
    Gerenciador do Selenium WebDriver
    
    Esta classe encapsula toda a lógica de configuração e gerenciamento
    do navegador Chrome, fornecendo métodos simples para:
    - Criar e configurar o driver
    - Obter o driver atual
    - Fechar o driver de forma segura
    """
    
    def __init__(self):
        """
        Inicializa o gerenciador do Selenium
        
        Attributes:
            driver: Instância do WebDriver (inicialmente None)
        """
        self.driver = None
    
    def setup_driver(self):
        """
        Configura e inicializa o driver do Chrome
        
        Este método:
        1. Define as opções do Chrome para melhor performance e compatibilidade
        2. Usa o WebDriverManager para baixar automaticamente o ChromeDriver
        3. Cria a instância do WebDriver com as configurações
        4. Define timeout implícito para encontrar elementos
        
        Returns:
            webdriver.Chrome: Instância configurada do driver do Chrome
            
        Raises:
            Exception: Se houver erro na configuração do driver
        """
        # Configurações do Chrome para melhor performance e compatibilidade
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")  # Necessário em alguns ambientes
        chrome_options.add_argument("--disable-dev-shm-usage")  # Evita problemas de memória
        chrome_options.add_argument("--window-size=1920,1080")  # Define tamanho da janela
        # chrome_options.add_argument("--headless")  # Descomente para modo headless (sem interface)
        
        # Usa WebDriverManager para baixar automaticamente o ChromeDriver compatível
        service = Service(ChromeDriverManager().install())
        
        # Cria a instância do WebDriver com as configurações
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Define timeout implícito de 10 segundos para encontrar elementos
        self.driver.implicitly_wait(10)
        
        print("✅ Driver do Chrome configurado com sucesso")
        return self.driver
    
    def close_driver(self):
        """
        Fecha o driver de forma segura
        
        Este método:
        1. Verifica se existe um driver ativo
        2. Tenta fechar o driver usando quit() (fecha todas as janelas)
        3. Define self.driver como None para liberar a referência
        4. Trata exceções que podem ocorrer durante o fechamento
        
        Note:
            É importante sempre fechar o driver para liberar recursos do sistema
        """
        if self.driver:
            try:
                self.driver.quit()  # Fecha todas as janelas e encerra o processo
                self.driver = None  # Remove a referência
                print("✅ Driver fechado com sucesso")
            except Exception as e:
                print(f"⚠️ Erro ao fechar driver: {e}")
    
    def get_driver(self):
        """
        Retorna o driver atual ou cria um novo se não existir
        
        Este método implementa o padrão Lazy Loading:
        - Se já existe um driver, retorna ele
        - Se não existe, cria um novo driver e retorna
        
        Returns:
            webdriver.Chrome: Instância do driver do Chrome
            
        Note:
            Este método garante que sempre haverá um driver disponível
            sem criar múltiplas instâncias desnecessárias
        """
        if self.driver is None:
            return self.setup_driver()
        return self.driver
