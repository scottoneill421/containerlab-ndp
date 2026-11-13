from pathlib import Path
from core.compiler import LabSpec
from core.provisioner import LabProvisioner

spec = LabSpec(
    lab_id="ai-fabric-mvp-01",
    topology_type="clos_spine_leaf",
    parameters={"spine_count": 2, "leaf_count": 4, "host_count": 4}
)

provisioner = LabProvisioner(spec)
print(f"[+] Provisioner initialized successfully!")
print(f"[+] Resolved Workspace: {provisioner.workspace_dir}")
print(f"[+] Detected Binary: {provisioner.tf_bin}")
