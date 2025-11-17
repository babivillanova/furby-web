import os
import asyncio
import tempfile
import random
import threading
from typing import Optional, List, Dict, Any
from pathlib import Path
import requests

# Importa módulo de conversão de áudio
try:
    from audio_converter import convert_wav_to_a18, is_a18_file
except ImportError:
    # Fallback se o módulo não existir
    def convert_wav_to_a18(wav_path: str, output_path: Optional[str] = None) -> str:
        raise RuntimeError("Módulo audio_converter não disponível")
    def is_a18_file(file_path: str) -> bool:
        return False

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

# Carregar variáveis de ambiente (.env)
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

MOCK_MODE = os.getenv("MOCK_MODE", "true").lower() == "true"
DEFAULT_PORT = int(os.getenv("PORT", "8000"))
PREFERRED_ADDRESS = os.getenv("FURBY_ADDRESS", "").strip() or None

# Configurações do Porcupine Wake Word
PORCUPINE_ACCESS_KEY = os.getenv("PORCUPINE_ACCESS_KEY", "").strip()
PORCUPINE_ENABLED = os.getenv("PORCUPINE_ENABLED", "false").lower() == "true"
PORCUPINE_KEYWORD = os.getenv("PORCUPINE_KEYWORD", "alexa")  # Palavra padrão enquanto não há modelo customizado

# Configurações da OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_ENABLED = os.getenv("OPENAI_ENABLED", "false").lower() == "true"
CONVERSATION_TIMEOUT = int(os.getenv("CONVERSATION_TIMEOUT", "5"))  # segundos para gravar após wake word

# BLE scan via Bleak (escaneia mesmo em modo simulado, se quiser)
from bleak import BleakScanner

# Tentar importar PyFluff (só necessário para modo real)
_pyfluff = None
if not MOCK_MODE:
    try:
        from pyfluff.furby import FurbyConnect  # type: ignore
        _pyfluff = FurbyConnect
    except Exception as e:
        # Se a lib não estiver disponível, forçamos modo simulado
        print(f"[warn] PyFluff não disponível ({e}); usando MOCK_MODE=true")
        MOCK_MODE = True
        _pyfluff = None

# ----------------- Conversação com OpenAI -----------------

class ConversationManager:
    """Gerencia conversação com OpenAI após wake word"""
    
    def __init__(self):
        self.recording = False
        
    async def handle_conversation(self):
        """Grava áudio, envia para OpenAI, toca resposta e dispara ação no Furby"""
        try:
            import pyaudio
            import wave
            import tempfile
            import struct
            from openai import OpenAI
            
            if not OPENAI_API_KEY:
                LOG.add("[openai] ❌ OPENAI_API_KEY não configurada")
                return
                
            LOG.add(f"[openai] 🎤 Escutando sua pergunta por {CONVERSATION_TIMEOUT} segundos...")
            
            # Configurar gravação
            CHUNK = 1024
            FORMAT = pyaudio.paInt16
            CHANNELS = 1
            RATE = 16000
            
            p = pyaudio.PyAudio()
            
            # Gravar áudio
            frames = []
            stream = p.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK
            )
            
            LOG.add("[openai] 🎙️ Gravando... Fale agora!")
            
            for i in range(0, int(RATE / CHUNK * CONVERSATION_TIMEOUT)):
                data = stream.read(CHUNK, exception_on_overflow=False)
                frames.append(data)
            
            LOG.add("[openai] ✓ Gravação concluída")
            
            stream.stop_stream()
            stream.close()
            p.terminate()
            
            # Salvar áudio temporário
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio:
                audio_filename = temp_audio.name
                
            wf = wave.open(audio_filename, 'wb')
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(p.get_sample_size(FORMAT))
            wf.setframerate(RATE)
            wf.writeframes(b''.join(frames))
            wf.close()
            
            LOG.add("[openai] 📤 Enviando para OpenAI (REST)...")
            
            headers_auth = {
                "Authorization": f"Bearer {OPENAI_API_KEY}"
            }
            headers_json = {
                **headers_auth,
                "Content-Type": "application/json"
            }
            
            # 1) Transcrição (Whisper)
            LOG.add("[openai] 📝 Transcrevendo áudio via /audio/transcriptions ...")
            with open(audio_filename, "rb") as audio_file:
                files = {
                    "file": ("audio.wav", audio_file, "audio/wav")
                }
                data = {"model": "whisper-1", "response_format": "json"}
                resp = requests.post(
                    "https://api.openai.com/v1/audio/transcriptions",
                    headers=headers_auth,
                    data=data,
                    files=files,
                    timeout=90
                )
            if resp.status_code >= 400:
                LOG.add(f"[openai] ❌ erro na transcrição: {resp.status_code} {resp.text}")
                raise RuntimeError(f"Falha ao transcrever áudio: {resp.text}")
            transcription_data = resp.json()
            user_text = transcription_data.get("text", "").strip()
            if not user_text:
                raise RuntimeError("Transcrição vazia")
            LOG.add(f"[openai] 💬 Você disse: '{user_text}'")
            
            # 2) Chat Completion
            LOG.add("[openai] 🤔 Gerando resposta via /chat/completions ...")
            chat_payload = {
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": "Você só responde um Oi animado!"},
                    {"role": "user", "content": user_text}
                ],
                "temperature": 0.8,
            }
            resp = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers_json,
                json=chat_payload,
                timeout=90
            )
            if resp.status_code >= 400:
                LOG.add(f"[openai] ❌ erro no chat: {resp.status_code} {resp.text}")
                raise RuntimeError(f"Falha ao gerar resposta: {resp.text}")
            response_data = resp.json()
            assistant_text = response_data["choices"][0]["message"]["content"].strip()
            LOG.add(f"[openai] 🤖 Furby responde: '{assistant_text}'")
            
            # 3) Text-to-Speech
            LOG.add("[openai] 🔊 Gerando áudio da resposta (gpt-4o-mini-tts)...")
            speech_payload = {
                "model": "gpt-4o-mini-tts",
                "voice": "nova",
                "input": assistant_text,
                "speed": 1.1
            }
            with requests.post(
                "https://api.openai.com/v1/audio/speech",
                headers=headers_json,
                json=speech_payload,
                stream=True,
                timeout=120
            ) as speech_resp:
                if speech_resp.status_code >= 400:
                    LOG.add(f"[openai] ❌ erro no TTS: {speech_resp.status_code} {speech_resp.text}")
                    raise RuntimeError(f"Falha ao gerar áudio: {speech_resp.text}")
                
                with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_response:
                    response_filename = temp_response.name
                    for chunk in speech_resp.iter_content(chunk_size=8192):
                        if chunk:
                            temp_response.write(chunk)
            
            LOG.add("[openai] 🔊 Tocando resposta no computador...")
            self._play_audio_on_computer(response_filename)
            LOG.add("[openai] ✓ Resposta tocada!")
            
            # Limpar arquivos temporários
            try:
                os.unlink(audio_filename)
                os.unlink(response_filename)
            except:
                pass
            
            # Disparar ação aleatória no Furby
            LOG.add("[openai] 🎲 Disparando ação aleatória no Furby...")
            await CTRL.random_action()
            LOG.add("[openai] ✅ Conversação completa!")
            
        except Exception as e:
            LOG.add(f"[openai] ❌ Erro na conversação: {e}")
            import traceback
            LOG.add(f"[openai] {traceback.format_exc()}")
    
    def _play_audio_on_computer(self, audio_file):
        """Toca áudio no computador usando pydub + pyaudio"""
        try:
            from pydub import AudioSegment
            from pydub.playback import play
            import pyaudio
            
            # Carregar e tocar áudio
            audio = AudioSegment.from_file(audio_file)
            play(audio)
            
        except Exception as e:
            LOG.add(f"[openai] erro ao tocar áudio: {e}")
            # Fallback: usar sistema operacional
            try:
                import platform
                if platform.system() == "Darwin":  # macOS
                    os.system(f"afplay {audio_file}")
                elif platform.system() == "Linux":
                    os.system(f"aplay {audio_file}")
                elif platform.system() == "Windows":
                    os.system(f"start {audio_file}")
            except:
                pass

