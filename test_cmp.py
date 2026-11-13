from pathlib import Path
from core.compiler import TopologyCompiler

compiler = TopologyCompiler(Path("labs/lab-spec.yaml"))
output_path = compiler.compile()
