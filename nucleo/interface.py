import os
import sys
import requests
from colorama import init, Fore, Style

from nucleo.configuracao import (
    VERSION, SEVERIDADE_MAP, SEVERIDADE_LABEL,
    carregar_config, salvar_config,
)

init(autoreset=True)

# ══════════════════════════════════════════════════════════════════════════════
# CORES
# ══════════════════════════════════════════════════════════════════════════════

C_TITULO   = Fore.CYAN + Style.BRIGHT
C_BORDA    = Fore.CYAN
C_OK       = Fore.GREEN + Style.BRIGHT
C_ERRO     = Fore.RED + Style.BRIGHT
C_AVISO    = Fore.YELLOW + Style.BRIGHT
C_DIM      = Fore.WHITE + Style.DIM
C_NORMAL   = Style.RESET_ALL
C_DESTAQUE = Fore.WHITE + Style.BRIGHT
C_MENU_TXT = Fore.WHITE

LARGURA = 52

# ══════════════════════════════════════════════════════════════════════════════
# PRIMITIVOS VISUAIS
# ══════════════════════════════════════════════════════════════════════════════

def limpar():
    os.system("cls" if os.name == "nt" else "clear")


def topo():
    print(C_BORDA + "╔" + "═" * (LARGURA - 2) + "╗")


def fundo():
    print(C_BORDA + "╚" + "═" * (LARGURA - 2) + "╝")


def separador():
    print(C_BORDA + "╠" + "═" * (LARGURA - 2) + "╣")


def linha_vazia():
    print(C_BORDA + "║" + " " * (LARGURA - 2) + "║")


def linha_texto(texto: str, cor=C_NORMAL, alinhamento: str = "esquerda", pad: int = 2):
    espaco = LARGURA - 2 - pad * 2
    if alinhamento == "centro":
        t = texto.center(espaco)
    elif alinhamento == "direita":
        t = texto.rjust(espaco)
    else:
        t = texto.ljust(espaco)
    t_limpo = t[:espaco]
    print(
        C_BORDA + "║" + " " * pad
        + cor + t_limpo
        + C_BORDA + " " * (espaco - len(t_limpo) + pad) + "║"
    )


def print_resultado(ok: bool, msg: str):
    icone = C_OK + "✔" if ok else C_ERRO + "✗"
    print(C_BORDA + "║  " + icone + " " + (C_OK if ok else C_ERRO) + msg)


def input_campo(prompt: str, valor_atual: str = "") -> str:
    sufixo = f" [{valor_atual}]" if valor_atual else ""
    print(C_BORDA + "║  " + C_AVISO + f"▶ {prompt}{sufixo}: " + C_DESTAQUE, end="")
    try:
        val = input().strip()
    except (KeyboardInterrupt, EOFError):
        val = ""
    return val if val else valor_atual


def input_senha(prompt: str) -> str:
    """Lê senha sem exibir no terminal."""
    import getpass
    print(C_BORDA + "║  " + C_AVISO + f"▶ {prompt}: " + C_DESTAQUE, end="", flush=True)
    try:
        val = getpass.getpass("")
    except (KeyboardInterrupt, EOFError):
        val = ""
    return val.strip()


def aguardar_enter(msg: str = "Pressione Enter para continuar..."):
    print(C_BORDA + "║  " + C_DIM + msg + C_NORMAL)
    try:
        input()
    except (KeyboardInterrupt, EOFError):
        pass


# ══════════════════════════════════════════════════════════════════════════════
# STATUS DE CONEXÃO
# ══════════════════════════════════════════════════════════════════════════════

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


# ══════════════════════════════════════════════════════════════════════════════
# LOGIN NO JARVIS GUARD
# ══════════════════════════════════════════════════════════════════════════════