# Instância global do gerenciador de conversação
CONVERSATION_MANAGER = ConversationManager()

# ----------------- Wake Word Detection -----------------

class WakeWordDetector:
    """Detecta a palavra-chave usando Porcupine e dispara ação aleatória"""
    
    def __init__(self):
        self.running = False
        self.thread = None
        self.porcupine = None
        self.audio_stream = None
        
    def start(self):
        """Inicia o detector em uma thread separada"""
        if not PORCUPINE_ENABLED:
            LOG.add("[wake-word] detector desabilitado (PORCUPINE_ENABLED=false)")
            return
            
        if not PORCUPINE_ACCESS_KEY:
            LOG.add("[wake-word] ERRO: PORCUPINE_ACCESS_KEY não configurada")
            LOG.add("[wake-word] Obtenha sua access key em: https://console.picovoice.ai/")
            return
        
        if self.running:
            LOG.add("[wake-word] detector já está rodando")
            return
        
        # Mostra qual modo está ativo
        if OPENAI_ENABLED and OPENAI_API_KEY:
            LOG.add("[wake-word] ========================================")
            LOG.add("[wake-word] 🤖 MODO OPENAI ATIVO")
            LOG.add("[wake-word] Após wake word: grava → OpenAI → resposta")
            LOG.add(f"[wake-word] Tempo de gravação: {CONVERSATION_TIMEOUT} segundos")
            LOG.add("[wake-word] ========================================")
        else:
            LOG.add("[wake-word] ========================================")
            LOG.add("[wake-word] 🎲 MODO SIMPLES ATIVO")
            LOG.add("[wake-word] Após wake word: apenas ação aleatória")
            if not OPENAI_API_KEY:
                LOG.add("[wake-word] Para ativar OpenAI: configure OPENAI_API_KEY no .env")
            if not OPENAI_ENABLED:
                LOG.add("[wake-word] Para ativar OpenAI: configure OPENAI_ENABLED=true no .env")
            LOG.add("[wake-word] ========================================")
            
        self.running = True
        self.thread = threading.Thread(target=self._run_detector, daemon=True)
        self.thread.start()
        LOG.add(f"[wake-word] detector iniciado, aguardando palavra '{PORCUPINE_KEYWORD}'...")
    
    def stop(self):
        """Para o detector"""
        if not self.running:
            return
            
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
        LOG.add("[wake-word] detector parado")
    
    def _run_detector(self):
        """Loop principal do detector (roda em thread separada)"""
        pa = None
        try:
            import pvporcupine
            import pyaudio
            import struct
            import numpy as np
            
            LOG.add("[wake-word] iniciando detector...")
            
            # Inicializa Porcupine com palavra-chave
            keywords = [PORCUPINE_KEYWORD]
            
            LOG.add(f"[wake-word] criando instância Porcupine para palavra: '{PORCUPINE_KEYWORD}'")
            self.porcupine = pvporcupine.create(
                access_key=PORCUPINE_ACCESS_KEY,
                keywords=keywords
            )
            
            LOG.add(f"[wake-word] Porcupine criado com sucesso")
            LOG.add(f"[wake-word] Sample rate: {self.porcupine.sample_rate} Hz")
            LOG.add(f"[wake-word] Frame length: {self.porcupine.frame_length}")
            
            # Inicializa PyAudio
            pa = pyaudio.PyAudio()
            
            # Lista dispositivos de áudio disponíveis
            LOG.add(f"[wake-word] dispositivos de áudio disponíveis:")
            for i in range(pa.get_device_count()):
                info = pa.get_device_info_by_index(i)
                if info['maxInputChannels'] > 0:
                    LOG.add(f"[wake-word]   [{i}] {info['name']} (canais: {info['maxInputChannels']})")
            
            LOG.add("[wake-word] abrindo stream de áudio...")
            self.audio_stream = pa.open(
                rate=self.porcupine.sample_rate,
                channels=1,
                format=pyaudio.paInt16,
                input=True,
                frames_per_buffer=self.porcupine.frame_length
            )
            
            LOG.add(f"[wake-word] ✓ DETECTOR ATIVO - Escutando por '{PORCUPINE_KEYWORD}'")
            LOG.add(f"[wake-word] Fale claramente e com volume adequado...")
            
            frame_count = 0
            last_volume_log = 0
            
            while self.running:
                try:
                    # Lê áudio do microfone
                    pcm = self.audio_stream.read(self.porcupine.frame_length, exception_on_overflow=False)
                    pcm = struct.unpack_from("h" * self.porcupine.frame_length, pcm)
                    
                    # Calcula volume do áudio (para debug)
                    frame_count += 1
                    if frame_count % 50 == 0:  # Log a cada 50 frames (~1.5 segundos)
                        audio_array = np.array(pcm, dtype=np.int16)
                        volume = np.abs(audio_array).mean()
                        if frame_count - last_volume_log >= 50:
                            LOG.add(f"[wake-word] 🎤 capturando áudio... (volume médio: {int(volume)})")
                            last_volume_log = frame_count
                    
                    # Processa áudio e detecta palavra-chave
                    keyword_index = self.porcupine.process(pcm)
                    
                    if keyword_index >= 0:
                        LOG.add(f"[wake-word] ✓✓✓ PALAVRA DETECTADA: '{keywords[keyword_index]}'! ✓✓✓")
                        
                        # Se OpenAI estiver habilitado, inicia conversação
                        if OPENAI_ENABLED and OPENAI_API_KEY:
                            LOG.add("[wake-word] 🤖 Iniciando conversação com OpenAI...")
                            self._trigger_conversation()
                        else:
                            # Fallback: dispara ação aleatória
                            LOG.add("[wake-word] 🎲 Disparando ação aleatória...")
                            self._trigger_random_action()
                        
                        # Pequena pausa para não detectar múltiplas vezes
                        import time
                        time.sleep(2.0)
                        
                except Exception as read_error:
                    if self.running:  # Só loga se ainda estiver rodando
                        LOG.add(f"[wake-word] erro ao ler/processar áudio: {read_error}")
                    
        except ImportError as e:
            LOG.add(f"[wake-word] ❌ erro ao importar bibliotecas: {e}")
            LOG.add("[wake-word] instale com: pip install pvporcupine pyaudio")
        except Exception as e:
            LOG.add(f"[wake-word] ❌ erro no detector: {e}")
            import traceback
            LOG.add(f"[wake-word] traceback: {traceback.format_exc()}")
        finally:
            # Cleanup
            LOG.add("[wake-word] limpando recursos...")
            if self.audio_stream:
                try:
                    self.audio_stream.stop_stream()
                    self.audio_stream.close()
                    LOG.add("[wake-word] stream de áudio fechado")
                except:
                    pass
            if pa:
                try:
                    pa.terminate()
                    LOG.add("[wake-word] PyAudio terminado")
                except:
                    pass
            if self.porcupine:
                try:
                    self.porcupine.delete()
                    LOG.add("[wake-word] Porcupine deletado")
                except:
                    pass
            LOG.add("[wake-word] detector parado completamente")
    
    def _trigger_conversation(self):
        """Inicia conversação com OpenAI quando palavra é detectada"""
        try:
            # Cria um novo event loop para a thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Executa a conversação
            loop.run_until_complete(CONVERSATION_MANAGER.handle_conversation())
            
            loop.close()
        except Exception as e:
            LOG.add(f"[wake-word] erro ao iniciar conversação: {e}")
    
    def _trigger_random_action(self):
        """Dispara ação aleatória quando palavra é detectada"""
        try:
            # Cria um novo event loop para a thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Executa a ação aleatória
            loop.run_until_complete(CTRL.random_action())
            
            loop.close()
        except Exception as e:
            LOG.add(f"[wake-word] erro ao disparar ação: {e}")

