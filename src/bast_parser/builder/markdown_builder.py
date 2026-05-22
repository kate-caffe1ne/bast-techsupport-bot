from src.bast_parser.models.product import Offer

def create_markdown_file_content(
    offer: Offer,
    product_page_md: str,
    manual_text: str
) -> str:
    """Builds the final Markdown content for a product based on a template."""
    
    # Helper for document links
    def get_doc_url(doc_url):
        return str(doc_url) if doc_url else "НЕДОСТУПНО"

    # Prepare picture list
    pictures_list = [f"- Изображение {i+1}: {pic.url}" for i, pic in enumerate(offer.pictures)]
    pictures_md = "\n".join(pictures_list) if pictures_list else "Изображения отсутствуют."

    # Prepare documents section
    docs = offer.documents
    if docs:
        documents_md = f"""- Руководство пользователя (Паспорт): {get_doc_url(docs.documentsUserManual)}
- Сертификат ТР ТС: {get_doc_url(docs.documentsCertificatesTrts)}
- Декларация 037: {get_doc_url(docs.documentsCertificateDeclaration037)}
- Прочие сертификаты: {get_doc_url(docs.documentsCertificateCertification)}
- BIM-модель Revit: {get_doc_url(docs.documentsBimModelsRevit)}
- BIM-модель AutoCAD: {get_doc_url(docs.documentsBimModelsAutocad)}"""
    else:
        documents_md = "Раздел с документами отсутствует."

    # Assemble the final Markdown file
    content = f"""# КАРТОЧКА ТОВАРА: {offer.model}
**Артикул:** {offer.vendorCode}
**Ссылка на сайт:** {offer.url}

## 1. ОБЩЕЕ ОПИСАНИЕ И ТТХ
{product_page_md}

## 2. МЕДИА-РЕСУРСЫ И ФОТО
{pictures_md}

## 3. ОФИЦИАЛЬНЫЕ ДОКУМЕНТЫ И ССЫЛКИ
{documents_md}

## 4. ПОЛНЫЙ ТЕКСТ РУКОВОДСТВА ПОЛЬЗОВАТЕЛЯ (ИЗВЛЕЧЕНО ИЗ PDF)
--- НАЧАЛО ТЕКСТА ИНСТРУКЦИИ ---
{manual_text if manual_text else 'Текст руководства не был извлечен.'}
--- КОНЕЦ ТЕКСТА ИНСТРУКЦИИ ---
"""
    
    return content