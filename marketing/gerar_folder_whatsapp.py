from pathlib import Path
from textwrap import wrap

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent
WIDTH, HEIGHT = 1080, 1350
FONT_REGULAR = Path(r"C:\Windows\Fonts\segoeui.ttf")
FONT_BOLD = Path(r"C:\Windows\Fonts\segoeuib.ttf")


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_BOLD if bold else FONT_REGULAR), size)


def draw_wrapped(draw, xy, text, font_obj, fill, width_chars, spacing=8):
    x, y = xy
    for line in wrap(text, width=width_chars):
        draw.text((x, y), line, font=font_obj, fill=fill)
        y += font_obj.size + spacing
    return y


background = Image.open(ROOT / "familia-organizando-financas.png").convert("RGB")
scale = max(WIDTH / background.width, HEIGHT / background.height)
background = background.resize((int(background.width * scale), int(background.height * scale)))
left = max(0, background.width - WIDTH)
background = background.crop((left, 0, left + WIDTH, HEIGHT))

canvas = background.convert("RGBA")
overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
overlay_draw = ImageDraw.Draw(overlay)
for x in range(WIDTH):
    pos = x / WIDTH
    if pos <= 0.43:
        opacity = 252
    elif pos <= 0.63:
        opacity = int(252 - ((pos - 0.43) / 0.20) * 156)
    elif pos <= 0.82:
        opacity = int(96 - ((pos - 0.63) / 0.19) * 84)
    else:
        opacity = 0
    overlay_draw.line((x, 0, x, HEIGHT), fill=(246, 251, 250, opacity))
overlay_draw.rectangle((0, 0, WIDTH, 18), fill="#087b7a")
overlay_draw.rectangle((0, HEIGHT - 15, WIDTH, HEIGHT), fill="#2e9b66")
canvas = Image.alpha_composite(canvas, overlay)
draw = ImageDraw.Draw(canvas)

icon = Image.open(ROOT.parent / "favicon.ico").convert("RGBA").resize((76, 76))
canvas.alpha_composite(icon, (62, 66))

draw.text((155, 72), "App Orçamento Familiar", font=font(30, True), fill="#14595a")
draw.text((155, 111), "Mais clareza para cuidar do seu dinheiro", font=font(17, True), fill="#496d6e")

y = 205
y = draw_wrapped(
    draw,
    (62, y),
    "Organize sua vida financeira com praticidade.",
    font(68, True),
    "#123436",
    20,
    spacing=4,
)
y += 18
y = draw_wrapped(
    draw,
    (62, y),
    "Acompanhe o que entra, controle seus gastos e planeje seus próximos passos com mais tranquilidade.",
    font(25, True),
    "#355b5c",
    45,
    spacing=8,
)

y += 24
draw.rounded_rectangle((62, y, 672, y + 74), radius=8, fill=(255, 255, 255, 220), outline="#2e9b66", width=2)
draw.rectangle((62, y, 68, y + 74), fill="#2e9b66")
draw_wrapped(
    draw,
    (82, y + 13),
    "Seus dados permanecem armazenados no seu próprio computador.",
    font(19, True),
    "#245354",
    49,
    spacing=4,
)
y += 74

features = [
    "Registre receitas, despesas e contas a vencer",
    "Crie metas financeiras e acompanhe seu progresso",
    "Receba alertas e gere relatorios mensais",
    "Exporte informações para apoio ao Imposto de Renda",
    "Utilize modo privacidade e backup local",
]
y += 30
for feature in features:
    draw.ellipse((62, y + 2, 89, y + 29), fill="#087b7a")
    draw.line((69, y + 17, 75, y + 23), fill="white", width=3)
    draw.line((75, y + 23, 84, y + 10), fill="white", width=3)
    y = draw_wrapped(draw, (102, y), feature, font(22, True), "#23494a", 34, spacing=4)
    y += 11

box_y = 1160
draw.rounded_rectangle((62, box_y, 560, 1320), radius=8, fill=(255, 255, 255, 242), outline="#b8d9d6", width=2)
draw.text((84, box_y + 18), "Licenca anual do app", font=font(25, True), fill="#087b7a")
draw.text((84, box_y + 58), "Use por 12 meses no seu computador", font=font(18, True), fill="#345f60")
draw.text((84, box_y + 83), "com dados locais.", font=font(18, True), fill="#345f60")
draw.text((84, box_y + 110), "Plano anual de lancamento: R$ 197,00", font=font(19, True), fill="#087b7a")
draw.text((84, box_y + 137), "Renovação anual: R$ 297,00", font=font(16, True), fill="#345f60")

contact_y = 1186
draw.rounded_rectangle((627, contact_y, 1042, 1320), radius=8, fill="#087b7a")
draw.text((651, contact_y + 19), "Solicite sua licenca anual", font=font(19, True), fill="white")
draw.text((651, contact_y + 52), "(12) 98161-2085", font=font(33, True), fill="white")
draw.text((651, contact_y + 101), "Atendimento pelo WhatsApp", font=font(16, True), fill="white")

canvas.convert("RGB").save(ROOT / "folder-whatsapp.png", quality=96)
print(ROOT / "folder-whatsapp.png")