# ----------------- Camada de controle -----------------

class Log:
    def __init__(self):
        self._lines: List[str] = []

    def add(self, msg: str):
        line = msg.strip()
        print(line)
        self._lines.append(line)
        if len(self._lines) > 500:
            self._lines = self._lines[-500:]

    def dump(self) -> List[str]:
        return self._lines[-200:]

LOG = Log()

class SimulatedFurby:
    def __init__(self):
        self.connected = False
        self.address: Optional[str] = None

    async def connect(self, address: Optional[str] = None):
        await asyncio.sleep(0.2)
        self.connected = True
        self.address = address or "FA:KE:FU:RB:YY:00"
        LOG.add(f"[sim] conectado ao Furby simulado @ {self.address}")

    async def disconnect(self):
        if self.connected:
            self.connected = False
            LOG.add("[sim] desconectado")

    async def set_antenna_color(self, r: int, g: int, b: int):
        LOG.add(f"[sim] antena RGB=({r},{g},{b})")

    async def trigger_action(self, input: int, index: int, subindex: int, specific: int):
        LOG.add(f"[sim] action input={input}, index={index}, subindex={subindex}, specific={specific}")

    async def play_wav(self, wav_path: str):
        LOG.add(f"[sim] [audio] simulando toque de áudio: {Path(wav_path).name}")

class RealFurby:
    def __init__(self):
        if _pyfluff is None:
            raise RuntimeError("PyFluff não carregado")
        self._furby = _pyfluff()
        self.connected = False
        self.address: Optional[str] = None

    async def connect(self, address: Optional[str] = None):
        # PyFluff consegue descobrir sozinho; address é opcional
        if address is None:
            await self._furby.connect()
        else:
            await self._furby.connect(address=address)
        self.connected = True
        self.address = address
        LOG.add("[real] conectado ao Furby via PyFluff")

    async def disconnect(self):
        await self._furby.disconnect()
        self.connected = False
        LOG.add("[real] desconectado")

    async def set_antenna_color(self, r: int, g: int, b: int):
        await self._furby.set_antenna_color(r, g, b)
        LOG.add(f"[real] antena RGB=({r},{g},{b})")

    async def trigger_action(self, input: int, index: int, subindex: int, specific: int):
        await self._furby.trigger_action(input=input, index=index, subindex=subindex, specific=specific)
        LOG.add(f"[real] action input={input}, index={index}, subindex={subindex}, specific={specific}")

    async def play_wav(self, wav_path: str):
        if not os.path.exists(wav_path):
            raise FileNotFoundError(f"Arquivo não encontrado: {wav_path}")
        
        LOG.add(f"[audio] carregando {wav_path}...")
        
        # Verifica se já é A18
        is_a18 = is_a18_file(wav_path)
        a18_path = None
        
        try:
            # Converte WAV para A18 se necessário
            if not is_a18:
                LOG.add("[audio] convertendo WAV para A18...")
                try:
                    a18_path = convert_wav_to_a18(wav_path)
                    LOG.add(f"[audio] conversão concluída: {Path(a18_path).name}")
                except Exception as e:
                    LOG.add(f"[audio] erro na conversão: {e}")
                    raise RuntimeError(f"Erro ao converter WAV para A18: {e}")
            else:
                a18_path = wav_path
                LOG.add("[audio] arquivo já está em formato A18")
            
            # Verifica se está conectado
            if not self.connected:
                raise RuntimeError("Furby não está conectado. Conecte antes de tocar áudio.")
            
            # Tenta diferentes métodos de upload
            methods_tried = []
            
            # Método 1: play_sound_file (PyFluff v0.3+)
            if hasattr(self._furby, 'play_sound_file'):
                try:
                    LOG.add("[audio] tentando play_sound_file...")
                    await self._furby.play_sound_file(a18_path if is_a18 else wav_path)
                    LOG.add(f"[audio] áudio enviado via play_sound_file: {Path(a18_path).name}")
                    return
                except Exception as e:
                    methods_tried.append(f"play_sound_file: {e}")
                    LOG.add(f"[audio] play_sound_file falhou: {e}")
            
            # Método 2: upload_and_play_sound
            if hasattr(self._furby, 'upload_and_play_sound'):
                try:
                    LOG.add("[audio] tentando upload_and_play_sound...")
                    await self._furby.upload_and_play_sound(a18_path)
                    LOG.add(f"[audio] áudio enviado via upload_and_play_sound")
                    return
                except Exception as e:
                    methods_tried.append(f"upload_and_play_sound: {e}")
                    LOG.add(f"[audio] upload_and_play_sound falhou: {e}")
            
            # Método 3: Upload via BLE usando client/device do PyFluff
            # Tenta fazer upload direto do arquivo A18 via características BLE
            if hasattr(self._furby, 'client') and self._furby.client:
                try:
                    LOG.add("[audio] tentando upload via client BLE...")
                    await self._upload_a18_via_ble(a18_path)
                    LOG.add(f"[audio] áudio enviado via BLE client")
                    return
                except Exception as e:
                    methods_tried.append(f"BLE client upload: {e}")
                    LOG.add(f"[audio] upload via BLE client falhou: {e}")
            
            # Se nenhum método funcionou
            error_msg = (
                "Não foi possível enviar o áudio ao Furby.\n\n"
                "Métodos tentados:\n" + "\n".join(f"  - {m}" for m in methods_tried) + "\n\n"
                "Alternativas:\n"
                "1. Use trigger_action com índices de som (ex: input=1, index=20-30)\n"
                "2. Verifique se o Furby está conectado\n"
                "3. Tente usar um arquivo A18 já convertido\n\n"
                "Nota: Para conversão completa WAV → A18, pode ser necessário usar "
                "ferramentas externas ou o projeto ctxis/Furby no Windows."
            )
            LOG.add(f"[audio] ERRO: {error_msg}")
            raise RuntimeError(error_msg)
            
        finally:
            # Limpa arquivo temporário A18 se foi criado
            if a18_path and a18_path != wav_path and os.path.exists(a18_path):
                try:
                    os.unlink(a18_path)
                except:
                    pass
    
    async def _upload_a18_via_ble(self, a18_path: str):
        """
        Tenta fazer upload do arquivo A18 via BLE usando características do PyFluff.
        Esta é uma implementação experimental baseada no protocolo BLE do Furby.
        """
        if not hasattr(self._furby, 'client') or not self._furby.client:
            raise RuntimeError("Client BLE não disponível")
        
        # Lê o arquivo A18
        with open(a18_path, 'rb') as f:
            a18_data = f.read()
        
        # UUIDs conhecidos do Furby Connect (podem variar)
        # Estes são valores comuns para características de upload de arquivo
        FILE_UPLOAD_CHAR_UUID = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"  # Exemplo
        
        # Tenta escrever em chunks (BLE tem limite de tamanho por pacote)
        chunk_size = 20  # Tamanho típico de chunk BLE
        
        LOG.add(f"[audio] enviando {len(a18_data)} bytes em chunks de {chunk_size}...")
        
        # Esta é uma implementação básica - pode precisar de ajustes
        # baseado na implementação real do PyFluff
        raise NotImplementedError(
            "Upload via BLE direto ainda não está totalmente implementado. "
            "Use trigger_action ou aguarde suporte completo no PyFluff."
        )

