# 🤖 Configuração de Conversação com OpenAI

Este guia explica como configurar o sistema de conversação inteligente com OpenAI, onde você pode falar com o Furby através do OpenAI!

## 🎯 Como Funciona

1. **Fale a palavra-chave** (ex: "blueberry")
2. **Sistema grava** sua pergunta por 5 segundos
3. **Envia para OpenAI** (Whisper transcreve + GPT-4o-mini responde)
4. **Resposta é falada** no computador (TTS da OpenAI)
5. **Furby reage** com uma ação aleatória!

## 📋 Pré-requisitos

- ✅ Conta OpenAI (https://platform.openai.com/)
- ✅ API Key da OpenAI
- ✅ Créditos na conta OpenAI
- ✅ Wake Word Detection configurado (Porcupine)

## 🚀 Passo a Passo

### 1. Obter API Key da OpenAI

1. Acesse: https://platform.openai.com/
2. Faça login ou crie uma conta
3. Vá em **API Keys** no menu
4. Clique em **"Create new secret key"**
5. Dê um nome (ex: "Furby Conversation")
6. Copie a chave (começa com `sk-...`)
7. **⚠️ IMPORTANTE:** Guarde bem, ela só aparece uma vez!

### 2. Adicionar Créditos (se necessário)

1. Vá em **Settings** → **Billing**
2. Adicione créditos (mínimo $5)
3. Verifique se tem saldo disponível

### 3. Configurar no `.env`

Edite (ou crie) o arquivo `.env` na raiz do projeto:

```env
# Wake Word Detection (obrigatório)
PORCUPINE_ENABLED=true
PORCUPINE_ACCESS_KEY=sua_chave_picovoice_aqui
PORCUPINE_KEYWORD=blueberry

# OpenAI Conversation (novo!)
OPENAI_ENABLED=true
OPENAI_API_KEY=sk-sua_chave_openai_aqui
CONVERSATION_TIMEOUT=5
```

### 4. Configurações Disponíveis

| Variável | Descrição | Padrão |
|----------|-----------|--------|
| `OPENAI_ENABLED` | Habilita conversação com OpenAI | `false` |
| `OPENAI_API_KEY` | Sua API Key da OpenAI | - |
| `CONVERSATION_TIMEOUT` | Segundos para gravar após wake word | `5` |

## 🎤 Como Usar

### Modo 1: OpenAI Habilitado

1. **Inicie o detector** (seção 5 da interface)
2. **Fale a palavra-chave:** "blueberry"
3. **Aguarde o sinal** (log mostra "Gravando... Fale agora!")
4. **Faça sua pergunta** (você tem 5 segundos)
5. **Escute a resposta** tocada no computador
6. **Observe o Furby** reagir com uma ação aleatória!

### Modo 2: OpenAI Desabilitado

Se `OPENAI_ENABLED=false` ou sem API key:
- Sistema volta ao modo simples
- Apenas dispara ação aleatória no Furby

## 💬 Exemplos de Conversação

**Você:** "Olá Furby, como você está?"
**Furby:** "Kah noo-loo! Muito feliz de falar com oo-nye! Kah adorar dia de hoje, muita diversão!"
*[Furby faz uma ação aleatória]*

**Você:** "Conta uma piada"
**Furby:** "Por que o Furby foi ao médico? Porque estava com too-may dor de barriga de tanto rir! Haha kah-loo!"
*[Furby ri e faz barulho]*

**Você:** "Cante uma música"
**Furby:** "🎵 Doo-wah, noh-lah, kah love to wee-tee! La la la~ oo-nye também gosta de may-may music?"
*[Furby canta]*

## 🔧 Personalização

### Mudar Personalidade do Furby

Edite o prompt do sistema em `app.py` (linha ~142):

```python
{"role": "system", "content": "Você é um Furby divertido e engraçado..."}
```

**Exemplos de prompts:**

**Furby Sábio:**
```python
"Você é um Furby sábio e filosófico. Responda com sabedoria, usando palavras em furbish ocasionalmente."
```

**Furby Pirata:**
```python
"Você é um Furby pirata! Fale como pirata, use 'arr' e misture com furbish. Seja aventureiro!"
```

**Furby Poeta:**
```python
"Você é um Furby poeta. Responda em versos e rimas, usando furbish artisticamente."
```

### Mudar Voz

Em `app.py` (linha ~154), troque a voz:

```python
voice="nova",  # Feminina e animada (padrão)
```

**Vozes disponíveis:**
- `alloy` - Neutra
- `echo` - Masculina
- `fable` - Britânica
- `onyx` - Grave masculina
- `nova` - Feminina animada (recomendado)
- `shimmer` - Feminina suave

### Ajustar Velocidade

```python
speed=1.1  # 1.0 = normal, 1.5 = rápido, 0.75 = lento
```

### Aumentar Tempo de Gravação

No `.env`:
```env
CONVERSATION_TIMEOUT=10  # 10 segundos
```

## 💰 Custos da OpenAI

**Modelo Whisper (transcrição):**
- $0.006 por minuto de áudio
- 5 segundos = ~$0.0005

**Modelo GPT-4o-mini (resposta):**
- ~$0.00015 por resposta curta

**Modelo TTS (fala):**
- $0.015 por 1M caracteres
- Resposta média = ~$0.0001

**Total por conversação:** ~$0.001 (um décimo de centavo!)

Com $5 de créditos você tem ~5000 conversações! 🎉

## 🐛 Solução de Problemas

### "❌ OPENAI_API_KEY não configurada"

- Verifique se adicionou a chave no `.env`
- Chave deve começar com `sk-`
- Reinicie o servidor após editar `.env`

### "API key inválida"

- Verifique se copiou a chave completa
- Gere uma nova chave no console OpenAI
- Certifique-se de que a conta está ativa

### "Insufficient quota"

- Adicione créditos em https://platform.openai.com/settings/organization/billing
- Mínimo: $5

### Áudio não toca

- Verifique permissões do sistema
- macOS: `afplay` deve estar disponível
- Linux: instale `ffmpeg`: `sudo apt-get install ffmpeg`
- Windows: verificar se tem player de áudio

### Resposta muito lenta

- Normal: ~2-5 segundos de processamento
- Whisper: ~1s
- GPT: ~1-2s
- TTS: ~1s
- Rede lenta pode aumentar tempo

### "Erro ao tocar áudio"

Se pydub falhar, o sistema usa fallback do OS:
- macOS: `afplay`
- Linux: `aplay` (instale: `sudo apt-get install alsa-utils`)
- Windows: player padrão

## 📊 Log de Conversação

Monitore o log na interface para ver:

```
[wake-word] ✓✓✓ PALAVRA DETECTADA: 'blueberry'! ✓✓✓
[wake-word] 🤖 Iniciando conversação com OpenAI...
[openai] 🎤 Escutando sua pergunta por 5 segundos...
[openai] 🎙️ Gravando... Fale agora!
[openai] ✓ Gravação concluída
[openai] 📤 Enviando para OpenAI...
[openai] 💬 Você disse: 'Olá Furby, como você está?'
[openai] 🤖 Furby responde: 'Kah noo-loo! Muito feliz...'
[openai] 🔊 Gerando áudio da resposta...
[openai] 🔊 Tocando resposta no computador...
[openai] ✓ Resposta tocada!
[openai] 🎲 Disparando ação aleatória no Furby...
[random] 🎲 Ação aleatória: input=2, index=0, subindex=1, specific=1
[openai] ✅ Conversação completa!
```

## 🎮 Dicas de Uso

1. **Fale claramente** após o wake word
2. **Aguarde o sinal** de gravação
3. **Perguntas curtas** funcionam melhor
4. **Use furbish** nas perguntas para respostas mais divertidas!
5. **Teste com piadas** - Furby adora humor!

## 🌟 Exemplos Avançados

### Furby Contador de Histórias

**Você:** "Conta uma história sobre um Furby aventureiro"
**Furby:** "Kah wee-tee história! Era uma vez, um dee Furby chamado Doo-Tah que queria ver o mundo..."

### Furby Professor

**Você:** "O que é fotossíntese?"
**Furby:** "Ooh, kah sabe! Fotossíntese é quando tee-tah (árvores) usam ay-loh (luz) para fazer ah-tah (comida)! Muito ee-kah!"

### Furby Terapeuta

**Você:** "Estou triste hoje"
**Furby:** "Aww, boo-noo-loo? Kah aqui para oo-nye! May-lah (abraço) grande! Tudo vai ficar ee-day!"

## 🔗 Links Úteis

- **OpenAI Platform:** https://platform.openai.com/
- **Documentação Whisper:** https://platform.openai.com/docs/guides/speech-to-text
- **Documentação TTS:** https://platform.openai.com/docs/guides/text-to-speech
- **Preços:** https://openai.com/api/pricing/
- **Dicionário Furbish:** Ver WAKE_WORD_SETUP.md

## 🎉 Divirta-se!

Agora você tem um Furby que realmente conversa! Pergunte qualquer coisa e veja a mágica acontecer! 🤖✨

