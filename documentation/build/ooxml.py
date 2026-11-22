"""Minimal WordprocessingML writer that reuses the university template's package.

The template is a PDF-to-Word conversion (typed page numbers, empty text-box footers), so
instead of editing its body we keep its styles, theme, fonts and logo and write a clean
body with real page-number fields, a TOC, caption sequences and inline images.
"""
from __future__ import annotations
import re, zipfile
from dataclasses import dataclass, field as dc_field
from pathlib import Path
from xml.sax.saxutils import escape
from PIL import Image

NS = ('xmlns:wpc="http://schemas.microsoft.com/office/word/2010/wordprocessingCanvas" '
      'xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006" '
      'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
      'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" '
      'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
      'xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture" '
      'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
      'xmlns:w14="http://schemas.microsoft.com/office/word/2010/wordml" mc:Ignorable="w14"')
REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"

# Page geometry (US Letter, as in the template). Text width = 12240 - 1418 - 1134 = 9688 dxa.
PAGE_W, PAGE_H = 12240, 15840
MARGIN = dict(top=1418, right=1134, bottom=1276, left=1418, header=709, footer=567)
TEXT_W = PAGE_W - MARGIN["left"] - MARGIN["right"]
EMU_PER_DXA = 635
FONT = "Times New Roman"


def t(text: str) -> str:
    return f'<w:t xml:space="preserve">{escape(text)}</w:t>'


def run(text: str, bold=False, italic=False, size=None, color=None, font=None, caps=False, superscript=False) -> str:
    props = ""
    if font: props += f'<w:rFonts w:ascii="{font}" w:hAnsi="{font}" w:cs="{font}"/>'
    if bold: props += "<w:b/><w:bCs/>"
    if italic: props += "<w:i/><w:iCs/>"
    if caps: props += "<w:caps/>"
    if color: props += f'<w:color w:val="{color}"/>'
    if size: props += f'<w:sz w:val="{int(size * 2)}"/><w:szCs w:val="{int(size * 2)}"/>'
    if superscript: props += '<w:vertAlign w:val="superscript"/>'
    return f"<w:r>{f'<w:rPr>{props}</w:rPr>' if props else ''}{t(text)}</w:r>"


INLINE = re.compile(r"(\*\*.+?\*\*|\*[^*\s][^*]*?\*|`[^`]+`)")


def rich(text: str, size=None, bold=False) -> str:
    """Runs from light markdown: **bold**, *italic*, `code`."""
    out = []
    for part in INLINE.split(text):
        if not part: continue
        if part.startswith("**"): out.append(run(part[2:-2], bold=True, size=size))
        elif part.startswith("`"): out.append(run(part[1:-1], size=(size or 12) - 1, font="Consolas", bold=bold))
        elif part.startswith("*") and len(part) > 2: out.append(run(part[1:-1], italic=True, size=size, bold=bold))
        else: out.append(run(part, size=size, bold=bold))
    return "".join(out)


def ppr(style=None, jc=None, before=None, after=None, line=None, ind_left=None, ind_hanging=None, first=None,
        keep_next=False, keep_lines=False, page_break_before=False, outline=None, num=None, border_bottom=False,
        tabs=None, right=None, sect=None) -> str:
    p = ""
    if style: p += f'<w:pStyle w:val="{style}"/>'
    if keep_next: p += "<w:keepNext/>"
    if keep_lines: p += "<w:keepLines/>"
    if page_break_before: p += "<w:pageBreakBefore/>"
    if num: p += f'<w:numPr><w:ilvl w:val="{num[1]}"/><w:numId w:val="{num[0]}"/></w:numPr>'
    if border_bottom: p += '<w:pBdr><w:bottom w:val="single" w:sz="12" w:space="4" w:color="000000"/></w:pBdr>'
    if tabs: p += "<w:tabs>" + "".join(f'<w:tab w:val="{k}" w:leader="{l}" w:pos="{pos}"/>' for k, l, pos in tabs) + "</w:tabs>"
    sp = ""
    if before is not None: sp += f' w:before="{before}"'
    if after is not None: sp += f' w:after="{after}"'
    if line is not None: sp += f' w:line="{line}" w:lineRule="auto"'
    if sp: p += f"<w:spacing{sp}/>"
    ind = ""
    if ind_left is not None: ind += f' w:left="{ind_left}"'
    if right is not None: ind += f' w:right="{right}"'
    if ind_hanging is not None: ind += f' w:hanging="{ind_hanging}"'
    if first is not None: ind += f' w:firstLine="{first}"'
    if ind: p += f"<w:ind{ind}/>"
    if jc: p += f'<w:jc w:val="{jc}"/>'
    if outline is not None: p += f'<w:outlineLvl w:val="{outline}"/>'
    if sect: p += sect
    return f"<w:pPr>{p}</w:pPr>" if p else ""