def _fazer_login(jarvis_url: str, usuario: str, senha: str) -> tuple[bool, str]:
    """
    Faz login no Jarvis Guard e retorna (ok, mensagem_erro).

    O Django usa sessão com cookie. Precisamos:
      1. GET /auth/login/  → pega o csrftoken do cookie
      2. POST /auth/login/ → envia usuário + senha + csrftoken
      3. Verifica se a resposta redireciona para o dashboard (login OK)

    Retorna (True, "") se autenticado, (False, mensagem) se falhou.
    """
    session = requests.Session()
    login_url = jarvis_url.rstrip("/") + "/auth/login/"

    try:
        # Passo 1: GET para pegar o CSRF
        r = session.get(login_url, timeout=5)
        csrf = session.cookies.get("csrftoken", "")
        if not csrf:
            # Tenta extrair do HTML (fallback)
            import re
            m = re.search(r'csrfmiddlewaretoken.*?value="([^"]+)"', r.text)
            csrf = m.group(1) if m else ""

        # Passo 2: POST com credenciais
        r2 = session.post(
            login_url,
            data={
                "username":          usuario,
                "password":          senha,
                "csrfmiddlewaretoken": csrf,
            },
            headers={"Referer": login_url},
            timeout=5,
            allow_redirects=True,
        )

        # Login OK = redirecionou para o dashboard (não voltou para /auth/login/)
        if "/auth/login/" not in r2.url and r2.status_code == 200:
            return True, ""

        # Ainda na página de login = credenciais erradas
        if "Usuário ou senha incorretos" in r2.text or "credenciais" in r2.text.lower():
            return False, "Usuário ou senha incorretos."

        # Redirecionou mas não sabemos para onde — considera OK se não for login
        if r2.status_code == 200 and "/auth/login/" not in r2.url:
            return True, ""

        return False, f"Login falhou (HTTP {r2.status_code}). Verifique as credenciais."

    except requests.exceptions.ConnectionError:
        return False, "Não foi possível conectar ao Jarvis Guard."
    except Exception as e:
        return False, f"Erro ao fazer login: {e}"


# ══════════════════════════════════════════════════════════════════════════════
# CABEÇALHO
# ══════════════════════════════════════════════════════════════════════════════

def cabecalho(cfg: dict):
    limpar()
    topo()
    linha_texto("JARVIS GUARD — SENSOR", C_TITULO, "centro")
    linha_texto(f"v{VERSION}  ·  github.com/pedrocavalcanti-dev", C_DIM, "centro")
    separador()
    status_str, status_cor = _status_conexao(cfg)
    linha_texto(f"Status  : {status_str}", status_cor)
    linha_texto(f"Jarvis  : {cfg['jarvis_url'] or '(não configurado)'}", C_DIM)
    linha_texto(f"Sensor  : {cfg['sensor_nome']}", C_DIM)
    linha_texto(f"Eve.json: {cfg['eve_path']}", C_DIM)
    separador()


# ══════════════════════════════════════════════════════════════════════════════
# WIZARD — primeira execução
# ══════════════════════════════════════════════════════════════════════════════

