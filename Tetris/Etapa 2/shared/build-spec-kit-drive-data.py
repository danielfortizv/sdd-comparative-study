"""Prepare native Docs layout data from the already verified final report."""
import json
import re
from pathlib import Path
from PIL import Image

docs = Path(__file__).resolve().parent.parent / "Spec Kit/docs"
lines = (docs / "FINAL_REPORT.md").read_text(encoding="utf-8-sig").splitlines()
browser = json.loads((docs / "browser-evidence.json").read_text(encoding="utf-8"))
corpus = json.loads((docs / "bertopic-corpus/final/manifest.json").read_text(encoding="utf-8"))
blocks = []
table_number = 0
aliases = {}

def clean(text):
    return re.sub(r"\[([^]]+)\]\([^)]+\)", r"\1", text).replace("**", "").replace("`", "").replace("no disponible", "N/D")

def heading(text, page=False):
    blocks.append({"kind": "heading2", "text": text, "page_break": page})

def body(text):
    blocks.append({"kind": "body", "text": clean(text)})

def table(headers, rows, widths, title=None, page=False):
    global table_number
    if title:
        heading(title, page)
    table_number += 1
    blocks.append({"kind": "table", "id": f"t{table_number}", "headers": headers, "rows": rows, "widths": widths})

def short_ids(value):
    return "; ".join(re.findall(r"\b\d{2}(?=-)", value)) or "—"

def alias_evidence(value):
    result = []
    for path in value.split("; "):
        aliases.setdefault(path, f"E{len(aliases)+1}")
        result.append(aliases[path])
    return ", ".join(result)

