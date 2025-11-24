import base64
import hashlib
import html
import os
import re
import sys
import time

import pycountry


def name_from_path(file_path, files_directory):
    path_parts = file_path.split("/")
    file_name = "_".join(path_parts[path_parts.index(files_directory) + 1 :]).replace("/", "_")
    return file_name


def table_to_html(table):
    table_html = "<table>"
    rows = [
        sorted(
            [cell for cell in table.cells if cell.row_index == i],
            key=lambda cell: cell.column_index,
        )
        for i in range(table.row_count)
    ]
    for row_cells in rows:
        table_html += "<tr>"
        for cell in row_cells:
            tag = "th" if (cell.get("kind") == "columnHeader" or cell.get("kind") == "rowHeader") else "td"
            cell_spans = ""
            if cell["columnIndex"] > 1:
                cell_spans += f" colSpan={cell['columnIndex']}"
            if cell["rowIndex"] > 1:
                cell_spans += f" rowSpan={cell['rowIndex']}"
            table_html += f"<{tag}{cell_spans}>{html.escape(cell['content'])}</{tag}>"
        table_html += "</tr>"
    table_html += "</table>"
    return table_html


def detectLang(text, detector, defaultLang="de"):
    try:
        lang = str(detector.detect_language_of(text))
        language = lang.split(".")[1].capitalize()
        iso_lang = pycountry.languages.get(name=language).alpha_2
        return iso_lang
    except Exception as e:
        print(e)
        return defaultLang


# Define function to get MD5 hash of a file
def get_md5_hash(file_path):
    with open(file_path, "rb") as f:
        file_hash = hashlib.md5()
        while chunk := f.read(8192):
            file_hash.update(chunk)
        return file_hash.digest()


def invalid_filename(string):
    pattern = r".+-\d+\.pdf$"
    if re.search(pattern, string) or "'" in string:
        return True
    return False


def file_path_to_id(file_path):
    filename_ascii = re.sub("[^0-9a-zA-Z_-]", "_", file_path)
    filename_hash = base64.b16encode(file_path.encode("utf-8")).decode("ascii")
    return f"file-{filename_ascii}-{filename_hash}"


# def url_to_id(url, counter):
#     url_hash = base64.b16encode(url.encode("utf-8")).decode("ascii")
#     return f"url-{url_hash}-{str(counter)}"


def url_to_id(url: str, counter_dict: dict[str, int]):
    # check if url is already in counter_dict, if not, add it and initialize with 0
    if counter_dict.get(url) is not None:
        counter_dict[url] += 1
    else:
        counter_dict[url] = 0

    # add counter value and increase counter in counter_dict for the source

    url_hash = base64.b16encode(url.encode("utf-8")).decode("ascii")
    return f"url-{url_hash}-{str(counter_dict[url])}"


# this function will create similar ids, but will create potential ids for cleanup
def url_to_id_cleanup(url: str, number: int):
    # add counter value and increase counter in counter_dict for the source

    url_hash = base64.b16encode(url.encode("utf-8")).decode("ascii")
    return f"url-{url_hash}-{str(number)}"


def check_time(start_time, seconds=300):
    current_time = time.time()
    elapsed_time = current_time - start_time
    if elapsed_time >= seconds:
        return True


def delete_uncompatible_files(directory):
    allowed_extensions = os.getenv("ALLOWED_EXTENSIONS", ".pdf,.jpg,.jpeg,.png,.tiff,.bmp,.docx,.xlsx,.pptx,.json").split(",")
    for root, dirs, files in os.walk(directory):
        for file in files:
            if not file.lower().endswith(tuple(allowed_extensions)):
                file_path = os.path.join(root, file)
                try:
                    os.remove(file_path)
                    print(f"Deleted: {file_path}")
                except FileNotFoundError:
                    print(f"File not found: {file_path}")
                except Exception as e:
                    print(f"Error deleting {file_path}: {e}")
                    sys.exit(99)
