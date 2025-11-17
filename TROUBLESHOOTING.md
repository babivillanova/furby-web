# 🔧 Troubleshooting - Wake Word Detection

## Problema: Detector não está captando a palavra

Se o detector inicia mas não detecta quando você fala, siga este guia:

### ✅ Passo 1: Verifique os Logs

Depois de clicar em "▶ Iniciar", verifique a seção **Log** na interface. Você deve ver:

```
[wake-word] iniciando detector...
[wake-word] criando instância Porcupine para palavra: 'blueberry'
[wake-word] Porcupine criado com sucesso
[wake-word] Sample rate: 16000 Hz
[wake-word] Frame length: 512
[wake-word] dispositivos de áudio disponíveis:
[wake-word]   [0] MacBook Pro Microphone (canais: 1)
[wake-word] abrindo stream de áudio...
[wake-word] ✓ DETECTOR ATIVO - Escutando por 'blueberry'
[wake-word] 🎤 capturando áudio... (volume médio: 150)
```

#### 🎤 Indicador de Volume

A cada ~1.5 segundos você deve ver:
```
[wake-word] 🎤 capturando áudio... (volume médio: XXX)
```

**Interpretação dos valores de volume:**
- `0-50`: Silêncio ou microfone muito baixo ⚠️
- `50-200`: Volume baixo (pode não funcionar) ⚠️
- `200-1000`: Volume adequado ✅
- `1000+`: Volume bom/alto ✅

### ✅ Passo 2: Teste o Microfone

#### No macOS:

1. **Verifique permissões:**
   - Abra **Preferências do Sistema** → **Segurança e Privacidade** → **Privacidade**
   - Clique em **Microfone** na lateral
   - Certifique-se de que **Terminal** ou **Python** estão marcados
   - Se não estiver na lista, você precisa dar permissão quando solicitado

2. **Teste o microfone:**
   - Abra **QuickTime Player** → **Arquivo** → **Nova Gravação de Áudio**
   - Clique no botão de gravação e fale
   - Se não gravar, o problema é do sistema, não do app

3. **Ajuste o volume:**
   - Preferências do Sistema → Som → Entrada
   - Selecione o microfone correto
   - Ajuste o "Volume de entrada" (recomendado: 70-80%)
   - Fale e veja se as barras se movem

### ✅ Passo 3: Teste a Palavra-Chave

Algumas dicas para melhorar a detecção:

#### Para "blueberry":
- ✅ Pronúncia correta: **"BLU-bé-ri"** (inglês americano)
- ✅ Fale claramente e pausadamente
- ✅ Volume normal de conversação
- ✅ Distância do microfone: 30-50cm
- ❌ Não grite (pode distorcer)
- ❌ Não sussurre (volume muito baixo)

#### Teste com outras palavras:

Se "blueberry" não funciona, teste com palavras mais fáceis:

```env
# No .env, tente:
PORCUPINE_KEYWORD=porcupine
```

A palavra "porcupine" geralmente tem melhor taxa de detecção.

**Ranking de facilidade de detecção:**
1. ⭐⭐⭐ `porcupine` (mais fácil)
2. ⭐⭐⭐ `picovoice`
3. ⭐⭐ `jarvis`
4. ⭐⭐ `computer`
5. ⭐ `blueberry` (mais difícil para não-nativos)

### ✅ Passo 4: Verifique a Access Key

Se o log mostrar erro na criação do Porcupine:

```
[wake-word] ❌ erro no detector: ...
```

1. Verifique se a `PORCUPINE_ACCESS_KEY` está correta
2. Gere uma nova chave em: https://console.picovoice.ai/
3. Copie SEM espaços extras
4. Cole no `.env` exatamente como está

### ✅ Passo 5: Reinicie Tudo

Às vezes, uma reinicialização resolve:

1. **Pare o detector** (clique em "⏸ Parar")
2. **Feche o navegador**
3. **Pare o servidor** (Ctrl+C no terminal)
4. **Reinicie o servidor:**
   ```bash
   uvicorn app:app --reload
   ```
5. **Abra o navegador novamente**
6. **Conecte ao Furby**
7. **Inicie o detector**

### ✅ Passo 6: Teste de Permissões (macOS)

