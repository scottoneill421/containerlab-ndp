import logging
import sys
from pathlib import Path
from core.compiler import TopologyCompiler
from core.context import LabContext
from core.provisioner import LabProvisioner
from core.deployer import RemoteDeployer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("NDPOrchestrator")

def main():
    lab_id = "ai-fabric-mvp-01"

    # 1. Context
    logger.info("[*] Resolving runtime context...")
    try:
        ctx = LabContext.from_environment(lab_id)
    except Exception as e:
        logger.error(f"Context initialization failed: {e}")
        sys.exit(1)

    # 2. Compile
    logger.info("[*] Compiling topology specification...")
    spec_path = Path("labs/lab-spec.yaml")
    compiler = TopologyCompiler(spec_path)
    compiler.compile()
    workspace_dir = Path(f"manifests/workspace-{compiler.spec.lab_id}").resolve()

    # 3. Provision Infrastructure via Terraform
    logger.info("[*] Provisioning infrastructure...")
    provisioner = LabProvisioner(compiler.spec, context=ctx)
    try:
        outputs = provisioner.apply()
        engine_ip = outputs.get("engine_ip")
        logger.info(f"[+] Engine VM online at IP: {engine_ip}")
    except Exception as e:
        logger.error(f"Provisioning failed:\n{e}")
        sys.exit(1)

    # 4. Deploy Containerlab Topology to Engine Guest
    logger.info("[*] Deploying containerlab topology to remote engine...")
    deployer = RemoteDeployer(guest_ip=engine_ip, remote_user="sysadmin")
    try:
        deployer.transfer_manifest(workspace_dir)
        deployer.deploy_topology()
        logger.info("[+] Containerlab topology deployed successfully!")
    except Exception as e:
        logger.error(f"Topology deployment failed:\n{e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
