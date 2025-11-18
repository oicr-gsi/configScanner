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

CONF_HEADER = {"missingUsesDefaults": False, "types": {"versions": {"is": "dictionary", "key": "s",
               "value": {"fields": {"workflows": "msas"}, "is": "object"}}, "reference": "s"}}
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
   Initialize filter dict. if we have matching prefix, put in include if there is a non-matching prefix
   put it in exclude
"""
def init_filters(prefs: dict, instance: str):
    p_filters = {}
    if isinstance(prefs, dict) and len(prefs) > 0:
        for p in prefs.keys():
            rule = 'include' if p == instance else 'exclude'
            if rule in p_filters.keys():
                p_filters[rule].append(prefs[p])
            else:
                p_filters[rule] = [prefs[p]]
    return p_filters


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

"""
                             ---- Save jsonconfig file for staging ----
   this should take in account both older ground truth (assay_info.jsonconfig) settings and all olives with checks
   update older information in ground truth with what we got from olive/assay_info scan and print into a file
"""
def save_config(conf_data: dict, output_conf: str):
    vetted_od = {"values": {}}
    try:
        for assay in conf_data.keys():
            vetted_od["values"][assay] = {"versions": {}}
            for version in conf_data[assay].keys():
                if version == configScanner.REF_KEY:
                    vetted_od["values"][assay][version] = conf_data[assay][version]
                else:
                    vetted_od["values"][assay]["versions"][version] = {"workflows": {}}
                    vetted_od["values"][assay]["versions"][version]["workflows"] = conf_data[assay][version]
        vetted_od.update(CONF_HEADER)
        vetted_od = configScanner.deepsort_dict(vetted_od)
        with open(output_conf, "w") as wfj:
            jstring = json.dumps(vetted_od, indent=2, ensure_ascii=False)
            jstring = re.sub(r'(\[)\n', r'\1', jstring)
            jstring = re.sub(r'(\d\")\s+', r'\1', jstring)
            jstring = re.sub(r'(\[)\s+', r'\1', jstring)
            jstring = re.sub(r'(\d\",)\n', r'\1', jstring)
            '''Take care of strings with reference'''
            pattern_string = configScanner.REF_KEY + r"\S+\s+\S+"
            ptr = re.compile(f'({pattern_string})')
            jstring = re.sub(ptr, r'\1' + "\n", jstring)
            wfj.write(jstring)
            print(f"INFO: Saved assay config into a .jsonconfig file {output_conf}")
    except:
        print(f"ERROR: writing to a config file {output_conf} failed")


# TODO need to add a staging GroundTruth output (analog of versions file)
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run parsing script to generate assay scan report table')
    parser.add_argument('-s', '--settings', help='Settings file in TOML format', required=False, default="config.toml")
    parser.add_argument('-o', '--out-prefix', help='Output base name', required=False, default="enabled_workflows")
    parser.add_argument('-j', '--jscript', help="Path UI js", required=False, default="js/dropDown.js")
    parser.add_argument('-c', '--config', help="Staging config", required=False, default="assay_staging.jsonconfig")
    parser.add_argument('-p', '--outpage', help='HTML page basename', required=False, default="running_workflows")
    args = parser.parse_args()

    settings_path = args.settings
    output_base = args.out_prefix
    output_page = args.outpage
    java_script = args.jscript
    output_config = args.config

    if not java_script or not os.path.exists(java_script):
        print("ERROR: Cannot access non-optional file with java script!")
        exit(1)

    ''' 1. Load settings'''
    settings = load_settings(settings_path)

    ''' 2. We have search patterns in config file, compile them here '''
    config_check = None
    try:
        check_pattern = settings["checks"]["assay"]
        config_check = re.compile(f'({check_pattern})' + '(?P<check>\\S+)')
    except:
        print("Failed to compile a search pattern for olive check detection")

    ''' 3. collect and process olives, extract modules and tags '''
    olive_files = []
    olive_info = {}
    blacklist = []
    combined_report = {}
    prefixes = {}

    if 'blacklist' in settings['checks'].keys():
        blacklist = settings['checks']['blacklist']

    ''' 4. with loaded config file check the assays for enabled workflows and construct the report '''
    try:
        config_data = load_config(settings["data"]["assay_config_file"])
    except:
        print("No config file configured in the settings")
        exit(1)

    ''' 5. check for instance-specific assay prefixes '''
    try:
        prefixes = settings["prefixes"]
    except:
        print("No instance-specific prefixes found")

    for instance_to_scan in settings['instances'].values():
        olive_files = gsiOlive.collect_olives(settings["data"]["local_olive_dir"], instance_to_scan, blacklist, {})
        olive_info[instance_to_scan] = gsiOlive.parse_olives(olive_files, config_check)
        vetted_report = {}
        '''Load and update the version settings, if available'''
        if len(olive_info[instance_to_scan]) > 0:
            filters = init_filters(prefixes, instance_to_scan)
            output_json = output_base + "_" + instance_to_scan + ".json"
            confScanner = configScanner(config_data, olive_info[instance_to_scan], filters, output_json)
            vetted_report = confScanner.get_report()
            combined_report.update(vetted_report)
            ''' 5. Dump the data into json file and generate a report HTML page '''
            if len(vetted_report) > 0:
                confScanner.save_report(output_json, instance_to_scan)
                html_page = htmlRenderer.convert2page(output_json, java_script, instance_to_scan)
                instance_page = output_page + "_" + instance_to_scan + ".html"
                with open(instance_page, 'w') as op:
                    op.write(html_page)
        else:
            print("ERROR: Was not able to collect up-to-date information, examine this log and make changes")

    save_config(combined_report, output_config)

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
