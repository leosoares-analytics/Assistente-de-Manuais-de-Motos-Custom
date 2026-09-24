from pathlib import Path
from shutil import rmtree
from datetime import datetime
from dotenv import load_dotenv

from docling.document_converter import (
    DocumentConverter,
    PdfFormatOption,
)

from docling.datamodel.pipeline_options import PdfPipelineOptions

from docling_core.types.doc import (
    ImageRefMode,
    PictureItem,
    TableItem,
)

import os
import re
import json


# ============================================================
# CONFIGURAÇÃO
# ============================================================

load_dotenv()

input_path = os.getenv("camada_bronze")
output_path = os.getenv("camada_silver")

#input_path = os.getenv("input_teste_pdf")
#output_path = os.getenv("output_teste_pdf")

if not input_path:
    raise ValueError(
        "A variável 'input_teste_pdf' não foi encontrada no .env"
    )

if not output_path:
    raise ValueError(
        "A variável 'output_teste_pdf' não foi encontrada no .env"
    )


INPUT_DIR = Path(input_path)
OUTPUT_DIR = Path(output_path)


if not INPUT_DIR.exists():
    raise FileNotFoundError(
        f"A pasta de entrada não existe: {INPUT_DIR}"
    )


OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# CONFIGURAÇÃO DO DOCLING
# ============================================================

pipeline_options = PdfPipelineOptions()

# Gera imagens das páginas
pipeline_options.generate_page_images = True

# Gera imagens de figuras, diagramas, fotos etc.
pipeline_options.generate_picture_images = True

# Escala das imagens
pipeline_options.images_scale = 2.0


converter = DocumentConverter(
    format_options={
        "pdf": PdfFormatOption(
            pipeline_options=pipeline_options
        )
    }
)


# ============================================================
# FUNÇÃO:
# VERIFICAR SE O ARQUIVO JÁ ESTÁ ATUALIZADO
# ============================================================

def arquivo_esta_atualizado(
    pdf_path: Path,
    md_path: Path,
    metadata_path: Path,
) -> bool:

    """
    Verifica se Markdown e metadata existem e estão
    atualizados em relação ao PDF.
    """

    if not md_path.exists():
        return False

    if not metadata_path.exists():
        return False

    data_pdf = pdf_path.stat().st_mtime
    data_md = md_path.stat().st_mtime
    data_metadata = metadata_path.stat().st_mtime

    return (
        data_md >= data_pdf
        and data_metadata >= data_pdf
    )


# ============================================================
# FUNÇÃO:
# SALVAR IMAGEM
# ============================================================

def salvar_imagem(
    imagem,
    caminho: Path,
) -> bool:

    """
    Salva uma imagem PIL em PNG.
    """

    if imagem is None:
        return False

    try:

        caminho.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        imagem.save(
            caminho,
            format="PNG"
        )

        return (
            caminho.exists()
            and caminho.stat().st_size > 0
        )

    except Exception as erro:

        print(
            f"      Erro ao salvar imagem "
            f"{caminho.name}: {erro}"
        )

        return False


# ============================================================
# FUNÇÃO:
# EXTRAIR IMAGENS
# ============================================================

