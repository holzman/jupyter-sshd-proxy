import os
import shutil
import subprocess

from typing import Any, Dict

HOSTKEY_PATH = os.path.expanduser('~/.ssh/jupyter_sshd_hostkey')
AUTHORIZED_KEYS_PATH = os.environ.get('JUPYTER_SSHD_PROXY_AUTHORIZED_KEYS_PATH', '.ssh/authorized_keys .ssh/authorized_keys2')
SSHD_LOG_LEVEL = os.environ.get('JUPYTER_SSHD_PROXY_LOG_LEVEL', 'INFO')

def is_current_user_allowed():
    try:
        allowed_uids = map(int, os.environ.get("ALLOWED_JSP_UIDS", '').split(','))
        return os.getuid() in allowed_uids
    except Exception:
        print("Error parsing ALLOWED_JSP_UIDS")
        return False

def setup_sshd() -> Dict[str, Any]:
    if not is_current_user_allowed():
        return { "command" : ['echo', 'Permission denied'], "launcher_entry": False }

    if not os.path.exists(HOSTKEY_PATH):
        # Create a per-user hostkey if it does not exist
        os.makedirs(os.path.dirname(HOSTKEY_PATH), mode=0o700, exist_ok=True)
        subprocess.check_call(['ssh-keygen', '-f', HOSTKEY_PATH, '-q', '-N', ''])

    sshd_path = shutil.which('sshd')

    cmd = [
        sshd_path, '-h', HOSTKEY_PATH, '-D', '-e',
        # Intentionally have sshd ignore global config
        '-f', 'none',
        '-o', 'ListenAddress 127.0.0.1:{port}',
        '-o', 'PidFile none',
        # Last login info is from /var/log/lastlog, which is transient in containerized systems
        '-o', 'PrintLastLog no',
        '-o', 'StrictModes no',
        '-o', f'AuthorizedKeysFile {AUTHORIZED_KEYS_PATH}',
        '-o', f'LogLevel {SSHD_LOG_LEVEL}',
        # Default to enabling sftp
        '-o', 'Subsystem    sftp    internal-sftp'

    ]

    return {
        "command": cmd,
        "raw_socket_proxy": True,
        "timeout": 60,
        "launcher_entry": {"enabled": False},
    }
