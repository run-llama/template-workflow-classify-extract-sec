"""
Script to export pydantic types from a python file (default "schemas.py") to json schemas and then to typescript interfaces.

For sharing types precisely between python and typescript
"""

import importlib.util
import inspect
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import jsonref
from pydantic import BaseModel
import click


def run_command(cmd: str):
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print(f"Command failed: {cmd}", file=sys.stderr)
        sys.exit(result.returncode)


@click.command()
@click.option(
    "--schema-file",
    default="schemas.py",
    help="The name of the model file to export types from",
)
def export_types(schema_file: str):
    app_path = Path(__file__).parent.parent.parent
    print("Exporting types...")
    schema_path = Path(__file__).parent / schema_file
    if not schema_path.exists():
        raise click.BadParameter(f"Schema file '{schema_file}' not found in app")
    print(f"Exporting types from {schema_path}...")
    output_dir = app_path / "ui" / "src" / "schemas"
    if output_dir.exists():
        shutil.rmtree(output_dir)
    os.makedirs(output_dir)
    export_schemas(schema_path, output_dir)
    generate_typescript_interfaces(output_dir)


def generate_typescript_interfaces(schema_dir: Path):
    run_command(
        f"npx -y json-schema-to-typescript@15.0.4 -i '{schema_dir / '*.json'}' -o {schema_dir} --additionalProperties=false"
    )


def load_module_from_path(module_name: str, file_path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise ValueError(f"Failed to load module from {file_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def export_schemas(py_file: Path, output_dir: Path):
    module_name = os.path.splitext(os.path.basename(py_file))[0]
    module = load_module_from_path(module_name, py_file)
    os.makedirs(output_dir, exist_ok=True)
    for name, obj in inspect.getmembers(module):
        if inspect.isclass(obj) and issubclass(obj, BaseModel) and obj is not BaseModel:
            schema = obj.model_json_schema()
            normalized_schema = jsonref.replace_refs(schema, proxies=False)
            with open(os.path.join(output_dir, f"{name}.json"), "w") as f:
                f.write(json.dumps(normalized_schema, indent=2))
            print(f"Exported {name} to {name}.json")


if __name__ == "__main__":
    export_types()
