#!/usr/bin/env python3
"""
Teste rápido do microfone e Porcupine
Execute: python3 test_microphone.py
"""

import os
import sys

print("=" * 70)
print("🎤 TESTE DE MICROFONE E WAKE WORD DETECTION")
print("=" * 70)

# 1. Teste de importações
print("\n[1/5] Testando importações...")
try:
    import pyaudio
    print("  ✅ PyAudio importado com sucesso")
except ImportError as e:
    print(f"  ❌ PyAudio não encontrado: {e}")
    sys.exit(1)

try:
    import pvporcupine
    print("  ✅ Porcupine importado com sucesso")
except ImportError as e:
    print(f"  ❌ Porcupine não encontrado: {e}")
    sys.exit(1)

try:
    import numpy as np
    print("  ✅ NumPy importado com sucesso")
except ImportError as e:
    print(f"  ❌ NumPy não encontrado: {e}")
    sys.exit(1)

# 2. Teste de dispositivos de áudio
print("\n[2/5] Listando dispositivos de áudio...")
pa = pyaudio.PyAudio()
device_count = pa.get_device_count()
print(f"  Total de dispositivos: {device_count}")

input_devices = []
for i in range(device_count):
    info = pa.get_device_info_by_index(i)
    if info['maxInputChannels'] > 0:
        input_devices.append((i, info))
        print(f"  [{i}] {info['name']}")
        print(f"      Canais: {info['maxInputChannels']}")
        print(f"      Sample Rate: {int(info['defaultSampleRate'])} Hz")

if not input_devices:
    print("  ❌ Nenhum dispositivo de entrada encontrado!")
    sys.exit(1)

# 3. Teste de variáveis de ambiente
print("\n[3/5] Verificando configuração...")
from dotenv import load_dotenv
load_dotenv()

ACCESS_KEY = os.getenv("PORCUPINE_ACCESS_KEY", "").strip()
KEYWORD = os.getenv("PORCUPINE_KEYWORD", "blueberry").strip()
ENABLED = os.getenv("PORCUPINE_ENABLED", "false").lower() == "true"

print(f"  PORCUPINE_ENABLED: {ENABLED}")
print(f"  PORCUPINE_KEYWORD: '{KEYWORD}'")
print(f"  PORCUPINE_ACCESS_KEY: {'✅ Configurada' if ACCESS_KEY else '❌ Não configurada'}")

if not ACCESS_KEY:
    print("\n  ⚠️  ATENÇÃO: Access key não configurada!")
    print("  Configure PORCUPINE_ACCESS_KEY no arquivo .env")
    print("  Obtenha em: https://console.picovoice.ai/")
    sys.exit(1)

# 4. Teste do Porcupine
print(f"\n[4/5] Inicializando Porcupine com palavra '{KEYWORD}'...")
try:
    porcupine = pvporcupine.create(
        access_key=ACCESS_KEY,
        keywords=[KEYWORD]
    )
    print(f"  ✅ Porcupine inicializado com sucesso")
    print(f"  Sample rate: {porcupine.sample_rate} Hz")
    print(f"  Frame length: {porcupine.frame_length}")
except Exception as e:
    print(f"  ❌ Erro ao inicializar Porcupine: {e}")
    print("\n  Possíveis causas:")
    print("  - Access key inválida")
    print("  - Palavra-chave não existe")
    print("  - Problema de conexão (Porcupine valida a chave online)")
    sys.exit(1)

# 5. Teste de captura de áudio
print(f"\n[5/5] Testando captura de áudio...")
import struct

try:
    audio_stream = pa.open(
        rate=porcupine.sample_rate,
        channels=1,
        format=pyaudio.paInt16,
        input=True,
        frames_per_buffer=porcupine.frame_length
    )
    print("  ✅ Stream de áudio aberto com sucesso")
except Exception as e:
    print(f"  ❌ Erro ao abrir stream: {e}")
    print("\n  Possíveis causas:")
    print("  - Permissões de microfone negadas (macOS)")
    print("  - Microfone em uso por outro aplicativo")
    print("  - Driver de áudio com problema")
    sys.exit(1)

print("\n" + "=" * 70)
print("🎤 INICIANDO TESTE DE DETECÇÃO")
print("=" * 70)
print(f"\nFale a palavra: '{KEYWORD.upper()}'")
print("(Pressione Ctrl+C para parar)")
print("\nMonitorando volume e aguardando detecção...")
print("-" * 70)

try:
    frame_count = 0
    while True:
        # Lê áudio
        pcm = audio_stream.read(porcupine.frame_length, exception_on_overflow=False)
        pcm = struct.unpack_from("h" * porcupine.frame_length, pcm)
        
        # Calcula volume
        frame_count += 1
        if frame_count % 25 == 0:  # A cada ~0.8 segundos
            audio_array = np.array(pcm, dtype=np.int16)
            volume = int(np.abs(audio_array).mean())
            
            # Indicador visual de volume
            bar_length = min(50, volume // 20)
            bar = "█" * bar_length
            
            status = ""
            if volume < 50:
                status = "⚠️  Silêncio/Muito baixo"
            elif volume < 200:
                status = "⚠️  Volume baixo"
            elif volume < 1000:
                status = "✅ Volume adequado"
            else:
                status = "✅ Volume bom"
            
            print(f"\r🎤 Volume: {volume:4d} | {bar:50s} | {status}", end="", flush=True)
        
        # Processa detecção
        keyword_index = porcupine.process(pcm)
        
        if keyword_index >= 0:
            print(f"\n\n{'=' * 70}")
            print(f"✅✅✅ SUCESSO! Palavra '{KEYWORD}' DETECTADA! ✅✅✅")
            print(f"{'=' * 70}\n")
            print("O detector está funcionando perfeitamente!")
            print("\nAgora você pode usar na aplicação web:")
            print("1. Acesse http://localhost:8000")
            print("2. Vá até seção '5) Random Action & Wake Word'")
            print("3. Clique em '▶ Iniciar'")
            print(f"4. Fale '{KEYWORD}' e o Furby fará uma ação aleatória!\n")
            break
            
except KeyboardInterrupt:
    print("\n\n⏸  Teste interrompido pelo usuário")
    print("\nResultados:")
    print("  - Importações: ✅")
    print("  - Dispositivos de áudio: ✅")
    print("  - Configuração: ✅")
    print("  - Porcupine: ✅")
    print("  - Captura de áudio: ✅")
    print(f"  - Detecção de '{KEYWORD}': ❌ Não detectada (mas sistema está OK)")
    print("\nDicas:")
    print(f"  • Tente falar '{KEYWORD}' mais claramente")
    print("  • Verifique se o volume está adequado (200-1000)")
    print("  • Tente palavras mais fáceis: 'porcupine', 'jarvis', 'computer'")
except Exception as e:
    print(f"\n\n❌ Erro durante teste: {e}")
    import traceback
    traceback.print_exc()
finally:
    # Cleanup
    print("\nLimpando recursos...")
    audio_stream.close()
    porcupine.delete()
    pa.terminate()
    print("✅ Teste concluído\n")


