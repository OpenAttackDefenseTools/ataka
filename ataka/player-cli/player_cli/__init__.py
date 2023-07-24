state = {
    'host': None,
    'bypass_tools': None,
}

import os
self_as_zip_path = os.path.dirname(os.path.dirname(__file__))

import player_cli.ctfconfig_wrapper

import player_cli.cmd_exploit
import player_cli.cmd_flag
import player_cli.cmd_service
import player_cli.root