class Controller:
    def __init__(self):
        self.mode = "mock" if MOCK_MODE else "real"
        self.device = SimulatedFurby() if MOCK_MODE else RealFurby()
        self.lock = asyncio.Lock()

    async def scan(self) -> List[Dict[str, Any]]:
        # Avisa se está conectado (dispositivos conectados podem não aparecer no scan)
        if self.device.connected:
            LOG.add("[scan] AVISO: Furby está conectado. Dispositivos conectados podem não aparecer no scan.")
            LOG.add("[scan] Se não encontrar o Furby, desconecte primeiro e tente novamente.")
        
        LOG.add("[scan] procurando dispositivos BLE…")
        try:
            LOG.add("[scan] iniciando descoberta (timeout: 5s)...")
            devices = await BleakScanner.discover(timeout=5.0)
            LOG.add(f"[scan] total de dispositivos BLE encontrados: {len(devices)}")
            
            # Log todos os dispositivos encontrados para debug
            for d in devices[:10]:  # Limita a 10 para não poluir o log
                name = d.name or "Sem nome"
                LOG.add(f"[scan] dispositivo: {name} @ {d.address}")
                
        except Exception as e:
            LOG.add(f"[scan] ERRO: {e}")
            LOG.add(f"[scan] tipo do erro: {type(e).__name__}")
            import traceback
            LOG.add(f"[scan] traceback: {traceback.format_exc()}")
            devices = []
        
        items = []
        for d in devices:
            name = d.name or ""
            if name and ("Furby" in name or "Furby Connect" in name or "BlueFur" in name):
                items.append({"name": d.name, "address": d.address})
        
        # No simulado, garante uma entrada fake para testes
        if MOCK_MODE and not items:
            items.append({"name": "Furby Simulado", "address": "FA:KE:FU:RB:YY:00"})
        
        LOG.add(f"[scan] Furbies encontrados: {len(items)}")
        if items:
            for item in items:
                LOG.add(f"[scan]   - {item['name']} @ {item['address']}")
        else:
            LOG.add("[scan] Nenhum Furby encontrado. Verifique se está ligado e próximo.")
        
        return items

    async def connect(self, address: Optional[str] = None):
        async with self.lock:
            await self.device.connect(address or PREFERRED_ADDRESS)

    async def disconnect(self):
        async with self.lock:
            try:
                if self.device.connected:
                    await self.device.disconnect()
            except Exception as e:
                LOG.add(f"[disconnect] erro ao desconectar: {e}")
                # Força limpeza do estado mesmo se houver erro
                self.device.connected = False
                self.device.address = None

    async def reset(self):
        """Desconecta e limpa o estado completamente"""
        async with self.lock:
            try:
                if self.device.connected:
                    await self.device.disconnect()
            except Exception as e:
                LOG.add(f"[reset] erro ao desconectar: {e}")
            finally:
                # Força limpeza do estado
                self.device.connected = False
                self.device.address = None
                LOG.add("[reset] estado resetado")

    async def set_color(self, r: int, g: int, b: int):
        async with self.lock:
            if not (0 <= r <= 255 and 0 <= g <= 255 and 0 <= b <= 255):
                raise ValueError("RGB entre 0 e 255")
            await self.device.set_antenna_color(r, g, b)

    async def action(self, input: int, index: int, subindex: int, specific: int):
        async with self.lock:
            await self.device.trigger_action(input, index, subindex, specific)

    async def play_wav(self, wav_path: str):
        async with self.lock:
            await self.device.play_wav(wav_path)
    
    async def random_action(self):
        """Dispara uma ação aleatória no Furby da lista de ações conhecidas"""
        async with self.lock:
            # Lista de ações divertidas do Furby
            actions = [
                # Generic reactions (pets)
                (1, 0, 0, 0), (1, 0, 0, 1), (1, 0, 0, 3), (1, 0, 0, 4),
                (1, 0, 1, 3), (1, 0, 1, 4), (1, 0, 1, 5),
                (1, 2, 0, 0), (1, 2, 0, 1), (1, 2, 0, 2), (1, 2, 0, 3),
                (1, 3, 0, 5), (1, 3, 0, 6), (1, 3, 0, 10), (1, 3, 0, 12),
                
                # Tickles
                (2, 0, 0, 0), (2, 0, 0, 1), (2, 0, 0, 2), (2, 0, 0, 3),
                (2, 0, 1, 0), (2, 0, 1, 1), (2, 0, 1, 2), (2, 0, 1, 4),
                (2, 3, 0, 0), (2, 3, 0, 1), (2, 3, 0, 4), (2, 3, 0, 11),
                
                # Pull/squeeze
                (3, 0, 0, 0), (3, 0, 0, 3), (3, 0, 0, 4), (3, 0, 0, 5),
                (3, 3, 0, 0), (3, 3, 0, 1), (3, 3, 0, 4), (3, 3, 0, 9),
                
                # Hugs
                (5, 0, 0, 0), (5, 0, 1, 0), (5, 0, 1, 1), (5, 0, 1, 2),
                (5, 3, 0, 0), (5, 3, 0, 3), (5, 3, 0, 4),
                
                # Farts & burps
                (7, 0, 0, 0), (7, 0, 0, 1), (7, 0, 0, 2), (7, 0, 0, 4),
                (7, 1, 0, 0), (7, 1, 0, 3), (7, 3, 0, 1), (7, 3, 0, 6),
                
                # Conversation
                (8, 0, 0, 0), (8, 0, 0, 1), (8, 0, 0, 3), (8, 0, 0, 9),
                (8, 0, 1, 0), (8, 0, 1, 3), (8, 0, 1, 4), (8, 0, 1, 9),
                (8, 3, 0, 0), (8, 3, 0, 3), (8, 3, 0, 7), (8, 3, 0, 17),
                
                # Shaking
                (9, 0, 0, 1), (9, 0, 1, 0), (9, 0, 1, 2), (9, 0, 1, 3),
                (9, 3, 0, 0), (9, 3, 0, 3), (9, 3, 0, 4),
                
                # Upside down
                (10, 0, 1, 0), (10, 0, 1, 1), (10, 0, 1, 4), (10, 0, 1, 6),
                (10, 3, 0, 0), (10, 3, 0, 4), (10, 3, 0, 6),
                
                # Hiccup/burp
                (16, 0, 0, 0), (16, 0, 2, 0), (16, 0, 2, 1), (16, 0, 2, 3),
                
                # Singing/dancing
                (17, 0, 0, 0), (17, 0, 0, 1), (17, 0, 0, 4), (17, 0, 0, 5),
                (17, 3, 0, 0), (17, 3, 0, 1), (17, 3, 0, 4), (17, 3, 0, 5),
                
                # Music reaction
                (18, 0, 1, 0), (18, 0, 1, 1), (18, 0, 1, 3), (18, 0, 1, 6),
                
                # Loud noise
                (20, 0, 0, 0), (20, 0, 0, 1), (20, 0, 0, 6),
                
                # Bored actions
                (24, 2, 0, 0), (24, 2, 0, 1), (24, 2, 0, 2), (24, 2, 1, 0),
                (24, 3, 0, 0), (24, 3, 0, 2), (24, 3, 0, 6),
            ]
            
            # Escolhe uma ação aleatória da lista
            input_val, index_val, subindex_val, specific_val = random.choice(actions)
            
            LOG.add(f"[random] 🎲 Ação aleatória: input={input_val}, index={index_val}, subindex={subindex_val}, specific={specific_val}")
            await self.device.trigger_action(input_val, index_val, subindex_val, specific_val)

