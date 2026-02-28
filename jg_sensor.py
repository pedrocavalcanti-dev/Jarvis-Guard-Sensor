#!/usr/bin/env python3
# =============================================================================
#
#     ██╗ ██████╗      ███████╗███████╗███╗   ██╗███████╗ ██████╗ ██████╗
#     ██║██╔════╝      ██╔════╝██╔════╝████╗  ██║██╔════╝██╔═══██╗██╔══██╗
#     ██║██║  ███╗     ███████╗█████╗  ██╔██╗ ██║███████╗██║   ██║██████╔╝
# ██  ██║██║   ██║     ╚════██║██╔══╝  ██║╚██╗██║╚════██║██║   ██║██╔══██╗
# ╚█████╔╝╚██████╔╝    ███████║███████╗██║ ╚████║███████║╚██████╔╝██║  ██║
#  ╚════╝  ╚═════╝     ╚══════╝╚══════╝╚═╝  ╚═══╝╚══════╝ ╚═════╝ ╚═╝  ╚═╝
#
#  Jarvis Guard Sensor — Agent v1.0
#  github.com/pedrocavalcanti-dev/Jarvis-Guard-Sensor
#
# =============================================================================

import os
import sys
import time
import json
import socket
import threading
import requests
from datetime import datetime
from colorama import init, Fore, Back, Style

init(autoreset=True)

# ══════════════════════════════════════════════════════════════════════════════
# CONSTANTES
# ══════════════════════════════════════════════════════════════════════════════

VERSION       = "1.0.0"
CONFIG_FILE   = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
EVE_PATH      = "/var/log/suricata/eve.json"
TIPOS_ACEITOS = {"alert", "dns", "http", "tls"}

SEVERIDADE_MAP = {
    "1": "critico",
    "2": "alto",
    "3": "medio",
    "4": "todos",
}

SEVERIDADE_LABEL = {
    "1": "Crítico (só alertas críticos)",
    "2": "Alto (crítico + alto)",
    "3": "Médio (crítico + alto + médio)",
    "4": "Todos (sem filtro)",
}

# Cores
C_TITULO   = Fore.CYAN + Style.BRIGHT
C_BORDA    = Fore.CYAN
C_OK       = Fore.GREEN + Style.BRIGHT
C_ERRO     = Fore.RED + Style.BRIGHT
C_AVISO    = Fore.YELLOW + Style.BRIGHT
C_DIM      = Fore.WHITE + Style.DIM
C_NORMAL   = Style.RESET_ALL
C_DESTAQUE = Fore.WHITE + Style.BRIGHT
C_MENU_NUM = Fore.CYAN + Style.BRIGHT
C_MENU_TXT = Fore.WHITE

# ══════════════════════════════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════════════════════════════

def config_padrao():
    return {
        "jarvis_url":    "",
        "sensor_nome":   socket.gethostname(),
        "min_severity":  "4",
        "batch_size":    20,
        "batch_timeout": 5,
        "eve_path":      EVE_PATH,
        "configurado":   False,
    }


def carregar_config() -> dict:
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                cfg = json.load(f)
            # garante que todos os campos existem
            padrao = config_padrao()
            for k, v in padrao.items():
                if k not in cfg:
                    cfg[k] = v
            return cfg
        except Exception:
            pass
    return config_padrao()


def salvar_config(cfg: dict):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS VISUAIS
# ══════════════════════════════════════════════════════════════════════════════

LARGURA = 52

def limpar():
    os.system("cls" if os.name == "nt" else "clear")


def linha(char="═", cor=C_BORDA):
    print(cor + "║" + char * (LARGURA - 2) + "║")


def linha_vazia():
    print(C_BORDA + "║" + " " * (LARGURA - 2) + "║")


def linha_texto(texto, cor=C_NORMAL, alinhamento="esquerda", pad=2):
    espaco = LARGURA - 2 - pad * 2
    if alinhamento == "centro":
        t = texto.center(espaco)
    elif alinhamento == "direita":
        t = texto.rjust(espaco)
    else:
        t = texto.ljust(espaco)
    # trunca se muito longo
    t_limpo = t[:espaco]
    print(C_BORDA + "║" + " " * pad + cor + t_limpo + C_BORDA + " " * (espaco - len(t_limpo) + pad) + "║")


def topo():
    print(C_BORDA + "╔" + "═" * (LARGURA - 2) + "╗")


