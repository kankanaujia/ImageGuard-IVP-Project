"""Sanity-check a generated .docx: well-formed parts, resolvable relationships, settings references."""
import re, sys, zipfile
from xml.dom import minidom

z = zipfile.ZipFile(sys.argv[1])
names = set(z.namelist())
for n in sorted(names):
    if n.endswith((".xml", ".rels")):
        minidom.parseString(z.read(n))
print("well-formed:", len(names), "parts")
rels = z.read("word/_rels/document.xml.rels").decode()
ids = set(re.findall(r'Id="([^"]+)"', rels))
for target in re.findall(r'Target="([^"]+)"', rels):
    if not target.startswith("http") and f"word/{target}" not in names:
        print("MISSING relationship target:", target)
doc = z.read("word/document.xml").decode()
used = set(re.findall(r'r:(?:id|embed)="([^"]+)"', doc))
print("unresolved r:ids in document:", sorted(used - ids))
settings = z.read("word/settings.xml").decode()
print("settings elements:", re.findall(r"<w:(\w+)", settings)[:60])
print("settings r:ids:", re.findall(r'r:id="[^"]+"', settings))
for part in ("footnotes", "endnotes"):
    if f"<w:{part[:-1]}Pr" in settings and f"word/{part}.xml" not in names:
        print(f"settings has {part[:-1]}Pr but word/{part}.xml is missing")
