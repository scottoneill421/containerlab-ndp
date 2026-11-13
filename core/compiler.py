from dataclasses import (
    dataclass,
    field,
)

from jinja2 import (
    Environment, 
    FileSystemLoader,
    TemplateNotFound,
    TemplateSyntaxError,
    UndefinedError,
)

from logging import(
    basicConfig,
    ERROR,
    getLogger,
)

from pathlib import Path

from yaml import (
    safe_load,
    YAMLError,
)

basicConfig(level=ERROR)
logger = getLogger("TopologyCompiler")

@dataclass
class LabSpec:
    "Dataclass resembling the user's intent manifest"
    lab_id: str
    topology_type: str
    parameters: dict = field(default_factory=dict)

    @classmethod
    def from_file(cls, manifest_path: Path) -> "LabSpec":
        path = Path(manifest_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"Lab specification manifest not found at: {path}")

        try:
            data = safe_load(path.read_text(encoding="utf-8")) or {}
        except YAMLError as exc:
            if hasattr(exc, "problem_mark"):
                mark = exc.problem_mark
                raise ValueError(f"YAML syntax error at Line {mark.line + 1}, Column {mark.column + 1}: {exc}")
            raise ValueError(f"Error parsing YAML file: {exc}")
    
        required_keys = {"lab_id", "topology_type"}
        missing = required_keys - data.keys()
        if missing:
            raise ValueError(f"Invalid lab spec manifest. Missing required fields: {missing}")

        return cls(
            lab_id=data["lab_id"],
            topology_type=data["topology_type"],
            parameters=data.get("parameters", {})
        )

class TopologyCompiler:
    def __init__(self, manifest_path: Path, template_dir: str = "templates"):
        self.spec = LabSpec.from_file(manifest_path)
        self.env = Environment(loader=FileSystemLoader(template_dir))
    
    def _render_template(self) -> str:
        template_file = f"{self.spec.topology_type}.clab.yml.j2"
        context = {"lab_id": self.spec.lab_id, **self.spec.parameters}

        try:
            template = self.env.get_template(template_file)
            return template.render(context)
        except TemplateNotFound:
            raise FileNotFoundError(f"Missing template file '{template_file}' in templates/ directory.")
        except TemplateSyntaxError as e:
            raise SyntaxError(f"Malformed template syntax in '{e.filename}' on line {e.lineno}: {e.message}")
        except UndefinedError as e:
            raise RuntimeError("Template rendering error - undefined variable: {e.message}")

    def _write_output(self, rendered_yaml: str) -> Path:
        output_path = Path(f"manifests/workspace-{self.spec.lab_id}/fabric.clab.yml").resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered_yaml, encoding="utf-8")

        logger.info(f"[+] Compiled topology '{self.spec.topology_type}' for lab '{self.spec.lab_id}' -> {output_path}")
        return output_path

    def compile(self) -> Path:
        rendered_yaml = self._render_template()
        return self._write_output(rendered_yaml)
