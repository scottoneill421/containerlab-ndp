import logging 
import subprocess
from pathlib import Path

logger = logging.getLogger("RemoteDeployer")

class RemoteDeployer:
    def __init__(self, guest_ip: str, remote_user: str = "root"):
        self.guest_ip = guest_ip
        self.remote_user = remote_user

    def _run_ssh(self, command: str) -> str:
        """Executes a remote command via SSH"""
        cmd = [
            "ssh",
            "-o", "StrictHostKeyChecking=no",
            f"{self.remote_user}@{self.guest_ip}",
            command
        ]
        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"SSH command failed on {self.guest_ip} (exit code {e.returncode}).\n"
                f"Command: {' '.join(cmd)}\n"
                f"STDOUT:\n{e.stdout}\n"
                f"STDERR:\n{e.stderr}"
            )

    def transfer_manifest(self, workspace_dir: Path, remote_dest: str = "/root/fabric.clab.yml") -> str:
        """Securly copy the compiled topology file to the remote node."""
        clab_file = workspace_dir / "fabric.clab.yml"
        if not clab_file.exists():
            raise FileNotFoundError(f"Compiler topology manifest missing: {clab_file}")

        logger.info(f"Transferring {clab_file.name} to {self.remote_user}@{self.guest_ip}:{remote_dest}...")

        cmd = [
            "scp",
            "-o", "StrictHostKeyChecking=no",
            str(clab_file),
            f"{self.remote_user}@{self.guest_ip}:{remote_dest}"
        ]

        try:
            subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )
            logger.info("Manifest transfer completed successfully.")
            return remote_dest
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"SCP transfer failed to {self.guest_ip} (exit code {e.returncode}).\n"
                f"STDOUT:\n{e.stdout}\n"
                f"STDERR:\n{e.stderr}"
            )


    def deploy_topology(self, remote_path: str = "/root/fabric.clab.yml") -> None:
        """Trigger containerlab deployment on the remote hypervisor/guest"""
        logger.info(f"Triggering containerlab deploy on remote target using '{remote_path}'...")

        deploy_cmd = f"containerlab deploy --topo {remote_path} --reconfigure"
        output = self._run_ssh(deploy_cmd)

        logger.info(f"Containerlab execution output:\n{output}")