def extrair_imagens(
    documento,
    pdf_path: Path,
    image_dir: Path,
):
    """
    Extrai figuras e tabelas identificadas pelo Docling.

    Retorna uma lista contendo os metadados das imagens.
    """

    image_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    imagens_metadata = []

    contador_figuras = 0
    contador_tabelas = 0


    print()
    print(
        "  Procurando figuras e tabelas..."
    )


    for item, _level in documento.iterate_items():

        # ====================================================
        # FIGURAS
        # ====================================================

        if isinstance(item, PictureItem):

            contador_figuras += 1

            image_id = (
                f"{pdf_path.stem}_figura_"
                f"{contador_figuras:03d}"
            )

            filename = f"{image_id}.png"

            image_path = (
                image_dir / filename
            )


            print(
                f"    Figura "
                f"{contador_figuras:03d}"
            )


            try:

                imagem = item.get_image(
                    documento
                )


                sucesso = salvar_imagem(
                    imagem,
                    image_path
                )


                if not sucesso:

                    print(
                        "      Não foi possível "
                        "salvar a imagem."
                    )

                    continue


                # --------------------------------------------
                # PÁGINA
                # --------------------------------------------

                page_number = None


                if item.prov:

                    try:

                        page_number = (
                            item.prov[0].page_no
                        )

                    except Exception:

                        page_number = None


                # --------------------------------------------
                # METADATA
                # --------------------------------------------

                imagens_metadata.append(
                    {
                        "id": image_id,

                        "filename": filename,

                        "path": (
                            f"images/"
                            f"{pdf_path.stem}/"
                            f"{filename}"
                        ),

                        "type": "picture",

                        "page": page_number,
                    }
                )


                print(
                    f"      ✓ {filename}"
                )


                if page_number:

                    print(
                        f"      Página: "
                        f"{page_number}"
                    )


            except Exception as erro:

                print(
                    f"      Erro ao extrair "
                    f"figura: {erro}"
                )


        # ====================================================
        # TABELAS
        # ====================================================

        elif isinstance(item, TableItem):

            contador_tabelas += 1

            image_id = (
                f"{pdf_path.stem}_tabela_"
                f"{contador_tabelas:03d}"
            )

            filename = f"{image_id}.png"

            image_path = (
                image_dir / filename
            )


            print(
                f"    Tabela "
                f"{contador_tabelas:03d}"
            )


            try:

                imagem = item.get_image(
                    documento
                )


                sucesso = salvar_imagem(
                    imagem,
                    image_path
                )


                if not sucesso:

                    print(
                        "      Não foi possível "
                        "salvar a tabela."
                    )

                    continue


                # --------------------------------------------
                # PÁGINA
                # --------------------------------------------

                page_number = None


                if item.prov:

                    try:

                        page_number = (
                            item.prov[0].page_no
                        )

                    except Exception:

                        page_number = None


                # --------------------------------------------
                # METADATA
                # --------------------------------------------

                imagens_metadata.append(
                    {
                        "id": image_id,

                        "filename": filename,

                        "path": (
                            f"images/"
                            f"{pdf_path.stem}/"
                            f"{filename}"
                        ),

                        "type": "table",

                        "page": page_number,
                    }
                )


                print(
                    f"      ✓ {filename}"
                )


                if page_number:

                    print(
                        f"      Página: "
                        f"{page_number}"
                    )


            except Exception as erro:

                print(
                    f"      Erro ao extrair "
                    f"tabela: {erro}"
                )


    # ========================================================
    # RESUMO
    # ========================================================

    print()

    print(
        f"  Figuras encontradas: "
        f"{contador_figuras}"
    )

    print(
        f"  Tabelas encontradas: "
        f"{contador_tabelas}"
    )

    print(
        f"  Imagens salvas: "
        f"{len(imagens_metadata)}"
    )


    return imagens_metadata


# ============================================================
# FUNÇÃO:
# INSERIR ÍNDICE DE IMAGENS NO MARKDOWN
# ============================================================

def inserir_indice_imagens(
    markdown: str,
    imagens_metadata: list,
) -> str:
    """
    Substitui os placeholders genéricos de imagem do Docling
    por referências Markdown contendo o ID e o caminho da imagem.

    Exemplo:
        <!-- image -->

    vira:

        ![bear-650_figura_001](images/bear-650/bear-650_figura_001.png)

    A associação é feita pela ordem em que os placeholders
    aparecem no Markdown e pela ordem em que as imagens/tabelas
    foram identificadas pelo Docling.
    """

    # O Docling pode gerar placeholders como:
    # <!-- image -->
    # <!-- image -->
    # etc.
    padrao = r"<!--\s*image\s*-->"

    total_placeholders = len(
        re.findall(padrao, markdown, flags=re.IGNORECASE)
    )

    if total_placeholders == 0:
        print("  Nenhum placeholder de imagem encontrado no Markdown.")
        return markdown

    if not imagens_metadata:
        print("  Nenhuma imagem disponível para indexar no Markdown.")
        return markdown

    indice = 0

    def substituir(match):
        nonlocal indice

        if indice >= len(imagens_metadata):
            return match.group(0)

        imagem = imagens_metadata[indice]

        image_id = imagem["id"]
        image_path = imagem["path"]
        image_type = imagem["type"]

        # Texto alternativo mais descritivo
        alt = f"{image_id} ({image_type})"

        indice += 1

        return f"![{alt}]({image_path})"

    markdown = re.sub(
        padrao,
        substituir,
        markdown,
        flags=re.IGNORECASE,
    )

    substituidos = min(
        total_placeholders,
        len(imagens_metadata),
    )

    print(
        f"  Índice de imagens inserido no Markdown: "
        f"{substituidos}/{total_placeholders}"
    )

    if total_placeholders != len(imagens_metadata):
        print(
            f"  ⚠ Aviso: placeholders no MD = "
            f"{total_placeholders} | "
            f"imagens no metadata = "
            f"{len(imagens_metadata)}"
        )

    return markdown