Execute este comando no terminal:

```bash
python3 -c "import pyaudio; p = pyaudio.PyAudio(); print('Dispositivos:', p.get_device_count()); p.terminate()"
```

**Resultado esperado:**
```
Dispositivos: 2 (ou mais)
```

**Se aparecer erro de permissão:**
- O macOS deve pedir permissão de microfone
- Clique em "OK" para permitir
- Reinicie o servidor

### ✅ Passo 7: Teste Manual do Porcupine

Crie um arquivo de teste `test_porcupine.py`:

```python
import pvporcupine
import pyaudio
import struct

# Substitua pela sua chave
ACCESS_KEY = "sua_chave_aqui"
KEYWORD = "blueberry"

porcupine = pvporcupine.create(
    access_key=ACCESS_KEY,
    keywords=[KEYWORD]
)

pa = pyaudio.PyAudio()
audio_stream = pa.open(
    rate=porcupine.sample_rate,
    channels=1,
    format=pyaudio.paInt16,
    input=True,
    frames_per_buffer=porcupine.frame_length
)

print(f"Escutando por '{KEYWORD}'... (Ctrl+C para parar)")

try:
    while True:
        pcm = audio_stream.read(porcupine.frame_length, exception_on_overflow=False)
        pcm = struct.unpack_from("h" * porcupine.frame_length, pcm)
        
        keyword_index = porcupine.process(pcm)
        if keyword_index >= 0:
            print(f"✓ DETECTADO: {KEYWORD}")
            
except KeyboardInterrupt:
    print("\nParando...")
finally:
    audio_stream.close()
    porcupine.delete()
    pa.terminate()
```

Execute:
```bash
python3 test_porcupine.py
```

Se funcionar aqui mas não na aplicação, há um problema na integração.

### ✅ Passo 8: Problemas Comuns

#### "Volume médio: 0" ou muito baixo
- **Causa:** Microfone desligado ou muito baixo
- **Solução:** Ajuste volume nas Preferências do Sistema

#### Não aparece "[wake-word] 🎤 capturando áudio..."
- **Causa:** Detector não iniciou corretamente
- **Solução:** Verifique logs de erro, reinicie

#### "Erro ao abrir stream de áudio"
- **Causa:** Permissões de microfone negadas
- **Solução:** Vá em Preferências do Sistema → Privacidade → Microfone

#### Palavra detectada em silêncio (falsos positivos)
- **Causa:** Ruído de fundo ou sensibilidade alta
- **Solução:** Reduza ruído ambiente, fale mais claramente

### 🆘 Ainda Não Funciona?

1. **Compartilhe os logs:** Copie os últimos 20 logs da seção Log
2. **Informe o sistema:** macOS versão X.X
3. **Dispositivo de áudio:** Qual microfone está usando?
4. **Valor de volume:** Qual o número que aparece?

### 💡 Dicas Extras

- **Ambiente silencioso:** Teste em lugar sem ruído de fundo
- **Microfone de qualidade:** Microfones ruins têm baixa taxa de detecção
- **Sotaque:** Palavras em inglês são treinadas com pronúncia americana
- **Velocidade:** Fale pausadamente, sem pressa
- **Repetição:** Tente falar 3-4 vezes seguidas

### ✅ Teste de Sucesso

Quando estiver funcionando, você verá:

```
[wake-word] 🎤 capturando áudio... (volume médio: 450)
[wake-word] ✓✓✓ PALAVRA DETECTADA: 'blueberry'! ✓✓✓
[random] 🎲 Ação aleatória: input=1, index=15, subindex=2, specific=5
```

E o Furby executará uma ação aleatória! 🎉

---

## Checklist Final

- [ ] Permissões de microfone concedidas
- [ ] Volume do microfone adequado (70-80%)
- [ ] PORCUPINE_ACCESS_KEY configurada corretamente
- [ ] Palavra-chave testada (tente "porcupine" primeiro)
- [ ] Logs mostram "capturando áudio" com volume > 200
- [ ] Ambiente silencioso
- [ ] Pronúncia clara e pausada
- [ ] Detector está ativo (status verde)

Se todos os itens estiverem ✅ e ainda não funcionar, pode ser um problema de compatibilidade do hardware/sistema.