i = 0
skip_capture_lines = False
while i < len(lines):
    line = lines[i].strip()
    if line.startswith("## Fuentes locales"):
        break
    if not line:
        i += 1
        continue
    if line.startswith("# "):
        blocks.append({"kind": "heading1", "text": "CIERRE VERIFICADO — SPEC KIT / TETRIS ETAPA 2 (21 oct 2026, hora Bogotá)", "page_break": True})
    elif line.startswith("## "):
        title = line[3:]
        heading(title, title.startswith(("Tamaño", "Ejecución", "Aceptación", "Capturas", "Corpus")))
        skip_capture_lines = title.startswith("Capturas")
        if skip_capture_lines:
            body("Tres capturas corresponden a la app local real después de QA-4; cuatro paneles son vistas derivadas de JSON/logs. Las tablas nativas anteriores conservan cifras legibles; los paneles permiten ampliar la evidencia. Ningún panel derivado se presenta como consola o interfaz web original de SonarQube.")
            labels = ["Interfaz real: inicio, HUD, tablero, preview y Hold vacío.", "Interfaz real: Hold ocupado y control deshabilitado antes del siguiente lock.", "Interfaz real: game over por gravedad normal y modal de reinicio."]
            for j, capture in enumerate(browser["captures"]):
                path = docs / capture["path"]
                w, h = Image.open(path).size
                scale = min(448 / w, 560 / h)
                caption = labels[j] if j < 3 else capture["caption"]
                sources = "; ".join(capture.get("raw_sources", []))
                blocks.append({"kind": "caption", "text": f"Captura {j+4}. {caption} Archivo: Spec Kit/docs/{capture['path']}." + (f" Fuentes: {sources}." if sources else "")})
                blocks.append({"kind": "image", "id": f"capture{j+4}", "path": str(path.resolve()), "width": round(w*scale, 3), "height": round(h*scale, 3)})
    elif skip_capture_lines:
        pass
    elif line.startswith("|"):
        chunk = []
        while i < len(lines) and lines[i].strip().startswith("|"):
            chunk.append([clean(x.strip()) for x in re.split(r"(?<!\\)\|", lines[i].strip())[1:-1]])
            i += 1
        headers, rows = chunk[0], chunk[2:]
        if headers == ["Sesión", "Entrada", "Caché incluida", "Salida candidata", "Pensamiento"]:
            table(headers[:3], [r[:3] for r in rows], [140,154,154], "Tokens por invocación: entrada y caché", True)
            table([headers[0], *headers[3:]], [[r[0], *r[3:]] for r in rows], [140,154,154], "Tokens por invocación: candidata y pensamiento", True)
        elif headers[:2] == ["Sesión", "Segundos"]:
            table(["Sesión", "Segundos", "API intentos", "Errores", "Éxitos", "JSONL"], rows, [132,70,65,55,60,66], "Tiempo, API y respuestas registradas", True)
            body("N/D conserva información desconocida. API = intentos incluidos errores; JSONL = respuestas únicas registradas, acotadas por intervalo y deduplicadas. Estas medidas no se suman.")
        elif headers[0] == "Categoría registrada":
            names = ["Especificación inicial", "Reintento de especificación", "Corrección previa de specs", "Plan nativo", "Tareas nativas", "Reintentos de tareas", "Implementación inicial", "Correcciones externas posteriores"]
            rows = [[names[j], r[1], r[2], short_ids(r[3])] for j,r in enumerate(rows)]
            table(["Categoría", "Intentos", "Con modelo", "IDs"], rows, [182,60,75,131], "Categorías de invocación")
        elif headers[0] == "Intención QA":
            rows = [[r[0], short_ids(r[1]), short_ids(r[2]), short_ids(r[3])] for r in rows]
            table(headers, rows, [70,140,130,108], "Intentos y resultados por intención QA")
        elif headers[0] == "Comprobación":
            commands = ["python -m pytest con cobertura XML", "npm run test -- --coverage", "npm run build", "npm audit --json"]
            logs = ["backend-coverage.log", "frontend-test-coverage.log", "frontend-build.log", "npm-audit.json"]
            table(["Comprobación", "Comando (resumen)", "Salida; estado"], [[r[0], commands[j], logs[j]+"; exit 0"] for j,r in enumerate(rows)], [148,162,138])
            body("Las rutas, argumentos completos, directorios de ejecución y horas están en verification-commands.json. Los resúmenes de comandos anteriores no sustituyen ese registro original.")
        elif headers[0] == "ID":
            rows = [[r[0], "OK", r[2].replace("_", " "), alias_evidence(r[3])] for r in rows]
            for offset in (0,10):
                table(["ID", "Estado", "Mecanismo", "Fuentes"], rows[offset:offset+10], [48,40,245,115], f"Aceptación S2-{offset+1:02} a S2-{offset+10:02}", True)
            body("Alias de evidencia (rutas relativas a Spec Kit o Spec Kit/docs, según el archivo):")
            for path, label in aliases.items():
                body(f"{label}: {path}")
        elif headers[0] == "Alcance":
            table(headers, rows, [140,50,70,100,88])
        elif headers[0] == "Comparación":
            table(["Comparación", "Archivos", "+ / − líneas", "Neto líneas", "Neto caracteres"], rows, [140,55,85,70,98])
        elif headers[0].startswith("Medida Sonar"):
            rows.insert(2,["Cobertura nueva (%)", "N/D", "47,3", "86,6"])
            table(["Medida Sonar", "Línea base", "Inicial Etapa 2", "Final"], rows, [160,96,96,96])
        else:
            table(headers, rows, [115,120,125,88])
        continue
    else:
        body(line[2:] if line.startswith("- ") else line)
        if line.startswith("Preguntas bloqueantes observadas"):
            body("Se revisaron 21 mensajes naturales únicos. Catorce intentos cerrados contienen aclaraciones del investigador, doce con entrega verificada; 05 perdió argumentos y 06 falló antes del modelo. Ninguna fue respuesta a una pregunta bloqueante observada. Se excluyen pensamientos, herramientas, avisos sintéticos, plantillas y signos de pregunta dentro de código.")
        if line.startswith("El corpus final incluye"):
            body(f"Corpus: ocho archivos Markdown; {corpus['unified_characters']:,} caracteres en unified.md. SHA-256 UTF-8/LF: {corpus['unified_utf8_sha256']}. Generaciones 08 y 16 permanecen como snapshots separados.")
    i += 1

data = {"document_id": "1JRZvjK8-fdFitwbiKLe2NhOsk1FZNCa_TclgnFwdjao", "blocks": blocks}
(docs / "drive-final-data.json").write_text(json.dumps(data, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
print(json.dumps(data, ensure_ascii=True))
