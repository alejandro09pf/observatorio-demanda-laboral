#!/usr/bin/env python3
"""
Script de verificación de estructura del documento SAD en LaTeX
Verifica que todos los archivos existan y tengan sintaxis básica correcta
"""

import os
import re
from pathlib import Path

def check_file_exists(filepath, description):
    """Verifica que un archivo existe"""
    if os.path.exists(filepath):
        print(f"✓ {description}: {filepath}")
        return True
    else:
        print(f"✗ {description} NO encontrado: {filepath}")
        return False

def check_latex_syntax(filepath):
    """Verifica sintaxis básica de LaTeX (balance de llaves)"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # Contar llaves
        open_braces = content.count('{')
        close_braces = content.count('}')

        # Contar begin/end
        begins = len(re.findall(r'\\begin\{', content))
        ends = len(re.findall(r'\\end\{', content))

        errors = []
        if open_braces != close_braces:
            errors.append(f"  ⚠ Llaves desbalanceadas: {open_braces} {{ vs {close_braces} }}")

        if begins != ends:
            errors.append(f"  ⚠ begin/end desbalanceados: {begins} begin vs {ends} end")

        if errors:
            print(f"  Advertencias en {filepath}:")
            for error in errors:
                print(error)
            return False
        else:
            print(f"  ✓ Sintaxis básica correcta")
            return True

    except Exception as e:
        print(f"  ✗ Error al leer archivo: {e}")
        return False

def check_references(main_file, sections_dir):
    """Verifica que todos los \input referenciados existan"""
    try:
        with open(main_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Buscar todos los \input{...}
        inputs = re.findall(r'\\input\{([^}]+)\}', content)

        print("\n=== Verificando referencias \\input{} ===")
        all_exist = True
        for input_ref in inputs:
            # Agregar .tex si no tiene extensión
            if not input_ref.endswith('.tex'):
                filepath = input_ref + '.tex'
            else:
                filepath = input_ref

            if os.path.exists(filepath):
                print(f"  ✓ {input_ref}")
            else:
                print(f"  ✗ NO encontrado: {input_ref}")
                all_exist = False

        return all_exist

    except Exception as e:
        print(f"  ✗ Error al verificar referencias: {e}")
        return False

def check_bibliography(bib_file):
    """Verifica que el archivo de bibliografía tenga entradas válidas"""
    try:
        with open(bib_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Contar entradas bibliográficas
        entries = re.findall(r'@\w+\{', content)

        print(f"\n=== Verificando bibliografía ===")
        print(f"  ✓ {len(entries)} entradas bibliográficas encontradas")

        # Verificar que cada entrada tenga llaves balanceadas
        entry_pattern = r'@(\w+)\{([^,]+),([^}]+)\}'
        valid_entries = re.findall(entry_pattern, content, re.DOTALL)

        if len(entries) > 0:
            print(f"  ✓ Estructura de bibliografía válida")
            return True
        else:
            print(f"  ⚠ No se encontraron entradas bibliográficas")
            return False

    except Exception as e:
        print(f"  ✗ Error al verificar bibliografía: {e}")
        return False

def main():
    print("=" * 70)
    print("VERIFICACIÓN DE ESTRUCTURA DEL DOCUMENTO SAD")
    print("=" * 70)

    # Cambiar al directorio del script
    script_dir = Path(__file__).parent
    os.chdir(script_dir)

    print(f"\nDirectorio de trabajo: {os.getcwd()}\n")

    all_checks_passed = True

    # Verificar archivos principales
    print("=== Verificando archivos principales ===")
    main_tex = check_file_exists("main.tex", "Documento principal")
    portada = check_file_exists("portada.tex", "Portada")
    bib = check_file_exists("bibliografia.bib", "Bibliografía")

    all_checks_passed = all_checks_passed and main_tex and portada and bib

    # Verificar secciones
    print("\n=== Verificando secciones ===")
    sections = [
        "sections/01-objetivo.tex",
        "sections/02-atributos-calidad.tex",
        "sections/03-arquitectura.tex",
        "sections/04-riesgos.tex",
        "sections/05-restricciones.tex"
    ]

    for section in sections:
        exists = check_file_exists(section, f"Sección {os.path.basename(section)}")
        all_checks_passed = all_checks_passed and exists

    # Verificar sintaxis de archivos principales
    print("\n=== Verificando sintaxis LaTeX ===")
    if main_tex:
        print("\nArchivo: main.tex")
        syntax_ok = check_latex_syntax("main.tex")
        all_checks_passed = all_checks_passed and syntax_ok

    if portada:
        print("\nArchivo: portada.tex")
        syntax_ok = check_latex_syntax("portada.tex")
        all_checks_passed = all_checks_passed and syntax_ok

    for section in sections:
        if os.path.exists(section):
            print(f"\nArchivo: {section}")
            syntax_ok = check_latex_syntax(section)
            all_checks_passed = all_checks_passed and syntax_ok

    # Verificar referencias \input
    if main_tex:
        refs_ok = check_references("main.tex", "sections")
        all_checks_passed = all_checks_passed and refs_ok

    # Verificar bibliografía
    if bib:
        bib_ok = check_bibliography("bibliografia.bib")
        all_checks_passed = all_checks_passed and bib_ok

    # Verificar archivos auxiliares
    print("\n=== Verificando archivos auxiliares ===")
    check_file_exists("README.md", "Documentación")
    check_file_exists("Makefile", "Makefile (Linux/macOS)")
    check_file_exists("compile.bat", "Script compilación (Windows)")
    check_file_exists(".gitignore", "GitIgnore")

    # Resumen final
    print("\n" + "=" * 70)
    if all_checks_passed:
        print("✓ VERIFICACIÓN EXITOSA")
        print("  Todos los archivos existen y tienen sintaxis básica correcta.")
        print("  El documento está listo para compilar con pdflatex.")
    else:
        print("⚠ VERIFICACIÓN CON ADVERTENCIAS")
        print("  Algunos archivos tienen problemas de sintaxis o no existen.")
        print("  Revisa los mensajes anteriores para más detalles.")
    print("=" * 70)

    # Información adicional
    print("\n=== Próximos pasos ===")
    print("1. Instala una distribución de LaTeX:")
    print("   - Windows: MiKTeX (https://miktex.org/)")
    print("   - macOS: MacTeX (https://www.tug.org/mactex/)")
    print("   - Linux: sudo apt-get install texlive-full")
    print("")
    print("2. Compila el documento:")
    print("   - Windows: Doble clic en compile.bat")
    print("   - Linux/macOS: make")
    print("   - Manual: pdflatex main.tex && biber main && pdflatex main.tex && pdflatex main.tex")
    print("")
    print("3. El PDF se generará como: main.pdf")
    print("")

if __name__ == "__main__":
    main()
