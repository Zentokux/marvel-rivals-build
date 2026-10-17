"""Validador del proyecto MARVEL RIVALS BUILD (lo ejecuta optimo-razonamiento-ia tras cada cambio y al terminar).

Comprueba las reglas del usuario:
  1. Cada guía (.md, salvo README) tiene una sección «Fuentes» y cada fuente lleva fecha.
  2. Solo vale información del mes actual: una fuente con fecha de un mes anterior
     tiene que decir que algo de este mes la confirma («confirmado …»).
  3. Los .json se pueden leer.
Salida 0 = todo bien. Otro código = Claude recibe la lista de errores y los corrige.
"""

import datetime
import json
import os
import re
import sys

RAIZ = os.path.dirname(os.path.abspath(__file__))
FASE = os.environ.get("ORIA_PHASE", "stop")
CAMBIADOS = [p for p in os.environ.get("ORIA_CHANGED_FILES", "").splitlines() if p.strip()]
TEXTO = (".md", ".html", ".js", ".json", ".csv", ".txt")

MESES = {"ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6, "jul": 7, "ago": 8, "sep": 9, "oct": 10, "nov": 11, "dic": 12}
FECHA = re.compile(r"\b(\d{1,2})[-/ ](ene|feb|mar|abr|may|jun|jul|ago|sep|oct|nov|dic)[a-z]*\.?[-/ ](20\d\d)\b|\b(20\d\d)-(\d{2})-(\d{2})\b", re.I)


def archivos():
    if FASE == "edit" and CAMBIADOS:
        return [p for p in CAMBIADOS if os.path.isfile(p) and p.lower().endswith(TEXTO)]
    out = []
    for d, dirs, nombres in os.walk(RAIZ):
        dirs[:] = [x for x in dirs if x not in (".git", ".claude", "__pycache__", "node_modules")]
        out += [os.path.join(d, n) for n in nombres if n.lower().endswith(TEXTO)]
    return out


def fechas(linea):
    for m in FECHA.finditer(linea):
        if m.group(3):
            yield int(m.group(3)), MESES[m.group(2).lower()[:3]]
        else:
            yield int(m.group(4)), int(m.group(5))


def revisar(ruta, errores):
    rel = os.path.relpath(ruta, RAIZ)
    texto = open(ruta, encoding="utf-8", errors="replace").read()
    if ruta.lower().endswith(".json"):
        try:
            json.loads(texto)
        except ValueError as e:
            errores.append(f"{rel}: JSON inválido: {e}")
    if ruta.lower().endswith(".md") and os.path.basename(ruta).lower() != "readme.md":
        m = re.search(r"^#+\s*Fuentes\b.*$", texto, re.M | re.I)
        if not m:
            errores.append(f"{rel}: falta la sección «Fuentes» (cada dato necesita fuente con fecha)")
            return
        hoy = datetime.date.today()
        inicio = texto[:m.start()].count("\n") + 1
        seccion = texto[m.end():].split("\n#", 1)[0]
        for i, linea in enumerate(seccion.splitlines(), 1):
            if not linea.strip().startswith(("-", "*", "|")) or set(linea.strip()) <= set("|-: "):
                continue
            fs = list(fechas(linea))
            if not fs:
                errores.append(f"{rel}:{inicio + i - 1}: fuente sin fecha")
            elif max(fs) < (hoy.year, hoy.month) and not re.search(r"confirmad", linea, re.I):
                errores.append(f"{rel}:{inicio + i - 1}: fuente de un mes anterior sin confirmación de este mes")


def main():
    errores = []
    for ruta in archivos():
        revisar(ruta, errores)
    for e in errores:
        print(f"{e}: error")
    print(f"validate ({FASE}): {len(errores)} error(es)")
    return 1 if errores else 0


if __name__ == "__main__":
    sys.exit(main())
