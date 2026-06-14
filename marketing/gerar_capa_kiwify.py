from pathlib import Path
from textwrap import wrap

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent
APP_ROOT = ROOT.parent
FONT_REGULAR = Path(r"C:\Windows\Fonts\segoeui.ttf")
FONT_BOLD = Path(r"C:\Windows\Fonts\segoeuib.ttf")

TEAL = "#087b7a"
DARK = "#102f32"
TEXT = "#244b4d"
GREEN = "#2e9b66"
SOFT = "#f4fbfa"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_BOLD if bold else FONT_REGULAR), size)


def cover_crop(image: Image.Image, width: int, height: int, anchor: str = "center", top_bias: float = 0.5) -> Image.Image:
    scale = max(width / image.width, height / image.height)
    resized = image.resize((int(image.width * scale), int(image.height * scale)), Image.Resampling.LANCZOS)
    if anchor == "right":
        left = resized.width - width
    elif anchor == "left":
        left = 0
    else:
        left = (resized.width - width) // 2
    top = int((resized.height - height) * top_bias)
    top = max(0, min(top, resized.height - height))
    return resized.crop((left, top, left + width, top + height))


def draw_wrapped(draw: ImageDraw.ImageDraw, xy, text: str, font_obj, fill, width_chars: int, spacing: int = 8):
    x, y = xy
    for line in wrap(text, width=width_chars):
        draw.text((x, y), line, font=font_obj, fill=fill)
        y += font_obj.size + spacing
    return y


def alpha_gradient(width: int, height: int, stops):
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    for x in range(width):
        pos = x / max(width - 1, 1)
        opacity = stops[-1][1]
        for i in range(len(stops) - 1):
            start, start_opacity = stops[i]
            end, end_opacity = stops[i + 1]
            if start <= pos <= end:
                span = max(end - start, 0.001)
                amount = (pos - start) / span
                opacity = int(start_opacity + (end_opacity - start_opacity) * amount)
                break
        draw.line((x, 0, x, height), fill=(244, 251, 250, opacity))
    return overlay


