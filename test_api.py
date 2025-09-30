"""
Script para testar a API de automação SGN

Este script fornece uma interface simples para testar todos os endpoints
da API de automação, incluindo:
- Teste de conectividade com a API
- Execução da automação completa
- Fechamento do navegador
- Verificação de health check

Uso:
    python test_api.py
"""
import requests
import json
import time

# Configurações da API
API_URL = "http://localhost:8000"

def test_health_check():
    """
    Testa o health check da API
    
    Verifica se a API está rodando e respondendo corretamente.
    Este é sempre o primeiro teste a ser executado.
    
    Returns:
        bool: True se a API estiver funcionando, False caso contrário
    """
    print("🔍 Testando health check da API...")
    
    try:
        response = requests.get(f"{API_URL}/health", timeout=5)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ API está funcionando: {result['status']}")
            print(f"   Serviço: {result['service']}")
            return True
        else:
            print(f"❌ API retornou status {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Erro: Não foi possível conectar com a API")
        print("   Certifique-se de que a API está rodando: python main.py")
        return False
    except requests.exceptions.Timeout:
        print("❌ Erro: Timeout ao conectar com a API")
        return False
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        return False

def test_api_info():
    """
    Testa o endpoint de informações da API
    
    Obtém informações sobre a API e lista os endpoints disponíveis.
    """
    print("\n📋 Obtendo informações da API...")
    
    try:
        response = requests.get(f"{API_URL}/", timeout=5)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ {result['message']}")
            print(f"   Versão: {result['version']}")
            print("   Endpoints disponíveis:")
            for endpoint, method in result['endpoints'].items():
                print(f"     - {endpoint}: {method}")
        else:
            print(f"❌ Erro ao obter informações: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Erro ao obter informações da API: {e}")

def test_login_and_navigate():
    """
    Testa o login e navegação no SGN
    
    Este é o teste principal que executa toda a automação:
    1. Faz login no sistema SGN
    2. Navega até a página de diários
    3. Acessa o diário da turma especificada
    4. Abre a aba de Conceitos
    
    Returns:
        bool: True se a automação foi bem-sucedida, False caso contrário
    """
    print("\n🤖 Testando automação completa...")
    
    # Dados de teste (substitua pelos seus dados reais)
    data = {
        "username": "natan.rubenich",
        "password": "senha123",
        "codigo_turma": "369528"
    }
    
    print(f"   Usuário: {data['username']}")
    print(f"   Turma: {data['codigo_turma']}")
    print("   Executando automação...")
    
    try:
        # Fazer requisição para a automação
        response = requests.post(
            f"{API_URL}/login-and-navigate", 
            json=data,
            timeout=60  # Timeout maior para automação
        )
        
        if response.status_code == 200:
            result = response.json()
            
            if result["success"]:
                print("✅ Automação concluída com sucesso!")
                print(f"   Mensagem: {result['message']}")
                return True
            else:
                print("❌ Falha na automação")
                print(f"   Erro: {result['message']}")
                return False
        else:
            print(f"❌ Erro HTTP: {response.status_code}")
            print(f"   Resposta: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ Timeout: A automação demorou mais que 60 segundos")
        return False
    except requests.exceptions.ConnectionError:
        print("❌ Erro: Conexão perdida durante a automação")
        return False
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        return False

def close_browser():
    """
    Fecha o navegador através da API
    
    Envia uma requisição para fechar o navegador e liberar recursos.
    Deve ser chamado após os testes para limpeza.
    
    Returns:
        bool: True se o navegador foi fechado com sucesso, False caso contrário
    """
    print("\n🔒 Fechando navegador...")
    
    try:
        response = requests.post(f"{API_URL}/close-browser", timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ {result['message']}")
            return True
        else:
            print(f"❌ Erro ao fechar navegador: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Erro ao fechar navegador: {e}")
        return False

def main():
    """
    Função principal que executa todos os testes em sequência
    
    Executa os testes na seguinte ordem:
    1. Health check da API
    2. Informações da API
    3. Automação completa (se o usuário confirmar)
    4. Fechamento do navegador
    """
    print("🚀 Teste da API SGN Automação")
    print("=" * 50)
    
    # 1. Testar conectividade
    if not test_health_check():
        print("\n❌ Não foi possível conectar com a API. Encerrando testes.")
        return
    
    # 2. Obter informações da API
    test_api_info()
    
    # 3. Confirmar execução da automação
    print("\n" + "=" * 50)
    print("⚠️  ATENÇÃO: O próximo teste irá abrir o navegador e executar a automação completa.")
    print("   Certifique-se de que:")
    print("   - Suas credenciais estão corretas no código")
    print("   - O código da turma está correto")
    print("   - Você tem acesso ao sistema SGN")
    
    confirmar = input("\nDeseja continuar com a automação? (s/N): ").lower().strip()
    
    if confirmar == 's' or confirmar == 'sim':
        # 4. Executar automação
        automation_success = test_login_and_navigate()
        
        # 5. Aguardar antes de fechar (para visualizar resultado)
        if automation_success:
            input("\n✅ Automação concluída! Pressione Enter para fechar o navegador...")
        else:
            input("\n❌ Automação falhou. Pressione Enter para tentar fechar o navegador...")
        
        # 6. Fechar navegador
        close_browser()
    else:
        print("🚫 Automação cancelada pelo usuário.")
    
    print("\n🏁 Testes concluídos!")

if __name__ == "__main__":
    main()
