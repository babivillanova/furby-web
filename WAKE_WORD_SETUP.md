# Configuração do Wake Word Detection (Porcupine)

Este guia explica como configurar o detector de wake word para disparar ações aleatórias no Furby quando você falar uma palavra-chave.

## 📋 Pré-requisitos

1. **Conta Picovoice** (gratuita)
2. **Python 3.7+**
3. **Microfone funcionando**

## 🚀 Passo a Passo

### 1. Instalar Dependências

```bash
pip install -r requirements.txt
```

### 2. Obter Access Key do Picovoice

1. Acesse: https://console.picovoice.ai/
2. Crie uma conta gratuita (ou faça login)
3. Vá em **"Access Keys"** no menu lateral
4. Clique em **"Create Access Key"**
5. Copie a chave gerada

### 3. Configurar Variáveis de Ambiente

Crie um arquivo `.env` na raiz do projeto (se ainda não existir) e adicione:

```env
# Habilitar detector de wake word
PORCUPINE_ENABLED=true

# Sua access key do Picovoice
PORCUPINE_ACCESS_KEY=sua_chave_aqui

# Palavra-chave para detecção (padrão: alexa)
PORCUPINE_KEYWORD=alexa
```

### 4. Palavras-chave Disponíveis (Built-in)

O Porcupine vem com estas palavras pré-treinadas:

- `alexa`
- `americano`
- `blueberry`
- `bumblebee`
- `computer`
- `grapefruit`
- `grasshopper`
- `hey google`
- `hey siri`
- `jarvis`
- `ok google`
- `picovoice`
- `porcupine`
- `terminator`

**Nota:** Por padrão, usamos `alexa` porque "aleatório" requer um modelo customizado.

### 5. Usar Palavra Customizada "aleatório" (Avançado)

Para usar "aleatório" ou qualquer palavra em português:

#### Opção A: Treinar Modelo Customizado (Recomendado)

1. Acesse: https://console.picovoice.ai/
2. Vá em **"Wake Words"** → **"Train Custom Wake Word"**
3. Digite **"aleatório"** e configure:
   - Language: Portuguese (BR)
   - Plataforma: macOS / Linux / Windows (conforme seu sistema)
4. Clique em **"Train"** e aguarde
5. Baixe o arquivo `.ppn` gerado
6. Salve na pasta do projeto como `aleatorio.ppn`

7. Modifique o código em `app.py`:

```python
# Linha ~103, dentro de _run_detector:
self.porcupine = pvporcupine.create(
    access_key=PORCUPINE_ACCESS_KEY,
    keyword_paths=['aleatorio.ppn']  # Usar arquivo customizado ao invés de keywords
)
```

#### Opção B: Usar Palavra Built-in (Mais Fácil)

Simplesmente use uma das palavras built-in listadas acima. Por exemplo:

```env
PORCUPINE_KEYWORD=jarvis
```

Então fale "Jarvis" para disparar ações aleatórias.

### 6. Iniciar o Detector

Existem duas formas:

#### Via Interface Web:
1. Execute o servidor: `python app.py` ou `uvicorn app:app`
2. Acesse: http://localhost:8000
3. Vá até a seção **"5) Random Action & Wake Word"**
4. Clique em **"▶ Iniciar"**
5. Fale a palavra-chave configurada!

#### Via API:
```bash
curl -X POST http://localhost:8000/api/wake-word/start
```

## 🎯 Como Usar

1. **Conecte-se ao Furby** (seção 1 da interface)
2. **Inicie o detector** (seção 5)
3. **Fale a palavra-chave** (ex: "Alexa")
4. O Furby executará uma ação aleatória! 🎲

## 🔧 Solução de Problemas

### Erro: "pvporcupine not found"
```bash
pip install pvporcupine
```

### Erro: "PyAudio not found"
**macOS:**
```bash
brew install portaudio
pip install pyaudio
```

**Linux:**
```bash
sudo apt-get install portaudio19-dev python3-pyaudio
pip install pyaudio
```

**Windows:**
```bash
pip install pipwin
pipwin install pyaudio
```

### Detector não inicia
- Verifique se `PORCUPINE_ENABLED=true`
- Verifique se `PORCUPINE_ACCESS_KEY` está configurada corretamente
- Verifique permissões do microfone no sistema

### Palavra não é detectada
- Fale claramente e com volume adequado
- Verifique se o microfone está funcionando
- Tente uma palavra built-in primeiro (ex: `alexa`, `jarvis`)
- Aumente o volume do microfone nas configurações do sistema

### Erro: "Access Key inválida"
- Verifique se copiou a chave completa
- Gere uma nova chave no console Picovoice
- Não compartilhe sua chave publicamente

## 📝 Notas

- **Plano Gratuito:** O Picovoice oferece uso gratuito com limitações razoáveis
- **Performance:** O detector roda em uma thread separada para não bloquear a aplicação
- **Privacidade:** Todo processamento é local, nenhum áudio é enviado para servidores
- **Múltiplas Palavras:** Você pode modificar o código para aceitar várias palavras

## 🎲 O que a Ação Aleatória Faz?

Quando a palavra é detectada, o sistema:
1. Gera parâmetros aleatórios (input, index, subindex, specific)
2. Dispara uma ação no Furby
3. Muda a cor da antena aleatoriamente

Cada vez que você falar a palavra, o Furby fará algo diferente! 🎉

## 🔗 Links Úteis

- **Picovoice Console:** https://console.picovoice.ai/
- **Documentação Porcupine:** https://picovoice.ai/docs/porcupine/
- **PyAudio Docs:** https://people.csail.mit.edu/hubert/pyaudio/

## 📞 Suporte

Se tiver problemas, verifique os logs na interface web (seção "Log" no final da página).


