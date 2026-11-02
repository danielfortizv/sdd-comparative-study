"""Expand the installed native Gemini command without losing multiline args.

The headless slash parser in the pinned CLI keeps only its first physical line.
This helper reads the original Spec Kit TOML prompt and substitutes its declared
{{args}} slots exactly, leaving the native workflow instructions unchanged.
"""

import argparse
import tomllib
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--request", required=True)
parser.add_argument("--commands", required=True)
parser.add_argument("--output", required=True)
args = parser.parse_args()
request = Path(args.request).read_text(encoding="utf-8-sig")
command, separator, arguments = request.partition(" ")
if not command.startswith("/speckit.") or not separator:
    raise ValueError("Expected a native Spec Kit command with arguments")
template_path = Path(args.commands) / (command.removeprefix("/") + ".toml")
template = tomllib.loads(template_path.read_text(encoding="utf-8-sig"))["prompt"]
if "{{args}}" not in template:
    raise ValueError("Native command does not declare an argument slot")
Path(args.output).write_text(template.replace("{{args}}", arguments), encoding="utf-8")
print(f"Expanded {command} from the installed TOML; multiline arguments preserved.")
