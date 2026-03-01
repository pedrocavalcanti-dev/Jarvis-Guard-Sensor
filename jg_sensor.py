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
#  Jarvis Guard Sensor — Agent v2.0
#  github.com/pedrocavalcanti-dev/Jarvis-Guard-Sensor
#
# =============================================================================

import sys

from nucleo.configuracao import carregar_config
from nucleo.interface    import wizard, menu_principal
from nucleo.monitoramento import modo_auto


def main():
    cfg = carregar_config()

    # Modo automático para systemd / headless
    if "--auto" in sys.argv:
        modo_auto(cfg)
        return

    # Primeira execução → wizard de configuração
    if not cfg.get("configurado"):
        cfg = wizard(cfg)

    # Menu principal
    menu_principal(cfg)


if __name__ == "__main__":
    main()