"""
   This module provides functions for converting json to html and formatting
   it into a proper HTML page. All hardcoded stuff is here!
   
   Note that we pass a number of errors which is instance-specific
"""
import datetime
import json
import os.path
from collections import defaultdict
from bs4 import BeautifulSoup as Bs
from jinja2 import Environment, FileSystemLoader

HTML_OVERVIEW = "config_overview.html"

"""
   Return JSON rendered into HTML table
"""
def convert2page(input_data: str, script_path: str, instance: str, log_file: str, errors: int = 0):
    html = ("<!DOCTYPE html><head><meta charset=\"UTF-8\"><title>Config Scanner</title> \
            <link rel=\"stylesheet\" href=\"css/config_scanner.css\"> \
            <style>body { font-family: sans-serif; padding: 20px; } select { margin-bottom: 20px; } \
            .reference { font-weight: bold; color: #3366cc; } \
            pre { background: #f4f4f4; padding: 10px; border-radius: 8px; }</style><script type=\"text/javascript\"> \
            readJson = function() { return " + convert2datachunk(input_data) + "} </script> </head>" +
            "<body><h2>Select an Assay and version to list the enabled workflows for [ " + instance + " ] shesmu</h2> \
            <label for=\"assay\">Assay:</label><select id=\"assay\"> \
            </select><label for=\"version\">Version:</label><select id=\"version\"></select> \
            <label for=\"reference\">Reference:</label><span id=\"reference\" class=\"reference-label\"></span><br> \
            <pre id=\"output\"></pre><script>" + append_script(script_path) + "</script>" + today_date() +
            "<br>" + process_log(log_file, errors) +
            "<br><br><form action=\"" + HTML_OVERVIEW + "\"><input type=\"submit\" value=\"Config Overview\" /></form>" +
            "</body></html>")
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
def convert2datachunk(input_json: str) -> str:
    try:
        with open(input_json, 'r') as inJson:
            data_chunk = json.load(inJson)
            return json.dumps(data_chunk)
    except FileNotFoundError:
        print(f'ERROR: Could not find file {input_json}')
    except ValueError:
        print('ERROR: Could not read JSON data')
    return "{}"


"""
   Read the text of the script and return it as a str to embed into HTML page
"""
def append_script(path: str) -> str:
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

"""
   Process log file:
   * if file exists, provide a link
   * in addition, if there are any errors show an indicator with a number of errors
"""
def process_log(path: str, errors: int):

    if path is None or not os.path.exists(path):
        return ""

    '''Check the number of errors, alert if it is not zero'''
    if errors > 0:
        return "Errors: " + str(errors) + "<br><br><a href=" + path + ">See full Log</a>"
    else:
        return "<a href=" + path + ">See full Log</a>"


"""
   In addition, render assay_info.jsonconfig entries as a table and write into config_overview.html
   HTML file (or whatever value we have in HTML_OVERVIEW).
"""

def update_config_overview(overview_data: dict):
    templates_dir = "templates"
    env = Environment(loader=FileSystemLoader(templates_dir))
    template = env.get_template('overview.html')

    # Collect assay → versions mapping
    assay_columns = defaultdict(list)
    for row in overview_data.values():
        for col in row.keys():
            assay, version = col.split(":")
            if version not in assay_columns[assay]:
                assay_columns[assay].append(version)

    for assay in assay_columns:
        assay_columns[assay].sort()

    output = template.render(data=overview_data, assay_columns=assay_columns)
    with open(HTML_OVERVIEW, "w") as f:
        f.write(output)
