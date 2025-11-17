"""
Módulo para conversão de áudio WAV para formato A1800 do Furby
e upload via BLE usando PyFluff.

Baseado no projeto ctxis/Furby (https://github.com/ctxis/Furby)
"""
import os
import struct
import tempfile
from pathlib import Path
from typing import Optional

# Header do formato A18
A18_HEADER = b"\x00\xff\x00\xffGENERALPLUS SP\x00\x00"


def is_a18_file(file_path: str) -> bool:
    """Verifica se um arquivo é um arquivo A18 válido"""
    try:
        with open(file_path, 'rb') as f:
            header = f.read(len(A18_HEADER))
            return header == A18_HEADER
    except:
        return False


def create_a18_from_wav(wav_path: str, output_path: Optional[str] = None) -> str:
    """
    Converte um arquivo WAV para formato A18.
    
    NOTA: Esta é uma implementação simplificada baseada no formato A18.
    Para conversão completa e compatível com o Furby, seria necessário
    usar a DLL a1800.dll do Windows (do projeto ctxis/Furby) ou uma
    biblioteca específica que implemente o codec A1800.
    
    Esta função cria um arquivo A18 básico que pode funcionar para alguns
    casos, mas pode não ser totalmente compatível com o Furby Connect.
    
    Para conversão completa, recomenda-se:
    1. Usar o projeto ctxis/Furby no Windows com a1800.dll:
       https://github.com/ctxis/Furby
    2. Converter WAV → A18 usando ferramentas externas
    3. Usar arquivos A18 já convertidos de DLCs originais
    
    Args:
        wav_path: Caminho para o arquivo WAV
        output_path: Caminho de saída (opcional, cria temporário se None)
    
    Returns:
        Caminho do arquivo A18 criado
    
    Raises:
        RuntimeError: Se houver erro na conversão
    """
    if output_path is None:
        with tempfile.NamedTemporaryFile(suffix=".a18", delete=False) as tmp:
            output_path = tmp.name
    
    # Lê o arquivo WAV
    try:
        import wave
        with wave.open(wav_path, 'rb') as wav_file:
            frames = wav_file.getnframes()
            sample_rate = wav_file.getframerate()
            channels = wav_file.getnchannels()
            sample_width = wav_file.getsampwidth()
            audio_data = wav_file.readframes(frames)
            
            # Validações básicas
            if sample_rate not in [8000, 16000, 16001]:  # Taxas comuns do Furby
                raise RuntimeError(
                    f"Sample rate {sample_rate} não suportado. "
                    "Use 8000, 16000 ou 16001 Hz."
                )
            if channels != 1:
                raise RuntimeError(
                    f"Canais {channels} não suportado. Use mono (1 canal)."
                )
            if sample_width != 2:  # 16-bit
                raise RuntimeError(
                    f"Sample width {sample_width} não suportado. Use 16-bit (2 bytes)."
                )
    except wave.Error as e:
        raise RuntimeError(f"Erro ao ler arquivo WAV: {e}")
    except Exception as e:
        raise RuntimeError(f"Erro ao processar arquivo WAV: {e}")
    
    # Cria arquivo A18 com header
    try:
        with open(output_path, 'wb') as a18_file:
            # Escreve header A18
            a18_file.write(A18_HEADER)
            
            # Escreve metadados básicos (formato simplificado baseado em análise de A18s reais)
            # Nota: O formato real pode ter mais campos e estrutura diferente
            a18_file.write(struct.pack('<I', sample_rate))  # Sample rate (little-endian)
            a18_file.write(struct.pack('<H', 1))  # Channels (sempre 1 para mono)
            a18_file.write(struct.pack('<H', sample_width))  # Sample width
            
            # Escreve tamanho dos dados
            a18_file.write(struct.pack('<I', len(audio_data)))
            
            # Escreve dados de áudio
            a18_file.write(audio_data)
    except Exception as e:
        raise RuntimeError(f"Erro ao escrever arquivo A18: {e}")
    
    return output_path


def convert_wav_to_a18(wav_path: str, output_path: Optional[str] = None) -> str:
    """
    Converte WAV para A18. Tenta múltiplas abordagens.
    
    Args:
        wav_path: Caminho para arquivo WAV
        output_path: Caminho de saída (opcional)
    
    Returns:
        Caminho do arquivo A18
    """
    # Se já é A18, retorna o próprio caminho
    if is_a18_file(wav_path):
        return wav_path
    
    # Tenta conversão básica
    return create_a18_from_wav(wav_path, output_path)