# ============================================================
# FUNÇÃO:
# GERAR METADATA
# ============================================================

def gerar_metadata(
    pdf_path: Path,
    documento,
    imagens_metadata: list,
):
    """
    Cria o arquivo metadata.json do documento.
    """

    pdf_stat = pdf_path.stat()


    metadata = {

        # ----------------------------------------------------
        # DOCUMENTO
        # ----------------------------------------------------

        "document": {

            "id": pdf_path.stem,

            "filename": pdf_path.name,

            "source_path": str(
                pdf_path.resolve()
            ),

            "file_size_bytes": (
                pdf_stat.st_size
            ),

            "modified_at": (
                datetime
                .fromtimestamp(
                    pdf_stat.st_mtime
                )
                .isoformat()
            ),

            "processed_at": (
                datetime.now().isoformat()
            ),

            "converter": "docling",

        },


        # ----------------------------------------------------
        # CONTEÚDO
        # ----------------------------------------------------

        "content": {

            "markdown": (
                f"{pdf_path.stem}.md"
            ),

            "format": "markdown",

        },


        # ----------------------------------------------------
        # IMAGENS
        # ----------------------------------------------------

        "images": imagens_metadata,


        # ----------------------------------------------------
        # ESTATÍSTICAS
        # ----------------------------------------------------

        "statistics": {

            "total_images": len(
                imagens_metadata
            ),

            "total_pictures": sum(
                1
                for image in imagens_metadata
                if image["type"] == "picture"
            ),

            "total_tables": sum(
                1
                for image in imagens_metadata
                if image["type"] == "table"
            ),

        },

    }


    return metadata


# ============================================================
# FUNÇÃO:
# PROCESSAR PDF
# ============================================================

