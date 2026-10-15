"""Valida TODOS os trechos de codes_source.json antes de entrarem no vídeo: compila/roda de verdade (local ou Docker).
Uso: python scripts/validate_codes.py [id ...]     (sem ids = os usados em plan_data.py)
Cada linguagem tem um runner e uma expectativa (saída esperada ou erro esperado, p.ex. Rust/TypeScript mostram erros de propósito).
Falha (exit 1) se algum trecho não compilar/rodar como esperado. Registra em validation_codes.log."""

import json, os, re, subprocess, sys, tempfile, textwrap

SOURCE = json.load(open("codes_source.json"))
USED = (
    sorted(set(re.findall(r'Codigo\("([a-z0-9]+)"', open("plan_data.py").read())))
    if os.path.exists("plan_data.py")
    else list(SOURCE)
)
ids = sys.argv[1:] or USED


def sh(cmd, cwd, timeout=900, inp=None):
    p = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True, timeout=timeout, input=inp)
    return p.returncode, (p.stdout + p.stderr).strip()


def docker(img, script, d, timeout=1800):
    return sh(f"docker run --rm -v '{d}':/w -w /w {img} sh -c \"{script}\"", d, timeout)


R = {}


def runner(name):
    def deco(f):
        R[name] = f
        return f

    return deco


@runner("assembly")
def _(d, file):  # Linux x86-64 em Docker (nasm + ld)
    return (
        docker(
            "ubuntu:24.04",
            f"apt-get update -qq >/dev/null && apt-get install -y -qq nasm binutils >/dev/null && nasm -f elf64 {file} -o o.o && ld o.o -o a.out && ./a.out",
            d,
        ),
        "Ola, mundo",
    )


@runner("fortran")
def _(d, file):
    return sh(f"gfortran {file} -o a.out && ./a.out", d), "Area:"


@runner("cobol")
def _(d, file):
    return (
        docker(
            "ubuntu:24.04",
            f"apt-get update -qq >/dev/null && apt-get install -y -qq gnucobol >/dev/null && cobc -x -free {file} -o a.out && ./a.out",
            d,
        ),
        "05",
    )


@runner("c")
def _(d, file):
    return sh(f"cc {file} -o a.out && ./a.out", d), "42"


@runner("php")
def _(d, file):
    return sh(f"php {file}", d), "<li>Item 3</li>"


@runner("javascript")
def _(d, file):
    return sh(f"node --check {file} && echo SINTAXE-OK", d), "SINTAXE-OK"


@runner("typescript")
def _(d, file):  # erro intencional: precisa dar TS2345
    rc, out = sh(f"npx --yes -p typescript tsc --noEmit {file}", d)
    return (0 if "TS2345" in out else 1, out), "TS2345"


@runner("java")
def _(d, file):
    return docker("eclipse-temurin:21-jdk-alpine", "javac Main.java && java Main", d), "Ol"


@runner("csharp")
def _(d, file):
    return (
        docker(
            "mcr.microsoft.com/dotnet/sdk:8.0",
            "dotnet new console -o app --force >/dev/null && cp Program.cs app/Program.cs && cd app && dotnet run",
            d,
        ),
        "Olá, mundo!",
    )


@runner("cpp")
def _(d, file):
    return sh(f"c++ -std=c++17 {file} -o a.out && ./a.out", d), "3"


@runner("rust")
def _(d, file):  # erro intencional: use after move (E0382)
    rc, out = sh(f"rustc {file} -o a.out", d)
    return (0 if "E0382" in out else 1, out), "E0382"


@runner("go")
def _(d, file):
    return sh(f"go run {file}", d), "goroutine"


@runner("python")
def _(d, file):
    open(os.path.join(d, "vendas.csv"), "w").write("valor\n10\n20\n30\n")
    return sh(f"uv run --with pandas python {file}", d), "Média: 20.00"


@runner("lua")
def _(d, file):
    return docker("alpine:3.20", f"apk add -q lua5.4 && lua5.4 {file}", d), "Olá, mundo"


@runner("elixir")
def _(d, file):
    return docker("elixir:1.16-alpine", f"elixir {file}", d), "Olá, mundo!"


@runner("sql")
def _(d, file):
    ddl = "CREATE TABLE usuarios(nome TEXT, cidade TEXT); INSERT INTO usuarios VALUES('Ana','Recife'),('Bia','Lima'),('Caio','Recife');"
    return sh(f'sqlite3 :memory: "{ddl}" < /dev/null; (echo "{ddl}"; cat {file}) | sqlite3', d), "Ana"


failures = []
with open("validation_codes.log", "a") as log:
    for i in ids:
        c = SOURCE[i]
        if i not in R:
            print(f"{i}: sem runner (não validado)")
            continue
        d = tempfile.mkdtemp(prefix=f"cod_{i}_")
        file = c["file"]
        open(os.path.join(d, file), "w").write(c["code"] + "\n")
        try:
            (rc, out), expected = R[i](d, file)
        except Exception as e:
            rc, out, expected = 1, f"EXCEÇÃO {e}", ""
        ok = rc == 0 and expected in out
        print(f"{i}: {'OK' if ok else 'FAILED'}  {out[:160]!r}")
        log.write(f"{i} {'OK' if ok else 'FAILED'} :: {out[:400]}\n")
        if not ok:
            failures.append(i)
if failures:
    print("FALHAS:", failures)
    sys.exit(1)
print("todos os códigos validados")
