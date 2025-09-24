"""
   Config scanner uses some ideas (and code) from workflowTracker, but to a small extent
   and modified (simplified) for local file parsing. It uses .toml configuration file to
   point the scripts to the directories with olives (.shesmu instruction files) and configuration
   file for assays (assay_info.jsonconfig). It may also take a path to a version control file
   which tracks the versions of workflows used by various assays. A special freeze flag allows
   to prevent updates to existing records, making it possible to run multiple versions of the same
   workflow in parallel, for specific assays

   By parsing both olives and assay config file we can get information on
   a) which flags the scanned olives are using to run workflows (and which version)
   b) are these flags set to 'enable' in assay config file
"""
import argparse
import json
from json import JSONDecodeError
import os.path
import re
import tomli

from configScanner import configScanner
import gsiOlive
import htmlRenderer


"""
   Load settings file and return a dict with obtained values
"""
def load_settings(path):
    try:
        with open(path, "rb") as f:
            toml_dict = tomli.load(f)
            print("Loaded configuration file")
    except tomli.TOMLDecodeError:
        print("Failed to load settings, invalid format")
    return toml_dict


"""
   Load assay setting according to the config, we need only enabled workflows
"""
def load_config(path):
    json_data = {}
    try:
        with open(path, "r") as conf_file:
            json_data = json.load(conf_file)
            if isinstance(json_data, dict) and 'values' in json_data.keys():
                return json_data['values']
    except FileNotFoundError:
        print("Error loading config data")
    except JSONDecodeError:
        print("ERROR: Config JSON file may be corrupted")
    return json_data


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run parsing script to generate assay scan report table')
    parser.add_argument('-s', '--settings', help='Settings file in TOML format', required=False, default="config.toml")
    parser.add_argument('-i', '--instance', help='Instance to scan', required=True)
    parser.add_argument('-o', '--out-json', help='Output json', required=False, default="enabled_workflows.json")
    parser.add_argument('-j', '--jscript', help="Pass to HTML UI javascript", required=True)
    parser.add_argument('-r', '--versions', help="Pass an optional json file with version info", required=False)
    parser.add_argument('-p', '--outpage', help='Output page, HTML', required=False, default="running_workflows.html")
    args = parser.parse_args()

    settings_path = args.settings
    instance_to_scan = args.instance
    output_json = args.out_json
    output_page = args.outpage
    java_script = args.jscript
    version_file = args.versions
    ''' 1. Load settings'''
    settings = load_settings(settings_path)

    if instance_to_scan not in settings["instances"].values():
        print(f"ERROR: instance {instance_to_scan} is not configured, aborting")
        exit(1)
    ''' If we do not have version file, try to find it in the repo dir '''
    if version_file is None and "version_file" in settings['data'].keys():
        version_file = settings['data']['version_file']
    ''' 2. We have search patterns in config file, compile them here '''
    config_check = None
    try:
        check_pattern = settings["checks"]["assay"]
        config_check = re.compile(f'({check_pattern})' + '(?P<check>\\S+)')
    except:
        print("Failed to compile a search pattern for olive check detection")

    ''' 3. collect and process olives, extract modules and tags '''
    olive_files = {}
    olive_info = {}
    blacklist = []
    if 'blacklist' in settings['checks'].keys():
        blacklist = settings['checks']['blacklist']

    olive_files = gsiOlive.collect_olives(settings["data"]["local_olive_dir"], [instance_to_scan], blacklist, {})
    olive_info = gsiOlive.parse_olives(olive_files[instance_to_scan], config_check)

    ''' 4. with loaded config file check the assays for enabled workflows and construct the report '''
    try:
        config_data = load_config(settings["data"]["assay_config_file"])
    except:
        print("No config file configured in the settings")
        exit(1)

    '''Load and update the version settings, if available'''
    confScanner = configScanner(config_data, olive_info, output_json, version_file)
    vetted_report = confScanner.get_report()

    '''Check that we have a non-optional javascript file'''
    if not java_script or not os.path.exists(java_script):
        print("ERROR: Cannot access non-optional file with java script!")
        exit(1)

    ''' 5. Dump the data into json file and generate a report HTML page '''
    if len(vetted_report) > 0:
        confScanner.save_report(output_json)
        html_page = htmlRenderer.convert2page(output_json, java_script, instance_to_scan)
        with open(output_page, 'w') as op:
            op.write(html_page)
    else:
        print("ERROR: Was not able to collect up-to-date information, examine this log and make changes")


# See PyCharm help at https://www.jetbrains.com/help/pycharm/