def para(runs: str = "", **kw) -> str:
    return f"<w:p>{ppr(**kw)}{runs}</w:p>"


def field(instr: str, placeholder: str = "", size=None, bold=False) -> str:
    """Complex field (TOC, PAGE, SEQ) with cached placeholder text that Word refreshes."""
    rp = (f'<w:rPr>{"<w:b/>" if bold else ""}<w:sz w:val="{int(size*2)}"/></w:rPr>' if size else (f"<w:rPr><w:b/></w:rPr>" if bold else ""))
    return (f'<w:r>{rp}<w:fldChar w:fldCharType="begin"/></w:r><w:r>{rp}<w:instrText xml:space="preserve"> {escape(instr)} </w:instrText></w:r>'
            f'<w:r>{rp}<w:fldChar w:fldCharType="separate"/></w:r><w:r>{rp}{t(placeholder)}</w:r><w:r>{rp}<w:fldChar w:fldCharType="end"/></w:r>')


def sect_pr(footer_rid: str | None, fmt: str | None, start: int | None, title_pg=False, next_page=True) -> str:
    s = "<w:sectPr>"
    if footer_rid: s += f'<w:footerReference w:type="default" r:id="{footer_rid}"/>'
    if not next_page: s += '<w:type w:val="continuous"/>'
    s += f'<w:pgSz w:w="{PAGE_W}" w:h="{PAGE_H}"/>'
    s += '<w:pgMar ' + " ".join(f'w:{k}="{v}"' for k, v in MARGIN.items()) + ' w:gutter="0"/>'
    if fmt: s += f'<w:pgNumType w:fmt="{fmt}"' + (f' w:start="{start}"' if start else "") + "/>"
    if title_pg: s += "<w:titlePg/>"
    s += "</w:sectPr>"
    return s


