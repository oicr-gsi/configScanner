import collections
import json
import re
import os
from copy import deepcopy
from json import JSONDecodeError
from typing import OrderedDict

class configScanner:
    REF_KEY = 'reference'

    def __init__(self, config_data, olive_info, filters):
        self.report = {}
        self.errors = 0
        self.config = deepcopy(config_data)
        self.validate_olives(olive_info)
        '''Get the data, make report'''
        for assay in config_data.keys():
            '''If we have prefixes, check assay names'''
            if len(filters) > 0 and configScanner.filter_assay(filters, assay):
                continue
            '''Get reference info and put it in'''
            self.report[assay] = {}
            if 'versions' in config_data[assay].keys():
                for version in config_data[assay]["versions"].keys():
                    '''Get the reference if we have it'''
                    if self.REF_KEY not in self.report[assay].keys():
                        self.extract_reference(config_data, assay)
                    '''If we have version specified, account for it here'''
                    self.report[assay][version] = {}
                    self.construct_report(assay,
                                          version,
                                          config_data[assay]["versions"][version]["workflows"],
                                          olive_info)

    """
       validate olives vs config file, report errors
    """
    def validate_olives(self, olive_info: dict):
        a_wfs = []
        avail_olives = []
        for a in self.config.keys():
            for a_version in self.config[a]['versions'].keys():
                a_wfs.extend(w for w in list(self.config[a]['versions'][a_version]['workflows'].keys()))
        for olive in olive_info:
            avail_olives.extend(n for n in olive['names'])
        for avail_olive in set(avail_olives):
            if avail_olive not in a_wfs:
                print(f'WARNING: Workflow {avail_olive} has an olive deployed but is not configured in assay_info')
                self.errors += 1

    """
       filter is prepared by the main runConfigScanner block, we may have include or/and exclude hashes
    """
    def extract_reference(self, config_data: dict, assay: str):
        try:
            assay_ref = config_data[assay][self.REF_KEY]
            if assay_ref is not None:
                self.report[assay][self.REF_KEY] = assay_ref[0] if isinstance(assay_ref, list) else assay_ref
        except:
            print(f"ERROR: No Reference found for Assay {assay}")
            self.errors += 1

    @staticmethod
    def filter_assay(filters: dict, assay_name: str):
        for f_type in filters.keys():
            for f in filters[f_type]:
                if re.match(f, assay_name):
                    return False if f_type == 'include' else True
            if f_type == 'include':
                return True
        return False

    """
       Load old report, if exists. It is needed to track the versions of workflows which may have already
       been decommissioned. The construct_report function will use this info for updating vetted_report 
    """
    @staticmethod
    def load_report(path) -> dict:
        report_data = {}
        if path is not None and os.path.exists(path):
            try:
                with open(path, "r") as f:
                    report_data = json.load(f)
                    print("INFO: Loaded older report data file")
            except JSONDecodeError:
                print("ERROR: Failed to load older report, invalid format")
        return report_data

    '''Return the report dict to be used for HTML UI rendering'''
    def get_report(self):
        return self.report

    '''Return number of errors (this is instance-specific, need to be checked in runConfigScanner)'''
    def get_errors(self):
        return self.errors

    '''Return config which may get updates from an olive scan'''
    def get_staged_config(self):
        return self.config

    '''Save report into a .json file for further analysis'''
    def save_report(self, output_json: str):
        vetted_od = configScanner.deepsort_dict(self.get_report())
        with open(output_json, "w") as wfj:
            jstring = json.dumps(vetted_od, indent=2, ensure_ascii=False)
            jstring = re.sub(r'(\[)\n', r'\1', jstring)
            jstring = re.sub(r'(\d\")\s+', r'\1', jstring)
            jstring = re.sub(r'(\d\",)\s+', r'\1', jstring)
            jstring = re.sub(r'(\[)\s+', r'\1', jstring)
            jstring = re.sub(r'(\d\",)\n', r'\1', jstring)
            wfj.write(jstring)
            print(f"INFO: Saved assay report into a .json file {output_json}")

    '''Flatten a list of mixed types (str, list, set)'''
    @staticmethod
    def flat2gen(alist):
        for item in alist:
            if isinstance(item, list):
                for subitem in item:
                    yield subitem
            else:
                yield item

    '''This is for making things pretty, deep sort of nested dict such as final config or report'''
    @staticmethod
    def deepsort_dict(input_dict, key=lambda item: item[0]) -> dict:
        """
        Recursively sorts an OrderedDict and its nested OrderedDicts.
        Args:
            input_dict (OrderedDict or dict): The dictionary to sort.
            key (function): A function to extract a comparison key from each item.
                            Defaults to sorting by key (item[0]).
        Returns:
            OrderedDict: A new OrderedDict with deeply sorted contents.
        """
        if not isinstance(input_dict, (OrderedDict, dict)):
            return input_dict  # Not a dictionary, return as is
        sorted_items = []
        for k, v in sorted(input_dict.items(), key=key):
            if isinstance(v, (OrderedDict, dict)):
                sorted_items.append((k, configScanner.deepsort_dict(v, key)))
            else:
                sorted_items.append((k, v))
        return OrderedDict(sorted_items)

    """
       when we have an olive check:
       returns False when it is not enabled in .jsonconfig 
    """
    @staticmethod
    def is_configured_2run(d1, d2):
        """Return True only if workflow version in d2 is also present in d1."""
        for k, v in d2.items():
            if k not in d1:
                return False
            if isinstance(d1[k], list):
                return v in d1[k]
        return False

    """
        A small utility function for vetting/tracking changes in version list (depends on settings and previous report)
    """
    def get_vetted_versions(self, oli_name: str, oli_tags: set, assay: str, assay_version: str) -> list:
        configured_olives = list(oli_tags)
        try:
            older_versions = self.config[assay]['versions'][assay_version]['workflows']
            if oli_name in older_versions.keys():
                updated_olives = list(set(configScanner.flat2gen([list(oli_tags), older_versions[oli_name]])))
                older_scan_list = older_versions[oli_name]
                if isinstance(older_scan_list, str):
                    print(f'WARNING: {oli_name} has version stored as str, not array')
                    older_scan_list = [older_scan_list]
                if collections.Counter(updated_olives) != collections.Counter(older_scan_list):
                    print(f"INFO: We have a change for {oli_name} in {assay} version {assay_version}")
                    configured_olives = updated_olives
        except ValueError:
            print(f"INFO: Could not find older report for {assay} version {assay_version}")
        except Exception as e:
            print(f"ERROR: problem with {e} in get_vetted_versions")
            self.errors += 1
        return configured_olives

    """
       Make sure we register values as the right type, also check if we have the same olive in report already -
       this takes care of multiple olive files running the same workflow
    """
    def safe_register(self, versions: list, assay: str, assay_version: str, o_name: str):
        vetted_versions = list(versions)
        if isinstance(self.report[assay][assay_version], dict) and o_name in self.report[assay][assay_version].keys():
            existing_tags = self.report[assay][assay_version][o_name]
            if isinstance(existing_tags, str):
                vetted_versions.append(existing_tags)
            elif isinstance(existing_tags, list):
                for t in existing_tags:
                    vetted_versions.append(t)
        '''Make sure we have unique tags in the list'''
        if len(vetted_versions) > 1:
            vetted_versions = list(set(vetted_versions))
        '''Make sure we register array all the time, for config and report'''
        self.report[assay][assay_version][o_name] = sorted(vetted_versions)

    """
       fuses config assay_info and olive data:
       * if the olive is in config and the version too, report
       * if the olive in config but version is not, do not report but add to staging config
       * if the olive is not in config and there are no checks, report
       
       in the config - no olives which are not checking assay_info settings
    """
    def construct_report(self, assay, assay_version, config: dict, olives: list):
        for oli in olives:
            try:
                """
                   Olive has checks, verify that it is enabled in the config
                   if an olive does not have checks, it will run regardless
                """
                for n in oli['names']:
                    vetted_versions = oli['tags']
                    if len(oli['checks']) > 0 and any(n in d for d in oli['checks']):
                        for o_check in oli['checks']:
                            if n in o_check.keys() and configScanner.is_configured_2run(config, o_check):
                                self.safe_register(vetted_versions, assay, assay_version, n)
                        if n in self.config[assay]['versions'][assay_version]['workflows'].keys():
                            '''get_vetted_versions new olive tags with existing (configured) ones, if present'''
                            vetted_versions = self.get_vetted_versions(n, oli['tags'], assay, assay_version)
                            self.config[assay]['versions'][assay_version]['workflows'][n] = sorted(vetted_versions)
                    else:
                        self.safe_register(vetted_versions, assay, assay_version, n)
            except Exception as e:
                print(f"An error occurred: {e}")
                print("ERROR: Could not construct workflow report given the inputs")
                self.errors += 1