def wizard(cfg: dict) -> dict:
    limpar()
    topo()
    linha_texto("JARVIS GUARD — SENSOR  SETUP", C_TITULO, "centro")
    linha_texto("Primeira execução detectada!", C_AVISO, "centro")
    separador()
    linha_texto("Vamos configurar o sensor em 4 passos.", C_NORMAL)
    linha_vazia()

    # ── PASSO 1 — URL do Jarvis ───────────────────────────────────────────────
    linha_texto("PASSO 1 de 4 — URL do Jarvis Guard", C_DESTAQUE)
    linha_texto("Ex: http://192.168.0.105:8000", C_DIM)
    linha_vazia()

    while True:
        url = input_campo("URL do Jarvis Guard")
        if not url:
            print_resultado(False, "URL obrigatória.")
            continue
        if not url.startswith("http"):
            url = "http://" + url
        url = url.rstrip("/")
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

    # ── PASSO 2 — Login no Jarvis Guard ──────────────────────────────────────
    linha_texto("PASSO 2 de 4 — Login no Jarvis Guard", C_DESTAQUE)
    linha_vazia()
    linha_texto("  Para que serve: o sensor precisa se autenticar", C_DIM)
    linha_texto("  no Jarvis para enviar eventos com segurança.", C_DIM)
    linha_texto("  Use o mesmo usuário e senha do painel web.", C_DIM)
    linha_vazia()

    tentativas = 0
    while True:
        usuario = input_campo("Usuário do Jarvis Guard", cfg.get("jarvis_usuario", ""))
        senha   = input_senha("Senha do Jarvis Guard")

        if not usuario or not senha:
            print_resultado(False, "Usuário e senha são obrigatórios.")
            continue

        linha_vazia()
        linha_texto("Verificando credenciais...", C_DIM)
        ok, erro = _fazer_login(cfg["jarvis_url"], usuario, senha)

        if ok:
            print_resultado(True, f"Login bem-sucedido! Olá, {usuario}.")
            cfg["jarvis_usuario"] = usuario
            cfg["jarvis_senha"]   = senha  # salvo para reconexão automática
            break
        else:
            tentativas += 1
            print_resultado(False, erro)
            if tentativas >= 3:
                linha_texto("3 tentativas falhas. Continuando sem login.", C_AVISO)
                linha_texto("O sensor pode falhar ao enviar eventos.", C_DIM)
                cfg["jarvis_usuario"] = usuario
                cfg["jarvis_senha"]   = ""
                break
            tentar = input_campo("Tentar novamente? (s/n)", "s")
            if tentar.lower() != "s":
                cfg["jarvis_usuario"] = usuario
                cfg["jarvis_senha"]   = ""
                break

    linha_vazia()
    separador()

    # ── PASSO 3 — Nome do sensor ──────────────────────────────────────────────
    linha_texto("PASSO 3 de 4 — Nome deste sensor", C_DESTAQUE)
    linha_texto("Ex: IDS-GATEWAY, SENSOR-LAB-01", C_DIM)
    linha_vazia()
    nome = input_campo("Nome do sensor", cfg["sensor_nome"])
    cfg["sensor_nome"] = nome or cfg["sensor_nome"]
    linha_vazia()
    separador()

    # ── PASSO 4 — Severidade ──────────────────────────────────────────────────
    linha_texto("PASSO 4 de 4 — Severidade mínima dos alertas", C_DESTAQUE)
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
    linha_texto("Configuração concluída!", C_OK, "centro")
    linha_vazia()
    linha_texto(f"Jarvis  : {cfg['jarvis_url']}", C_DIM)
    linha_texto(f"Usuário : {cfg.get('jarvis_usuario', '(não configurado)')}", C_DIM)
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
    from nucleo.monitoramento import tela_sensor

    while True:
        cabecalho(cfg)

        # Mostra usuário configurado no menu para deixar claro o estado atual
        usuario_atual = cfg.get("jarvis_usuario") or "(não configurado)"
        tem_senha     = bool(cfg.get("jarvis_senha"))
        cred_status   = f"{usuario_atual} {'✔' if tem_senha else '✗ sem senha'}"

        opcoes = [
            ("0", "Instalar / Configurar Suricata"),
            ("1", "Iniciar sensor"),
            ("2", "Configurar IP do Jarvis"),
            ("3", "Configurar nome do sensor"),
            ("4", "Configurar severidade mínima"),
            ("5", "Configurar caminho do eve.json"),
            ("6", "Testar conexão com Jarvis"),
            ("7", "Ver configuração atual"),
            ("8", f"Credenciais do Jarvis  ({cred_status})"),
            ("9", "Diagnóstico do sistema"),
            ("Q", "Sair"),
        ]
        for num, txt in opcoes:
            linha_texto(f"  [{num}] {txt}", C_MENU_TXT)
        linha_vazia()
        fundo()

        print(C_AVISO + "  Opção: " + C_DESTAQUE, end="")
        try:
            opcao = input().strip().upper()
        except (KeyboardInterrupt, EOFError):
            opcao = "Q"

        if opcao == "0":
            cfg = tela_instalar_suricata(cfg)
        elif opcao == "1":
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
            cfg = tela_config_credenciais(cfg)
        elif opcao == "9":
            cfg = tela_diagnostico(cfg)
        elif opcao == "Q":
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
            print_resultado(False, "Arquivo não encontrado (OK se Suricata ainda não iniciou).")
        cfg["eve_path"] = caminho
        salvar_config(cfg)
        print_resultado(True, f"Caminho salvo: {caminho}")

    linha_vazia()
    aguardar_enter()
    return cfg


def tela_testar_conexao(cfg: dict):
    import time
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

    # Teste de conectividade
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

    # Teste de login
    linha_vazia()
    linha_texto("Testando credenciais...", C_DIM)
    usuario = cfg.get("jarvis_usuario", "")
    senha   = cfg.get("jarvis_senha", "")

    if not usuario or not senha:
        print_resultado(False, "Credenciais não configuradas. Use [2] para configurar.")
    else:
        ok, erro = _fazer_login(cfg["jarvis_url"], usuario, senha)
        if ok:
            print_resultado(True, f"Login OK — usuário: {usuario}")
        else:
            print_resultado(False, f"Login falhou: {erro}")
            linha_texto("  Use a opção [2] para reconfigurar a URL e refazer o login.", C_DIM)

    # Teste do endpoint de ingestão
    linha_vazia()
    linha_texto("Testando endpoint de ingestão...", C_DIM)
    try:
        payload = {"sensor": cfg["sensor_nome"], "eventos": []}
        r2 = requests.post(
            cfg["jarvis_url"] + "/incidentes/api/ingest/",
            json=payload,
            timeout=5,
            headers={"X-JG-TOKEN": cfg.get("token", "")},
        )
        if r2.status_code == 200:
            print_resultado(True, "POST /incidentes/api/ingest/  →  HTTP 200  Pronto!")
        elif r2.status_code == 403:
            print_resultado(False, "HTTP 403 — verifique o token ou modo do Jarvis.")
        else:
            print_resultado(False, f"HTTP {r2.status_code}  →  {r2.text[:80]}")
    except Exception as e:
        print_resultado(False, f"Erro no ingest: {e}")

    linha_vazia()
    aguardar_enter()