def fundo():
    print(C_BORDA + "╚" + "═" * (LARGURA - 2) + "╝")


def separador():
    print(C_BORDA + "╠" + "═" * (LARGURA - 2) + "╣")


def cabecalho(cfg: dict):
    limpar()
    topo()
    linha_texto("JARVIS GUARD — SENSOR", C_TITULO, "centro")
    linha_texto(f"v{VERSION}  ·  github.com/pedrocavalcanti-dev", C_DIM, "centro")
    separador()

    # Status conexão
    status_str, status_cor = _status_conexao(cfg)
    linha_texto(f"Status  : {status_str}", status_cor)
    linha_texto(f"Jarvis  : {cfg['jarvis_url'] or '(não configurado)'}", C_DIM)
    linha_texto(f"Sensor  : {cfg['sensor_nome']}", C_DIM)
    linha_texto(f"Eve.json: {cfg['eve_path']}", C_DIM)
    separador()


def _status_conexao(cfg: dict) -> tuple:
    if not cfg.get("jarvis_url"):
        return "● NÃO CONFIGURADO", C_AVISO
    try:
        r = requests.get(cfg["jarvis_url"] + "/", timeout=2)
        if r.status_code < 500:
            return "● JARVIS ACESSÍVEL", C_OK
        return f"● HTTP {r.status_code}", C_AVISO
    except Exception:
        return "● SEM CONEXÃO", C_ERRO


def input_campo(prompt: str, valor_atual: str = "") -> str:
    sufixo = f" [{valor_atual}]" if valor_atual else ""
    print(C_BORDA + "║  " + C_AVISO + f"▶ {prompt}{sufixo}: " + C_DESTAQUE, end="")
    try:
        val = input().strip()
    except (KeyboardInterrupt, EOFError):
        val = ""
    return val if val else valor_atual


def aguardar_enter(msg="Pressione Enter para continuar..."):
    print(C_BORDA + "║  " + C_DIM + msg + C_NORMAL)
    try:
        input()
    except (KeyboardInterrupt, EOFError):
        pass


def print_resultado(ok: bool, msg: str):
    icone = C_OK + "✔" if ok else C_ERRO + "✗"
    print(C_BORDA + "║  " + icone + " " + (C_OK if ok else C_ERRO) + msg)


# ══════════════════════════════════════════════════════════════════════════════
# WIZARD — primeira execução
# ══════════════════════════════════════════════════════════════════════════════

def wizard(cfg: dict) -> dict:
    limpar()
    topo()
    linha_texto("JARVIS GUARD — SENSOR  SETUP", C_TITULO, "centro")
    linha_texto("Primeira execução detectada!", C_AVISO, "centro")
    separador()
    linha_texto("Vamos configurar o sensor em 3 passos.", C_NORMAL)
    linha_vazia()

    # ── Passo 1: IP do Jarvis ─────────────────────────────────────────────────
    linha_texto("PASSO 1 — IP do Jarvis Guard", C_DESTAQUE)
    linha_texto("Ex: http://192.168.0.105:8000", C_DIM)
    linha_vazia()

    while True:
        url = input_campo("URL do Jarvis Guard")
        if not url:
            print_resultado(False, "URL obrigatória.")
            continue
        # normaliza
        if not url.startswith("http"):
            url = "http://" + url
        url = url.rstrip("/")

        # testa conexão
        linha_vazia()
        linha_texto("Testando conexão...", C_DIM)
        try:
            r = requests.get(url + "/", timeout=4)
            print_resultado(True, f"Jarvis acessível — HTTP {r.status_code}")
            cfg["jarvis_url"] = url
            break
        except Exception as e:
            print_resultado(False, f"Não consegui conectar: {e}")
            linha_texto("Verifique o IP e se o Jarvis está rodando.", C_DIM)
            nova = input_campo("Tentar outro endereço? (s/n)", "s")
            if nova.lower() != "s":
                cfg["jarvis_url"] = url
                break

    linha_vazia()
    separador()

    # ── Passo 2: Nome do sensor ───────────────────────────────────────────────
    linha_texto("PASSO 2 — Nome deste sensor", C_DESTAQUE)
    linha_texto("Ex: IDS-GATEWAY, SENSOR-LAB-01", C_DIM)
    linha_vazia()

    nome = input_campo("Nome do sensor", cfg["sensor_nome"])
    cfg["sensor_nome"] = nome or cfg["sensor_nome"]

    linha_vazia()
    separador()

    # ── Passo 3: Severidade mínima ────────────────────────────────────────────
    linha_texto("PASSO 3 — Severidade mínima dos alertas", C_DESTAQUE)
    linha_vazia()
    for k, v in SEVERIDADE_LABEL.items():
        linha_texto(f"  [{k}] {v}", C_MENU_TXT)
    linha_vazia()

    while True:
        sev = input_campo("Escolha (1-4)", cfg["min_severity"])
        if sev in SEVERIDADE_MAP:
            cfg["min_severity"] = sev
            break
        print_resultado(False, "Opção inválida. Digite 1, 2, 3 ou 4.")

    linha_vazia()
    separador()

    # ── Confirma e salva ──────────────────────────────────────────────────────
    linha_texto("Configuração concluída!", C_OK, "centro")
    linha_vazia()
    linha_texto(f"Jarvis  : {cfg['jarvis_url']}", C_DIM)
    linha_texto(f"Sensor  : {cfg['sensor_nome']}", C_DIM)
    linha_texto(f"Severity: {SEVERIDADE_LABEL[cfg['min_severity']]}", C_DIM)
    linha_vazia()

    cfg["configurado"] = True
    salvar_config(cfg)
    print_resultado(True, "config.json salvo.")
    linha_vazia()
    aguardar_enter()
    return cfg


