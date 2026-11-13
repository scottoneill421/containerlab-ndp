import getpass
import os
from dataclasses import dataclass

@dataclass
class LabContext:
    lab_id: str
    ssh_user: str
    ssh_pubkey: str
    remote_host: str = "172.16.32.2"

    @classmethod
    def from_environment(cls, lab_id: str) -> "LabContext":
        ssh_user = os.environ.get("LAB_SSH_USER") or getpass.getuser()
        pubkey_path = os.path.expanduser("~/.ssh/id_ed25519.pub")

        if not os.path.exists(pubkey_path):
            raise FileNotFoundError(f"SSH public key missing for user {ssh_user} at {pubkey_path}")

        with open(pubkey_path, "r") as f:
            pubkey_content = f.read().strip()

        return cls(
            lab_id=lab_id,
            ssh_user=ssh_user,
            ssh_pubkey=pubkey_content
        )

    def to_tf_env(self) -> dict:
        env = os.environ.copy()
        env["TF_VAR_lab_id"] = self.lab_id
        env["TF_VAR_ssh_user"] = self.ssh_user
        env["TF_VAR_ssh_pubkey"] = self.ssh_pubkey
        return env