def processar_pdf(
    pdf_path: Path,
):

    md_path = (
        OUTPUT_DIR
        / f"{pdf_path.stem}.md"
    )


    metadata_path = (
        OUTPUT_DIR
        / f"{pdf_path.stem}.metadata.json"
    )


    image_dir = (
        OUTPUT_DIR
        / "images"
        / pdf_path.stem
    )


    print()
    print("=" * 80)

    print(
        f"PDF: {pdf_path.name}"
    )


    # ========================================================
    # PROCESSAMENTO INCREMENTAL
    # ========================================================

    if arquivo_esta_atualizado(
        pdf_path,
        md_path,
        metadata_path,
    ):

        print(
            "Markdown + metadata "
            "já estão atualizados."
        )

        print(
            "Pulando arquivo."
        )

        return


    if md_path.exists():

        print(
            "Arquivo existente será "
            "reprocessado."
        )

    else:

        print(
            "Novo PDF."
        )


    # ========================================================
    # REMOVER IMAGENS ANTIGAS
    # ========================================================

    if image_dir.exists():

        print(
            "Removendo imagens antigas..."
        )

        rmtree(
            image_dir
        )


    try:

        # ====================================================
        # CONVERSÃO
        # ====================================================

        print()
        print(
            "Convertendo PDF com Docling..."
        )


        resultado = converter.convert(
            pdf_path
        )


        documento = resultado.document


        # ====================================================
        # EXTRAÇÃO DE IMAGENS
        # ====================================================

        imagens_metadata = (
            extrair_imagens(
                documento=documento,
                pdf_path=pdf_path,
                image_dir=image_dir,
            )
        )


        # ====================================================
        # EXPORTAR MARKDOWN
        # ====================================================

        print()

        print(
            "Exportando Markdown..."
        )


        markdown = (
            documento.export_to_markdown(
                image_mode=ImageRefMode.REFERENCED
            )
        )

        # --------------------------------------------------------
        # INSERIR ÍNDICE/REFERÊNCIAS DAS IMAGENS NO MARKDOWN
        # --------------------------------------------------------

        markdown = inserir_indice_imagens(
            markdown=markdown,
            imagens_metadata=imagens_metadata,
        )

        md_path.write_text(
            markdown,
            encoding="utf-8"
        )


        # ====================================================
        # GERAR METADATA
        # ====================================================

        metadata = (
            gerar_metadata(
                pdf_path=pdf_path,
                documento=documento,
                imagens_metadata=(
                    imagens_metadata
                ),
            )
        )


        metadata_path.write_text(
            json.dumps(
                metadata,
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8"
        )


        # ====================================================
        # RESULTADO
        # ====================================================

        print()

        print(
            f"✓ Markdown: "
            f"{md_path.name}"
        )

        print(
            f"✓ Metadata: "
            f"{metadata_path.name}"
        )

        print(
            f"✓ Imagens: "
            f"{len(imagens_metadata)}"
        )

        print(
            "✓ Processamento concluído."
        )


    except Exception as erro:

        print()

        print(
            f"✗ ERRO ao processar "
            f"{pdf_path.name}"
        )

        print(
            f"  {erro}"
        )


# ============================================================
# FUNÇÃO:
# BARRA DE PROGRESSO
# ============================================================

def mostrar_progresso(
    atual: int,
    total: int,
):

    largura_barra = 40


    if total == 0:

        return


    progresso = atual / total


    preenchido = int(
        largura_barra * progresso
    )


    vazio = (
        largura_barra
        - preenchido
    )


    barra = (
        "█" * preenchido
        + "░" * vazio
    )


    porcentagem = (
        progresso * 100
    )


    restantes = (
        total - atual
    )


    print(
        f"\r"
        f"Progresso: "
        f"[{barra}] "
        f"{porcentagem:6.2f}% "
        f"| Arquivos: "
        f"{atual}/{total} "
        f"| Restantes: "
        f"{restantes}",
        end="",
        flush=True,
    )


# ============================================================
# MAIN
# ============================================================

def main():

    pdf_files = sorted(
        INPUT_DIR.glob("*.pdf")
    )


    # ========================================================
    # NENHUM PDF
    # ========================================================

    if not pdf_files:

        print(
            f"Nenhum PDF encontrado em: "
            f"{INPUT_DIR}"
        )

        return


    # ========================================================
    # INFORMAÇÕES INICIAIS
    # ========================================================

    total_arquivos = len(
        pdf_files
    )


    print(
        f"PDFs encontrados: "
        f"{total_arquivos}"
    )


    print(
        f"Pasta de entrada: "
        f"{INPUT_DIR}"
    )


    print(
        f"Pasta de saída: "
        f"{OUTPUT_DIR}"
    )


    print()


    # ========================================================
    # BARRA INICIAL
    # ========================================================

    mostrar_progresso(
        atual=0,
        total=total_arquivos,
    )


    print()


    # ========================================================
    # PROCESSAMENTO
    # ========================================================

    for indice, pdf_path in enumerate(
        pdf_files,
        start=1
    ):

        processar_pdf(
            pdf_path
        )


        # ----------------------------------------------------
        # ATUALIZA PROGRESSO
        # ----------------------------------------------------

        mostrar_progresso(
            atual=indice,
            total=total_arquivos,
        )


        print()


    # ========================================================
    # FINAL
    # ========================================================

    print()
    print()

    print("=" * 80)

    print(
        f"✓ Processamento concluído: "
        f"{total_arquivos}/{total_arquivos} "
        f"arquivos."
    )

    print("=" * 80)


# ============================================================
# EXECUÇÃO
# ============================================================

if __name__ == "__main__":

    main()