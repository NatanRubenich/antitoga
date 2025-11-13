"""
Métodos auxiliares para aprimoramento da automação SGN

Este módulo contém métodos auxiliares que suportam as melhorias implementadas
no sistema de lançamento de conceitos, incluindo validações, retry e logging.
"""

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import requests
import threading
import concurrent.futures
from queue import Queue


class SGNAutomationHelpers:
    """Classe com métodos auxiliares para automação SGN"""
    
    def __init__(self, selenium_manager):
        self.selenium_manager = selenium_manager
        self.driver = None
        # Cache para otimização de performance
        self._cached_cookies = None
        self._cached_headers = None
        self._cached_url = None
        self._cache_timestamp = 0
        # Rate limiting para evitar erro 500
        self._last_request_time = 0
        self._min_request_interval = 0.5  # 500ms entre requisições
        # Cache global de contadores (todos os alunos têm a mesma quantidade)
        self._cache_total_atitudes = None
        self._cache_total_conceitos = None
        self._cache_contadores_timestamp = 0
        # Cache de estrutura de capacidades (todos alunos têm a mesma estrutura)
        self._cache_capacidades_expandidas = False
        self._cache_estrutura_capacidades = None
    
    def _get_driver(self):
        """Obtém o driver atual"""
        if not self.driver:
            self.driver = self.selenium_manager.get_driver()
        return self.driver
    
    def _get_cached_request_data(self, force_refresh=False):
        """
        Obtém dados de requisição em cache (cookies, headers, URL) para otimizar performance
        
        Args:
            force_refresh (bool): Forçar atualização do cache
            
        Returns:
            tuple: (cookies, headers, url)
        """
        current_time = time.time()
        
        # Cache válido por 30 segundos
        if (not force_refresh and 
            self._cached_cookies and 
            self._cached_headers and 
            self._cached_url and 
            current_time - self._cache_timestamp < 30):
            return self._cached_cookies, self._cached_headers, self._cached_url
        
        # Atualizar cache
        driver = self._get_driver()
        
        self._cached_cookies = {cookie['name']: cookie['value'] for cookie in driver.get_cookies()}
        self._cached_url = driver.current_url.split('?')[0]
        self._cached_headers = {
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'X-Requested-With': 'XMLHttpRequest',
            'Faces-Request': 'partial/ajax',
            'User-Agent': driver.execute_script("return navigator.userAgent;"),
            'Referer': driver.current_url
        }
        self._cache_timestamp = current_time
        
        return self._cached_cookies, self._cached_headers, self._cached_url
    
    def _get_contadores_globais(self, force_refresh=False):
        """
        Obtém contadores globais de atitudes e conceitos (cache por sessão)
        Como todos os alunos têm a mesma quantidade, só precisa verificar uma vez
        
        Args:
            force_refresh (bool): Forçar nova contagem
            
        Returns:
            tuple: (total_atitudes, total_conceitos)
        """
        current_time = time.time()
        
        # Cache válido por toda a sessão (até forçar refresh)
        if (not force_refresh and 
            self._cache_total_atitudes is not None and 
            self._cache_total_conceitos is not None and 
            current_time - self._cache_contadores_timestamp < 3600):  # 1 hora
            return self._cache_total_atitudes, self._cache_total_conceitos
        
        try:
            print("   🔢 Descobrindo contadores globais (primeira vez na sessão)...")
            driver = self._get_driver()
            
            # Contar atitudes
            try:
                atitudes_elements = driver.find_elements(By.CSS_SELECTOR, "select[id*='observacaoAtitude']")
                total_atitudes = len(atitudes_elements)
                print(f"   📊 Total de atitudes por aluno: {total_atitudes}")
            except:
                total_atitudes = 119  # Fallback baseado nos logs
                print(f"   ⚠️ Usando fallback para atitudes: {total_atitudes}")
            
            # Contar conceitos de habilidades
            try:
                conceitos_elements = driver.find_elements(By.CSS_SELECTOR, "select[id*='notaConceito']")
                total_conceitos = len(conceitos_elements)
                print(f"   📊 Total de conceitos por aluno: {total_conceitos}")
            except:
                total_conceitos = 10  # Fallback baseado nos logs
                print(f"   ⚠️ Usando fallback para conceitos: {total_conceitos}")
            
            # Salvar no cache
            self._cache_total_atitudes = total_atitudes
            self._cache_total_conceitos = total_conceitos
            self._cache_contadores_timestamp = current_time
            
            print(f"   ✅ Contadores globais cached: {total_atitudes} atitudes, {total_conceitos} conceitos")
            return total_atitudes, total_conceitos
            
        except Exception as e:
            print(f"   ❌ Erro ao obter contadores globais: {e}")
            # Usar fallbacks se der erro
            return 119, 10
    
    def _verificar_atitudes_pendentes_otimizado(self, opcao_atitude, max_atitudes):
        """
        Verifica quais atitudes estão pendentes usando contadores globais
        
        Args:
            opcao_atitude (str): Valor da atitude desejada
            max_atitudes (int): Total de atitudes (do cache global)
            
        Returns:
            list: Lista de índices das atitudes pendentes
        """
        print(f"   🔍 Verificando {max_atitudes} atitudes (usando cache global)...")
        atitudes_pendentes = []
        atitudes_ja_preenchidas = 0
        
        try:
            driver = self._get_driver()
            
            for i in range(max_atitudes):
                try:
                    select_id = f"formAtitudes:panelAtitudes:dataTableAtitudes:{i}:observacaoAtitude_input"
                    select_element = driver.find_element(By.ID, select_id)
                    valor_atual = select_element.get_attribute("value")
                    
                    # Verificar se já tem o valor correto
                    if valor_atual != opcao_atitude:
                        atitudes_pendentes.append(i)
                    else:
                        atitudes_ja_preenchidas += 1
                except:
                    # Se não conseguir verificar, assumir que precisa processar
                    atitudes_pendentes.append(i)
            
            print(f"   📊 {len(atitudes_pendentes)} atitudes pendentes de {max_atitudes} total ({atitudes_ja_preenchidas} já preenchidas)")
            return atitudes_pendentes
            
        except Exception as e:
            print(f"   ❌ Erro ao verificar atitudes: {e}")
            # Se der erro, assumir que todas precisam ser processadas
            return list(range(max_atitudes))
    
    def _expandir_capacidades_uma_vez(self):
        """
        Expande capacidades apenas uma vez por sessão (todos alunos têm a mesma estrutura)
        
        Returns:
            bool: True se capacidades foram expandidas ou já estavam expandidas
        """
        # Se já expandiu nesta sessão, não fazer novamente
        if self._cache_capacidades_expandidas:
            print("   ✅ Capacidades já expandidas nesta sessão (usando cache)")
            return True
        
        try:
            print("   🔍 Expandindo capacidades pela primeira vez na sessão...")
            driver = self._get_driver()
            
            capacidades_expandidas = 0
            
            # Procurar por painéis/accordions que podem conter capacidades
            accordion_selectors = [
                "//div[contains(@class, 'ui-accordion-header')]",
                "//div[contains(@id, 'capacidade') or contains(@class, 'capacidade')]",
                "//div[contains(@id, 'painel') or contains(@class, 'painel')]",
                "//h3[contains(text(), 'Capacidade') or contains(text(), 'C1') or contains(text(), 'C2') or contains(text(), 'C3')]",
                "//div[contains(@class, 'ui-fieldset-legend')]"
            ]
            
            for selector in accordion_selectors:
                try:
                    elementos = driver.find_elements(By.XPATH, selector)
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
                                        driver.execute_script("arguments[0].scrollIntoView(true);", elemento)
                                        time.sleep(0.5)
                                        driver.execute_script("arguments[0].click();", elemento)
                                        time.sleep(1)
                                        
                                        capacidades_expandidas += 1
                                        print(f"     ✅ Painel expandido: {texto[:30]}")
                                    else:
                                        print(f"     ✓ Painel já expandido: {texto[:30]}")
                                        capacidades_expandidas += 1
                                        
                        except Exception as e:
                            print(f"     ⚠️ Erro ao processar elemento: {e}")
                            continue
                            
                except Exception as e:
                    print(f"     ⚠️ Erro com seletor {selector}: {e}")
                    continue
            
            # Marcar como expandido para não repetir
            self._cache_capacidades_expandidas = True
            self._cache_estrutura_capacidades = capacidades_expandidas
            
            if capacidades_expandidas > 0:
                print(f"   ✅ {capacidades_expandidas} capacidades expandidas e cached para toda a sessão")
            else:
                print(f"   ℹ️ Nenhuma capacidade adicional encontrada para expandir")
            
            return True
            
        except Exception as e:
            print(f"   ❌ Erro ao expandir capacidades: {e}")
            return False
    
    def _rate_limit_request(self):
        """
        Implementa rate limiting para evitar sobrecarregar o servidor SGN
        """
        current_time = time.time()
        time_since_last_request = current_time - self._last_request_time
        
        if time_since_last_request < self._min_request_interval:
            sleep_time = self._min_request_interval - time_since_last_request
            time.sleep(sleep_time)
        
        self._last_request_time = time.time()
    
    def _detectar_sessao_expirada(self, response_text):
        """
        Detecta se a sessão expirou baseado na resposta do servidor
        
        Args:
            response_text (str): Texto da resposta HTTP
            
        Returns:
            bool: True se sessão expirou, False caso contrário
        """
        indicadores_sessao_expirada = [
            'Oops! Ocorreu um erro ao carregar essa página',
            'logic:notAuthenticated',
            'login.html',
            'autenticacao',
            'session expired',
            'sessão expirou',
            'redirect url="/login.html"',
            'redirect url="/errors/403.html"'
        ]
        
        response_lower = response_text.lower()
        for indicador in indicadores_sessao_expirada:
            if indicador.lower() in response_lower:
                return True
        
        return False
    
    def _tentar_renovar_sessao(self):
        """
        Tenta renovar a sessão navegando para a página principal
        
        Returns:
            bool: True se conseguiu renovar, False caso contrário
        """
        try:
            print("   🔄 Tentando renovar sessão...")
            driver = self._get_driver()
            
            # Navegar para página principal do SGN
            driver.get("https://sgn.sesisenai.org.br/pages/diarioClasse/diario-classe.html")
            
            # Aguardar carregamento
            time.sleep(3)
            
            # Verificar se conseguiu acessar
            current_url = driver.current_url
            if "diario-classe.html" in current_url and "login" not in current_url:
                print("   ✅ Sessão renovada com sucesso")
                # Limpar cache para forçar atualização
                self._cached_cookies = None
                self._cached_headers = None
                self._cached_url = None
                return True
            else:
                print(f"   ❌ Falha ao renovar sessão - URL atual: {current_url}")
                return False
                
        except Exception as e:
            print(f"   ❌ Erro ao tentar renovar sessão: {e}")
            return False
    
    def _validar_elementos_conceitos(self):
        """
        Valida se os elementos necessários para lançamento de conceitos estão presentes
        Baseado na estrutura HTML real do SGN com PrimeFaces
        
        Returns:
            bool: True se todos os elementos estão presentes, False caso contrário
        """
        try:
            driver = self._get_driver()
            
            print("      🔍 Verificando se estamos na página correta...")
            # Verificar se estamos na página de conceitos
            current_url = driver.current_url
            if "diario-classe.html" not in current_url:
                print(f"      ❌ Não estamos na página de diário. URL atual: {current_url}")
                return False
            
            print("      🔍 Aguardando página carregar completamente...")
            # Aguardar um pouco para a página carregar
            import time
            time.sleep(3)
            
            print("      🔍 Verificando estrutura PrimeFaces da tabela de conceitos...")
            # Seletores baseados na estrutura HTML real do SGN
            seletores_sgn = [
                # Seletor principal - tbody com dados dos alunos
                "#tabViewDiarioClasse\\:formAbaConceitos\\:dataTableConceitos_data",
                # Alternativo - div scrollável com tabela
                ".ui-datatable-scrollable-body table tbody",
                # Genérico - qualquer tbody com classe ui-datatable-data
                "tbody.ui-datatable-data",
                # Fallback - tabela com role grid
                "table[role='grid'] tbody"
            ]
            
            tabela_encontrada = False
            seletor_usado = None
            
            for seletor in seletores_sgn:
                try:
                    wait = WebDriverWait(driver, 5)
                    tabela = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, seletor)))
                    print(f"      ✅ Tabela SGN encontrada com seletor: {seletor}")
                    tabela_encontrada = True
                    seletor_usado = seletor
                    break
                except TimeoutException:
                    print(f"      ⚠️ Seletor não funcionou: {seletor}")
                    continue
            
            if not tabela_encontrada:
                print("      ❌ Tabela de conceitos SGN não encontrada")
                print("      🔍 Aguardando mais tempo para carregamento...")
                time.sleep(5)
                
                # Segunda tentativa com mais tempo
                for seletor in seletores_sgn:
                    try:
                        tabela = driver.find_element(By.CSS_SELECTOR, seletor)
                        print(f"      ✅ Tabela encontrada na segunda tentativa: {seletor}")
                        tabela_encontrada = True
                        seletor_usado = seletor
                        break
                    except NoSuchElementException:
                        continue
                
                if not tabela_encontrada:
                    print("      ❌ Tabela ainda não encontrada. Analisando estrutura da página...")
                    self._debug_estrutura_pagina(driver)
                    return False
            
            # Verificar se há linhas de alunos na tabela
            print(f"      🔍 Verificando linhas de alunos com seletor: {seletor_usado}")
            try:
                linhas = driver.find_elements(By.CSS_SELECTOR, f"{seletor_usado} tr[data-ri]")
                if len(linhas) == 0:
                    print("      ❌ Nenhuma linha de aluno encontrada")
                    return False
                
                print(f"      ✅ {len(linhas)} linhas de alunos encontradas")
                
                # Verificar estrutura da primeira linha
                primeira_linha = linhas[0]
                colunas = primeira_linha.find_elements(By.TAG_NAME, "td")
                print(f"      📊 Primeira linha tem {len(colunas)} colunas")
                
                return True
                
            except Exception as e:
                print(f"      ❌ Erro ao verificar linhas: {e}")
                return False
            
        except Exception as e:
            print(f"      ❌ Erro na validação: {e}")
            import traceback
            print(f"      📋 Detalhes: {traceback.format_exc()}")
            return False
    
    def _debug_estrutura_pagina(self, driver):
        """Faz debug da estrutura da página para identificar problemas"""
        try:
            print("      🔍 DEBUG: Analisando estrutura da página...")
            
            # Verificar todas as tabelas
            all_tables = driver.find_elements(By.TAG_NAME, "table")
            print(f"      📊 Total de tabelas na página: {len(all_tables)}")
            
            for i, table in enumerate(all_tables[:5]):  # Mostrar apenas as 5 primeiras
                class_name = table.get_attribute("class") or "sem-classe"
                id_name = table.get_attribute("id") or "sem-id"
                print(f"         Tabela {i+1}: class='{class_name}', id='{id_name}'")
            
            # Verificar divs com classe datatable
            datatable_divs = driver.find_elements(By.CSS_SELECTOR, "div[class*='datatable']")
            print(f"      📊 Divs com 'datatable': {len(datatable_divs)}")
            
            # Verificar elementos com IDs do SGN
            sgn_elements = driver.find_elements(By.CSS_SELECTOR, "[id*='tabViewDiarioClasse']")
            print(f"      📊 Elementos SGN encontrados: {len(sgn_elements)}")
            
            if len(sgn_elements) > 0:
                print("      📋 IDs SGN encontrados:")
                for elem in sgn_elements[:3]:
                    elem_id = elem.get_attribute("id")
                    print(f"         - {elem_id}")
                    
        except Exception as e:
            print(f"      ❌ Erro no debug: {e}")
    
    def _obter_lista_alunos_sgn(self):
        """
        Obtém lista de alunos baseado na estrutura HTML real do SGN
        Usa os seletores corretos identificados na análise das requisições
        
        Returns:
            list: Lista de dicionários com informações dos alunos
                  [{"nome": str, "linha": int, "data_ri": str, "seletores": dict}, ...]
        """
        print("   🔍 Coletando lista de alunos SGN...")
        
        try:
            driver = self._get_driver()
            
            # Aguardar carregamento completo da tabela
            if not self._aguardar_carregamento_tabela_completo():
                print("   ❌ Falha ao aguardar carregamento da tabela")
                return []
            
            # Seletor principal baseado na estrutura HTML real
            tbody_selector = "#tabViewDiarioClasse\\:formAbaConceitos\\:dataTableConceitos_data"
            
            try:
                wait = WebDriverWait(driver, 10)
                tbody = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, tbody_selector)))
                print(f"   ✅ Tbody encontrado: {tbody_selector}")
            except TimeoutException:
                print(f"   ⚠️ Tbody principal não encontrado, tentando alternativas...")
                # Tentar seletores alternativos
                seletores_alternativos = [
                    "tbody.ui-datatable-data",
                    ".ui-datatable-scrollable-body tbody",
                    "table[role='grid'] tbody"
                ]
                
                tbody = None
                for seletor in seletores_alternativos:
                    try:
                        tbody = driver.find_element(By.CSS_SELECTOR, seletor)
                        tbody_selector = seletor
                        print(f"   ✅ Tbody encontrado com alternativo: {seletor}")
                        break
                    except NoSuchElementException:
                        continue
                
                if not tbody:
                    print("   ❌ Nenhum tbody encontrado")
                    return []
            
            # Obter todas as linhas de alunos
            linhas = tbody.find_elements(By.CSS_SELECTOR, "tr[data-ri]")
            print(f"   📊 {len(linhas)} linhas de alunos encontradas")
            
            alunos = []
            
            # Debug detalhado apenas nas primeiras 3 linhas
            for i, linha in enumerate(linhas):
                try:
                    data_ri = linha.get_attribute("data-ri")
                    colunas = linha.find_elements(By.TAG_NAME, "td")
                    
                    if i < 3:  # Debug detalhado apenas nas primeiras 3 linhas
                        print(f"   🔍 Linha {i+1}: {len(colunas)} células encontradas")
                        for j, coluna in enumerate(colunas[:6]):  # Mostrar apenas as 6 primeiras colunas
                            texto = coluna.text.strip()[:50]  # Limitar texto
                            print(f"      Célula {j+1}: '{texto}'")
                    
                    # Extrair nome do aluno (coluna 3 baseada na estrutura HTML)
                    nome_aluno = ""
                    if len(colunas) >= 3:
                        # Tentar link do nome do estudante
                        try:
                            link_nome = colunas[2].find_element(By.CSS_SELECTOR, "a[id*='linkNomeEstudanteAbaConceitos']")
                            nome_aluno = link_nome.text.strip()
                        except NoSuchElementException:
                            # Fallback: pegar texto da coluna
                            nome_aluno = colunas[2].text.strip()
                    
                    # Validar se é um nome válido
                    if self._validar_nome_aluno(nome_aluno):
                        if i < 3:
                            print(f"   ✅ Nome encontrado na célula 3: '{nome_aluno}'")
                        
                        # Buscar botões/elementos de ação na linha
                        seletores_linha = self._obter_seletores_linha(linha, data_ri, i < 3)
                        
                        aluno_info = {
                            "nome": nome_aluno,
                            "linha": i + 1,
                            "data_ri": data_ri,
                            "seletores": seletores_linha,
                            "linha_element": linha
                        }
                        
                        alunos.append(aluno_info)
                        
                        if i < 3:
                            print(f"   ✅ Aluno {i+1} adicionado: {nome_aluno}")
                    else:
                        if i < 3:
                            print(f"   ⚠️ Nome inválido na linha {i+1}: '{nome_aluno}'")
                
                except Exception as e:
                    if i < 3:
                        print(f"   ❌ Erro ao processar linha {i+1}: {e}")
                    continue
            
            print(f"   ✅ {len(alunos)} alunos válidos encontrados")
            return alunos
            
        except Exception as e:
            print(f"   ❌ Erro ao obter lista de alunos SGN: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _validar_nome_aluno(self, nome):
        """Valida se o texto é um nome de aluno válido"""
        if not nome or len(nome) < 5:
            return False
        
        # Deve conter espaços (nomes compostos)
        if " " not in nome:
            return False
        
        # Deve conter letras
        if not any(c.isalpha() for c in nome):
            return False
        
        # Não deve ser URL ou conter palavras específicas
        palavras_excluir = ["conceito", "http", "www", "javascript", "onclick"]
        nome_lower = nome.lower()
        if any(palavra in nome_lower for palavra in palavras_excluir):
            return False
        
        return True
    
    def _obter_seletores_linha(self, linha, data_ri, debug=False):
        """Obtém seletores específicos para elementos da linha do aluno"""
        seletores = {}
        
        try:
            # Buscar botão de atitudes/habilidades
            botoes_atitude = [
                "a[id*='linkEditarAtitudes']",
                "a[title*='Habilidades']",
                "a[title*='Atitudes']",
                "a[onclick*='modalDadosAtitudes']"
            ]
            
            for seletor in botoes_atitude:
                try:
                    botao = linha.find_element(By.CSS_SELECTOR, seletor)
                    seletores["botao_atitudes"] = seletor
                    if debug:
                        title = botao.get_attribute("title") or "sem-title"
                        onclick = botao.get_attribute("onclick") or "sem-onclick"
                        print(f"   ✅ Botão atitudes encontrado: title='{title[:30]}', onclick='{onclick[:30]}'")
                    break
                except NoSuchElementException:
                    continue
            
            # Buscar select de conceito final
            seletores_conceito = [
                f"select[id*='comboConceitoFinal_input']",
                f"select[name*='comboConceitoFinal_input']",
                ".conceito-select select"
            ]
            
            for seletor in seletores_conceito:
                try:
                    select = linha.find_element(By.CSS_SELECTOR, seletor)
                    seletores["select_conceito_final"] = seletor
                    if debug:
                        select_id = select.get_attribute("id") or "sem-id"
                        print(f"   ✅ Select conceito final encontrado: id='{select_id}'")
                    break
                except NoSuchElementException:
                    continue
            
            # Listar todos os elementos clicáveis para debug
            if debug:
                elementos_clicaveis = linha.find_elements(By.CSS_SELECTOR, "a, button, select, input")
                print(f"   🔍 Linha {data_ri}: {len(elementos_clicaveis)} elementos clicáveis encontrados")
                
                for j, elem in enumerate(elementos_clicaveis[:5]):  # Mostrar apenas os 5 primeiros
                    tag = elem.tag_name
                    elem_id = elem.get_attribute("id") or "sem-id"
                    title = elem.get_attribute("title") or "sem-title"
                    onclick = elem.get_attribute("onclick") or "sem-onclick"
                    text = elem.text.strip()[:20] or "sem-texto"
                    
                    print(f"      Elemento {j+1} ({tag}): id='{elem_id[:30]}', title='{title[:30]}', text='{text}'")
        
        except Exception as e:
            if debug:
                print(f"   ❌ Erro ao obter seletores da linha: {e}")
        
        return seletores
    
    def _obter_lista_alunos_com_validacao(self):
        """
        Obtém lista de alunos com validação adicional
        
        Returns:
            list: Lista de dicionários com informações dos alunos
        """
        try:
            driver = self._get_driver()
            import time
            
            print("      🔍 Aguardando carregamento da tabela...")
            
            # Tentar diferentes seletores para encontrar a tabela
            seletores_tabela = [
                "table.ui-datatable-data",
                "table[role='grid']",
                ".ui-datatable table",
                "table tbody",
                ".datatable table"
            ]
            
            tabela = None
            for seletor in seletores_tabela:
                try:
                    wait = WebDriverWait(driver, 10)
                    tabela = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, seletor)))
                    print(f"      ✅ Tabela encontrada: {seletor}")
                    break
                except:
                    continue
            
            if not tabela:
                print("      ❌ Tabela não encontrada com nenhum seletor")
                return []
            
            # Aguardar dados carregarem
            time.sleep(3)
            
            # Tentar diferentes seletores para as linhas
            seletores_linhas = [
                "table.ui-datatable-data tbody tr",
                "table tbody tr",
                "tr[role='row']",
                ".ui-datatable tbody tr",
                "tbody tr"
            ]
            
            linhas = []
            for seletor in seletores_linhas:
                try:
                    linhas = driver.find_elements(By.CSS_SELECTOR, seletor)
                    if len(linhas) > 0:
                        print(f"      ✅ {len(linhas)} linhas encontradas: {seletor}")
                        break
                except:
                    continue
            
            if not linhas:
                print("      ❌ Nenhuma linha de aluno encontrada após validação")
                return []
            
            alunos = []
            debug_detalhado = True  # Mostrar debug apenas para as primeiras linhas
            
            for i, linha in enumerate(linhas):
                try:
                    # Limitar debug detalhado às primeiras 3 linhas
                    mostrar_debug = debug_detalhado and i < 3
                    
                    # Tentar diferentes posições para o nome do aluno
                    nome = None
                    
                    # Primeiro, tentar encontrar todas as células da linha
                    try:
                        celulas = linha.find_elements(By.TAG_NAME, "td")
                        if mostrar_debug:
                            print(f"      🔍 Linha {i+1}: {len(celulas)} células encontradas")
                            
                            # Mostrar conteúdo das primeiras células para debug
                            for j, celula in enumerate(celulas[:5]):  # Mostrar apenas as 5 primeiras
                                texto = celula.text.strip()
                                print(f"         Célula {j+1}: '{texto}'")
                        
                        # Procurar por nome nas células
                        for j, celula in enumerate(celulas):
                            texto = celula.text.strip()
                            # Verificar se parece um nome (contém letras, não é só número, tem espaços)
                            if (texto and 
                                len(texto) > 5 and 
                                not texto.isdigit() and 
                                ' ' in texto and 
                                any(c.isalpha() for c in texto) and
                                not texto.startswith('http') and
                                'conceito' not in texto.lower()):
                                nome = texto
                                if mostrar_debug:
                                    print(f"      ✅ Nome encontrado na célula {j+1}: '{nome}'")
                                break
                    except Exception as e:
                        print(f"      ❌ Erro ao processar células da linha {i+1}: {str(e)}")
                    
                    # Fallback: tentar seletores específicos se não encontrou nas células
                    if not nome:
                        seletores_nome = [
                            "td:nth-child(2)",  # Segunda coluna
                            "td:nth-child(1)",  # Primeira coluna
                            "td:nth-child(3)",  # Terceira coluna
                            "td:nth-child(4)",  # Quarta coluna
                        ]
                        
                        for seletor_nome in seletores_nome:
                            try:
                                celula_nome = linha.find_element(By.CSS_SELECTOR, seletor_nome)
                                texto = celula_nome.text.strip()
                                # Verificar se parece um nome
                                if (texto and 
                                    len(texto) > 5 and 
                                    not texto.isdigit() and 
                                    ' ' in texto and 
                                    any(c.isalpha() for c in texto)):
                                    nome = texto
                                    print(f"      ✅ Nome encontrado com seletor {seletor_nome}: '{nome}'")
                                    break
                            except:
                                continue
                    
                    if not nome:
                        print(f"      ⚠️ Nome não encontrado na linha {i+1}, pulando...")
                        continue
                    
                    # Tentar encontrar botão de ação
                    botao_conceito = None
                    
                    # Primeiro, mostrar todos os botões/inputs da linha para debug
                    if mostrar_debug:
                        try:
                            todos_botoes = linha.find_elements(By.CSS_SELECTOR, "button, input[type='button'], input[type='submit'], a")
                            print(f"      🔍 Linha {i+1} ({nome}): {len(todos_botoes)} elementos clicáveis encontrados")
                            
                            for j, botao in enumerate(todos_botoes):
                                try:
                                    title = botao.get_attribute("title") or ""
                                    onclick = botao.get_attribute("onclick") or ""
                                    text = botao.text.strip()
                                    tag = botao.tag_name
                                    print(f"         Elemento {j+1} ({tag}): title='{title}', onclick='{onclick[:50]}...', text='{text}'")
                                except:
                                    pass
                        except Exception as e:
                            print(f"      ❌ Erro ao listar botões da linha {i+1}: {str(e)}")
                    
                    # Procurar botão específico
                    seletores_botao = [
                        "button[title*='Conceito']",
                        "button[title*='conceito']", 
                        "input[title*='Conceito']",
                        "input[title*='conceito']",
                        "button[onclick*='conceito']",
                        "input[onclick*='conceito']",
                        "button[onclick*='Conceito']",
                        "input[onclick*='Conceito']",
                        ".ui-button[title*='Conceito']",
                        "a[title*='Conceito']",
                        "a[onclick*='conceito']"
                    ]
                    
                    for seletor_botao in seletores_botao:
                        try:
                            botao_conceito = linha.find_element(By.CSS_SELECTOR, seletor_botao)
                            print(f"      ✅ Botão encontrado para {nome} com seletor: {seletor_botao}")
                            break
                        except:
                            continue
                    
                    # Se não encontrou, tentar qualquer botão que contenha texto relacionado
                    if not botao_conceito:
                        try:
                            todos_botoes = linha.find_elements(By.CSS_SELECTOR, "button, input[type='button'], input[type='submit'], a")
                            for botao in todos_botoes:
                                title = (botao.get_attribute("title") or "").lower()
                                onclick = (botao.get_attribute("onclick") or "").lower()
                                text = botao.text.lower()
                                
                                if any(palavra in title + onclick + text for palavra in ['conceito', 'nota', 'avaliar', 'lancar']):
                                    botao_conceito = botao
                                    print(f"      ✅ Botão encontrado para {nome} por conteúdo relacionado")
                                    break
                        except:
                            pass
                    
                    if not botao_conceito:
                        print(f"      ⚠️ Botão não encontrado para {nome}, mas continuando...")
                    
                    aluno_info = {
                        'nome': nome,
                        'linha': linha,
                        'botao_conceito': botao_conceito,
                        'indice': i
                    }
                    
                    alunos.append(aluno_info)
                    
                except Exception as e:
                    print(f"      ⚠️ Erro ao processar linha {i+1}: {str(e)}")
                    continue
            
            print(f"      ✅ {len(alunos)} alunos validados e coletados")
            return alunos
            
        except Exception as e:
            print(f"      ❌ Erro ao obter lista de alunos: {str(e)}")
            import traceback
            print(f"      📋 Detalhes: {traceback.format_exc()}")
            return []
    
    def _acessar_aba_notas_aluno_com_validacao(self, aluno_info):
        """
        Acessa aba de notas do aluno com validação adicional
        
        Args:
            aluno_info (dict): Informações do aluno
            
        Returns:
            bool: True se conseguiu acessar, False caso contrário
        """
        try:
            driver = self._get_driver()
            wait = WebDriverWait(driver, 15)
            
            print(f"      🔍 Clicando no botão de conceito para {aluno_info['nome']}...")
            
            # Scroll para o elemento se necessário
            driver.execute_script("arguments[0].scrollIntoView(true);", aluno_info['botao_conceito'])
            time.sleep(1)
            
            # Clicar no botão
            aluno_info['botao_conceito'].click()
            
            # Aguardar modal abrir
            print("      🔍 Aguardando modal de conceitos abrir...")
            modal = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".ui-dialog[style*='display: block']"))
            )
            
            # Verificar se o modal tem o conteúdo esperado
            print("      🔍 Validando conteúdo da modal...")
            
            # Aguardar elementos de atitudes carregarem
            atitudes = wait.until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "select[id*='atitude']"))
            )
            
            # Aguardar elementos de habilidades carregarem
            habilidades = wait.until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "select[id*='habilidade']"))
            )
            
            print(f"      ✅ Modal aberta: {len(atitudes)} atitudes, {len(habilidades)} habilidades")
            return True
            
        except TimeoutException:
            print(f"      ❌ Timeout ao abrir modal para {aluno_info['nome']}")
            return False
        except Exception as e:
            print(f"      ❌ Erro ao acessar modal para {aluno_info['nome']}: {str(e)}")
            return False
    
    def _preencher_observacoes_atitudes_com_validacao(self, atitude_observada):
        """
        Preenche observações de atitudes com validação
        
        Args:
            atitude_observada (str): Valor da atitude a ser selecionada
            
        Returns:
            bool: True se preencheu corretamente, False caso contrário
        """
        try:
            driver = self._get_driver()
            wait = WebDriverWait(driver, 10)
            
            print(f"      🔍 Preenchendo atitudes com '{atitude_observada}'...")
            
            # Encontrar todos os selects de atitude
            selects_atitude = wait.until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "select[id*='atitude']"))
            )
            
            preenchidos = 0
            total = len(selects_atitude)
            
            for i, select in enumerate(selects_atitude):
                try:
                    # Verificar se o select está visível e habilitado
                    if not select.is_displayed() or not select.is_enabled():
                        continue
                    
                    # Encontrar a opção correta
                    opcoes = select.find_elements(By.TAG_NAME, "option")
                    opcao_encontrada = False
                    
                    for opcao in opcoes:
                        if opcao.text.strip() == atitude_observada:
                            opcao.click()
                            preenchidos += 1
                            opcao_encontrada = True
                            break
                    
                    if not opcao_encontrada:
                        print(f"      ⚠️ Opção '{atitude_observada}' não encontrada no select {i+1}")
                    
                except Exception as e:
                    print(f"      ⚠️ Erro ao preencher select de atitude {i+1}: {str(e)}")
                    continue
            
            print(f"      ✅ Atitudes preenchidas: {preenchidos}/{total}")
            return preenchidos > 0
            
        except Exception as e:
            print(f"      ❌ Erro ao preencher atitudes: {str(e)}")
            return False
    
    def _preencher_conceitos_habilidades_com_validacao(self, conceito_habilidade):
        """
        Preenche conceitos de habilidades com validação
        
        Args:
            conceito_habilidade (str): Valor do conceito a ser selecionado
            
        Returns:
            bool: True se preencheu corretamente, False caso contrário
        """
        try:
            driver = self._get_driver()
            wait = WebDriverWait(driver, 10)
            
            print(f"      🔍 Preenchendo conceitos com '{conceito_habilidade}'...")
            
            # Encontrar todos os selects de habilidade
            selects_habilidade = wait.until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "select[id*='habilidade']"))
            )
            
            preenchidos = 0
            total = len(selects_habilidade)
            
            for i, select in enumerate(selects_habilidade):
                try:
                    # Verificar se o select está visível e habilitado
                    if not select.is_displayed() or not select.is_enabled():
                        continue
                    
                    # Encontrar a opção correta
                    opcoes = select.find_elements(By.TAG_NAME, "option")
                    opcao_encontrada = False
                    
                    for opcao in opcoes:
                        if opcao.text.strip() == conceito_habilidade:
                            opcao.click()
                            preenchidos += 1
                            opcao_encontrada = True
                            break
                    
                    if not opcao_encontrada:
                        print(f"      ⚠️ Opção '{conceito_habilidade}' não encontrada no select {i+1}")
                    
                except Exception as e:
                    print(f"      ⚠️ Erro ao preencher select de habilidade {i+1}: {str(e)}")
                    continue
            
            print(f"      ✅ Conceitos preenchidos: {preenchidos}/{total}")
            return preenchidos > 0
            
        except Exception as e:
            print(f"      ❌ Erro ao preencher conceitos: {str(e)}")
            return False
    
    def _validar_dados_preenchidos(self, atitude_esperada, conceito_esperado):
        """
        Valida se os dados foram preenchidos corretamente antes do salvamento
        
        Args:
            atitude_esperada (str): Valor esperado para atitudes
            conceito_esperado (str): Valor esperado para conceitos
            
        Returns:
            bool: True se os dados estão corretos, False caso contrário
        """
        try:
            driver = self._get_driver()
            
            print("      🔍 Validando dados preenchidos...")
            
            # Validar atitudes
            selects_atitude = driver.find_elements(By.CSS_SELECTOR, "select[id*='atitude']")
            atitudes_corretas = 0
            
            for select in selects_atitude:
                if select.is_displayed() and select.is_enabled():
                    opcao_selecionada = select.find_element(By.CSS_SELECTOR, "option:checked")
                    if opcao_selecionada.text.strip() == atitude_esperada:
                        atitudes_corretas += 1
            
            # Validar conceitos
            selects_conceito = driver.find_elements(By.CSS_SELECTOR, "select[id*='habilidade']")
            conceitos_corretos = 0
            
            for select in selects_conceito:
                if select.is_displayed() and select.is_enabled():
                    opcao_selecionada = select.find_element(By.CSS_SELECTOR, "option:checked")
                    if opcao_selecionada.text.strip() == conceito_esperado:
                        conceitos_corretos += 1
            
            print(f"      📊 Validação: {atitudes_corretas} atitudes, {conceitos_corretos} conceitos corretos")
            
            # Considerar válido se pelo menos alguns campos foram preenchidos corretamente
            return (atitudes_corretas > 0 or conceitos_corretos > 0)
            
        except Exception as e:
            print(f"      ❌ Erro na validação: {str(e)}")
            return False
    
    def _fechar_modal_conceitos_com_validacao(self):
        """
        Fecha a modal de conceitos com validação
        
        Returns:
            bool: True se fechou corretamente, False caso contrário
        """
        try:
            driver = self._get_driver()
            wait = WebDriverWait(driver, 10)
            
            print("      🔍 Fechando modal de conceitos...")
            
            # Tentar encontrar botão de fechar (X)
            botao_fechar = None
            
            # Tentar diferentes seletores para o botão de fechar
            seletores_fechar = [
                ".ui-dialog-titlebar-close",
                "button[aria-label='Close']",
                ".ui-icon-closethick",
                "span.ui-icon-closethick"
            ]
            
            for seletor in seletores_fechar:
                try:
                    botao_fechar = driver.find_element(By.CSS_SELECTOR, seletor)
                    if botao_fechar.is_displayed():
                        break
                except:
                    continue
            
            if botao_fechar:
                botao_fechar.click()
                
                # Aguardar modal fechar
                wait.until(
                    EC.invisibility_of_element_located((By.CSS_SELECTOR, ".ui-dialog[style*='display: block']"))
                )
                
                print("      ✅ Modal fechada com sucesso")
                return True
            else:
                # Tentar ESC como alternativa
                driver.find_element(By.TAG_NAME, "body").send_keys("\ue00c")  # ESC
                time.sleep(1)
                print("      ✅ Modal fechada com ESC")
                return True
                
        except Exception as e:
            print(f"      ⚠️ Erro ao fechar modal: {str(e)}")
            return False
    
    def _mapear_colunas_avaliacoes_sgn(self):
        """
        Mapeia as colunas de avaliações baseado na estrutura HTML real do SGN
        
        Returns:
            dict: Mapeamento {identificador: índice_coluna}
        """
        print("   🔍 Mapeando colunas de avaliações SGN...")
        
        try:
            driver = self._get_driver()
            
            # Aguardar cabeçalho da tabela carregar
            time.sleep(2)
            
            # Seletores para o cabeçalho da tabela
            seletores_header = [
                "#tabViewDiarioClasse\\:formAbaConceitos\\:dataTableConceitos_head tr",
                ".ui-datatable-scrollable-header thead tr",
                "thead tr"
            ]
            
            header_row = None
            for seletor in seletores_header:
                try:
                    header_row = driver.find_element(By.CSS_SELECTOR, seletor)
                    print(f"   ✅ Cabeçalho encontrado: {seletor}")
                    break
                except NoSuchElementException:
                    continue
            
            if not header_row:
                print("   ❌ Cabeçalho da tabela não encontrado")
                return {}
            
            # Obter todas as colunas do cabeçalho
            colunas_th = header_row.find_elements(By.TAG_NAME, "th")
            print(f"   📊 {len(colunas_th)} colunas encontradas no cabeçalho")
            
            mapeamento = {}
            
            for i, th in enumerate(colunas_th):
                try:
                    # Obter texto da coluna
                    texto_coluna = th.text.strip()
                    
                    # Obter span com title para mais informações
                    try:
                        span_title = th.find_element(By.CSS_SELECTOR, "span[title]")
                        title_info = span_title.get_attribute("title")
                        print(f"      Coluna {i+1}: '{texto_coluna}' - {title_info}")
                    except NoSuchElementException:
                        print(f"      Coluna {i+1}: '{texto_coluna}'")
                    
                    # Mapear baseado no texto da coluna
                    if texto_coluna in ["AV1", "AV2", "AV3", "AV4", "AV5"]:
                        # Índice relativo (descontando as primeiras 3 colunas: número, ação, estudante)
                        indice_relativo = i - 3
                        mapeamento[texto_coluna] = indice_relativo
                        print(f"         → Mapeado: {texto_coluna} = índice {indice_relativo}")
                    
                    elif texto_coluna.startswith("RP"):  # RP1, RP2, etc.
                        indice_relativo = i - 3
                        mapeamento[texto_coluna] = indice_relativo
                        print(f"         → Mapeado: {texto_coluna} = índice {indice_relativo}")
                    
                    elif texto_coluna in ["CF", "SA", "SM"]:
                        # Conceito Final, Situação Atual, Situação Matrícula
                        indice_relativo = i - 3
                        mapeamento[texto_coluna] = indice_relativo
                        print(f"         → Mapeado: {texto_coluna} = índice {indice_relativo}")
                
                except Exception as e:
                    print(f"      ⚠️ Erro ao processar coluna {i+1}: {e}")
                    continue
            
            print(f"   ✅ Mapeamento concluído: {mapeamento}")
            return mapeamento
            
        except Exception as e:
            print(f"   ❌ Erro ao mapear colunas SGN: {e}")
            return {}
    
    def _atualizar_tabela_conceitos_ajax(self):
        """
        Força atualização da tabela de conceitos via AJAX
        Baseado nas requisições capturadas do SGN
        
        Returns:
            bool: True se conseguiu atualizar, False caso contrário
        """
        print("   🔄 Atualizando tabela de conceitos via AJAX...")
        
        try:
            driver = self._get_driver()
            
            # Aguardar página estar pronta
            time.sleep(2)
            
            # Obter ViewState atual
            try:
                viewstate_input = driver.find_element(By.NAME, "javax.faces.ViewState")
                viewstate = viewstate_input.get_attribute("value")
                print(f"   📋 ViewState obtido: {viewstate[:50]}...")
            except NoSuchElementException:
                print("   ❌ ViewState não encontrado")
                return False
            
            # Executar JavaScript para fazer requisição AJAX (baseado nas requisições capturadas)
            ajax_script = f"""
            // Função para atualizar tabela via PrimeFaces AJAX
            PrimeFaces.ab({{
                s: "tabViewDiarioClasse:formAbaConceitos:j_idt1191",
                f: "tabViewDiarioClasse:formAbaConceitos",
                p: "tabViewDiarioClasse:formAbaConceitos:j_idt1191",
                u: "tabViewDiarioClasse:formAbaConceitos:dataTableConceitos"
            }});
            """
            
            print("   🚀 Executando requisição AJAX...")
            driver.execute_script(ajax_script)
            
            # Aguardar requisição completar
            time.sleep(3)
            
            # Verificar se a tabela foi atualizada
            try:
                wait = WebDriverWait(driver, 10)
                # Aguardar tbody aparecer
                tbody = wait.until(EC.presence_of_element_located((
                    By.CSS_SELECTOR, 
                    "#tabViewDiarioClasse\\:formAbaConceitos\\:dataTableConceitos_data"
                )))
                
                # Verificar se há linhas com dados
                linhas = tbody.find_elements(By.CSS_SELECTOR, "tr[data-ri]")
                if len(linhas) > 0:
                    print(f"   ✅ Tabela atualizada com sucesso - {len(linhas)} linhas encontradas")
                    return True
                else:
                    print("   ⚠️ Tabela atualizada mas sem linhas de dados")
                    return False
                    
            except TimeoutException:
                print("   ❌ Timeout aguardando atualização da tabela")
                return False
                
        except Exception as e:
            print(f"   ❌ Erro ao atualizar tabela via AJAX: {e}")
            return False
    
    def _obter_lista_alunos_com_ajax(self):
        """
        Obtém lista de alunos forçando atualização via AJAX primeiro
        
        Returns:
            list: Lista de dicionários com informações dos alunos
        """
        print("   🔄 Obtendo lista de alunos com atualização AJAX...")
        
        try:
            # Primeiro, tentar atualizar a tabela via AJAX
            if self._atualizar_tabela_conceitos_ajax():
                # Aguardar um pouco mais para garantir que os dados carregaram
                time.sleep(2)
                
                # Agora usar o método normal para extrair os dados
                return self._obter_lista_alunos_sgn()
            else:
                print("   ⚠️ Falha na atualização AJAX, tentando método direto...")
                return self._obter_lista_alunos_sgn()
                
        except Exception as e:
            print(f"   ❌ Erro ao obter lista com AJAX: {e}")
            return []
    
    def _aguardar_carregamento_tabela_completo(self):
        """
        Aguarda o carregamento completo da tabela com múltiplas estratégias
        
        Returns:
            bool: True se a tabela carregou completamente, False caso contrário
        """
        print("   ⏳ Aguardando carregamento completo da tabela...")
        
        try:
            driver = self._get_driver()
            
            # Estratégia 1: Aguardar indicadores de carregamento desaparecerem
            print("   🔄 Aguardando indicadores de carregamento...")
            try:
                wait = WebDriverWait(driver, 10)
                # Aguardar qualquer indicador de loading desaparecer
                wait.until_not(EC.presence_of_element_located((By.CSS_SELECTOR, ".ui-blockui, .loading, [style*='loading']")))
                time.sleep(1)
            except TimeoutException:
                print("   ⚠️ Nenhum indicador de loading encontrado")
            
            # Estratégia 2: Aguardar JavaScript estar pronto
            print("   🔄 Verificando se JavaScript está pronto...")
            for i in range(10):
                try:
                    ready = driver.execute_script("return document.readyState === 'complete' && typeof PrimeFaces !== 'undefined'")
                    if ready:
                        print("   ✅ JavaScript pronto")
                        break
                    time.sleep(0.5)
                except:
                    time.sleep(0.5)
            
            # Estratégia 3: Aguardar tabela específica aparecer e ter conteúdo
            print("   🔄 Aguardando tabela de conceitos...")
            try:
                wait = WebDriverWait(driver, 15)
                
                # Aguardar tbody aparecer
                tbody = wait.until(EC.presence_of_element_located((
                    By.CSS_SELECTOR, 
                    "#tabViewDiarioClasse\\:formAbaConceitos\\:dataTableConceitos_data"
                )))
                
                # Aguardar pelo menos uma linha aparecer
                print("   🔄 Aguardando dados aparecerem...")
                for tentativa in range(20):  # 10 segundos
                    linhas = tbody.find_elements(By.CSS_SELECTOR, "tr[data-ri]")
                    if len(linhas) > 0:
                        # Verificar se as linhas têm conteúdo real
                        primeira_linha = linhas[0]
                        colunas = primeira_linha.find_elements(By.TAG_NAME, "td")
                        
                        # Verificar se há pelo menos 3 colunas e algum texto
                        if len(colunas) >= 3:
                            texto_total = ""
                            for coluna in colunas[:5]:  # Verificar primeiras 5 colunas
                                texto_total += coluna.text.strip()
                            
                            if len(texto_total) > 10:  # Se há conteúdo suficiente
                                print(f"   ✅ Tabela carregada com {len(linhas)} linhas e conteúdo")
                                return True
                    
                    time.sleep(0.5)
                
                print("   ⚠️ Tabela encontrada mas sem conteúdo suficiente")
                return False
                
            except TimeoutException:
                print("   ❌ Timeout aguardando tabela de conceitos")
                return False
            
        except Exception as e:
            print(f"   ❌ Erro ao aguardar carregamento: {e}")
            return False
    
    def _obter_lista_alunos_via_requisicao(self):
        """
        Obtém lista de alunos fazendo requisição HTTP direta ao servidor
        Baseado na análise das requisições capturadas
        
        Returns:
            list: Lista de dicionários com informações dos alunos
        """
        print("   🌐 Obtendo lista de alunos via requisição HTTP...")
        
        try:
            driver = self._get_driver()
            
            # Obter cookies e headers necessários
            cookies = {cookie['name']: cookie['value'] for cookie in driver.get_cookies()}
            
            # Obter ViewState
            try:
                viewstate_input = driver.find_element(By.NAME, "javax.faces.ViewState")
                viewstate = viewstate_input.get_attribute("value")
                print(f"   📋 ViewState: {viewstate[:50]}...")
            except NoSuchElementException:
                print("   ❌ ViewState não encontrado")
                return []
            
            # Preparar dados da requisição baseados nas requisições capturadas
            url = driver.current_url
            if "?" in url:
                url = url.split("?")[0]
            
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'X-Requested-With': 'XMLHttpRequest',
                'Faces-Request': 'partial/ajax',
                'User-Agent': driver.execute_script("return navigator.userAgent;")
            }
            
            # Dados do POST baseados na requisição capturada
            post_data = {
                'javax.faces.partial.ajax': 'true',
                'javax.faces.source': 'tabViewDiarioClasse:formAbaConceitos:j_idt1191',
                'javax.faces.partial.execute': 'tabViewDiarioClasse:formAbaConceitos:j_idt1191',
                'javax.faces.partial.render': 'tabViewDiarioClasse:formAbaConceitos:dataTableConceitos',
                'tabViewDiarioClasse:formAbaConceitos:j_idt1191': 'tabViewDiarioClasse:formAbaConceitos:j_idt1191',
                'javax.faces.ViewState': viewstate
            }
            
            print("   🚀 Fazendo requisição AJAX...")
            
            # Fazer requisição usando requests
            import requests
            from urllib.parse import urlencode
            
            session = requests.Session()
            
            # Adicionar cookies
            for name, value in cookies.items():
                session.cookies.set(name, value)
            
            # Fazer POST
            response = session.post(
                url,
                data=urlencode(post_data),
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                print(f"   ✅ Requisição bem-sucedida ({len(response.text)} bytes)")
                
                # Extrair dados do XML retornado
                return self._extrair_alunos_do_xml(response.text)
            else:
                print(f"   ❌ Erro na requisição: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"   ❌ Erro na requisição HTTP: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _extrair_alunos_do_xml(self, xml_content):
        """
        Extrai informações dos alunos do XML retornado pela requisição AJAX
        
        Args:
            xml_content (str): Conteúdo XML da resposta
            
        Returns:
            list: Lista de alunos extraídos
        """
        print("   🔍 Extraindo dados dos alunos do XML...")
        
        try:
            import re
            
            # Debug: mostrar início do XML recebido
            print(f"   🔍 DEBUG: XML recebido ({len(xml_content)} chars): {xml_content[:200]}...")
            
            # VERIFICAR SE É ERRO 500 DO SERVIDOR
            if 'redirect url="/errors/500.html"' in xml_content:
                print("   🚨 ERRO 500 DETECTADO: Servidor SGN com problema interno!")
                print("   ⚠️ Retornando lista vazia para forçar fallback para Selenium")
                return []
            
            # VERIFICAR SE É OUTRO TIPO DE ERRO
            if '<redirect url=' in xml_content and 'error' in xml_content.lower():
                print("   🚨 ERRO DO SERVIDOR DETECTADO no XML!")
                print(f"   📋 Conteúdo do erro: {xml_content}")
                print("   ⚠️ Retornando lista vazia para forçar fallback para Selenium")
                return []
            
            alunos = []
            
            # Buscar por nomes dos estudantes no XML
            pattern_nomes = r'linkNomeEstudanteAbaConceitos[^>]*>([^<]+)</a>'
            nomes_encontrados = re.findall(pattern_nomes, xml_content)
            
            print(f"   📊 {len(nomes_encontrados)} nomes encontrados no XML")
            
            # Buscar por data-ri para cada linha
            pattern_linhas = r'<tr data-ri="(\d+)"[^>]*>(.*?)</tr>'
            linhas_encontradas = re.findall(pattern_linhas, xml_content, re.DOTALL)
            
            print(f"   📊 {len(linhas_encontradas)} linhas encontradas no XML")
            
            # Processar cada linha
            for i, (data_ri, linha_html) in enumerate(linhas_encontradas):
                try:
                    # Extrair nome da linha
                    nome_match = re.search(r'linkNomeEstudanteAbaConceitos[^>]*>([^<]+)</a>', linha_html)
                    if nome_match:
                        nome_aluno = nome_match.group(1).strip()
                        
                        # Validar nome
                        if self._validar_nome_aluno(nome_aluno):
                            # Buscar botão de atitudes
                            botao_atitudes = None
                            if 'linkEditarAtitudes' in linha_html:
                                botao_match = re.search(r'id="([^"]*linkEditarAtitudes[^"]*)"', linha_html)
                                if botao_match:
                                    botao_atitudes = botao_match.group(1)
                            
                            aluno_info = {
                                "nome": nome_aluno,
                                "linha": i + 1,
                                "data_ri": data_ri,
                                "seletores": {
                                    "botao_atitudes": f"#{botao_atitudes}" if botao_atitudes else None
                                },
                                "xml_source": True  # Indicar que veio do XML
                            }
                            
                            alunos.append(aluno_info)
                            
                            if i < 5:  # Debug apenas primeiros 5
                                print(f"   ✅ Aluno {i+1}: {nome_aluno} (data-ri={data_ri})")
                
                except Exception as e:
                    print(f"   ⚠️ Erro ao processar linha {i+1}: {e}")
                    continue
            
            print(f"   ✅ {len(alunos)} alunos extraídos com sucesso do XML")
            return alunos
            
        except Exception as e:
            print(f"   ❌ Erro ao extrair dados do XML: {e}")
            return []
    
    def _lancar_atitude_via_requisicao(self, data_ri, atitude_id, valor_atitude, viewstate):
        """
        Lança uma atitude específica via requisição HTTP direta
        
        Args:
            data_ri (str): Índice da linha do aluno
            atitude_id (str): ID da atitude (ex: 118)
            valor_atitude (str): Valor da atitude (Sempre, Às vezes, Raramente, Nunca, etc.)
            viewstate (str): ViewState atual da sessão
            
        Returns:
            bool: True se sucesso, False caso contrário
        """
        print(f"   🎯 Lançando atitude via requisição: {valor_atitude}")
        
        try:
            driver = self._get_driver()
            
            # Extrair valor da atitude se for Enum
            if hasattr(valor_atitude, 'value'):
                valor_final = str(valor_atitude.value)
            elif hasattr(valor_atitude, 'name'):
                valor_final = str(valor_atitude.name).replace('_', ' ').replace('AS VEZES', 'Às vezes')
            else:
                valor_final = str(valor_atitude)
            
            # Obter cookies e URL
            cookies = {cookie['name']: cookie['value'] for cookie in driver.get_cookies()}
            url = driver.current_url
            if "?" in url:
                url = url.split("?")[0]
            
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'X-Requested-With': 'XMLHttpRequest',
                'Faces-Request': 'partial/ajax',
                'User-Agent': driver.execute_script("return navigator.userAgent;")
            }
            
            # Dados da requisição baseados na captura
            element_id = f"formAtitudes:panelAtitudes:dataTableAtitudes:{atitude_id}:observacaoAtitude"
            
            post_data = {
                'javax.faces.partial.ajax': 'true',
                'javax.faces.source': element_id,
                'javax.faces.partial.execute': element_id,
                'javax.faces.partial.render': element_id,
                'javax.faces.behavior.event': 'valueChange',
                'javax.faces.partial.event': 'change',
                f'{element_id}_focus': '',
                f'{element_id}_input': valor_final,
                'javax.faces.ViewState': viewstate
            }
            
            import requests
            from urllib.parse import urlencode
            
            session = requests.Session()
            for name, value in cookies.items():
                session.cookies.set(name, value)
            
            response = session.post(
                url,
                data=urlencode(post_data),
                headers=headers,
                timeout=10  # Timeout reduzido para performance
            )
            
            if response.status_code == 200:
                # Verificar se a resposta contém erro 500
                if 'redirect url="/errors/500.html"' in response.text:
                    print(f"   🚨 ERRO 500 DETECTADO ao lançar atitude: Servidor SGN com problema!")
                    return False
                
                print(f"   ✅ Atitude lançada com sucesso: {valor_final}")
                return True
            else:
                print(f"   ❌ Erro na requisição: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"   ❌ Erro ao lançar atitude: {e}")
            return False

    def _lancar_atitude_via_requisicao_rapida(self, data_ri, atitude_id, valor_atitude, viewstate, timeout=5):
        """
        Versão otimizada para lançar atitude com timeout reduzido e menos logs
        
        Args:
            data_ri (str): Índice da linha do aluno
            atitude_id (str): ID da atitude
            valor_atitude (str): Valor da atitude
            viewstate (str): ViewState atual da sessão
            timeout (int): Timeout em segundos (padrão: 5)
            
        Returns:
            bool: True se sucesso, False caso contrário
        """
        try:
            driver = self._get_driver()
            
            # Extrair valor da atitude se for Enum
            if hasattr(valor_atitude, 'value'):
                valor_final = str(valor_atitude.value)
            elif hasattr(valor_atitude, 'name'):
                valor_final = str(valor_atitude.name).replace('_', ' ').replace('AS VEZES', 'Às vezes')
            else:
                valor_final = str(valor_atitude)
            
            # Obter cookies e URL (cache otimizado)
            cookies = {cookie['name']: cookie['value'] for cookie in driver.get_cookies()}
            url = driver.current_url.split('?')[0]
            
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'X-Requested-With': 'XMLHttpRequest',
                'Faces-Request': 'partial/ajax',
                'User-Agent': driver.execute_script("return navigator.userAgent;")
            }
            
            element_id = f"formAtitudes:panelAtitudes:dataTableAtitudes:{atitude_id}:observacaoAtitude"
            
            post_data = {
                'javax.faces.partial.ajax': 'true',
                'javax.faces.source': element_id,
                'javax.faces.partial.execute': element_id,
                'javax.faces.partial.render': element_id,
                'javax.faces.behavior.event': 'valueChange',
                'javax.faces.partial.event': 'change',
                f'{element_id}_focus': '',
                f'{element_id}_input': valor_final,
                'javax.faces.ViewState': viewstate
            }
            
            from urllib.parse import urlencode
            
            session = requests.Session()
            for name, value in cookies.items():
                session.cookies.set(name, value)
            
            response = session.post(
                url,
                data=urlencode(post_data),
                headers=headers,
                timeout=timeout
            )
            
            # Verificação rápida de sucesso
            return response.status_code == 200 and 'redirect url="/errors/500.html"' not in response.text
                
        except Exception:
            return False

    def _lancar_lote_atitudes_paralelo(self, lote_indices, opcao_atitude, viewstate, timeout=3):
        """
        Lança um lote de atitudes em paralelo usando threads
        
        Args:
            lote_indices (list): Lista de índices das atitudes
            opcao_atitude (str): Valor da atitude
            viewstate (str): ViewState atual
            timeout (int): Timeout por requisição
            
        Returns:
            tuple: (sucessos, falhas)
        """
        sucessos = 0
        falhas = 0
        
        # Obter dados em cache uma vez para todo o lote
        cookies, headers, url = self._get_cached_request_data()
        
        def processar_atitude(i):
            try:
                # Usar dados em cache para evitar acessar Selenium em cada thread
                sucesso = self._lancar_atitude_via_requisicao_otimizada(str(i), str(i), opcao_atitude, viewstate, cookies, headers, url, timeout)
                return (i, sucesso)
            except Exception:
                return (i, False)
        
        # Usar ThreadPoolExecutor para paralelizar (máximo 2 threads para evitar erro 500)
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            # Submeter todas as tarefas
            futures = [executor.submit(processar_atitude, i) for i in lote_indices]
            
            # Coletar resultados
            for future in concurrent.futures.as_completed(futures):
                try:
                    i, sucesso = future.result(timeout=timeout + 2)  # Timeout um pouco maior
                    if sucesso:
                        sucessos += 1
                        print(f"   ✅ Atitude {i+1} preenchida: {opcao_atitude}")
                    else:
                        falhas += 1
                        print(f"   ❌ Falha na atitude {i+1}")
                except Exception as e:
                    falhas += 1
                    print(f"   ❌ Erro na thread da atitude: {e}")
        
        return sucessos, falhas

    def _lancar_atitude_via_requisicao_otimizada(self, data_ri, atitude_id, valor_atitude, viewstate, cookies, headers, url, timeout=3):
        """
        Versão ultra-otimizada que usa dados em cache (thread-safe) com retry e rate limiting
        
        Args:
            data_ri (str): Índice da linha do aluno
            atitude_id (str): ID da atitude
            valor_atitude (str): Valor da atitude
            viewstate (str): ViewState atual da sessão
            cookies (dict): Cookies em cache
            headers (dict): Headers em cache
            url (str): URL em cache
            timeout (int): Timeout em segundos
            
        Returns:
            bool: True se sucesso, False caso contrário
        """
        max_retries = 2
        base_delay = 1.0
        
        for attempt in range(max_retries + 1):
            try:
                # Rate limiting para evitar sobrecarregar servidor
                self._rate_limit_request()
                
                # Extrair valor da atitude se for Enum
                if hasattr(valor_atitude, 'value'):
                    valor_final = str(valor_atitude.value)
                elif hasattr(valor_atitude, 'name'):
                    valor_final = str(valor_atitude.name).replace('_', ' ').replace('AS VEZES', 'Às vezes')
                else:
                    valor_final = str(valor_atitude)
                
                element_id = f"formAtitudes:panelAtitudes:dataTableAtitudes:{atitude_id}:observacaoAtitude"
                
                post_data = {
                    'javax.faces.partial.ajax': 'true',
                    'javax.faces.source': element_id,
                    'javax.faces.partial.execute': element_id,
                    'javax.faces.partial.render': element_id,
                    'javax.faces.behavior.event': 'valueChange',
                    'javax.faces.partial.event': 'change',
                    f'{element_id}_focus': '',
                    f'{element_id}_input': valor_final,
                    'javax.faces.ViewState': viewstate
                }
                
                from urllib.parse import urlencode
                
                session = requests.Session()
                for name, value in cookies.items():
                    session.cookies.set(name, value)
                
                response = session.post(
                    url,
                    data=urlencode(post_data),
                    headers=headers,
                    timeout=timeout
                )
                
                # Verificar se foi sucesso
                if response.status_code == 200 and 'redirect url="/errors/500.html"' not in response.text:
                    # Verificar se não é erro de sessão
                    if not self._detectar_sessao_expirada(response.text):
                        return True
                
                # Se foi erro de sessão, tentar renovar
                if self._detectar_sessao_expirada(response.text):
                    print(f"   🚨 Sessão expirada detectada na atitude {atitude_id}")
                    if attempt < max_retries and self._tentar_renovar_sessao():
                        # Atualizar dados após renovação
                        cookies, headers, url = self._get_cached_request_data(force_refresh=True)
                        delay = base_delay * (2 ** attempt)
                        time.sleep(delay)
                        continue
                    else:
                        print(f"   ❌ Não foi possível renovar sessão para atitude {atitude_id}")
                        return False
                
                # Se foi erro 500, tentar novamente
                if 'redirect url="/errors/500.html"' in response.text and attempt < max_retries:
                    delay = base_delay * (2 ** attempt)  # Backoff exponencial
                    time.sleep(delay)
                    continue
                
                return False
                    
            except Exception:
                if attempt < max_retries:
                    delay = base_delay * (2 ** attempt)
                    time.sleep(delay)
                    continue
                return False
        
        return False

    def _lancar_conceitos_habilidades_paralelo(self, conceitos_pendentes, conceito_valor, viewstate, timeout=3):
        """
        Lança conceitos de habilidades em paralelo usando threads
        
        Args:
            conceitos_pendentes (list): Lista de data-ri dos conceitos pendentes
            conceito_valor (str): Valor do conceito
            viewstate (str): ViewState atual
            timeout (int): Timeout por requisição
            
        Returns:
            tuple: (sucessos, falhas)
        """
        sucessos = 0
        falhas = 0
        
        def processar_conceito(data_ri):
            try:
                sucesso = self._lancar_conceito_habilidade_via_requisicao(data_ri, conceito_valor, viewstate)
                return (data_ri, sucesso)
            except Exception:
                return (data_ri, False)
        
        # Usar ThreadPoolExecutor para paralelizar (máximo 3 threads para conceitos - evitar erro 500)
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            # Submeter todas as tarefas
            futures = [executor.submit(processar_conceito, data_ri) for data_ri in conceitos_pendentes]
            
            # Coletar resultados
            for future in concurrent.futures.as_completed(futures):
                try:
                    data_ri, sucesso = future.result(timeout=timeout + 3)  # Timeout maior para conceitos
                    if sucesso:
                        sucessos += 1
                        print(f"   ✅ Conceito {data_ri} preenchido: {conceito_valor}")
                    else:
                        falhas += 1
                        print(f"   ❌ Falha no conceito {data_ri}")
                except Exception as e:
                    falhas += 1
                    print(f"   ❌ Erro na thread do conceito: {e}")
        
        return sucessos, falhas
    
    def _lancar_conceito_via_requisicao(self, data_ri, avaliacao_id, conceito, viewstate):
        """
        Lança um conceito específico via requisição HTTP direta
        
        Args:
            data_ri (str): Índice da linha do aluno
            avaliacao_id (str): ID da avaliação (ex: 0, 1, 2 para AV1, AV2, AV3)
            conceito (str): Conceito a ser lançado (A, B, C, NE)
            viewstate (str): ViewState atual da sessão
            
        Returns:
            bool: True se sucesso, False caso contrário
        """
        print(f"   🎯 Lançando conceito via requisição: {conceito}")
        
        try:
            driver = self._get_driver()
            
            # Obter cookies e URL
            cookies = {cookie['name']: cookie['value'] for cookie in driver.get_cookies()}
            url = driver.current_url
            if "?" in url:
                url = url.split("?")[0]
            
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'X-Requested-With': 'XMLHttpRequest',
                'Faces-Request': 'partial/ajax',
                'User-Agent': driver.execute_script("return navigator.userAgent;")
            }
            
            # Dados da requisição baseados na captura
            element_id = f"tabViewDiarioClasse:formAbaConceitos:dataTableConceitos:{data_ri}:avaliacoes:{avaliacao_id}:j_idt1114"
            
            post_data = {
                'javax.faces.partial.ajax': 'true',
                'javax.faces.source': element_id,
                'javax.faces.partial.execute': element_id,
                'javax.faces.partial.render': element_id,
                'javax.faces.behavior.event': 'valueChange',
                'javax.faces.partial.event': 'change',
                f'{element_id}_focus': '',
                f'{element_id}_input': conceito,
                'javax.faces.ViewState': viewstate
            }
            
            import requests
            from urllib.parse import urlencode
            
            session = requests.Session()
            for name, value in cookies.items():
                session.cookies.set(name, value)
            
            response = session.post(
                url,
                data=urlencode(post_data),
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                print(f"   ✅ Conceito lançado com sucesso: {conceito}")
                return True
            else:
                print(f"   ❌ Erro na requisição: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"   ❌ Erro ao lançar conceito: {e}")
            return False
    
    def _lancar_conceito_habilidade_via_requisicao(self, data_ri, conceito, viewstate):
        """
        Lança conceito de habilidade via requisição HTTP direta
        
        Args:
            data_ri: Índice da linha da habilidade
            conceito: Conceito a ser lançado (A, B, C, NE ou ConceitoHabilidade.X)
            viewstate: ViewState atual da página
            
        Returns:
            bool: True se sucesso, False caso contrário
        """
        try:
            # Debug: mostrar tipo e valor original
            print(f"   🔍 DEBUG: conceito recebido = '{conceito}' (tipo: {type(conceito)})")
            
            # Extrair apenas o valor do conceito - lidar com Enum e String
            if hasattr(conceito, 'value'):
                # É um Enum - usar o valor do enum
                conceito_valor = str(conceito.value)
                print(f"   🔍 DEBUG: Extraído valor do Enum '{conceito_valor}' de '{conceito}'")
            elif hasattr(conceito, 'name'):
                # É um Enum - usar o nome do enum
                conceito_valor = str(conceito.name)
                print(f"   🔍 DEBUG: Extraído nome do Enum '{conceito_valor}' de '{conceito}'")
            elif isinstance(conceito, str) and '.' in conceito:
                # É string com formato "ConceitoHabilidade.B"
                conceito_valor = conceito.split('.')[-1]  # Pega apenas "B" de "ConceitoHabilidade.B"
                print(f"   🔍 DEBUG: Extraído valor da string '{conceito_valor}' de '{conceito}'")
            else:
                # Usar valor direto convertido para string
                conceito_valor = str(conceito)
                print(f"   🔍 DEBUG: Usando valor direto '{conceito_valor}'")
            
            print(f"   🎯 Lançando conceito de habilidade via requisição: {conceito_valor} (data-ri={data_ri}) [original: {conceito}]")
            
            # Obter driver e cookies
            driver = self._get_driver()
            if not driver:
                print(f"   ❌ Driver não disponível")
                return False
            
            cookies = {cookie['name']: cookie['value'] for cookie in driver.get_cookies()}
            print(f"   🍪 DEBUG: Usando {len(cookies)} cookies para conceito (data-ri={data_ri})")
            
            # URL da requisição (sem query parameters)
            url = driver.current_url.split('?')[0]
            print(f"   🌐 DEBUG: URL da requisição: {url}")
            
            # Headers baseados no exemplo REAL fornecido pelo usuário
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'X-Requested-With': 'XMLHttpRequest',
                'Faces-Request': 'partial/ajax',
                'User-Agent': driver.execute_script("return navigator.userAgent;"),
                'Referer': driver.current_url
            }
            
            # Dados da requisição baseados no exemplo REAL fornecido pelo usuário
            element_id = f"formAtitudes:panelAtitudes:dataTableHabilidades:{data_ri}:notaConceito"
            
            post_data = {
                'javax.faces.partial.ajax': 'true',
                'javax.faces.source': element_id,
                'javax.faces.partial.execute': element_id,
                'javax.faces.partial.render': 'formAtitudes:panelAtitudes',
                'javax.faces.behavior.event': 'valueChange',
                'javax.faces.partial.event': 'change',
                f'{element_id}_focus': '',
                f'{element_id}_input': conceito_valor,  # Usar apenas o valor extraído
                'javax.faces.ViewState': viewstate
            }
            
            print(f"   📋 DEBUG: Dados da requisição (conceito_valor={conceito_valor}):")
            for key, value in post_data.items():
                if 'ViewState' in key:
                    print(f"     {key}: {str(value)[:50]}...")
                else:
                    print(f"     {key}: {value}")
            
            # Fazer requisição usando o mesmo método das atitudes (que funciona)
            from urllib.parse import urlencode
            
            session = requests.Session()
            for name, value in cookies.items():
                session.cookies.set(name, value)
            
            response = session.post(
                url,
                data=urlencode(post_data),
                headers=headers,
                timeout=15
            )
            
            if response.status_code == 200:
                # Debug: mostrar resposta
                print(f"   📋 DEBUG: Resposta HTTP ({len(response.text)} chars): {response.text[:200]}...")
                
                # Verificar se a sessão expirou
                if self._detectar_sessao_expirada(response.text):
                    print(f"   🚨 Sessão expirada detectada no conceito data-ri={data_ri}")
                    return False
                
                # Verificar se a resposta contém erro 500
                if 'redirect url="/errors/500.html"' in response.text:
                    print(f"   🚨 ERRO 500 DETECTADO ao lançar conceito: Servidor SGN com problema!")
                    return False
                
                # Verificar se há outros tipos de erro
                if '<redirect url=' in response.text and 'error' in response.text.lower():
                    print(f"   🚨 ERRO DETECTADO na resposta: {response.text}")
                    return False
                
                # Verificar se a resposta contém uma atualização válida do painel
                if 'formAtitudes:panelAtitudes' in response.text and 'update id=' in response.text:
                    # Verificar se o conceito aparece na resposta (indicando que foi aceito)
                    if f'selected="selected"' in response.text and conceito_valor in response.text:
                        print(f"   ✅ Conceito {conceito_valor} CONFIRMADO na resposta (data-ri={data_ri})")
                        return True
                    else:
                        print(f"   ⚠️ Conceito {conceito_valor} NÃO CONFIRMADO na resposta (data-ri={data_ri})")
                        print(f"   📋 Resposta completa: {response.text[:500]}...")
                        return False
                else:
                    print(f"   ❌ Resposta não contém atualização esperada do painel")
                    print(f"   📋 Resposta: {response.text[:300]}...")
                    return False
            else:
                print(f"   ❌ Erro HTTP {response.status_code} ao lançar conceito de habilidade")
                print(f"   📋 Resposta: {response.text[:200]}...")
                return False
                
        except Exception as e:
            print(f"   ❌ Erro ao lançar conceito de habilidade: {e}")
            return False

    def _lancar_conceito_final_via_requisicao(self, data_ri, conceito, viewstate):
        """
        Lança conceito final via requisição HTTP direta
        
        Args:
            data_ri (str): Índice da linha do aluno
            conceito (str): Conceito final (A, B, C, NE)
            viewstate (str): ViewState atual da sessão
            
        Returns:
            bool: True se sucesso, False caso contrário
        """
        print(f"   🎯 Lançando conceito final via requisição: {conceito}")
        
        try:
            driver = self._get_driver()
            
            # Obter cookies e URL
            cookies = {cookie['name']: cookie['value'] for cookie in driver.get_cookies()}
            url = driver.current_url
            if "?" in url:
                url = url.split("?")[0]
            
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'X-Requested-With': 'XMLHttpRequest',
                'Faces-Request': 'partial/ajax',
                'User-Agent': driver.execute_script("return navigator.userAgent;")
            }
            
            # Dados da requisição baseados na captura
            element_id = f"tabViewDiarioClasse:formAbaConceitos:dataTableConceitos:{data_ri}:comboConceitoFinal"
            
            post_data = {
                'javax.faces.partial.ajax': 'true',
                'javax.faces.source': element_id,
                'javax.faces.partial.execute': element_id,
                'javax.faces.partial.render': element_id,
                'javax.faces.behavior.event': 'valueChange',
                'javax.faces.partial.event': 'change',
                f'{element_id}_focus': '',
                f'{element_id}_input': conceito,
                'javax.faces.ViewState': viewstate
            }
            
            import requests
            from urllib.parse import urlencode
            
            session = requests.Session()
            for name, value in cookies.items():
                session.cookies.set(name, value)
            
            response = session.post(
                url,
                data=urlencode(post_data),
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                print(f"   ✅ Conceito final lançado com sucesso: {conceito}")
                return True
            else:
                print(f"   ❌ Erro na requisição: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"   ❌ Erro ao lançar conceito final: {e}")
            return False
    
    def _obter_viewstate_atual(self):
        """
        Obtém o ViewState atual da página
        
        Returns:
            str: ViewState ou None se não encontrado
        """
        try:
            driver = self._get_driver()
            
            # Múltiplas tentativas para encontrar ViewState
            seletores = [
                (By.NAME, "javax.faces.ViewState"),
                (By.ID, "javax.faces.ViewState"),
                (By.CSS_SELECTOR, "input[name='javax.faces.ViewState']"),
                (By.XPATH, "//input[@name='javax.faces.ViewState']")
            ]
            
            for by, selector in seletores:
                try:
                    viewstate_input = driver.find_element(by, selector)
                    viewstate = viewstate_input.get_attribute("value")
                    if viewstate:
                        print(f"   ✅ ViewState encontrado: {viewstate[:50]}...")
                        return viewstate
                except:
                    continue
            
            print("   ❌ ViewState não encontrado com nenhum seletor")
            return None
            
        except Exception as e:
            print(f"   ❌ Erro ao obter ViewState: {e}")
            return None
