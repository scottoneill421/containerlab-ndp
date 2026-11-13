import json
import os
import shutil
import subprocess

from logging import (
    getLogger,
    basicConfig,
    ERROR,
)

from pathlib import Path
from core.compiler import LabSpec
from core.context import LabContext

basicConfig(level=ERROR)
logger = getLogger("Lab Provisioner")

class LabProvisioner:
    def __init__(self, spec: LabSpec, context: LabContext, base_workspace_dir: str = "manifests"):
        self.spec = spec
        self.ctx = context

        self.remote_image_path = "/var/lib/libvirt/golden-containerlab-base.qcow2"
        self.local_image_path = Path("packer/output-images/golden-containerlab-base.qcow2")

        self.workspace_dir = Path(base_workspace_dir).resolve() / f"workspace-{spec.lab_id}"

        self.tf_bin = shutil.which("terraform") or shutil.which("tofu")
        if not self.tf_bin:
            raise FileNotFoundError("Neither 'terraform' nor 'tofu' binary found in system PATH.")

    def _build_local_base_image(self):
        """Build the Packer golden image"""
        logger.info("[*] Building golden base image via Packer...")
        packer_dir = Path("packer").resolve()
        
        packer_bin = shutil.which("packer")
        if not packer_bin:
            raise FileNotFoundError("Packer binary not found in system PATH.")

        # Initialize and build via Packer
        subprocess.run([packer_bin, "init", "ubuntu-base.pkr.hcl"], cwd=packer_dir, check=True)
        subprocess.run([packer_bin, "build", "ubuntu-base.pkr.hcl"], cwd=packer_dir, check=True)
        logger.info("[+] Golden base image built successfully via Packer.")

    def _ensure_remote_base_image(self):
        logger.info(f"[*] Checking of base image exists on {self.ctx.remote_host}...")

        check_cmd = [
            "ssh", 
            f"{self.ctx.ssh_user}@{self.ctx.remote_host}",
            f"sudo test -f {self.remote_image_path} && sudo stat -c%s {self.remote_image_path}"
        ]
        res = subprocess.run(check_cmd, capture_output=True, text=True)

        image_ready = False
        if res.returncode == 0 and res.stdout.strip().isdigit():
            size = int(res.stdout.strip())
            if size > 1024 * 1024:
                logger.info(f"[+] Base image already present on remote hypervisor ({size} bytes).")
                image_ready = True

        if not image_ready:
            logger.info(f"[*] Base image missing on remote. Checking local image...")
            
            # AUTOMATIC BUILD: If local image is missing, build it via Packer right now
            if not os.path.exists(self.local_image_path):
                self._build_local_base_image()

            if not os.path.exists(self.local_image_path):
                raise FileNotFoundError(f"Local golden base image still not found at {self.local_image_path} after Packer build.")

            logger.info(f"[*] Streaming local base image to {self.ctx.remote_host} via SSH/sudo...")
            with open(self.local_image_path, "rb") as f:
                upload_cmd = [
                    "ssh",
                    f"{self.ctx.ssh_user}@{self.ctx.remote_host}",
                    f"sudo tee {self.remote_image_path} > /dev/null"
                ]
                subprocess.run(upload_cmd, stdin=f, check=True)

            logger.info("[+] Successfully streamed base image to {self.ctx.remote_host}:{self.remote_image_path}")


    def _run_tf(self, args: list[str]) -> str:
        """Executes a terraform command inside the isolated lab workspace"""
        cmd = [self.tf_bin] + args
        try:
            result = subprocess.run(
                cmd,
                cwd=self.workspace_dir,
                env=self.ctx.to_tf_env(),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True,
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"Terraform command '{' '.join(cmd)}' failed with exit code {e.returncode}.\n"
                f"STDOUT:\n{e.stdout}\n"
                f"STDERR:\n{e.stderr}"
            )

    def init(self) -> None:
        """Initialise terraform workspace if not already initialised"""
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        central_manifests = Path("manifests").resolve()

        for src_file in central_manifests.iterdir():
            if src_file.is_file() and not src_file.name.startswith("workspace-"):
                dest_link = self.workspace_dir / src_file.name
                if not dest_link.exists() and not dest_link.is_symlink():
                    dest_link.symlink_to(src_file)

        if not (self.workspace_dir / ".terraform").exists():
            logger.info(f"[*] Initialising Terraform workspace for lab '{self.spec.lab_id}'...")
            self._run_tf(["init", "-input=false"])


    def apply(self) -> dict:
        """Provisions the KVM/Containerlab stack and returns parsed outputs"""
        self._ensure_remote_base_image()
        self.init()
        logger.info(f"[*] Provisioning infrastructure for lab '{self.spec.lab_id}' via Terraform...")

        self._run_tf([
            "apply", 
            "-auto-approve", 
            "-input=false",
        ])

        return self.get_outputs()

    def get_outputs(self) -> dict:
        """Extracts outputs from Terraform into a Py Dict"""
        output_json = self._run_tf(["output", "-json"])
        try:
            raw_outputs = json.loads(output_json)
            return {k: v["value"] for k, v in raw_outputs.items()}
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse Terraform outputs as JSON: {e}")

    def destroy(self) -> None:
        """Tears down KVM/Containerlab stack"""
        self.init()
        logger.info(f"[*] Teaing down infrastructure for lab '{self.spec.lab_id}'...")
        
        self._run_tf([
            "destroy", 
            "-auto-approve", 
            "-input=false",
        ])
