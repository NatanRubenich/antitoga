"""
Sistema de captura de logs para retornar ao frontend
"""
import sys
import io

class TeeOutput:
    """
    Classe que escreve tanto no terminal quanto captura para enviar ao frontend
    Similar ao comando 'tee' do Unix
    """
    def __init__(self, original_stdout, string_io):
        self.original_stdout = original_stdout
        self.string_io = string_io
    
    def write(self, text):
        """Escreve no terminal E captura"""
        self.original_stdout.write(text)  # Escreve no terminal
        self.original_stdout.flush()
        self.string_io.write(text)  # Captura para enviar ao frontend
    
    def flush(self):
        """Flush em ambos os outputs"""
        self.original_stdout.flush()
        self.string_io.flush()

class LogCapture:
    """Captura prints e logs do Python para retornar ao frontend"""
    
    def __init__(self):
        self.logs = []
        self.original_stdout = None
        self.string_io = None
        self.tee = None
    
    def start(self):
        """Inicia a captura de logs"""
        self.logs = []
        self.original_stdout = sys.stdout
        self.string_io = io.StringIO()
        self.tee = TeeOutput(self.original_stdout, self.string_io)
        sys.stdout = self.tee
    
    def stop(self):
        """Para a captura e retorna os logs"""
        if self.original_stdout:
            sys.stdout = self.original_stdout
        
        if self.string_io:
            captured = self.string_io.getvalue()
            self.logs = captured.split('\n') if captured else []
            self.string_io.close()
        
        return self.logs
    
    def get_logs(self):
        """Retorna os logs capturados até o momento"""
        if self.string_io:
            return self.string_io.getvalue().split('\n')
        return self.logs
