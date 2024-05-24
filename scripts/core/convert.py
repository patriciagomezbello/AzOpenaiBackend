import json
import os

import pdfkit
from md2pdf.core import md2pdf
from PIL import Image
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

pdfkit_options = {"encoding": "UTF-8"}


def convert_website_to_pdf(site_url, output):
    # Konvertieren der Startseite in das erste PDF-Dokument
    try:
        pdfkit.from_url(site_url, output)
        print("PDF was created successfully")
    except IOError:
        print("Error, PDF was not created")


def convert_files(folder):
    # handle data2convert folder to get a unique approach only using pdf files
    for root, dirs, files in os.walk(folder):
        for file in files:
            # create filepath and targetpath and ensure the directories will be created
            file_path = os.path.join(root, file)
            target = file_path.replace("data2convert/", "data/").rsplit(".", 1)[0] + ".pdf"
            os.makedirs(os.path.dirname(target), exist_ok=True)

            if file.endswith(".md"):
                md2pdf(
                    target,
                    md_content=None,
                    md_file_path=file_path,
                    css_file_path=None,
                    base_url=None,
                )

            elif file.endswith(".html"):
                pdfkit.from_file(file_path, target, options=pdfkit_options)

            elif file.endswith(".txt"):
                pdfkit.from_file(file_path, target, options=pdfkit_options)

            # handle pictures
            elif file.endswith(".jpg") or file.endswith(".jpeg") or file.endswith(".png"):
                thecanvas = canvas.Canvas(target, pagesize=A4)
                img = Image.open(file_path)
                img_width, img_height = img.size
                aspect_ratio = img_width / img_height
                canvas_width, canvas_height = A4
                if aspect_ratio > 1:
                    # Bild ist breiter als hoch, Skalierung an der Breite orientieren
                    img_width = canvas_width
                    img_height = int(img_width / aspect_ratio)
                else:
                    # Bild ist höher als breit, Skalierung an der Höhe orientieren
                    img_height = canvas_height
                    img_width = int(img_height * aspect_ratio)
                x = (canvas_width - img_width) / 2
                y = (canvas_height - img_height) / 2
                thecanvas.drawImage(file_path, x, y, width=img_width, height=img_height)
                # PDF-Dokument speichern
                thecanvas.save()

            elif file == "pages.json":
                with open(file_path) as json_file:
                    # Load the JSON data
                    data = json.load(json_file)

                # Loop through each key-value pair and print them separately
                for key, value in data.items():
                    print(f"{key}.pdf will be created from {value}")
                    try:
                        url_target = target.replace("pages", key)
                        convert_website_to_pdf(value, url_target)
                    except Exception as e:
                        print(f"Error creating PDF {key} from URL: {value}, Error: {str(e)}")

            elif file.endswith(".json"):
                print("please rename json files with URLs to -> pages.json")
