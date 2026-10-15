"""Valida TODOS os trechos de codigos_fonte.json antes de entrarem no vídeo: compila/roda de verdade (local ou Docker).
Uso: python scripts/validar_codigos.py [id ...]     (sem ids = os usados em plano_dados.py)
Cada linguagem tem um runner e uma expectativa (saída esperada ou erro esperado, p.ex. Rust/TypeScript mostram erros de propósito).
Falha (exit 1) se algum trecho não compilar/rodar como esperado. Registra em validacao_codigos.log."""

import json, os, re, subprocess, sys, tempfile, textwrap

FONTE = json.load(open("codigos_fonte.json"))
USADOS = (
    sorted(set(re.findall(r'Codigo\("([a-z0-9]+)"', open("plano_dados.py").read())))
    if os.path.exists("plano_dados.py")
    else list(FONTE)
)
ids = sys.argv[1:] or USADOS


def sh(cmd, cwd, timeout=900, inp=None):
    p = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True, timeout=timeout, input=inp)
    return p.returncode, (p.stdout + p.stderr).strip()


def docker(img, script, d, timeout=1800):
    return sh(f"docker run --rm -v '{d}':/w -w /w {img} sh -c \"{script}\"", d, timeout)


R = {}


def runner(nome):
    def deco(f):
        R[nome] = f
        return f

    return deco


@runner("assembly")
def _(d, arq):  # Linux x86-64 em Docker (nasm + ld)
    return (
        docker(
            "ubuntu:24.04",
            f"apt-get update -qq >/dev/null && apt-get install -y -qq nasm binutils >/dev/null && nasm -f elf64 {arq} -o o.o && ld o.o -o a.out && ./a.out",
            d,
        ),
        "Ola, mundo",
    )


@runner("fortran")
def _(d, arq):
    return sh(f"gfortran {arq} -o a.out && ./a.out", d), "Area:"


@runner("cobol")
def _(d, arq):
    return (
        docker(
            "ubuntu:24.04",
            f"apt-get update -qq >/dev/null && apt-get install -y -qq gnucobol >/dev/null && cobc -x -free {arq} -o a.out && ./a.out",
            d,
        ),
        "05",
    )


@runner("c")
def _(d, arq):
    return sh(f"cc {arq} -o a.out && ./a.out", d), "42"


@runner("php")
def _(d, arq):
    return sh(f"php {arq}", d), "<li>Item 3</li>"


@runner("javascript")
def _(d, arq):
    return sh(f"node --check {arq} && echo SINTAXE-OK", d), "SINTAXE-OK"


@runner("typescript")
def _(d, arq):  # erro intencional: precisa dar TS2345
    rc, out = sh(f"npx --yes -p typescript tsc --noEmit {arq}", d)
    return (0 if "TS2345" in out else 1, out), "TS2345"


@runner("java")
def _(d, arq):
    return docker("eclipse-temurin:21-jdk-alpine", "javac Main.java && java Main", d), "Ol"


@runner("csharp")
def _(d, arq):
    return (
        docker(
            "mcr.microsoft.com/dotnet/sdk:8.0",
            "dotnet new console -o app --force >/dev/null && cp Program.cs app/Program.cs && cd app && dotnet run",
            d,
        ),
        "Olá, mundo!",
    )


@runner("cpp")
def _(d, arq):
    return sh(f"c++ -std=c++17 {arq} -o a.out && ./a.out", d), "3"


@runner("rust")
def _(d, arq):  # erro intencional: use after move (E0382)
    rc, out = sh(f"rustc {arq} -o a.out", d)
    return (0 if "E0382" in out else 1, out), "E0382"


@runner("go")
def _(d, arq):
    return sh(f"go run {arq}", d), "goroutine"


@runner("python")
def _(d, arq):
    open(os.path.join(d, "vendas.csv"), "w").write("valor\n10\n20\n30\n")
    return sh(f"uv run --with pandas python {arq}", d), "Média: 20.00"


@runner("lua")
def _(d, arq):
    return docker("alpine:3.20", f"apk add -q lua5.4 && lua5.4 {arq}", d), "Olá, mundo"


@runner("elixir")
def _(d, arq):
    return docker("elixir:1.16-alpine", f"elixir {arq}", d), "Olá, mundo!"


@runner("sql")
def _(d, arq):
    ddl = "CREATE TABLE usuarios(nome TEXT, cidade TEXT); INSERT INTO usuarios VALUES('Ana','Recife'),('Bia','Lima'),('Caio','Recife');"
    return sh(f'sqlite3 :memory: "{ddl}" < /dev/null; (echo "{ddl}"; cat {arq}) | sqlite3', d), "Ana"


falhas = []
with open("validacao_codigos.log", "a") as log:
    for i in ids:
        c = FONTE[i]
        if i not in R:
            print(f"{i}: sem runner (não validado)")
            continue
        d = tempfile.mkdtemp(prefix=f"cod_{i}_")
        arq = c["arquivo"]
        open(os.path.join(d, arq), "w").write(c["codigo"] + "\n")
        try:
            (rc, out), esperado = R[i](d, arq)
        except Exception as e:
            rc, out, esperado = 1, f"EXCEÇÃO {e}", ""
        ok = rc == 0 and esperado in out
        print(f"{i}: {'OK' if ok else 'FALHOU'}  {out[:160]!r}")
        log.write(f"{i} {'OK' if ok else 'FALHOU'} :: {out[:400]}\n")
        if not ok:
            falhas.append(i)
if falhas:
    print("FALHAS:", falhas)
    sys.exit(1)
print("todos os códigos validados")