# ══════════════════════════════════════════════════════════════════════════════
# MENU PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════

def menu_principal(cfg: dict):
    while True:
        cabecalho(cfg)
        opcoes = [
            ("1", "Iniciar sensor"),
            ("2", "Configurar IP do Jarvis"),
            ("3", "Configurar nome do sensor"),
            ("4", "Configurar severidade mínima"),
            ("5", "Configurar caminho do eve.json"),
            ("6", "Testar conexão com Jarvis"),
            ("7", "Ver configuração atual"),
            ("8", "Sair"),
        ]
        for num, txt in opcoes:
            linha_texto(f"  [{num}] {txt}", C_MENU_TXT)
        linha_vazia()
        fundo()

        print(C_AVISO + "  Opção: " + C_DESTAQUE, end="")
        try:
            opcao = input().strip()
        except (KeyboardInterrupt, EOFError):
            opcao = "8"

        if opcao == "1":
            tela_sensor(cfg)
        elif opcao == "2":
            cfg = tela_config_ip(cfg)
        elif opcao == "3":
            cfg = tela_config_nome(cfg)
        elif opcao == "4":
            cfg = tela_config_severidade(cfg)
        elif opcao == "5":
            cfg = tela_config_eve(cfg)
        elif opcao == "6":
            tela_testar_conexao(cfg)
        elif opcao == "7":
            tela_ver_config(cfg)
        elif opcao == "8":
            limpar()
            print(C_DIM + "\nJarvis Guard Sensor encerrado.\n")
            sys.exit(0)


# ══════════════════════════════════════════════════════════════════════════════
# TELAS DE CONFIGURAÇÃO
# ══════════════════════════════════════════════════════════════════════════════

def tela_config_ip(cfg: dict) -> dict:
    cabecalho(cfg)
    linha_texto("CONFIGURAR IP DO JARVIS GUARD", C_DESTAQUE)
    linha_texto("Ex: http://192.168.0.105:8000", C_DIM)
    linha_vazia()

    url = input_campo("Nova URL do Jarvis Guard", cfg["jarvis_url"])
    if url:
        if not url.startswith("http"):
            url = "http://" + url
        url = url.rstrip("/")
        cfg["jarvis_url"] = url
        salvar_config(cfg)
        print_resultado(True, f"URL salva: {url}")
    else:
        print_resultado(False, "Nenhuma alteração feita.")

    linha_vazia()
    aguardar_enter()
    return cfg


def tela_config_nome(cfg: dict) -> dict:
    cabecalho(cfg)
    linha_texto("CONFIGURAR NOME DO SENSOR", C_DESTAQUE)
    linha_vazia()

    nome = input_campo("Novo nome do sensor", cfg["sensor_nome"])
    if nome:
        cfg["sensor_nome"] = nome
        salvar_config(cfg)
        print_resultado(True, f"Nome salvo: {nome}")
    else:
        print_resultado(False, "Nenhuma alteração feita.")

    linha_vazia()
    aguardar_enter()
    return cfg


