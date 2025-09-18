"""
   This module provides functions for converting json to html and formatting
   it into a proper HTML page. All hardcoded stuff is here!
"""
import datetime
import json
from bs4 import BeautifulSoup as Bs


"""
   Return JSON rendered into HTML table
"""
def convert2page(input_data: str, script_path: str, instance: str):
    html = ("<!DOCTYPE html><head><meta charset=\"UTF-8\"><title>Config Scanner</title> \
            <link rel=\"stylesheet\" href=\"css/config_scanner.css\"> \
            <style>body { font-family: sans-serif; padding: 20px; }select { margin-bottom: 20px; } \
            pre { background: #f4f4f4; padding: 10px; border-radius: 8px; }</style><script type=\"text/javascript\"> \
            readJson = function() { return " + convert2datachunk(input_data) + "} </script> </head>" +
            "<body><h2>Select an Assay and version to list the enabled workflows for [ " + instance + " ] shesmu</h2> \
            <label for=\"assay\">Assay:</label><select id=\"assay\"><br> \
            </select><label for=\"version\">Version:</label><select id=\"version\"></select><br> \
            <pre id=\"output\"></pre><script>" + append_script(script_path) + "</script>" + today_date() + "</body></html>")
    soup = Bs(html, "html.parser")
    return soup.prettify()


"""
   Return date wrapped in div
"""
def today_date() -> str:
    today = datetime.date.today()
    formatted_today = today.strftime("%A %d. %B %Y")
    return "<div>Updated on: " + formatted_today + "</div>"


"""
   Using supplied data file path return html-compliant block
"""
def convert2datachunk(input: str) -> str:
    try:
        with open(input, 'r') as inJson:
            data_chunk = json.load(inJson)
            return json.dumps(data_chunk)
    except FileNotFoundError:
        print(f'ERROR: Could not find file {input}')
    except ValueError:
        print('ERROR: Could not read JSON data')
    return "{}"


"""
   Read the text of the script and return it as a str to embed into HTML page
"""
def append_script(path: str)->str:
    script_text = ""
    try:
        with open(path, 'r') as inScript:
            lines = inScript.readlines()
        for l in lines:
            script_text += l
    except:
        print(f"ERROR: Could not read from {path} to load the javascript")
        exit(1)
    return script_text
