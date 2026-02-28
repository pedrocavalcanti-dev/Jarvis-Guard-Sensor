# Jarvis Guard Sensor

```
     ██╗ ██████╗      ███████╗███████╗███╗   ██╗███████╗ ██████╗ ██████╗ 
     ██║██╔════╝      ██╔════╝██╔════╝████╗  ██║██╔════╝██╔═══██╗██╔══██╗
     ██║██║  ███╗     ███████╗█████╗  ██╔██╗ ██║███████╗██║   ██║██████╔╝
██   ██║██║   ██║     ╚════██║██╔══╝  ██║╚██╗██║╚════██║██║   ██║██╔══██╗
╚█████╔╝╚██████╔╝     ███████║███████╗██║ ╚████║███████║╚██████╔╝██║  ██║
 ╚════╝  ╚═════╝      ╚══════╝╚══════╝╚═╝  ╚═══╝╚══════╝ ╚═════╝ ╚═╝  ╚═╝
```

**Sensor Agent oficial do Jarvis Guard**  
Lê o `eve.json` do Suricata e envia eventos em tempo real para o Jarvis Guard.

---

## O que é isso?

O **Jarvis Guard Sensor** é o agente que roda na máquina Linux com Suricata.  
Ele monitora o `eve.json` e envia alertas, DNS, HTTP e TLS para o painel SOC do Jarvis Guard via HTTP POST.

```
Linux Gateway (Suricata)                Servidor Jarvis Guard
────────────────────────                ──────────────────────
Suricata → eve.json
    └── JG-Sensor.py  ───── POST ────▶  /incidentes/api/ingest/
                                              └── Dashboard SOC
```

---

## Pré-requisitos

### Python 3.9 ou superior

Verifique se já está instalado:
```bash
python3 --version
```

Se não estiver:

**Debian / Ubuntu:**
```bash
sudo apt update && sudo apt install python3 python3-pip python3-venv -y
```

**CentOS / RHEL / Fedora:**
```bash
sudo dnf install python3 python3-pip -y
```

**Arch Linux:**
```bash
sudo pacman -S python python-pip
```

---

## Instalação

### Passo 1 — Instale o Git

Verifique se já está instalado:
```bash
git --version
```

Se não estiver:

**Debian / Ubuntu:**
```bash
sudo apt install git -y
```

**CentOS / RHEL / Fedora:**
```bash
sudo dnf install git -y
```

**Arch Linux:**
```bash
sudo pacman -S git
```

---

### Passo 2 — Clone o repositório

```bash
git clone https://github.com/pedrocavalcanti-dev/Jarvis-Guard-Sensor.git
cd Jarvis-Guard-Sensor
```

### Passo 3 — Crie o ambiente virtual

```bash
python3 -m venv venv
source venv/bin/activate
```

### Passo 4 — Instale as dependências

```bash
pip install -r requirements.txt
```

### Passo 5 — Execute

```bash
python JG-Sensor.py
```

> Na **primeira execução** o wizard de configuração abre automaticamente.  
> Você informa o IP do Jarvis Guard, o nome deste sensor e a severidade mínima.  
> Tudo é salvo em `config.json` — próximas execuções vão direto pro menu.

---

## Instalação rápida (tudo de uma vez)

```bash
sudo apt install git python3 python3-pip python3-venv -y
git clone https://github.com/pedrocavalcanti-dev/Jarvis-Guard-Sensor.git
cd Jarvis-Guard-Sensor
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python JG-Sensor.py
```

---

## Menu principal

```
╔══════════════════════════════════════════╗
║        JARVIS GUARD — SENSOR             ║
╠══════════════════════════════════════════╣
║  Status : ● CONECTADO                    ║
║  Jarvis : http://192.168.0.105:8000      ║
║  Sensor : IDS-LAB-01                     ║
╠══════════════════════════════════════════╣
║  [1] Iniciar sensor                      ║
║  [2] Configurar IP do Jarvis             ║
║  [3] Configurar nome do sensor           ║
║  [4] Testar conexão com Jarvis           ║
║  [5] Ver configuração atual              ║
║  [6] Sair                                ║
╚══════════════════════════════════════════╝
```

---

## Rodar como serviço systemd (produção)

Para o sensor iniciar automaticamente com o Linux:

```bash
sudo nano /etc/systemd/system/jg-sensor.service
```

Cole:
```ini
[Unit]
Description=Jarvis Guard Sensor Agent
After=network.target suricata.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/Jarvis-Guard-Sensor
ExecStart=/opt/Jarvis-Guard-Sensor/venv/bin/python JG-Sensor.py --auto
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Ative:
```bash
sudo systemctl daemon-reload
sudo systemctl enable jg-sensor
sudo systemctl start jg-sensor
sudo systemctl status jg-sensor
```

---

## Requisitos de rede

- O sensor precisa alcançar o Jarvis Guard via HTTP
- Porta padrão: `8000`
- O Jarvis Guard precisa estar em modo **Produção** com IDS **ativo**

---

## Problemas comuns

**`eve.json` não encontrado**
```bash
# Verifique se o Suricata está rodando
sudo systemctl status suricata

# Verifique o caminho no suricata.yaml
grep -A5 "eve-log" /etc/suricata/suricata.yaml
```

**Jarvis não acessível**
```bash
# Jarvis Guard deve rodar com 0.0.0.0
python gerenciar.py runserver 0.0.0.0:8000

# Verifique ALLOWED_HOSTS no settings.py do Jarvis Guard
```

**Permissão negada no `eve.json`**
```bash
sudo chmod 644 /var/log/suricata/eve.json
```

---

## Estrutura do repositório

```
Jarvis-Guard-Sensor/
├── JG-Sensor.py        ← Sensor com menu TUI completo
├── config.json         ← Gerado automaticamente (não sobe no git)
├── requirements.txt    ← Dependências Python
├── .gitignore
└── README.md
```

---

## Compatibilidade

| Sistema | Suporte |
|---|---|
| Ubuntu 20.04+ | ✅ |
| Debian 11+ | ✅ |
| CentOS / RHEL 8+ | ✅ |
| Arch Linux | ✅ |
| Windows WSL | ✅ |

---

## Relacionado

- [Jarvis Guard](https://github.com/pedrocavalcanti-dev/Jarvis-Guard) — Dashboard SOC principal

---

<div align="center">
Parte do ecossistema <strong>Jarvis Guard</strong>
</div>