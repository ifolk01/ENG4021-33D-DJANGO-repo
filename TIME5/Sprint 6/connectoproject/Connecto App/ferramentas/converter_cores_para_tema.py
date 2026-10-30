import re, sys, collections
from pathlib import Path

PASTA = Path("static")
APLICAR = "--aplicar" in sys.argv
FIM = r"(\s*(?:;|!important|}))"

BRANCO = r"(?:#fff(?:fff)?|white)"
TEXTO  = r"(?:#33364f|#30354f|#262a3e|#1c1c1c|#17191f|#111(?:111)?)"
MUDO   = r"(?:#6b6f80|#73757d)"
FUNDO  = r"(?:#f2f2ed|#f5f5ef)"
BORDA  = r"(?:#e4e4dd|#e8e7df|#dcdcd3|#e9e9e4|#eae9e4)"
CINZA  = r"(?:#fafaf7|#f7f8fa|#f6f5f0|#efefeb|#ededeb|#efefea|#e9e9e4|#e8e8e4|#edf0f3|#eceff1|#eef1f3|#e6e6f2|#e5e6e8|#dededb|#e6e7e8|#e9eaf0)"
CIANO  = r"(?:#ddeef4|#dff2f7|#e4f3f8|#dfeefa|#e4f4f8)"
VERM   = r"(?:#f0e2e0|#f8e7e5|#fde8ec|#f9e8e7)"
AMBAR  = r"(?:#fbf0dc|#fff1c7|#f2e9d5|#f2e8ce|#fbf1de)"
VERDE  = r"(?:#e7f3eb)"

def com_reserva(var, prop_grupo=True):
    def f(m):
        prop, cor, resto = m.group(1), m.group(2), m.group(3)
        return f"{prop}: var({var}, {cor}){resto}"
    return f

REGRAS = [
    ("texto navy -> ink",
     r"(?<![\w-])color\s*:\s*var\(--connecto-navy\)",
     lambda m: "color: var(--tema-ink, var(--connecto-navy))"),
    ("fundo branco -> surface",
     rf"(?<![\w-])(background(?:-color)?)\s*:\s*({BRANCO}){FIM}",
     com_reserva("--tema-surface")),
    ("texto escuro fixo -> ink",
     rf"(?<![\w-])(color)\s*:\s*({TEXTO}){FIM}",
     com_reserva("--tema-ink")),
    ("texto cinza fixo -> muted",
     rf"(?<![\w-])(color)\s*:\s*({MUDO}){FIM}",
     com_reserva("--tema-muted")),
    ("fundo da página -> bg",
     rf"(?<![\w-])(background(?:-color)?)\s*:\s*({FUNDO}){FIM}",
     com_reserva("--tema-bg")),
    ("fundo cinza-claro -> surface-2",
     rf"(?<![\w-])(background(?:-color)?)\s*:\s*({CINZA}){FIM}",
     com_reserva("--tema-surface-2")),
    ("fundo azul-claro -> cyan-soft",
     rf"(?<![\w-])(background(?:-color)?)\s*:\s*({CIANO}){FIM}",
     com_reserva("--tema-cyan-soft")),
    ("fundo vermelho-claro -> red-soft",
     rf"(?<![\w-])(background(?:-color)?)\s*:\s*({VERM}){FIM}",
     com_reserva("--tema-red-soft")),
    ("fundo âmbar-claro -> amber-soft",
     rf"(?<![\w-])(background(?:-color)?)\s*:\s*({AMBAR}){FIM}",
     com_reserva("--tema-amber-soft")),
    ("fundo verde-claro -> green-soft",
     rf"(?<![\w-])(background(?:-color)?)\s*:\s*({VERDE}){FIM}",
     com_reserva("--tema-green-soft")),
    ("borda fixa -> line",
     rf"(?<![\w-])(border(?:-(?:top|right|bottom|left))?(?:-color)?\s*:[^;{{}}]*?)(?<!--tema-line, )({BORDA})",
     lambda m: f"{m.group(1)}var(--tema-line, {m.group(2)})"),
]

total = collections.Counter()
restantes = collections.defaultdict(collections.Counter)
for css in sorted(PASTA.glob("*.css")):
    if css.name == "tema.css":
        continue
    txt = css.read_text(encoding="utf-8")
    novo, n_arq = txt, 0
    for desc, rx, fn in REGRAS:
        novo, n = re.subn(rx, fn, novo, flags=re.I)
        total[desc] += n
        n_arq += n
    assert novo.count("{") == novo.count("}"), f"chaves desbalanceadas em {css.name}"
    limpo = re.sub(r"/\*.*?\*/", "", novo, flags=re.S)
    limpo = re.sub(r"var\(--tema-[a-z0-9-]+,\s*#[0-9a-fA-F]{3,8}\)", "", limpo)   # já tratadas
    limpo = re.sub(r"--[\w-]+\s*:\s*#[0-9a-fA-F]{3,8}", "", limpo)                 # definições de variável
    for h in re.findall(r"#[0-9a-fA-F]{3,8}\b", limpo):
        restantes[css.name][h.lower()] += 1
    print(f"{css.name:26s} {n_arq:3d} substituições")
    if APLICAR and novo != txt:
        css.write_text(novo, encoding="utf-8", newline="")

print("\nPor regra:")
for d, n in total.items():
    print(f"  {n:3d}  {d}")
print("\n" + ("GRAVADO." if APLICAR else "SIMULAÇÃO: nada foi gravado (use --aplicar)."))
print("\nCores fixas que SOBRARAM (checklist para revisar no modo noturno):")
for arq, c in restantes.items():
    print(f"  {arq}: " + ", ".join(f"{h}×{n}" for h, n in sorted(c.items())))