CTRL = Controller()

# Instância global do detector de wake word (criada depois do CTRL)
WAKE_WORD_DETECTOR = WakeWordDetector()

# ----------------- FastAPI -----------------

app = FastAPI(title="Furby Web (PyFluff-ready)")

class ColorBody(BaseModel):
    r: int
    g: int
    b: int

class ActionBody(BaseModel):
    input: int
    index: int
    subindex: int
    specific: int

@app.get("/api/mode")
async def get_mode():
    return {
        "mode": CTRL.mode, 
        "preferredAddress": PREFERRED_ADDRESS,
        "openai_enabled": OPENAI_ENABLED,
        "has_openai_key": bool(OPENAI_API_KEY),
        "porcupine_enabled": PORCUPINE_ENABLED,
        "has_porcupine_key": bool(PORCUPINE_ACCESS_KEY)
    }

@app.get("/api/scan")
async def api_scan():
    items = await CTRL.scan()
    return {"devices": items}

@app.post("/api/connect")
async def api_connect(address: Optional[str] = None):
    try:
        await CTRL.connect(address)
        return {"ok": True, "address": address or PREFERRED_ADDRESS}
    except Exception as e:
        LOG.add(f"[connect] erro: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/disconnect")
async def api_disconnect():
    try:
        await CTRL.disconnect()
        return {"ok": True}
    except Exception as e:
        LOG.add(f"[disconnect] erro: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/reset")
async def api_reset():
    """Desconecta e reseta o estado completamente"""
    try:
        await CTRL.reset()
        return {"ok": True, "message": "Estado resetado com sucesso"}
    except Exception as e:
        LOG.add(f"[reset] erro: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/antenna")
async def api_antenna(body: ColorBody):
    try:
        await CTRL.set_color(body.r, body.g, body.b)
        return {"ok": True}
    except Exception as e:
        LOG.add(f"[antenna] erro: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/action")
async def api_action(body: ActionBody):
    try:
        await CTRL.action(body.input, body.index, body.subindex, body.specific)
        return {"ok": True}
    except Exception as e:
        LOG.add(f"[action] erro: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/play-audio")
async def api_play_audio(file: UploadFile = File(...)):
    try:
        # Valida extensão do arquivo
        if not file.filename.lower().endswith('.wav'):
            raise HTTPException(status_code=400, detail="Apenas arquivos WAV são suportados")
        
        # Salva arquivo temporariamente
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            wav_path = tmp.name
            content = await file.read()
            tmp.write(content)
        
        try:
            # Toca o áudio no Furby
            await CTRL.play_wav(wav_path)
            return {"ok": True, "filename": file.filename}
        finally:
            # Limpa arquivo temporário
            try:
                os.unlink(wav_path)
            except:
                pass
    except HTTPException:
        raise
    except Exception as e:
        LOG.add(f"[play-audio] erro: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/play-audio-path")
async def api_play_audio_path(wav_path: str):
    try:
        await CTRL.play_wav(wav_path)
        return {"ok": True, "path": wav_path}
    except Exception as e:
        LOG.add(f"[play-audio-path] erro: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/random-action")
async def api_random_action():
    """Dispara uma ação aleatória no Furby"""
    try:
        await CTRL.random_action()
        return {"ok": True, "message": "Ação aleatória disparada!"}
    except Exception as e:
        LOG.add(f"[random-action] erro: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/wake-word/start")
