from pathlib import Path
import shutil
import re
import os
from dotenv import load_dotenv

load_dotenv()

# Pastas existentes
input = os.getenv("camada_silver")
output = os.getenv("camada_gold")

input_dir = Path(input)
output_dir = Path(output)


def limpar_tabela(linha):
    """
    Limpa excesso de '-' dentro das células das tabelas,
    mas mantém os '-' necessários na linha separadora do Markdown.
    """

    if "|" not in linha:
        return linha

    partes = linha.split("|")
    novas_partes = []

    for parte in partes:
        conteudo = parte.strip()

        if not conteudo:
            novas_partes.append("")
            continue

        if re.fullmatch(r"-{3,}", conteudo):
            novas_partes.append("")
            continue

        conteudo = re.sub(r"-{3,}", " ", conteudo)
        conteudo = re.sub(r" {2,}", " ", conteudo).strip()
        novas_partes.append(conteudo)

    return "|".join(novas_partes)


def limpar_texto(texto):
    """
    Aplica as regras de limpeza de caracteres, listas, tabelas e
    espaçamentos em conteúdos de texto (.md e .json).
    """
    linhas = texto.splitlines()
    resultado = []

    for linha in linhas:
        # NORMALIZAÇÃO DE LISTAS
        linha = re.sub(r"^\s*-\s*&lt;\s*", "- ", linha)
        linha = re.sub(r"^\s*-\s*«\s*", "- ", linha)
        linha = re.sub(r"^\s*-\s*n\s+", "- ", linha)

        # TABELAS
        if "|" in linha:
            linha = limpar_tabela(linha)

        # ESPAÇOS DUPLICADOS
        linha = re.sub(r" {2,}", " ", linha)

        # EXCESSO DE PONTOS
        linha = re.sub(r"\.{4,}", "...", linha)

        # ESPAÇOS NO INÍCIO E FIM
        linha = linha.strip()

        resultado.append(linha)

    # REMOVE EXCESSO DE LINHAS VAZIAS
    texto_limpo = "\n".join(resultado)
    texto_limpo = re.sub(r"\n{3,}", "\n\n", texto_limpo)

    return texto_limpo


def main():
    if not input_dir.exists():
        print(f"ERRO: pasta de entrada não encontrada: {input_dir}")
        return

    # Garante que a pasta de saída existe
    output_dir.mkdir(parents=True, exist_ok=True)

    # Recorre recursivamente todas as pastas e arquivos
    for item in input_dir.rglob("*"):
        caminho_relativo = item.relative_to(input_dir)
        destino = output_dir / caminho_relativo

        # Se for um diretório, recria a pasta no destino
        if item.is_dir():
            destino.mkdir(parents=True, exist_ok=True)
            continue

        # Processa arquivos de texto (.md e .json) com a limpeza
        if item.suffix.lower() in [".md", ".json"]:
            print(f"Limpando e copiando: {caminho_relativo}")
            try:
                texto = item.read_text(encoding="utf-8")
                texto_limpo = limpar_texto(texto)
                destino.parent.mkdir(parents=True, exist_ok=True)
                destino.write_text(texto_limpo, encoding="utf-8")
            except Exception as e:
                print(f"Erro ao processar {item.name}: {e}")

        # Copia todos os outros tipos de arquivo (ex: .jpeg, .jpg, .png) sem alterações
        else:
            print(f"Copiando arquivo: {caminho_relativo}")
            destino.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, destino)

    print("\nProcessamento concluído com sucesso.")


if __name__ == "__main__":
    main()