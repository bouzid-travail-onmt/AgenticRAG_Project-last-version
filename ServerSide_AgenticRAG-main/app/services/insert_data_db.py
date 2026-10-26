import gridfs
from typing import List, AsyncGenerator, Union
from fastapi import UploadFile
from io import BytesIO
from openpyxl import load_workbook
from pymongo.database import Database
from app.db import get_mongo_client


def get_collections(db: Database):
    """Retourne les instances GridFS séparées pour PDF, Excel, JSON, TXT + collection URLs."""
    return {
        "pdfs": gridfs.GridFS(db, collection="pdfs"),
        "excels": gridfs.GridFS(db, collection="excels"),
        "training_data_json": gridfs.GridFS(db, collection="training_data_json"),
        "training_data_txt": gridfs.GridFS(db, collection="training_data_txt"),
        "urls_scraping": db["urls_scraping"],
    }


async def process_and_store_data(
    files: List[Union[UploadFile, dict]],
    urls: List[str]
) -> AsyncGenerator[str, None]:
    """
    Traite et stocke les fichiers et URLs dans MongoDB avec logs en temps réel.
    PDFs, Excels, JSON et TXT sont stockés via GridFS dans leurs collections respectives.
    """
    db = get_mongo_client()
    collections = get_collections(db)

    yield "🔄 Démarrage du traitement...\n"

    inserted_files = 0
    existing_files = 0
    errors = 0


    for file in files:
        try:
            filename = None
            
            content = None

            # Lecture du contenu selon le type
            if isinstance(file, UploadFile):
                filename = file.filename
                content = await file.read()
            elif isinstance(file, dict):
                filename = file.get("filename") or file.get("name")
                content = file.get("content")
                if isinstance(content, str):
                    content = content.encode("utf-8")

            if not filename or not content:
                yield f"⚠️ Fichier invalide : {file}\n"
                continue

            ext = filename.lower().split(".")[-1]

            # --- Gestion des PDFs via GridFS ---
            if ext == "pdf":
                fs_pdf = collections["pdfs"]
                if not fs_pdf.exists({"filename": filename}):
                    fs_pdf.put(content, filename=filename)
                    inserted_files += 1
                    yield f"✅ PDF inséré dans GridFS : {filename}\n"
                else:
                    existing_files += 1
                    yield f"⚠️ PDF déjà existant : {filename}\n"

            # --- Gestion des fichiers Excel via GridFS ---
            elif ext in ["xls", "xlsx"]:
                fs_excel = collections["excels"]

                # 🔍 Ouverture du fichier Excel en mémoire
                workbook = load_workbook(filename=BytesIO(content), read_only=True)
                sheet_names = workbook.sheetnames

                # 📄 CAS 1 — Excel avec UNE seule feuille
                if len(sheet_names) == 1:
                    if not fs_excel.exists({"filename": filename}):
                        fs_excel.put(content, filename=filename)
                        inserted_files += 1
                        yield f"✅ Excel (1 feuille) inséré dans GridFS : {filename}\n"
                    else:
                        existing_files += 1
                        yield f"⚠️ Excel déjà existant : {filename}\n"

                # 📚 CAS 2 — Excel MULTI-feuilles
                else:
                    base_name = filename.rsplit(".", 1)[0]
                    extension = filename.rsplit(".", 1)[1]

                    yield f"📑 Excel multi-feuilles détecté ({len(sheet_names)} feuilles) : {filename}\n"

                    for sheet_name in sheet_names:
                        try:
                            # 🔧 Création d’un nouveau classeur pour UNE feuille
                            single_wb = load_workbook(filename=BytesIO(content), read_only=False)
                            ws = single_wb[sheet_name]

                            # ❌ Supprimer toutes les autres feuilles
                            for ws_name in list(single_wb.sheetnames):
                                if ws_name != sheet_name:
                                    del single_wb[ws_name]

                            # 🧹 1. Supprimer toutes les lignes entièrement vides
                            for row_idx in range(ws.max_row, 0, -1):
                                if all(
                                    str(ws.cell(row=row_idx, column=col_idx).value).strip() in ("", "None")
                                    for col_idx in range(1, ws.max_column + 1)
                                ):
                                    ws.delete_rows(row_idx)

                            # 🧹 2. Supprimer toutes les colonnes entièrement vides
                            for col_idx in range(ws.max_column, 0, -1):
                                if all(
                                    str(ws.cell(row=row_idx, column=col_idx).value).strip() in ("", "None")
                                    for row_idx in range(1, ws.max_row + 1)
                                ):
                                    ws.delete_cols(col_idx)

                            # 🧹 3. Supprimer les lignes d’index ou décalages en haut
                            while ws.max_row > 0:
                                first_row_values = [
                                    ws.cell(row=1, column=col_idx).value
                                    for col_idx in range(1, ws.max_column + 1)
                                ]
                                if all(val is None or (isinstance(val, (int, float, str)) and str(val).strip() == "")
                                       for val in first_row_values):
                                    ws.delete_rows(1)
                                else:
                                    break

                            # 🧹 4. Supprimer la ligne et la colonne contenant "index" si elles existent
                            row_to_delete = None
                            col_to_delete = None
                            for row_idx in range(1, ws.max_row + 1):
                                for col_idx in range(1, ws.max_column + 1):
                                    cell_val = ws.cell(row=row_idx, column=col_idx).value
                                    if cell_val and str(cell_val).strip().lower() == "index":
                                        row_to_delete = row_idx
                                        col_to_delete = col_idx
                                        break
                                if row_to_delete and col_to_delete:
                                    break
                            if row_to_delete:
                                ws.delete_rows(row_to_delete)
                            if col_to_delete:
                                ws.delete_cols(col_to_delete)

                            # 💾 Sauvegarde de la feuille nettoyée en mémoire
                            output = BytesIO()
                            single_wb.save(output)
                            output.seek(0)

                            # 🏷️ Nom logique : nomfichier_nomclasseur.xlsx
                            sheet_filename = f"{base_name}_{sheet_name}.{extension}"

                            # 📥 Stockage GridFS
                            if not fs_excel.exists({"filename": sheet_filename}):
                                fs_excel.put(output.read(), filename=sheet_filename)
                                inserted_files += 1
                                yield f"✅ Feuille insérée : {sheet_filename}\n"
                            else:
                                existing_files += 1
                                yield f"⚠️ Feuille déjà existante : {sheet_filename}\n"

                        except Exception as e:
                            errors += 1
                            yield f"❌ Erreur feuille {sheet_name} ({filename}) : {e}\n"

            # --- Gestion des fichiers JSON via GridFS ---
            elif ext == "json":
                fs_json = collections["training_data_json"]
                if not fs_json.exists({"filename": filename}):
                    fs_json.put(content, filename=filename)
                    inserted_files += 1
                    yield f"✅ JSON inséré dans GridFS : {filename}\n"
                else:
                    existing_files += 1
                    yield f"⚠️ JSON déjà existant : {filename}\n"

            # --- Gestion des fichiers TXT via GridFS ---
            elif ext == "txt":
                fs_txt = collections["training_data_txt"]
                if not fs_txt.exists({"filename": filename}):
                    fs_txt.put(content, filename=filename)
                    inserted_files += 1
                    yield f"✅ TXT inséré dans GridFS : {filename}\n"
                else:
                    existing_files += 1
                    yield f"⚠️ TXT déjà existant : {filename}\n"

            else:
                yield f"⚠️ Type de fichier non pris en charge : {filename}\n"

        except Exception as e:
            errors += 1
            yield f"❌ Erreur lors du traitement de {getattr(file, 'filename', 'inconnu')} : {e}\n"

    # --- Traitement des URLs ---
    if urls:
        yield "🌐 Traitement des URLs...\n"
        for url in urls:
            try:
                if collections["urls_scraping"].count_documents({"url": url}) == 0:
                    collections["urls_scraping"].insert_one({"url": url})
                    inserted_files += 1
                    yield f"✅ URL ajoutée : {url}\n"
                else:
                    existing_files += 1
                    yield f"⚠️ URL déjà présente : {url}\n"
            except Exception as e:
                errors += 1
                yield f"❌ Erreur lors de l'ajout de l'URL {url} : {e}\n"

    # --- Résumé final ---
    summary = (
        f"✅ {inserted_files} insérés | "
        f"⚠️ {existing_files} déjà existants | "
        f"❌ {errors} erreurs"
    )
    yield f"🚀 Traitement terminé — {summary}\n"
