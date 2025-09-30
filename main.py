"""
Ponto de entrada da aplicação SGN Automação de Notas

Este é o arquivo principal que inicializa e executa a aplicação.
Ele importa a função factory que cria a aplicação FastAPI configurada
e a executa usando o servidor Uvicorn.

Uso:
    python main.py  # Executa a aplicação em modo desenvolvimento
    
    Ou via uvicorn diretamente:
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload
"""
from src.api import create_app

# Criar aplicação FastAPI usando a função factory
# Esta instância será usada pelo Uvicorn para servir a aplicação
app = create_app()

if __name__ == "__main__":
    """
    Executa a aplicação em modo desenvolvimento
    
    Configurações do Uvicorn:
    - host="0.0.0.0": Permite acesso de qualquer IP (não apenas localhost)
    - port=8000: Porta padrão da aplicação
    - reload=True: Reinicia automaticamente quando arquivos são modificados
    """
    import uvicorn
    
    print("🚀 Iniciando SGN Automação de Notas API...")
    print("📖 Documentação disponível em: http://localhost:8001/docs")
    print("🔍 Health check em: http://localhost:8001/health")
    
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=8001, 
        reload=True,
        log_level="info"
    )