def tela_ver_config(cfg: dict):
    cabecalho(cfg)
    linha_texto("CONFIGURAÇÃO ATUAL", C_DESTAQUE)
    linha_vazia()
    linha_texto(f"Jarvis URL    : {cfg['jarvis_url'] or '(vazio)'}", C_DIM)
    linha_texto(f"Usuário       : {cfg.get('jarvis_usuario') or '(não configurado)'}", C_DIM)
    linha_texto(f"Senha         : {'••••••••' if cfg.get('jarvis_senha') else '(não configurada)'}", C_DIM)
    linha_texto(f"Nome sensor   : {cfg['sensor_nome']}", C_DIM)
    linha_texto(f"Eve.json      : {cfg['eve_path']}", C_DIM)
    linha_texto(f"Severidade    : {SEVERIDADE_LABEL.get(cfg['min_severity'], '?')}", C_DIM)
    linha_texto(f"Batch size    : {cfg['batch_size']} eventos", C_DIM)
    linha_texto(f"Batch timeout : {cfg['batch_timeout']}s", C_DIM)
    linha_vazia()

    if os.path.exists(cfg["eve_path"]):
        from nucleo.utilitarios import tamanho_arquivo
        tam = tamanho_arquivo(cfg["eve_path"])
        print_resultado(True, f"eve.json encontrado ({tam:,} bytes)")
    else:
        print_resultado(False, "eve.json NÃO encontrado no caminho configurado.")

    linha_vazia()
    aguardar_enter()


def tela_config_credenciais(cfg: dict) -> dict:
    cabecalho(cfg)
    linha_texto("CREDENCIAIS DO JARVIS GUARD", C_DESTAQUE)
    linha_vazia()
    linha_texto("  Use o mesmo usuário e senha do painel web.", C_DIM)
    linha_texto("  As credenciais ficam salvas no config.json.", C_DIM)
    linha_vazia()

    usuario_atual = cfg.get("jarvis_usuario", "")
    tem_senha     = bool(cfg.get("jarvis_senha"))

    linha_texto(f"  Usuário atual : {usuario_atual or '(não configurado)'}", C_DIM)
    linha_texto(f"  Senha atual   : {'••••••••' if tem_senha else '(não configurada)'}", C_DIM)
    linha_vazia()

    usuario = input_campo("Novo usuário", usuario_atual)
    if not usuario:
        print_resultado(False, "Nenhuma alteração feita.")
        linha_vazia()
        aguardar_enter()
        return cfg

    senha = input_senha("Nova senha (Enter para manter atual)")

    # Se não digitou senha nova, mantém a atual
    if not senha and tem_senha:
        senha = cfg["jarvis_senha"]
        linha_texto("  Mantendo senha atual.", C_DIM)

    if not senha:
        print_resultado(False, "Senha obrigatória.")
        linha_vazia()
        aguardar_enter()
        return cfg

    linha_vazia()
    linha_texto("Verificando credenciais no Jarvis...", C_DIM)
    ok, erro = _fazer_login(cfg["jarvis_url"], usuario, senha)

    if ok:
        cfg["jarvis_usuario"] = usuario
        cfg["jarvis_senha"]   = senha
        salvar_config(cfg)
        print_resultado(True, f"Login OK! Credenciais salvas para {usuario}.")
    else:
        print_resultado(False, f"Login falhou: {erro}")
        linha_texto("  Credenciais NÃO foram salvas.", C_AVISO)
        linha_vazia()
        forcar = input_campo("Salvar mesmo assim? (s/n)", "n")
        if forcar.strip().lower() == "s":
            cfg["jarvis_usuario"] = usuario
            cfg["jarvis_senha"]   = senha
            salvar_config(cfg)
            print_resultado(True, "Credenciais salvas (sem verificação).")

    linha_vazia()
    aguardar_enter()
    return cfg


# ══════════════════════════════════════════════════════════════════════════════
# TELAS PLACEHOLDER
# ══════════════════════════════════════════════════════════════════════════════

def tela_instalar_suricata(cfg: dict):
    from suricata.instalador import executar_instalacao
    cfg = executar_instalacao(cfg)
    return cfg


def tela_diagnostico(cfg: dict):
    from suricata.diagnostico import executar_diagnostico
    cfg = executar_diagnostico(cfg)
    return cfg