def tela_config_severidade(cfg: dict) -> dict:
    cabecalho(cfg)
    linha_texto("CONFIGURAR SEVERIDADE MÍNIMA", C_DESTAQUE)
    linha_vazia()

    for k, v in SEVERIDADE_LABEL.items():
        linha_texto(f"  [{k}] {v}", C_MENU_TXT)
    linha_vazia()

    sev = input_campo("Escolha (1-4)", cfg["min_severity"])
    if sev in SEVERIDADE_MAP:
        cfg["min_severity"] = sev
        salvar_config(cfg)
        print_resultado(True, f"Severidade salva: {SEVERIDADE_LABEL[sev]}")
    else:
        print_resultado(False, "Opção inválida.")

    linha_vazia()
    aguardar_enter()
    return cfg


def tela_config_eve(cfg: dict) -> dict:
    cabecalho(cfg)
    linha_texto("CONFIGURAR CAMINHO DO EVE.JSON", C_DESTAQUE)
    linha_texto("Padrão: /var/log/suricata/eve.json", C_DIM)
    linha_vazia()

    caminho = input_campo("Caminho do eve.json", cfg["eve_path"])
    if caminho:
        if os.path.exists(caminho):
            print_resultado(True, "Arquivo encontrado.")
        else:
            print_resultado(False, "Arquivo não encontrado agora (OK se Suricata ainda não iniciou).")
        cfg["eve_path"] = caminho
        salvar_config(cfg)
        print_resultado(True, f"Caminho salvo: {caminho}")

    linha_vazia()
    aguardar_enter()
    return cfg


def tela_testar_conexao(cfg: dict):
    cabecalho(cfg)
    linha_texto("TESTAR CONEXÃO COM JARVIS GUARD", C_DESTAQUE)
    linha_vazia()

    if not cfg["jarvis_url"]:
        print_resultado(False, "URL não configurada.")
        linha_vazia()
        aguardar_enter()
        return

    linha_texto(f"Testando: {cfg['jarvis_url']}", C_DIM)
    linha_vazia()

    # Teste 1: GET /
    try:
        t0 = time.time()
        r = requests.get(cfg["jarvis_url"] + "/", timeout=5)
        ms = int((time.time() - t0) * 1000)
        print_resultado(True, f"GET /  →  HTTP {r.status_code}  ({ms}ms)")
    except requests.exceptions.ConnectionError:
        print_resultado(False, "Conexão recusada. Jarvis está rodando?")
        linha_vazia()
        aguardar_enter()
        return
    except Exception as e:
        print_resultado(False, f"Erro: {e}")
        linha_vazia()
        aguardar_enter()
        return

    # Teste 2: POST /incidentes/api/ingest/ com payload vazio
    linha_vazia()
    linha_texto("Testando endpoint de ingestão...", C_DIM)
    try:
        payload = {"sensor": cfg["sensor_nome"], "eventos": []}
        r2 = requests.post(
            cfg["jarvis_url"] + "/incidentes/api/ingest/",
            json=payload,
            timeout=5,
        )
        if r2.status_code == 200:
            print_resultado(True, f"POST /incidentes/api/ingest/  →  HTTP 200 — Pronto para enviar!")
        elif r2.status_code == 403:
            print_resultado(False, "HTTP 403 — Jarvis em modo Demo ou IDS desativado.")
            linha_texto("  Ative o modo Produção e o toggle IDS no painel.", C_DIM)
        else:
            print_resultado(False, f"HTTP {r2.status_code}  →  {r2.text[:100]}")
    except Exception as e:
        print_resultado(False, f"Erro no ingest: {e}")

    linha_vazia()
    aguardar_enter()


def tela_ver_config(cfg: dict):
    cabecalho(cfg)
    linha_texto("CONFIGURAÇÃO ATUAL", C_DESTAQUE)
    linha_vazia()
    linha_texto(f"Jarvis URL    : {cfg['jarvis_url'] or '(vazio)'}", C_DIM)
    linha_texto(f"Nome sensor   : {cfg['sensor_nome']}", C_DIM)
    linha_texto(f"Eve.json      : {cfg['eve_path']}", C_DIM)
    linha_texto(f"Severidade    : {SEVERIDADE_LABEL.get(cfg['min_severity'], '?')}", C_DIM)
    linha_texto(f"Batch size    : {cfg['batch_size']} eventos", C_DIM)
    linha_texto(f"Batch timeout : {cfg['batch_timeout']}s", C_DIM)
    linha_texto(f"Config file   : {CONFIG_FILE}", C_DIM)

    # Verifica eve.json
    linha_vazia()
    if os.path.exists(cfg["eve_path"]):
        tamanho = os.path.getsize(cfg["eve_path"])
        print_resultado(True, f"eve.json encontrado ({tamanho:,} bytes)")
    else:
        print_resultado(False, "eve.json NÃO encontrado no caminho configurado.")

    linha_vazia()
    aguardar_enter()


