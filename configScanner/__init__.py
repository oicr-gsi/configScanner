import collections
import copy
import json
import os
from json import JSONDecodeError
from typing import OrderedDict


class configScanner:

    def __init__(self, config_data, olive_info, output_json, version_file):
        self.report = {}
        self.older_report = {}
        if version_file is not None:
            self.versions_checks = configScanner.load_versions(version_file)
        if output_json is not None:
            self.older_report = configScanner.load_report(output_json)
        self.versions_updated = False
        '''Get the data, make report'''
        for assay in config_data.keys():
            self.report[assay] = {}
            if 'versions' in config_data[assay].keys():
                for version in config_data[assay]["versions"].keys():
                    version_checker = self.get_checks(assay, version)
                    '''If we have version specified, account for it here'''
                    self.report[assay][version] = {}
                    self.construct_report(assay,
                                          version,
                                          config_data[assay]["versions"][version],
                                          olive_info,
                                          version_checker)

    """
       Load version control data, if valid return a dict. Version-specific freeze flags may be present
       indicating that we do not want any new workflow versions to be added to these snippets
       we also need to check what we have in olives and update the settings, accordingly
    """
    @staticmethod
    def load_versions(path) -> dict:
        version_data = {}
        if path is not None and os.path.exists(path):
            try:
                with open(path, "r") as f:
                    version_data = json.load(f)
                    print("INFO: Loaded workflow versions configuration file")
            except JSONDecodeError:
                print("ERROR: Failed to load wf version settings, invalid format")
            '''Using olive info we can update versions for matching entries in version_data'''
        return version_data

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

    '''Save report into a .json file for further analysis'''
    def save_report(self, output_json: str):
        vetted_od = configScanner.deepsort_dict(self.get_report())
        with open(output_json, "w") as wfj:
            json.dump(vetted_od, wfj, indent=2)
            print(f"WARNING: Saved assay report into a .json file {output_json}")

    '''Flatten a list of mixed types (str, list, set)'''
    @staticmethod
    def flat2gen(alist):
        for item in alist:
            if isinstance(item, list):
                for subitem in item:
                    yield subitem
            else:
                yield item

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
       A simple getter which returns either config snippet (if available)
       or empty dict, if not
    """
    def get_checks(self, assay: str, version: str):
        try:
            return self.versions_checks['values'][assay]['versions'][version]
        except:
            print(f"INFO: No workflow version restriction found for {assay} version {version}")
            return {}

    """
       The heart of this class - a function which verifies the configuration is enabled in 
       assay_info config file when we have an olive check. In case when
       olives checks for a setting:
       * returns False when it is not enabled in .jsonconfig 
       * returns True if this setting is enabled in the .jsonconfig or not None for pipelines
    """
    def is_ok_2run(self, d1, d2):
        """Return True if all path->value in d2 that exist in d1 are not False or None in d1."""
        for k, v in d2.items():
            if k not in d1:
                continue  # ignore missing branches

            if isinstance(v, dict):
                if not isinstance(d1[k], dict):
                    return False
                if not self.is_ok_2run(d1[k], v):
                    return False
            else:
                if d1[k] in [False, None]:
                    return False
        return True

    """
        A small utility function for vetting/tracking changes in version list (depends on settings and previous report)
    """
    def get_vetted_versions(self, oli_name: str, oli_tags: set, assay: str, assay_version: str) -> list:
        reported_olives = list(oli_tags)[0] if len(oli_tags) == 1 else list(oli_tags)
        try:
            older_versions = self.older_report[assay][assay_version]
            if oli_name in older_versions.keys():
                reported_olives = list(set(configScanner.flat2gen([reported_olives, older_versions[oli_name]])))
                older_scan_list = older_versions[oli_name]
                if isinstance(older_scan_list, str):
                    older_scan_list = [older_scan_list]
                if collections.Counter(reported_olives) != collections.Counter(older_scan_list):
                    print(f"INFO: We have a change for {oli_name} in {assay} version {assay_version}")
        except ValueError:
            print(f"INFO: Could not find older report for {assay} version {assay_version}")
        except Exception as e:
            print(f"ERROR: problem with {e} in get_vetted_versions")
        finally:
            return reported_olives

    """
       Make sure we register values as the right type, also check if we have the same olive in report already -
       this takes care of multiple olive files running the same workflow
    """
    def safe_register(self, versions: list, assay: str, assay_version: str, olive_name: str):
        vetted_versions = versions
        try:
            existing_tags = self.report[assay][assay_version][olive_name]
            if isinstance(existing_tags, str):
                vetted_versions.append(existing_tags)
            elif isinstance(existing_tags, list):
                vetted_versions.extend(existing_tags)
        except KeyError:
            pass
        '''Make sure we have unique tags in the list'''
        if len(vetted_versions) > 1:
            vetted_versions = list(set(vetted_versions))
        '''Make sure we register str if there is only one value and array if there are multiple'''
        if len(vetted_versions) == 1:
            copied_tags = copy.deepcopy(vetted_versions)
            self.report[assay][assay_version][olive_name] = str(copied_tags.pop())
        else:
            self.report[assay][assay_version][olive_name] = sorted(vetted_versions)

    """
       fuses config assay_info and olive data. (Returns a dict with all workflows which run for a setting snippet
       at this point we do not support custom wf versioning and report all tags if an olive has appropriate check
    """
    def construct_report(self, assay, assay_version, config: dict, olives: list, v_check: dict):
        try:
            for oli in olives:
                """Olive has checks, verify that it is enabled in the config
                   if an olive does not have checks, it will run regardless
                   if we have a dict with wf versions, use it
                """
                if (len(oli['checks']) > 0 and self.is_ok_2run(config, oli['checks'])) or len(oli['checks']) == 0:
                    for n in oli['names']:
                        '''Get info from version_check, add version from olive if the config is not frozen'''
                        vetted_versions = oli['tags']
                        if len(v_check) > 0 and n in v_check['workflows'].keys():
                            if isinstance(v_check['workflows'][n], str):
                                vetted_versions = [v_check['workflows'][n]]
                            else:
                                vetted_versions = v_check['workflows'][n]
                        elif len(self.older_report) > 0:
                            vetted_versions = self.get_vetted_versions(n, oli['tags'], assay, assay_version)
                        '''Handle lists of tags and single tags differently, single entry is a str type'''
                        self.safe_register(vetted_versions, assay, assay_version, n)
        except:
            print("ERROR: Could not construct workflow report given the inputs")