def paste_logo(canvas: Image.Image, draw: ImageDraw.ImageDraw, x: int, y: int, size: int, title_size: int, subtitle_size: int):
    icon = Image.open(APP_ROOT / "favicon.ico").convert("RGBA").resize((size, size), Image.Resampling.LANCZOS)
    canvas.alpha_composite(icon, (x, y))
    draw.text((x + size + 24, y + 7), "App Orçamento Familiar", font=font(title_size, True), fill="#135658")
    draw.text((x + size + 24, y + size // 2 + 9), "Mais clareza para cuidar do seu dinheiro", font=font(subtitle_size, True), fill="#40686a")


def draw_check(draw: ImageDraw.ImageDraw, x: int, y: int, text: str, size: int, width_chars: int):
    radius = int(size * 0.62)
    draw.ellipse((x, y + 4, x + radius, y + 4 + radius), fill=TEAL)
    draw.line((x + 8, y + 19, x + 15, y + 27), fill="white", width=max(3, size // 8))
    draw.line((x + 15, y + 27, x + 28, y + 10), fill="white", width=max(3, size // 8))
    return draw_wrapped(draw, (x + radius + 18, y), text, font(size, True), TEXT, width_chars, spacing=4)


def gerar_horizontal():
    width, height = 2000, 590
    bg = Image.open(ROOT / "familia-organizando-financas.png").convert("RGB")
    bg = cover_crop(bg, width, height, anchor="right")
    canvas = bg.convert("RGBA")
    canvas = Image.alpha_composite(canvas, alpha_gradient(width, height, [(0.0, 255), (0.48, 247), (0.62, 110), (0.80, 25), (1.0, 0)]))
    draw = ImageDraw.Draw(canvas)

    draw.rectangle((0, 0, width, 18), fill=TEAL)
    draw.rectangle((0, height - 14, width, height), fill=GREEN)
    paste_logo(canvas, draw, 92, 62, 92, 45, 24)

    draw.text((92, 172), "Organize sua vida financeira", font=font(78, True), fill=DARK)
    draw.text((94, 265), "Controle receitas, despesas, metas e relatórios no seu computador.", font=font(37, True), fill=TEXT)

    y = 334
    y = draw_check(draw, 96, y, "Licença anual para uso familiar", 28, 40) + 12
    y = draw_check(draw, 96, y, "Dados armazenados localmente", 28, 40) + 12
    draw_check(draw, 96, y, "Backup, privacidade e relatórios", 28, 40)

    draw.rounded_rectangle((1095, 70, 1878, 185), radius=14, fill=(255, 255, 255, 235), outline="#b7d9d6", width=3)
    draw.text((1130, 92), "Plano anual de lançamento", font=font(31, True), fill=TEAL)
    draw.text((1130, 132), "R$ 197,00", font=font(43, True), fill=DARK)
    draw.text((1395, 145), "por 12 meses", font=font(24, True), fill=TEXT)

    draw.rounded_rectangle((92, 460, 820, 555), radius=14, fill=TEAL)
    draw.text((128, 477), "Solicite sua licença anual", font=font(25, True), fill="white")
    draw.text((128, 508), "(12) 98161-2085", font=font(36, True), fill="white")

    out = ROOT / "capa-kiwify-horizontal.png"
    canvas.convert("RGB").save(out, quality=96)
    return out


def gerar_quadrada():
    width = height = 1080
    bg = Image.open(ROOT / "familia-organizando-financas.png").convert("RGB")
    bg = cover_crop(bg, width, height, anchor="right", top_bias=0.63)
    canvas = bg.convert("RGBA")
    overlay = Image.new("RGBA", (width, height), (244, 251, 250, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    for x in range(width):
        pos = x / width
        if pos < 0.50:
            opacity = 238
        elif pos < 0.78:
            opacity = int(238 - ((pos - 0.50) / 0.28) * 165)
        else:
            opacity = 55
        overlay_draw.line((x, 0, x, height), fill=(244, 251, 250, opacity))
    canvas = Image.alpha_composite(canvas, overlay)
    draw = ImageDraw.Draw(canvas)

    draw.rectangle((0, 0, width, 18), fill=TEAL)
    draw.rectangle((0, height - 14, width, height), fill=GREEN)
    paste_logo(canvas, draw, 70, 74, 88, 40, 22)

    draw.text((70, 205), "App Orçamento", font=font(74, True), fill=DARK)
    draw.text((70, 289), "Familiar", font=font(74, True), fill=DARK)
    draw_wrapped(
        draw,
        (74, 394),
        "Controle receitas, despesas e metas em um só lugar.",
        font(35, True),
        TEXT,
        34,
        spacing=7,
    )

    y = 528
    y = draw_check(draw, 76, y, "Dados no seu computador", 28, 30) + 14
    y = draw_check(draw, 76, y, "Relatórios e alertas", 28, 30) + 14
    draw_check(draw, 76, y, "Licença anual", 28, 30)

    draw.rounded_rectangle((62, 805, 1018, 1010), radius=16, fill=(255, 255, 255, 242), outline="#b7d9d6", width=3)
    draw.text((98, 836), "Plano anual de lançamento", font=font(32, True), fill=TEAL)
    draw.text((98, 884), "R$ 197,00", font=font(58, True), fill=DARK)
    draw.text((98, 955), "WhatsApp: (12) 98161-2085", font=font(30, True), fill=TEXT)

    out = ROOT / "capa-kiwify-quadrada.png"
    canvas.convert("RGB").save(out, quality=96)
    return out


def gerar_miniaturas(horizontal: Path, quadrada: Path):
    h = Image.open(horizontal).convert("RGB")
    q = Image.open(quadrada).convert("RGB")
    h_small = h.resize((680, 201), Image.Resampling.LANCZOS)
    q_small = q.resize((260, 260), Image.Resampling.LANCZOS)
    sheet = Image.new("RGB", (760, 560), "white")
    draw = ImageDraw.Draw(sheet)
    draw.text((40, 26), "Teste de leitura em tamanho reduzido", font=font(30, True), fill=DARK)
    draw.text((40, 74), "Horizontal simulada pequena", font=font(20, True), fill=TEXT)
    sheet.paste(h_small, (40, 106))
    draw.text((40, 340), "Quadrada simulada pequena", font=font(20, True), fill=TEXT)
    sheet.paste(q_small, (40, 374))
    out = ROOT / "capa-kiwify-teste-miniatura.png"
    sheet.save(out, quality=96)
    return out


def gerar_modulo_download():
    width, height = 320, 480
    bg = Image.open(ROOT / "familia-organizando-financas.png").convert("RGB")
    bg = cover_crop(bg, width, height, anchor="right", top_bias=0.62)
    canvas = bg.convert("RGBA")

    overlay = Image.new("RGBA", (width, height), (244, 251, 250, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    for y in range(height):
        if y < 280:
            opacity = 238
        elif y < 390:
            opacity = int(238 - ((y - 280) / 110) * 135)
        else:
            opacity = 88
        overlay_draw.line((0, y, width, y), fill=(244, 251, 250, opacity))
    canvas = Image.alpha_composite(canvas, overlay)
    draw = ImageDraw.Draw(canvas)

    draw.rectangle((0, 0, width, 8), fill=TEAL)
    draw.rectangle((0, height - 8, width, height), fill=GREEN)

    icon = Image.open(APP_ROOT / "favicon.ico").convert("RGBA").resize((50, 50), Image.Resampling.LANCZOS)
    canvas.alpha_composite(icon, (24, 26))
    draw.text((84, 29), "App Orçamento", font=font(20, True), fill="#135658")
    draw.text((84, 53), "Familiar", font=font(20, True), fill="#135658")

    draw.text((24, 112), "Download", font=font(43, True), fill=DARK)
    draw.text((24, 160), "do App", font=font(43, True), fill=DARK)
    draw_wrapped(
        draw,
        (26, 222),
        "Instalador e solicitação da licença anual",
        font(20, True),
        TEXT,
        25,
        spacing=5,
    )

    box = (24, 378, 296, 438)
    draw.rounded_rectangle(box, radius=10, fill=TEAL)
    line1 = "Instalador + licença"
    line2 = "Acesso anual"
    line1_font = font(19, True)
    line2_font = font(18, True)
    line1_box = draw.textbbox((0, 0), line1, font=line1_font)
    line2_box = draw.textbbox((0, 0), line2, font=line2_font)
    line_gap = 3
    text_height = (line1_box[3] - line1_box[1]) + line_gap + (line2_box[3] - line2_box[1])
    start_y = box[1] + ((box[3] - box[1]) - text_height) // 2 - 1
    line1_x = box[0] + ((box[2] - box[0]) - (line1_box[2] - line1_box[0])) // 2
    line2_x = box[0] + ((box[2] - box[0]) - (line2_box[2] - line2_box[0])) // 2
    draw.text((line1_x, start_y), line1, font=line1_font, fill="white")
    draw.text((line2_x, start_y + (line1_box[3] - line1_box[1]) + line_gap), line2, font=line2_font, fill="white")

    out = ROOT / "capa-modulo-download-kiwify-320x480.png"
    canvas.convert("RGB").save(out, quality=96)
    return out


def gerar_slide_area_membros_desktop():
    width, height = 1920, 520
    canvas = Image.new("RGBA", (width, height), SOFT)
    draw = ImageDraw.Draw(canvas)

    draw.rectangle((0, 0, width, 18), fill=TEAL)
    draw.rectangle((0, height - 12, width, height), fill=GREEN)
    margin = 72
    panel = (margin, 58, width - margin, height - 58)
    draw.rounded_rectangle(panel, radius=18, fill="white", outline="#b7d9d6", width=3)

    paste_logo(canvas, draw, 118, 98, 82, 41, 22)

    pill = (1508, 98, 1802, 154)
    draw.rounded_rectangle(pill, radius=28, fill="#eff8f7", outline="#b7d9d6", width=2)
    pill_text = "Área de membros"
    pill_font = font(27, True)
    pill_box = draw.textbbox((0, 0), pill_text, font=pill_font)
    draw.text(
        (
            pill[0] + ((pill[2] - pill[0]) - (pill_box[2] - pill_box[0])) // 2,
            pill[1] + ((pill[3] - pill[1]) - (pill_box[3] - pill_box[1])) // 2 - 2,
        ),
        pill_text,
        font=pill_font,
        fill=TEAL,
    )

    left = 118
    top = 200
    draw.text((left, top), "App Orçamento Familiar", font=font(64, True), fill=DARK)
    draw.text((left + 2, top + 78), "Instalador, guia de uso e licença anual", font=font(34, True), fill=TEXT)

    box_y = 342
    box_w = 536
    box_h = 76
    gap = 28
    items = [
        ("1", "Baixe o instalador"),
        ("2", "Solicite a licença"),
        ("3", "Ative no computador"),
    ]
    for index, (number, label) in enumerate(items):
        x = left + index * (box_w + gap)
        draw.rounded_rectangle((x, box_y, x + box_w, box_y + box_h), radius=12, fill="#eff8f7", outline="#b7d9d6", width=2)
        draw.ellipse((x + 24, box_y + 16, x + 68, box_y + 60), fill=TEAL)
        nb = draw.textbbox((0, 0), number, font=font(24, True))
        draw.text((x + 46 - (nb[2] - nb[0]) / 2, box_y + 23), number, font=font(24, True), fill="white")
        label_font = font(28, True)
        label_box = draw.textbbox((0, 0), label, font=label_font)
        draw.text((x + 92, box_y + ((box_h - (label_box[3] - label_box[1])) // 2) - 2), label, font=label_font, fill=TEXT)

    out = ROOT / "capa-area-membros-desktop.png"
    canvas.convert("RGB").save(out, quality=95)
    return out


def gerar_slide_area_membros_mobile():
    width, height = 1080, 608
    canvas = Image.new("RGBA", (width, height), SOFT)
    draw = ImageDraw.Draw(canvas)

    draw.rectangle((0, 0, width, 14), fill=TEAL)
    draw.rectangle((0, height - 12, width, height), fill=GREEN)
    panel = (44, 44, width - 44, height - 44)
    draw.rounded_rectangle(panel, radius=18, fill="white", outline="#b7d9d6", width=3)
    paste_logo(canvas, draw, 82, 76, 70, 33, 18)

    pill = (762, 82, 998, 132)
    draw.rounded_rectangle(pill, radius=25, fill="#eff8f7", outline="#b7d9d6", width=2)
    pill_text = "Área de membros"
    pill_font = font(22, True)
    pill_box = draw.textbbox((0, 0), pill_text, font=pill_font)
    draw.text(
        (
            pill[0] + ((pill[2] - pill[0]) - (pill_box[2] - pill_box[0])) // 2,
            pill[1] + ((pill[3] - pill[1]) - (pill_box[3] - pill_box[1])) // 2 - 2,
        ),
        pill_text,
        font=pill_font,
        fill=TEAL,
    )

    left = 82
    draw.text((left, 198), "App Orçamento Familiar", font=font(55, True), fill=DARK)
    draw.text((left + 2, 270), "Instalador, guia e licença anual", font=font(30, True), fill=TEXT)

    box_y = 354
    items = [
        ("1", "Baixar instalador"),
        ("2", "Solicitar licença"),
        ("3", "Ativar no computador"),
    ]
    for index, (number, label) in enumerate(items):
        y = box_y + index * 60
        draw.rounded_rectangle((left, y, width - 82, y + 46), radius=10, fill="#eff8f7", outline="#b7d9d6", width=2)
        draw.ellipse((left + 16, y + 8, left + 48, y + 40), fill=TEAL)
        nb = draw.textbbox((0, 0), number, font=font(18, True))
        draw.text((left + 32 - (nb[2] - nb[0]) / 2, y + 12), number, font=font(18, True), fill="white")
        label_font = font(24, True)
        label_box = draw.textbbox((0, 0), label, font=label_font)
        draw.text((left + 68, y + ((46 - (label_box[3] - label_box[1])) // 2) - 2), label, font=label_font, fill=TEXT)

    out = ROOT / "capa-area-membros-mobile.png"
    canvas.convert("RGB").save(out, quality=95)
    return out


if __name__ == "__main__":
    horizontal = gerar_horizontal()
    quadrada = gerar_quadrada()
    miniatura = gerar_miniaturas(horizontal, quadrada)
    modulo = gerar_modulo_download()
    slide_desktop = gerar_slide_area_membros_desktop()
    slide_mobile = gerar_slide_area_membros_mobile()
    print(horizontal)
    print(quadrada)
    print(miniatura)
    print(modulo)
    print(slide_desktop)
    print(slide_mobile)