async def api_wake_word_start():
    """Inicia o detector de wake word"""
    try:
        WAKE_WORD_DETECTOR.start()
        return {"ok": True, "message": "Detector de wake word iniciado"}
    except Exception as e:
        LOG.add(f"[wake-word] erro ao iniciar: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/wake-word/stop")
async def api_wake_word_stop():
    """Para o detector de wake word"""
    try:
        WAKE_WORD_DETECTOR.stop()
        return {"ok": True, "message": "Detector de wake word parado"}
    except Exception as e:
        LOG.add(f"[wake-word] erro ao parar: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/wake-word/status")
async def api_wake_word_status():
    """Retorna o status do detector de wake word e OpenAI"""
    return {
        "running": WAKE_WORD_DETECTOR.running,
        "enabled": PORCUPINE_ENABLED,
        "keyword": PORCUPINE_KEYWORD,
        "has_access_key": bool(PORCUPINE_ACCESS_KEY),
        "openai_enabled": OPENAI_ENABLED,
        "has_openai_key": bool(OPENAI_API_KEY),
        "conversation_timeout": CONVERSATION_TIMEOUT
    }

@app.get("/api/log")
async def api_log():
    return {"lines": CTRL.device.__class__.__name__ + " | " + CTRL.mode, "log": LOG.dump()}

# Página muito simples (HTML + JS) para controlar do navegador