@dataclass
class Doc:
    template: Path
    body: list[str] = dc_field(default_factory=list)
    media: list[tuple[str, bytes]] = dc_field(default_factory=list)   # (name, bytes)
    rels: list[tuple[str, str, str]] = dc_field(default_factory=list)  # (rid, type, target)
    table_no: int = 0
    figure_no: int = 0
    _rid: int = 100
    _img: int = 0
    _nums: int = 10   # numbered-list instances start at numId 11

    def rid(self) -> str:
        self._rid += 1
        return f"rId{self._rid}"

    # ---------------------------------------------------------------- blocks
    def add(self, xml: str): self.body.append(xml)

    def heading(self, text: str, level: int, page_break=False, in_toc=True):
        """level 1 = chapter (right aligned, rule below), 2 = x.y, 3 = x.y.z.
        in_toc=False keeps the look but leaves it out of the table of contents (front matter)."""
        if level == 1:
            self.add(para(run(text, bold=True, size=16), style="Heading1" if in_toc else None, jc="right", before=0, after=360,
                          border_bottom=True, keep_next=True, page_break_before=page_break, outline=0 if in_toc else None))
        elif level == 2:
            self.add(para(run(text, bold=True, size=14), style="Heading2", jc="left", before=300, after=120, keep_next=True, keep_lines=True, outline=1, ind_left=0, right=0))
        else:
            self.add(para(run(text, bold=True, size=12), style="Heading3", jc="left", before=200, after=80, keep_next=True, keep_lines=True, outline=2, ind_left=0, right=0))

    def p(self, text: str, jc="both", before=0, after=140, size=12, keep_next=False, italic=False):
        runs = rich(f"*{text}*" if italic else text, size=size)
        self.add(para(runs, style="BodyText", jc=jc, before=before, after=after, line=360, keep_next=keep_next))

    def bullets(self, items: list[str], numbered=False, size=12):
        if numbered:  # each numbered list gets its own instance so it restarts at 1
            self._nums += 1; num = (self._nums, 0)
        else:
            num = (NUM_BULLET, 0)
        for i, item in enumerate(items):
            self.add(para(rich(item, size=size), style="BodyText", jc="both", num=num, ind_left=720, ind_hanging=360,
                          before=0, after=80 if i < len(items) - 1 else 160, line=320))

    def caption(self, kind: str, text: str, keep_next=False):
        label = "TABLE" if kind == "Table" else "FIGURE"
        if kind == "Table": self.table_no += 1; n = self.table_no
        else: self.figure_no += 1; n = self.figure_no
        runs = run(f"{label} ", bold=True, size=10) + field(f"SEQ {kind} \\* ARABIC", str(n), size=10, bold=True) + run(f": {text}", size=10)
        self.add(para(runs, jc="center", before=60 if kind == "Figure" else 200, after=200 if kind == "Figure" else 80, keep_next=keep_next))
        return n

    def table(self, caption: str | None, headers: list[str], rows: list[list[str]], widths: list[float], size=10, header_fill="D9E2F3",
              align: list[str] | None = None, first_col_bold=False):
        """widths are relative; scaled to the text width."""
        if caption: self.caption("Table", caption, keep_next=True)
        total = sum(widths); cols = [int(TEXT_W * w / total) for w in widths]; cols[-1] = TEXT_W - sum(cols[:-1])
        align = align or ["left"] * len(cols)
        border = "".join(f'<w:{s} w:val="single" w:sz="4" w:space="0" w:color="808080"/>' for s in ("top", "left", "bottom", "right", "insideH", "insideV"))
        x = (f'<w:tbl><w:tblPr><w:tblW w:w="{TEXT_W}" w:type="dxa"/><w:jc w:val="center"/><w:tblBorders>{border}</w:tblBorders>'
             f'<w:tblLayout w:type="fixed"/><w:tblCellMar><w:top w:w="40" w:type="dxa"/><w:left w:w="80" w:type="dxa"/><w:bottom w:w="40" w:type="dxa"/><w:right w:w="80" w:type="dxa"/></w:tblCellMar></w:tblPr>'
             "<w:tblGrid>" + "".join(f'<w:gridCol w:w="{c}"/>' for c in cols) + "</w:tblGrid>")

        def cell(text, w, fill=None, bold=False, jc="left"):
            shade = f'<w:shd w:val="clear" w:color="auto" w:fill="{fill}"/>' if fill else ""
            paras = "".join(para(rich(line, size=size, bold=bold), jc=jc, before=0, after=0, line=240) for line in str(text).split("\n"))
            return f'<w:tc><w:tcPr><w:tcW w:w="{w}" w:type="dxa"/>{shade}<w:vAlign w:val="center"/></w:tcPr>{paras}</w:tc>'

        x += '<w:tr><w:trPr><w:tblHeader/><w:cantSplit/></w:trPr>' + "".join(cell(h, c, header_fill, True, "center") for h, c in zip(headers, cols)) + "</w:tr>"
        for r in rows:
            x += "<w:tr><w:trPr><w:cantSplit/></w:trPr>" + "".join(cell(v, c, None, first_col_bold and i == 0, align[i]) for i, (v, c) in enumerate(zip(r, cols))) + "</w:tr>"
        x += "</w:tbl>"
        self.add(x)
        self.add(para("", before=0, after=120))

    def image(self, path: Path, width_in: float, caption: str | None = None, max_height_in: float = 7.6):
        data = path.read_bytes()
        with Image.open(path) as im: w, h = im.size
        width_in = min(width_in, TEXT_W / 1440)
        height_in = width_in * h / w
        if height_in > max_height_in: width_in, height_in = max_height_in * w / h, max_height_in
        self._img += 1
        ext = path.suffix.lower().lstrip(".").replace("jpg", "jpeg")
        name = f"report_img{self._img}.{ext}"
        rid = self.rid(); self.media.append((name, data)); self.rels.append((rid, f"{REL}/image", f"media/{name}"))
        cx, cy = int(width_in * 914400), int(height_in * 914400)
        drawing = (f'<w:r><w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0"><wp:extent cx="{cx}" cy="{cy}"/>'
                   f'<wp:docPr id="{self._img}" name="Picture {self._img}"/><wp:cNvGraphicFramePr><a:graphicFrameLocks noChangeAspect="1"/></wp:cNvGraphicFramePr>'
                   f'<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:pic>'
                   f'<pic:nvPicPr><pic:cNvPr id="{self._img}" name="{name}"/><pic:cNvPicPr/></pic:nvPicPr>'
                   f'<pic:blipFill><a:blip r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
                   f'<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom>'
                   f'<a:ln w="3175"><a:solidFill><a:srgbClr val="BFBFBF"/></a:solidFill></a:ln></pic:spPr></pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r>')
        self.add(para(drawing, jc="center", before=160, after=0, keep_next=bool(caption)))
        if caption: return self.caption("Figure", caption)

    def page_break(self):
        self.add('<w:p><w:r><w:br w:type="page"/></w:r></w:p>')

    def section_break(self, footer_rid, fmt, start):
        """Ends the current section (its properties live in this paragraph)."""
        self.add(f"<w:p>{ppr(sect=sect_pr(footer_rid, fmt, start))}</w:p>")

    def toc(self, instr: str, placeholder: str):
        self.add(f'<w:p>{ppr(before=0, after=0)}{field(instr, placeholder)}</w:p>')

    # ---------------------------------------------------------------- package
    def save(self, out: Path, final_sect: str, core: dict):
        src = zipfile.ZipFile(self.template)
        doc = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document {NS}><w:body>{"".join(self.body)}{final_sect}</w:body></w:document>'
        footer = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:ftr {NS}>'
                  + para(field("PAGE", "1", size=11), jc="center") + "</w:ftr>")
        rels = [("rId1", f"{REL}/styles", "styles.xml"), ("rId2", f"{REL}/settings", "settings.xml"), ("rId3", f"{REL}/webSettings", "webSettings.xml"),
                ("rId4", f"{REL}/fontTable", "fontTable.xml"), ("rId5", f"{REL}/theme", "theme/theme1.xml"), ("rId6", f"{REL}/numbering", "numbering.xml"),
                ("rId7", f"{REL}/footer", "footer1.xml"), *self.rels]
        rels_xml = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                    + "".join(f'<Relationship Id="{i}" Type="{ty}" Target="{tg}"/>' for i, ty, tg in rels) + "</Relationships>")
        ct = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
              '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/>'
              '<Default Extension="png" ContentType="image/png"/><Default Extension="jpeg" ContentType="image/jpeg"/>'
              '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
              '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
              '<Override PartName="/word/settings.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml"/>'
              '<Override PartName="/word/webSettings.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.webSettings+xml"/>'
              '<Override PartName="/word/fontTable.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.fontTable+xml"/>'
              '<Override PartName="/word/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>'
              '<Override PartName="/word/numbering.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.numbering+xml"/>'
              '<Override PartName="/word/footer1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/>'
              '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
              '<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/></Types>')
        root_rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                     '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
                     '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>'
                     '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/></Relationships>')
        core_xml = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
                    'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
                    f'<dc:title>{escape(core["title"])}</dc:title><dc:creator>{escape(core["author"])}</dc:creator>'
                    f'<dcterms:created xsi:type="dcterms:W3CDTF">{core["date"]}</dcterms:created><dcterms:modified xsi:type="dcterms:W3CDTF">{core["date"]}</dcterms:modified></cp:coreProperties>')
        app_xml = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">'
                   '<Application>Microsoft Office Word</Application></Properties>')
        settings = src.read("word/settings.xml").decode("utf-8")
        # The template's footnote/endnote separators live in parts we do not copy; drop the references.
        settings = re.sub(r"<w:(footnotePr|endnotePr)>.*?</w:\1>", "", settings, flags=re.S)
        if "<w:updateFields" not in settings:  # ask Word to refresh TOC / page fields on open
            # Schema order: updateFields comes right before hdrShapeDefaults / compat.
            anchor = next(a for a in ("<w:hdrShapeDefaults", "<w:compat", "<w:rsids") if a in settings)
            settings = settings.replace(anchor, '<w:updateFields w:val="true"/>' + anchor, 1)

        # The converted template's TOC styles carry large spacing; replace them with clean ones.
        styles = src.read("word/styles.xml").decode("utf-8")
        for level, (ind, bold, before) in {1: (0, True, 120), 2: (240, False, 0), 3: (480, False, 0)}.items():
            clean = (f'<w:style w:type="paragraph" w:styleId="TOC{level}"><w:name w:val="toc {level}"/><w:basedOn w:val="Normal"/>'
                     f'<w:next w:val="Normal"/><w:uiPriority w:val="39"/><w:unhideWhenUsed/><w:pPr><w:tabs><w:tab w:val="right" w:leader="dot" w:pos="{TEXT_W}"/></w:tabs>'
                     f'<w:spacing w:before="{before}" w:after="40" w:line="276" w:lineRule="auto"/><w:ind w:left="{ind}" w:right="0" w:firstLine="0"/></w:pPr>'
                     f'<w:rPr><w:rFonts w:ascii="{FONT}" w:hAnsi="{FONT}" w:cs="{FONT}"/>{"<w:b/><w:bCs/>" if bold else ""}<w:sz w:val="24"/><w:szCs w:val="24"/></w:rPr></w:style>')
            styles = re.sub(rf'<w:style [^>]*w:styleId="TOC{level}"[^>]*>.*?</w:style>', clean, styles, count=1, flags=re.S)
        tof = (f'<w:style w:type="paragraph" w:styleId="TableofFigures"><w:name w:val="table of figures"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/>'
               f'<w:uiPriority w:val="99"/><w:unhideWhenUsed/><w:pPr><w:tabs><w:tab w:val="right" w:leader="dot" w:pos="{TEXT_W}"/></w:tabs>'
               f'<w:spacing w:before="0" w:after="60"/></w:pPr><w:rPr><w:rFonts w:ascii="{FONT}" w:hAnsi="{FONT}" w:cs="{FONT}"/><w:sz w:val="24"/><w:szCs w:val="24"/></w:rPr></w:style>')
        if 'w:styleId="TableofFigures"' not in styles:
            styles = styles.replace("</w:styles>", tof + "</w:styles>")

        keep = {"word/webSettings.xml", "word/fontTable.xml", "word/theme/theme1.xml"}
        out.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("[Content_Types].xml", ct); z.writestr("_rels/.rels", root_rels)
            z.writestr("docProps/core.xml", core_xml); z.writestr("docProps/app.xml", app_xml)
            z.writestr("word/document.xml", doc); z.writestr("word/_rels/document.xml.rels", rels_xml)
            extra = "".join(f'<w:num w:numId="{i}"><w:abstractNumId w:val="2"/><w:lvlOverride w:ilvl="0"><w:startOverride w:val="1"/></w:lvlOverride></w:num>'
                            for i in range(11, self._nums + 1))
            z.writestr("word/footer1.xml", footer); z.writestr("word/numbering.xml", NUMBERING.replace("</w:numbering>", extra + "</w:numbering>"))
            z.writestr("word/settings.xml", settings); z.writestr("word/styles.xml", styles)
            for name in keep: z.writestr(name, src.read(name))
            for name, data in self.media: z.writestr(f"word/media/{name}", data)


NUM_BULLET, NUM_DECIMAL = 1, 2
NUMBERING = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
             '<w:numbering xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
             '<w:abstractNum w:abstractNumId="1"><w:multiLevelType w:val="hybridMultilevel"/>'
             '<w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="bullet"/><w:lvlText w:val="•"/><w:lvlJc w:val="left"/>'
             '<w:pPr><w:ind w:left="720" w:hanging="360"/></w:pPr><w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/></w:rPr></w:lvl></w:abstractNum>'
             '<w:abstractNum w:abstractNumId="2"><w:multiLevelType w:val="hybridMultilevel"/>'
             '<w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="decimal"/><w:lvlText w:val="%1."/><w:lvlJc w:val="left"/>'
             '<w:pPr><w:ind w:left="720" w:hanging="360"/></w:pPr></w:lvl></w:abstractNum>'
             '<w:num w:numId="1"><w:abstractNumId w:val="1"/></w:num><w:num w:numId="2"><w:abstractNumId w:val="2"/></w:num></w:numbering>')