# ══════════════════════════════════════════════════════════════════════════════
# TELA DO SENSOR — loop principal de envio
# ══════════════════════════════════════════════════════════════════════════════

# Stats globais do sensor (acessadas pela thread de display)
_stats = {
    "seen":   0,
    "sent":   0,
    "erros":  0,
    "buffer": 0,
    "ultimo": "—",
    "rodando": True,
}
_stats_lock = threading.Lock()


def tela_sensor(cfg: dict):
    # Validações básicas
    if not cfg["jarvis_url"]:
        cabecalho(cfg)
        print_resultado(False, "URL do Jarvis não configurada. Configure primeiro.")
        linha_vazia()
        aguardar_enter()
        return

    if not os.path.exists(cfg["eve_path"]):
        cabecalho(cfg)
        print_resultado(False, f"eve.json não encontrado: {cfg['eve_path']}")
        linha_texto("Verifique se o Suricata está instalado e rodando.", C_DIM)
        linha_texto("Use a opção 5 para configurar o caminho correto.", C_DIM)
        linha_vazia()
        aguardar_enter()
        return

    # Reset stats
    with _stats_lock:
        _stats["seen"]    = 0
        _stats["sent"]    = 0
        _stats["erros"]   = 0
        _stats["buffer"]  = 0
        _stats["ultimo"]  = "—"
        _stats["rodando"] = True

    # Thread de display
    t_display = threading.Thread(target=_loop_display, args=(cfg,), daemon=True)
    t_display.start()

    # Loop de leitura + envio (thread principal)
    try:
        _loop_sensor(cfg)
    except KeyboardInterrupt:
        pass
    finally:
        with _stats_lock:
            _stats["rodando"] = False
        time.sleep(0.3)
        limpar()


def _loop_display(cfg: dict):
    """Redesenha a tela de status a cada 2s enquanto o sensor roda."""
    while True:
        with _stats_lock:
            if not _stats["rodando"]:
                break
            seen   = _stats["seen"]
            sent   = _stats["sent"]
            erros  = _stats["erros"]
            buf    = _stats["buffer"]
            ultimo = _stats["ultimo"]

        limpar()
        topo()
        linha_texto("JARVIS GUARD — SENSOR  ATIVO", C_TITULO, "centro")
        separador()
        linha_texto(f"Jarvis  : {cfg['jarvis_url']}", C_DIM)
        linha_texto(f"Sensor  : {cfg['sensor_nome']}", C_DIM)
        linha_texto(f"Eve.json: {cfg['eve_path']}", C_DIM)
        separador()
        linha_texto(f"  Eventos vistos   : {seen:,}", C_NORMAL)
        linha_texto(f"  Eventos enviados  : {sent:,}", C_OK)
        linha_texto(f"  Erros de envio    : {erros:,}", C_ERRO if erros > 0 else C_DIM)
        linha_texto(f"  Buffer pendente   : {buf}", C_DIM)
        linha_texto(f"  Último envio      : {ultimo}", C_DIM)
        separador()
        linha_texto("  Pressione Ctrl+C para parar o sensor", C_DIM)
        fundo()

        time.sleep(2)