INDEX_HTML = """
<!doctype html>
<html>
<head>
  <meta charset='utf-8'/>
  <meta name='viewport' content='width=device-width, initial-scale=1'/>
  <meta http-equiv='Cache-Control' content='no-cache, no-store, must-revalidate'/>
  <meta http-equiv='Pragma' content='no-cache'/>
  <meta http-equiv='Expires' content='0'/>
  <title>Furby Web - PyFluff Ready</title>
  <style>
    body { font-family: ui-sans-serif, system-ui; max-width: 900px; margin: 24px auto; padding: 0 16px; }
    h1 { margin: 0 0 8px; }
    #mode { padding: 12px; background: #e0f2fe; border: 1px solid #0284c7; border-radius: 8px; margin: 16px 0; font-weight: 600; color: #0c4a6e; }
    .row { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
    button { padding: 8px 12px; border: 1px solid #ccc; border-radius: 8px; background: #f9f9f9; cursor: pointer; }
    button:hover { background: #eee; }
    input[type="number"] { width: 80px; }
    #log { height: 220px; overflow: auto; border: 1px solid #ddd; padding: 8px; border-radius: 8px; background: #fafafa; font-family: monospace; font-size: 12px; }
    .card { border: 1px solid #e5e7eb; border-radius: 12px; padding: 16px; margin: 12px 0; }
    label { font-size: 12px; color: #555; }
    select { padding: 6px; }
  </style>
</head>
<body>
  <h1>Furby Web <small>(PyFluff-ready)</small></h1>
  <div id="mode" style="padding: 12px; background: #e0f2fe; border: 1px solid #0284c7; border-radius: 8px; margin: 16px 0; font-weight: 600; color: #0c4a6e;">Carregando modo...</div>
  <div id="js-test" style="padding: 8px; background: #fee2e2; border: 1px solid #dc2626; border-radius: 4px; margin: 8px 0; font-size: 12px;">JavaScript não está funcionando - recarregue a página</div>

  <div class="card">
    <h3>1) Scan & Connect</h3>
    <div class="row">
      <button id="scan">Scan</button>
      <select id="devices"></select>
      <button id="connect">Connect</button>
      <button id="disconnect">Disconnect</button>
      <button id="reset" style="background: #fee2e2; border-color: #dc2626; color: #991b1b;">Reset</button>
    </div>
    <div style="font-size: 11px; color: #888; margin-top: 8px; padding-top: 8px; border-top: 1px solid #eee;">
      <strong>Dica:</strong> Se o scan não encontrar o Furby, clique em "Reset" para desconectar e limpar o estado, depois faça scan novamente.
    </div>
  </div>

  <div class="card">
    <h3>2) Antenna Color</h3>
    <div class="row">
      <label>RGB:</label>
      <input type="number" id="r" min="0" max="255" value="128"/>
      <input type="number" id="g" min="0" max="255" value="0"/>
      <input type="number" id="b" min="0" max="255" value="128"/>
      <button id="applyColor">Apply</button>
    </div>
  </div>

  <div class="card">
    <h3>3) Action</h3>
    <div style="font-size: 12px; color: #666; margin-bottom: 8px;">
      <strong>Parâmetros:</strong><br/>
      <strong>input:</strong> Tipo de ação (1=trigger, 2=set, etc.)<br/>
      <strong>index:</strong> Índice da ação (0-255)<br/>
      <strong>subindex:</strong> Sub-índice da ação (0-255)<br/>
      <strong>specific:</strong> ID específico da ação (0-255)
    </div>
    <div class="row" style="margin-bottom: 8px;">
      <label>input</label><input type="number" id="ainput" value="1" min="0" max="255"/>
      <label>index</label><input type="number" id="aindex" value="0" min="0" max="255"/>
      <label>subindex</label><input type="number" id="asub" value="0" min="0" max="255"/>
      <label>specific</label><input type="number" id="aspec" value="0" min="0" max="255"/>
      <button id="sendAction">Send Action</button>
    </div>
    <div style="font-size: 11px; color: #888; margin-top: 8px; padding-top: 8px; border-top: 1px solid #eee;">
      <strong>Valores comuns para testar:</strong><br/>
      • input=1, index=1-10, subindex=0, specific=0 (ações básicas)<br/>
      • input=1, index=20-30, subindex=0, specific=0 (efeitos sonoros)<br/>
      • Experimente diferentes combinações para descobrir novas ações!
    </div>
  </div>

  <div class="card">
    <h3>4) Play Audio</h3>
    <div style="font-size: 12px; color: #666; margin-bottom: 8px;">
      <strong>Envie um arquivo WAV para tocar no Furby:</strong>
    </div>
    <div class="row">
      <input type="file" id="audioFile" accept=".wav" style="padding: 6px; border: 1px solid #ccc; border-radius: 4px;"/>
      <button id="playAudio">Play Audio</button>
    </div>
    <div style="font-size: 11px; color: #888; margin-top: 8px; padding-top: 8px; border-top: 1px solid #eee;">
      <strong>Nota:</strong> Apenas arquivos WAV são suportados. O arquivo será convertido para o formato A1800 do Furby.
    </div>
  </div>

  <div class="card">
    <h3>5) Random Action & Wake Word</h3>
    <div style="font-size: 12px; color: #666; margin-bottom: 8px;">
      <strong>Dispare ações aleatórias (4 valores) manualmente ou por comando de voz:</strong><br/>
      <span style="font-size: 11px; color: #888;">Gera valores aleatórios para: input, index, subindex, specific</span>
    </div>
    <div class="row" style="margin-bottom: 12px;">
      <button id="randomAction" style="background: #dbeafe; border-color: #3b82f6; color: #1e40af; font-weight: 600;">🎲 Ação Aleatória</button>
    </div>
    <div style="border-top: 1px solid #eee; padding-top: 12px; margin-top: 12px;">
      <div style="font-size: 12px; color: #666; margin-bottom: 8px;">
        <strong>Detector de Wake Word (Porcupine):</strong>
      </div>
      <div id="wakeWordStatus" style="padding: 8px; background: #f3f4f6; border: 1px solid #d1d5db; border-radius: 4px; margin-bottom: 8px; font-size: 12px;">
        Carregando status...
      </div>
      <div class="row">
        <button id="startWakeWord" style="background: #d1fae5; border-color: #10b981; color: #065f46;">▶ Iniciar</button>
        <button id="stopWakeWord" style="background: #fee2e2; border-color: #ef4444; color: #991b1b;">⏸ Parar</button>
      </div>
    </div>
    <div style="font-size: 11px; color: #888; margin-top: 8px; padding-top: 8px; border-top: 1px solid #eee;">
      <strong>🤖 Modo OpenAI:</strong> Se habilitado, fale a palavra-chave, faça sua pergunta, e o Furby responde pelo computador + faz uma ação aleatória!<br/>
      <strong>🎲 Modo Simples:</strong> Se OpenAI desabilitado, apenas dispara ação aleatória no Furby.<br/><br/>
      <strong>Configuração Wake Word:</strong><br/>
      Configure PORCUPINE_ACCESS_KEY e PORCUPINE_ENABLED=true no .env<br/>
      Obtenha em: <a href="https://console.picovoice.ai/" target="_blank">https://console.picovoice.ai/</a><br/><br/>
      <strong>Configuração OpenAI (opcional):</strong><br/>
      Configure OPENAI_API_KEY e OPENAI_ENABLED=true no .env<br/>
      Obtenha em: <a href="https://platform.openai.com/api-keys" target="_blank">https://platform.openai.com/api-keys</a>
    </div>
  </div>

  <div class="card">
    <h3>Log</h3>
    <div id="log"></div>
  </div>

<script>
async function refreshMode(){
  try {
    console.log('Chamando /api/mode...');
    const res = await fetch('/api/mode');
    const j = await res.json();
    console.log('Resposta:', j);
    let modeText = 'Mode: ' + j.mode;
    if (j.preferredAddress) {
      modeText += ' | Preferred=' + j.preferredAddress;
    }
    
    // Adiciona status OpenAI
    if (j.openai_enabled && j.has_openai_key) {
      modeText += ' | 🤖 OpenAI: ATIVO';
    } else if (!j.has_openai_key) {
      modeText += ' | ⚠️ OpenAI: SEM API KEY';
    } else if (!j.openai_enabled) {
      modeText += ' | ⚠️ OpenAI: DESABILITADO';
    }
    
    document.getElementById('mode').innerText = modeText;
  } catch(e) {
    console.error('Erro ao carregar modo:', e);
    document.getElementById('mode').innerText = 'Erro ao carregar modo: ' + e.message;
  }
}
async function scan(){
  const btn = document.getElementById('scan');
  const sel = document.getElementById('devices');
  
  try {
    btn.disabled = true;
    btn.innerText = 'Scanning...';
    sel.innerHTML = '<option>Procurando dispositivos...</option>';
    
    console.log('Iniciando scan...');
    const res = await fetch('/api/scan');
    
    if (!res.ok) {
      throw new Error('Erro HTTP: ' + res.status);
    }
    
    const j = await res.json();
    console.log('Dispositivos encontrados:', j.devices);
    
    sel.innerHTML = '';
    
    if (j.devices && j.devices.length > 0) {
      j.devices.forEach(function(d) {
        const opt = document.createElement('option');
        opt.value = d.address;
        opt.text = d.name + ' (' + d.address + ')';
        sel.appendChild(opt);
      });
      alert('Encontrados ' + j.devices.length + ' dispositivo(s)');
    } else {
      sel.innerHTML = '<option>Nenhum dispositivo encontrado</option>';
      alert('Nenhum Furby encontrado. Verifique se está ligado e próximo ao computador.');
    }
  } catch(e) {
    console.error('Erro no scan:', e);
    sel.innerHTML = '<option>Erro ao fazer scan</option>';
    alert('Erro ao fazer scan: ' + e.message);
  } finally {
    btn.disabled = false;
    btn.innerText = 'Scan';
    await log();
  }
}
async function connect(){
  const sel = document.getElementById('devices');
  const address = sel.value || '';
  await fetch('/api/connect?address='+encodeURIComponent(address), {method:'POST'});
  await log();
}
async function disconnect(){
  await fetch('/api/disconnect', {method:'POST'});
  await log();
}
async function reset(){
  try {
    const btn = document.getElementById('reset');
    btn.disabled = true;
    btn.innerText = 'Resetting...';
    
    const res = await fetch('/api/reset', {method:'POST'});
    const j = await res.json();
    
    if (res.ok) {
      alert('Estado resetado com sucesso! Agora você pode fazer scan novamente.');
    } else {
      throw new Error(j.detail || 'Erro ao resetar');
    }
  } catch(e) {
    console.error('Erro ao resetar:', e);
    alert('Erro ao resetar: ' + e.message);
  } finally {
    const btn = document.getElementById('reset');
    btn.disabled = false;
    btn.innerText = 'Reset';
    await log();
  }
}
async function applyColor(){
  const r = +document.getElementById('r').value;
  const g = +document.getElementById('g').value;
  const b = +document.getElementById('b').value;
  await fetch('/api/antenna', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({r,g,b})});
  await log();
}
async function sendAction(){
  const input = +document.getElementById('ainput').value;
  const index = +document.getElementById('aindex').value;
  const subindex = +document.getElementById('asub').value;
  const specific = +document.getElementById('aspec').value;
  await fetch('/api/action', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({input,index,subindex,specific})});
  await log();
}
async function playAudio(){
  const fileInput = document.getElementById('audioFile');
  const btn = document.getElementById('playAudio');
  
  if (!fileInput.files || fileInput.files.length === 0) {
    alert('Por favor, selecione um arquivo WAV');
    return;
  }
  
  const file = fileInput.files[0];
  
  if (!file.name.toLowerCase().endsWith('.wav')) {
    alert('Apenas arquivos WAV são suportados');
    return;
  }
  
  try {
    btn.disabled = true;
    btn.innerText = 'Enviando...';
    
    const formData = new FormData();
    formData.append('file', file);
    
    const res = await fetch('/api/play-audio', {
      method: 'POST',
      body: formData
    });
    
    if (!res.ok) {
      const error = await res.json();
      throw new Error(error.detail || 'Erro ao tocar áudio');
    }
    
    const result = await res.json();
    alert('Áudio enviado com sucesso!');
  } catch(e) {
    console.error('Erro ao tocar áudio:', e);
    alert('Erro ao tocar áudio: ' + e.message);
  } finally {
    btn.disabled = false;
    btn.innerText = 'Play Audio';
    await log();
  }
}
async function randomAction(){
  const btn = document.getElementById('randomAction');
  
  try {
    btn.disabled = true;
    btn.innerText = '🎲 Disparando...';
    
    const res = await fetch('/api/random-action', {method: 'POST'});
    
    if (!res.ok) {
      const error = await res.json();
      throw new Error(error.detail || 'Erro ao disparar ação aleatória');
    }
    
    await log();
  } catch(e) {
    console.error('Erro ao disparar ação aleatória:', e);
    alert('Erro: ' + e.message);
  } finally {
    btn.disabled = false;
    btn.innerText = '🎲 Ação Aleatória';
  }
}
async function refreshWakeWordStatus(){
  try {
    const res = await fetch('/api/wake-word/status');
    const status = await res.json();
    
    const statusDiv = document.getElementById('wakeWordStatus');
    let statusText = '';
    
    if (!status.enabled) {
      statusText = '⚠️ Detector desabilitado (configure PORCUPINE_ENABLED=true no .env)';
    } else if (!status.has_access_key) {
      statusText = '⚠️ Access key não configurada (configure PORCUPINE_ACCESS_KEY no .env)';
    } else if (status.running) {
      const mode = status.openai_enabled && status.has_openai_key ? '🤖 MODO OPENAI' : '🎲 MODO SIMPLES';
      statusText = '✅ Detector ATIVO - ' + mode + ' - Palavra: "' + status.keyword + '"';
      if (status.openai_enabled && status.has_openai_key) {
        statusText += ' (gravar ' + status.conversation_timeout + 's)';
      }
      statusDiv.style.background = '#d1fae5';
      statusDiv.style.borderColor = '#10b981';
    } else {
      const mode = status.openai_enabled && status.has_openai_key ? '🤖 MODO OPENAI' : '🎲 MODO SIMPLES';
      statusText = '⏸ Detector parado - ' + mode + ' - Palavra: "' + status.keyword + '"';
      statusDiv.style.background = '#f3f4f6';
      statusDiv.style.borderColor = '#d1d5db';
    }
    
    statusDiv.innerText = statusText;
  } catch(e) {
    console.error('Erro ao obter status:', e);
    document.getElementById('wakeWordStatus').innerText = '❌ Erro ao obter status';
  }
}
async function startWakeWord(){
  const btn = document.getElementById('startWakeWord');
  
  try {
    btn.disabled = true;
    btn.innerText = 'Iniciando...';
    
    const res = await fetch('/api/wake-word/start', {method: 'POST'});
    
    if (!res.ok) {
      const error = await res.json();
      throw new Error(error.detail || 'Erro ao iniciar detector');
    }
    
    await refreshWakeWordStatus();
    await log();
  } catch(e) {
    console.error('Erro ao iniciar detector:', e);
    alert('Erro ao iniciar: ' + e.message);
  } finally {
    btn.disabled = false;
    btn.innerText = '▶ Iniciar';
  }
}
async function stopWakeWord(){
  const btn = document.getElementById('stopWakeWord');
  
  try {
    btn.disabled = true;
    btn.innerText = 'Parando...';
    
    const res = await fetch('/api/wake-word/stop', {method: 'POST'});
    
    if (!res.ok) {
      const error = await res.json();
      throw new Error(error.detail || 'Erro ao parar detector');
    }
    
    await refreshWakeWordStatus();
    await log();
  } catch(e) {
    console.error('Erro ao parar detector:', e);
    alert('Erro ao parar: ' + e.message);
  } finally {
    btn.disabled = false;
    btn.innerText = '⏸ Parar';
  }
}
async function log(){
  const res = await fetch('/api/log');
  const j = await res.json();
  const div = document.getElementById('log');
  if (j.log && Array.isArray(j.log)) {
    var newline = String.fromCharCode(10);
    div.innerText = j.log.join(newline);
  } else {
    div.innerText = 'Nenhum log disponível';
  }
  div.scrollTop = div.scrollHeight;
}

// Teste se JavaScript está funcionando
var jsTest = document.getElementById('js-test');
if (jsTest) {
  jsTest.style.display = 'none';
}

// Inicializar - múltiplas tentativas para garantir que execute
function initApp() {
  try {
    console.log('Inicializando app...');
    refreshMode();
    refreshWakeWordStatus();
    
    var scanBtn = document.getElementById('scan');
    if (scanBtn) {
      scanBtn.onclick = scan;
      console.log('Botão scan configurado');
    } else {
      console.error('Botão scan não encontrado!');
    }
    
    var connectBtn = document.getElementById('connect');
    if (connectBtn) connectBtn.onclick = connect;
    
    var disconnectBtn = document.getElementById('disconnect');
    if (disconnectBtn) disconnectBtn.onclick = disconnect;
    
    var resetBtn = document.getElementById('reset');
    if (resetBtn) resetBtn.onclick = reset;
    
    var applyColorBtn = document.getElementById('applyColor');
    if (applyColorBtn) applyColorBtn.onclick = applyColor;
    
    var sendActionBtn = document.getElementById('sendAction');
    if (sendActionBtn) sendActionBtn.onclick = sendAction;
    
    var playAudioBtn = document.getElementById('playAudio');
    if (playAudioBtn) playAudioBtn.onclick = playAudio;
    
    var randomActionBtn = document.getElementById('randomAction');
    if (randomActionBtn) randomActionBtn.onclick = randomAction;
    
    var startWakeWordBtn = document.getElementById('startWakeWord');
    if (startWakeWordBtn) startWakeWordBtn.onclick = startWakeWord;
    
    var stopWakeWordBtn = document.getElementById('stopWakeWord');
    if (stopWakeWordBtn) stopWakeWordBtn.onclick = stopWakeWord;
    
    setInterval(log, 1200);
    setInterval(refreshWakeWordStatus, 3000);
    console.log('App inicializado com sucesso');
  } catch(e) {
    console.error('Erro ao inicializar app:', e);
    setTimeout(initApp, 100);
  }
}

// Tentar inicializar imediatamente
try {
  if (document.readyState === 'complete' || document.readyState === 'interactive') {
    console.log('Página já carregada, inicializando...');
    initApp();
  } else {
    console.log('Aguardando DOMContentLoaded...');
    document.addEventListener('DOMContentLoaded', function() {
      console.log('DOMContentLoaded disparado');
      initApp();
    });
    // Fallback caso DOMContentLoaded não dispare
    setTimeout(function() {
      console.log('Timeout fallback executando...');
      initApp();
    }, 1000);
  }
} catch(e) {
  console.error('Erro crítico:', e);
}
</script>
</body>
</html>
"""

@app.get("/")
async def index():
    return HTMLResponse(INDEX_HTML)

