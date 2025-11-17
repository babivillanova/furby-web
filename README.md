# furby-web-sim (PyFluff‑ready)

Pequena aplicação web para brincar **agora** (modo simulado) e, quando seu **Furby Connect** chegar, é só desativar o modo simulado para controlar de verdade via **BLE** usando **PyFluff**.

Funciona no **macOS** (iMac com BLE OK), Linux e Raspberry Pi.

---

## 🗂️ Estrutura de pastas

Crie uma pasta no seu repositório (ex.: `furby-web`) e adicione estes arquivos:

```
furby-web/
├─ app.py
├─ requirements.txt
├─ .env.example
└─ README.md   ← (este arquivo)
```

> Se você usa **Cursor**, basta abrir essa pasta como projeto.

---

## ⚙️ Instalação

> **IMPORTANTE**: Requer **Python 3.11+** (PyFluff não funciona com versões anteriores).

```bash
# 1) Entrar na pasta do projeto
cd furby-web

# 2) Verificar versão do Python (deve ser 3.11+)
python3 --version

# 3) Criar e ativar venv (use python3.11, python3.12 ou python3.13 se disponível)
python3.13 -m venv .venv  # ou python3.11, python3.12
source .venv/bin/activate

# 4) Atualizar pip (recomendado)
python -m pip install --upgrade pip

# 5) Instalar dependências (inclui FastAPI, Bleak e PyFluff via Git)
pip install -r requirements.txt

# 6) (Opcional) Copiar .env.example para .env e ajustar variáveis
cp .env.example .env
```

> **Sem Furby ainda?** Deixe `MOCK_MODE=true` no `.env` (padrão). Você já consegue abrir o painel web e "fazer de conta" — perfeito para testar no navegador.

---

## ▶️ Rodar a aplicação

```bash
uvicorn app:app --reload
```

Abra no navegador: [http://localhost:8000](http://localhost:8000)

* Em **MOCK_MODE=true**: tudo funciona em simulado (logs mostram o que seria enviado ao Furby).
* Quando o Furby chegar: ponha `MOCK_MODE=false`, ligue o Furby e use **Scan → Connect** no painel.

---

## 🔧 Configuração por ambiente (`.env`)

```ini
# .env.example
# Quando ainda está sem o brinquedo, mantenha true (modo simulado)
MOCK_MODE=true

# Opcional: MAC address do Furby (ex.: AA:BB:CC:DD:EE:FF). Se vazio, o app tenta descoberta.
FURBY_ADDRESS=

# Porta do servidor web
PORT=8000
```

---

## 🧪 O que dá pra fazer no painel

* **Scan**: procurar dispositivos BLE próximos; mostra Furbies encontrados (no simulado, lista fake).

* **Connect**: conecta no endereço selecionado (ou tenta auto‑descobrir).

* **Antenna Color**: escolher cor (RGB) e aplicar.

* **Action**: enviar um comando (input/index/subindex/specific) — quando em simulado, apenas loga a chamada.

* **Play Audio**: enviar arquivos WAV para tocar no Furby.

* **🎲 Random Action**: dispara uma ação aleatória da lista de ~90 ações divertidas do Furby (pets, tickles, farts, singing, etc).

* **🎤 Wake Word Detection**: detecta palavra-chave por voz e dispara ação aleatória automaticamente!

* **Log ao vivo**: janela com eventos/erros.

---

## 🎤 Wake Word Detection (Comando de Voz)

**Novidade!** Agora você pode controlar o Furby por voz usando detecção de wake word com Porcupine.

### Como funciona:
1. Configure sua access key do Picovoice (grátis)
2. Ative o detector no painel web
3. Fale a palavra-chave (ex: "Alexa" ou "Jarvis")
4. O sistema gera 4 valores aleatórios (input, index, subindex, specific) e envia para o Furby! 🎲

### Configuração Rápida:

1. **Obtenha sua access key** (gratuita):
   - Acesse: https://console.picovoice.ai/
   - Crie uma conta e copie sua access key

2. **Configure no `.env`**:
```ini
PORCUPINE_ENABLED=true
PORCUPINE_ACCESS_KEY=sua_chave_aqui
PORCUPINE_KEYWORD=alexa  # ou jarvis, computer, etc
```

3. **Inicie o detector** pela interface web (seção 5)

📖 **Documentação completa:** [WAKE_WORD_SETUP.md](./WAKE_WORD_SETUP.md)

> **Nota:** Para usar a palavra "aleatório" em português, você precisa treinar um modelo customizado no console Picovoice. Veja instruções detalhadas no arquivo WAKE_WORD_SETUP.md.

---

## 🐍 Código — `app.py`

O código completo está em `app.py`. Principais componentes:

* **Log**: classe para armazenar logs em memória
* **WakeWordDetector**: detecção de wake word usando Porcupine (roda em thread separada)
* **SimulatedFurby**: implementação simulada para testes
* **RealFurby**: wrapper para PyFluff quando em modo real
* **Controller**: camada de controle que abstrai mock vs real (inclui método `random_action()`)
* **FastAPI**: endpoints REST para o frontend (inclui endpoints para wake word)
* **INDEX_HTML**: interface web simples e funcional com controles de wake word

---

## 📦 Dependências — `requirements.txt`

```txt
fastapi>=0.115
uvicorn[standard]>=0.30
bleak>=0.22
python-dotenv>=1.0
# PyFluff diretamente do Git (mantém o app pronto para o modo real)
# Se não quiser instalar agora, você pode comentar a linha abaixo
git+https://github.com/martinwoodward/PyFluff.git
# Porcupine para wake word detection
pvporcupine>=3.0.0
pyaudio>=0.2.13
```

---

## ✅ Checklist rápido (sem Furby)

1. Criar pasta e salvar os arquivos acima.
2. `python3 -m venv .venv && source .venv/bin/activate`
3. `pip install -r requirements.txt`
4. `uvicorn app:app --reload` → abrir [http://localhost:8000](http://localhost:8000)
5. Brincar no modo **simulado**: Scan/Connect/Antenna/Action + log.

## ✅ Quando o Furby chegar

1. Ligue o Furby.
2. Edite `.env` → `MOCK_MODE=false` (e, se quiser, defina `FURBY_ADDRESS`).
3. Reinicie o app (`Ctrl+C` e rode de novo).
4. Faça **Scan** e **Connect** no painel.
5. Use **Antenna** e **Action** para testar.

> Dica: se o macOS pedir permissões de Bluetooth para o Python, permita.

---

## 🧰 Notas

* O **scan** usa `BleakScanner` para procurar nomes com "Furby"/"Furby Connect".
* A camada "real" usa **PyFluff** (`FurbyConnect`) por trás. Se a importação falhar, o app volta ao modo simulado automaticamente.
* Você pode personalizar a UI direto no HTML inline do `app.py`.

---

## 🧯 Solução de problemas

* **Nada aparece no Scan** (modo real): confira se o Furby está acordado; tente aproximar; reinicie Bluetooth do macOS.
* **Erro ao importar PyFluff**: garanta que `pip install -r requirements.txt` completou sem erros.
* **Porta em uso**: mude `PORT` no `.env` ou rode `uvicorn app:app --reload --port 8001`.