def _loop_sensor(cfg: dict):
    """Lê o eve.json e envia eventos pro Jarvis em lote."""
    eve_path      = cfg["eve_path"]
    jarvis_url    = cfg["jarvis_url"] + "/incidentes/api/ingest/"
    sensor_nome   = cfg["sensor_nome"]
    batch_size    = int(cfg.get("batch_size", 20))
    batch_timeout = int(cfg.get("batch_timeout", 5))
    min_sev       = int(cfg.get("min_severity", 4))

    buffer     = []
    last_send  = time.time()

    with open(eve_path, "r", encoding="utf-8", errors="ignore") as f:
        f.seek(0, os.SEEK_END)

        while True:
            # Verifica se deve parar
            with _stats_lock:
                if not _stats["rodando"]:
                    break

            line = f.readline()
            if not line:
                # Nenhuma linha nova — verifica timeout do batch
                if buffer and (time.time() - last_send) >= batch_timeout:
                    ok = _enviar(jarvis_url, sensor_nome, buffer)
                    with _stats_lock:
                        if ok:
                            _stats["sent"]  += len(buffer)
                            _stats["ultimo"] = _agora()
                        else:
                            _stats["erros"] += len(buffer)
                        _stats["buffer"] = 0
                    buffer.clear()
                    last_send = time.time()
                time.sleep(0.2)
                continue

            line = line.strip()
            if not line:
                continue

            try:
                evt = json.loads(line)
            except json.JSONDecodeError:
                continue

            with _stats_lock:
                _stats["seen"] += 1

            # Filtra tipo
            tipo = evt.get("event_type", "").lower()
            if tipo not in TIPOS_ACEITOS:
                continue

            # Filtra severidade (só para alerts)
            if tipo == "alert":
                sev_num = evt.get("alert", {}).get("severity", 4)
                if sev_num > min_sev:
                    continue

            buffer.append(evt)

            with _stats_lock:
                _stats["buffer"] = len(buffer)

            # Envia se batch cheio ou timeout
            batch_cheio   = len(buffer) >= batch_size
            tempo_expirou = (time.time() - last_send) >= batch_timeout and buffer

            if batch_cheio or tempo_expirou:
                ok = _enviar(jarvis_url, sensor_nome, buffer)
                with _stats_lock:
                    if ok:
                        _stats["sent"]  += len(buffer)
                        _stats["ultimo"] = _agora()
                    else:
                        _stats["erros"] += len(buffer)
                    _stats["buffer"] = 0
                buffer.clear()
                last_send = time.time()


def _enviar(url: str, sensor_nome: str, buffer: list) -> bool:
    """Envia lote de eventos pro Jarvis Guard."""
    try:
        payload = {"sensor": sensor_nome, "eventos": buffer}
        resp = requests.post(url, json=payload, timeout=5,
                             headers={"Content-Type": "application/json"})
        return 200 <= resp.status_code < 300
    except Exception:
        return False


def _agora() -> str:
    return datetime.now().strftime("%H:%M:%S")


# ══════════════════════════════════════════════════════════════════════════════
# MODO --auto (systemd / headless)
# ══════════════════════════════════════════════════════════════════════════════

def modo_auto(cfg: dict):
    """Roda o sensor direto sem menu — ideal para systemd."""
    print(f"[{_agora()}] JG-Sensor v{VERSION} iniciando em modo automático...")
    print(f"[{_agora()}] Jarvis : {cfg['jarvis_url']}")
    print(f"[{_agora()}] Sensor : {cfg['sensor_nome']}")
    print(f"[{_agora()}] Eve    : {cfg['eve_path']}")

    if not cfg["jarvis_url"]:
        print(f"[{_agora()}] ERRO: URL do Jarvis não configurada. Execute sem --auto primeiro.")
        sys.exit(1)

    if not os.path.exists(cfg["eve_path"]):
        print(f"[{_agora()}] ERRO: eve.json não encontrado: {cfg['eve_path']}")
        sys.exit(1)

    with _stats_lock:
        _stats["rodando"] = True

    # Heartbeat simples no stdout
    def heartbeat():
        while True:
            time.sleep(30)
            with _stats_lock:
                s = _stats["seen"]
                e = _stats["sent"]
                er = _stats["erros"]
            print(f"[{_agora()}] heartbeat | vistos={s} | enviados={e} | erros={er}", flush=True)

    t_hb = threading.Thread(target=heartbeat, daemon=True)
    t_hb.start()

    try:
        _loop_sensor(cfg)
    except KeyboardInterrupt:
        print(f"\n[{_agora()}] Sensor encerrado.")
        sys.exit(0)


# ══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

def main():
    cfg = carregar_config()

    # Modo automático (systemd)
    if "--auto" in sys.argv:
        modo_auto(cfg)
        return

    # Primeira execução → wizard
    if not cfg.get("configurado"):
        cfg = wizard(cfg)

    # Menu principal
    menu_principal(cfg)


if __name__ == "__main__":
    main()