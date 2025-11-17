# Changelog

## [Nova Funcionalidade] Wake Word Detection & Random Actions

### 🎉 O que foi adicionado:

#### 1. **Detecção de Wake Word (Porcupine)**
- ✅ Integração completa com `pvporcupine`
- ✅ Suporte para palavras-chave built-in (alexa, jarvis, computer, etc)
- ✅ Suporte para modelos customizados (.ppn)
- ✅ Execução em thread separada (não bloqueia a aplicação)
- ✅ Acesso ao microfone via PyAudio

#### 2. **Sistema de Ações Aleatórias**
- ✅ Método `random_action()` no Controller
- ✅ Lista curada de ~90 ações divertidas do Furby
- ✅ Categorias: pets, tickles, hugs, farts/burps, conversation, singing, dancing, etc
- ✅ Escolhe aleatoriamente da lista de ações conhecidas
- ✅ Funciona tanto em modo simulado quanto real
- ✅ Foco em variações de ações sem mudar cor da antena

#### 3. **API Endpoints**
Novos endpoints adicionados:
- `POST /api/random-action` - Dispara uma ação aleatória
- `POST /api/wake-word/start` - Inicia o detector de wake word
- `POST /api/wake-word/stop` - Para o detector de wake word
- `GET /api/wake-word/status` - Retorna status do detector

#### 4. **Interface Web**
- ✅ Nova seção "5) Random Action & Wake Word"
- ✅ Botão "🎲 Ação Aleatória" para teste manual
- ✅ Controles para iniciar/parar detector
- ✅ Indicador de status em tempo real
- ✅ Atualização automática do status a cada 3 segundos

#### 5. **Configuração via Variáveis de Ambiente**
Novas variáveis no `.env`:
```env
PORCUPINE_ENABLED=false          # Habilita/desabilita o detector
PORCUPINE_ACCESS_KEY=            # Access key do Picovoice
PORCUPINE_KEYWORD=alexa          # Palavra-chave a ser detectada
```

#### 6. **Documentação**
- ✅ `WAKE_WORD_SETUP.md` - Guia completo de configuração
- ✅ README atualizado com instruções de uso
- ✅ Exemplos de configuração

### 📦 Novas Dependências

```txt
pvporcupine>=3.0.0   # Wake word detection
pyaudio>=0.2.13      # Captura de áudio do microfone
```

### 🔧 Arquivos Modificados

1. **requirements.txt**
   - Adicionado `pvporcupine` e `pyaudio`

2. **app.py**
   - Imports: `random`, `threading`
   - Nova classe: `WakeWordDetector`
   - Método novo: `Controller.random_action()`
   - 4 novos endpoints API
   - Interface web atualizada com nova seção
   - 4 novas funções JavaScript

3. **README.md**
   - Seção sobre Wake Word Detection
   - Lista atualizada de funcionalidades
   - Componentes principais atualizados

### 🎯 Como Usar

#### Modo 1: Testar Ação Aleatória (sem wake word)
1. Acesse http://localhost:8000
2. Conecte-se ao Furby
3. Clique em "🎲 Ação Aleatória"

#### Modo 2: Usar Wake Word Detection
1. Configure `PORCUPINE_ACCESS_KEY` no `.env`
2. Defina `PORCUPINE_ENABLED=true`
3. Reinicie o servidor
4. Clique em "▶ Iniciar" na seção Wake Word
5. Fale a palavra-chave configurada!

### 🐛 Tratamento de Erros

- ✅ Verifica se bibliotecas estão instaladas
- ✅ Valida access key antes de iniciar
- ✅ Mensagens de erro claras no log
- ✅ Graceful degradation (continua funcionando sem wake word)
- ✅ Cleanup automático de recursos (audio stream, porcupine)

### 🔒 Privacidade

- Todo processamento é **local** (on-device)
- Nenhum áudio é enviado para servidores externos
- Access key é usada apenas para inicializar o modelo local

### 📊 Compatibilidade

Testado em:
- ✅ macOS (ARM64)
- ⚠️ Linux (requer instalação de portaudio)
- ⚠️ Windows (requer instalação especial do PyAudio)

### 🚀 Próximos Passos (Sugestões)

- [ ] Suporte para múltiplas palavras-chave
- [ ] Configuração de sensibilidade
- [ ] Histórico de ações aleatórias
- [ ] Presets de ações aleatórias customizáveis
- [ ] Integração com outros comandos de voz

### 📝 Notas Técnicas

**Threading:**
- O detector roda em uma thread daemon separada
- Usa `asyncio.new_event_loop()` para executar ações assíncronas da thread

**Performance:**
- O detector tem overhead mínimo
- Não afeta a performance da aplicação web
- Processamento de áudio otimizado pelo Porcupine

**Limitações:**
- Plano gratuito do Picovoice tem limites de uso (generosos)
- Palavras customizadas requerem treinamento no console
- PyAudio pode ter problemas de instalação em alguns sistemas


