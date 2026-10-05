"""Repair Python venv launchers after moving Stage 1 from Moviles to Proyecto.

Only virtual-environment metadata and generated console launchers are changed.
Application and experiment source files are left untouched.
"""

from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
OLD_ROOT = Path(r"D:\KEVIN\UNIVERSIDAD\Trabajos\Moviles\Caso 2-Tetris\Etapa 1")
ENVS = (
    Path("_toolchain/venv"),
    Path("OpenSpec/backend/venv"),
    Path("Tessl/backend/.venv"),
)

REBUILD_LAUNCHERS = r"""
from importlib.metadata import entry_points
from pathlib import Path
from pip._vendor.distlib.scripts import ScriptMaker
import sys

scripts = Path(sys.executable).parent
maker = ScriptMaker(None, str(scripts))
maker.executable = sys.executable
maker.clobber = True
maker.variants = {''}
count = 0
for ep in entry_points(group='console_scripts'):
    maker.make(f'{ep.name} = {ep.value}')
    count += 1
print(f'{scripts}: regenerated {count} console launchers')
"""


def main() -> None:
    if not ROOT.is_dir() or ROOT == OLD_ROOT:
        raise RuntimeError(f"Unexpected project root: {ROOT}")

    old = str(OLD_ROOT).encode("utf-8")
    new = str(ROOT).encode("utf-8")
    for relative in ENVS:
        venv = ROOT / relative
        python = venv / "Scripts" / "python.exe"
        if not python.is_file():
            raise FileNotFoundError(python)

        for metadata in (venv / "pyvenv.cfg", venv / "Scripts" / "activate.bat"):
            original = metadata.read_bytes()
            updated = original.replace(old, new)
            if updated != original:
                metadata.write_bytes(updated)
                print(f"Updated {metadata.relative_to(ROOT)}")

        subprocess.run([str(python), "-c", REBUILD_LAUNCHERS], check=True)


if __name__ == "__main__":
    main()
