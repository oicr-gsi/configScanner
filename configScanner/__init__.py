import collections
import copy
import json
import os
from json import JSONDecodeError


class configScanner:

    def __init__(self, config_data, olive_info, version_file):
        self.report = {}
        self.versions_checks = self.load_versions(version_file)
        self.versions_updated = False
        '''Get the data, make report'''
        for conf in config_data.keys():
            self.report[conf] = {}
            if 'versions' in config_data[conf].keys():
                for ver in config_data[conf]["versions"].keys():
                    version_checker = self.get_checks(conf, ver)
                    '''If we have version specified, account for it here'''
                    self.report[conf][ver] = {}
                    self.construct_report(conf,
                                          ver,
                                          config_data[conf]["versions"][ver],
                                          olive_info,
                                          version_checker)
            else:
                self.construct_report(conf, ver, config_data[conf], olive_info, {})

        if self.versions_updated:
            self.update_versions_file(version_file)

    """
       Load version control data, if valid return a dict. Version-specific freeze flags may be present
       indicating that we do not want any new workflow versions to be added to these snippets
       we also need to check what we have in olives and update the settings, accordingly
    """
    def load_versions(self, path) -> dict:
        version_data = {}
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    version_data = json.load(f)
                    print("INFO: Loaded workflow versions configuration file")
            except JSONDecodeError:
                print("ERROR: Failed to load wf version settings, invalid format")
            '''Using olive info we can update versions for matching entries in version_data'''
        return version_data

    '''Simple getter, return the value of versions update flag'''
    def is_versions_updated(self):
        return self.versions_updated

    '''Return the report dict to be used for HTML UI rendering'''
    def get_report(self):
        return self.report

    '''Flatten a list of mixed types (str, list, set)'''
    @staticmethod
    def flat2gen(alist):
        for item in alist:
            if isinstance(item, list):
                for subitem in item:
                    yield subitem
            else:
                yield item

    '''
       In case we need to add new workflow versions, update the version-tracking file
       This should trigger a creation of a JIRA ticket so that the version tracking file is updated
    '''
    def update_versions_file(self, versions_file):
        if isinstance(self.versions_checks, dict) and len(self.versions_checks) > 0:
            with open(versions_file, 'w') as vf:
                json.dump(self.versions_checks, vf)
            print("WARNING: version-tracking file was updated, take action")

    '''Save report into a .json file for further analysis'''
    def save_report(self, output_json: str):
        vetted_od = collections.OrderedDict(sorted(self.report.items()))
        with open(output_json, "w") as wfj:
            json.dump(vetted_od, wfj)
            print(f"WARNING: Saved assay report into a .json file {output_json}")

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
       assay_info or project_info config files when we have an olive check. In case when
       olives checks for a setting:
       * returns False when it is not enabled in .jsonconfig 
       * returns True if this setting is enabled in the .jsonconfig or not None for pipelines
    """
    def is_configured_2run(self, d1, d2):
        """Return True if all path->value in d2 that exist in d1 are not False or None in d1."""
        for k, v in d2.items():
            if k not in d1:
                continue  # ignore missing branches

            if isinstance(v, dict):
                if not isinstance(d1[k], dict):
                    return False
                if not self.is_configured_2run(d1[k], v):
                    return False
            else:
                if d1[k] in [False, None]:
                    return False
        return True

    """
        A small utility function for vetting version list (depends on settings)
    """
    def get_vetted_versions(self, oli_name: str, oli_tags: set, versions_check, assay: str, assay_version: str):
        reported_olives = list(oli_tags)[0] if len(oli_tags) == 1 else list(oli_tags)
        try:
            if 'freeze' in versions_check.keys():
                reported_olives = [versions_check['workflows'][oli_name]]
            elif oli_name in versions_check['workflows'].keys():
                reported_olives = list(set(configScanner.flat2gen([reported_olives, versions_check['workflows'][oli_name]])))
                controlled_list = versions_check['workflows'][oli_name]
                if isinstance(controlled_list, str):
                    controlled_list = [controlled_list]
                if collections.Counter(reported_olives) != collections.Counter(controlled_list):
                    self.versions_updated = True
                    self.versions_checks['values'][assay]['versions'][assay_version]['workflows'][oli_name] = reported_olives
        except ValueError:
            print("ERROR: Could not update the list of versions")
        except Exception as e:
            print(f"ERROR: problem with {e} in versions_check dict")
        finally:
            return reported_olives

    """
       fuses config (project or assay) and olive data. Returns a dict with all workflows which run for a setting snippet
       at this point we do not support custom wf versioning and report all tags if an olive has appropriate check
    """
    def construct_report(self, assay, assay_version, config: dict, olives: list, v_check: dict):
        try:
            for oli in olives:
                '''Olive has checks, verify that it is enabled in the config'''
                '''if an olive does not have checks, it will run regardless'''
                '''if we have a dict with wf versions, use it'''
                if (len(oli['checks']) > 0 and self.is_configured_2run(config, oli['checks'])) or len(oli['checks']) == 0:
                    for n in oli['names']:
                        '''Get info from version_check if available, add version from olive if the config is not frozen'''
                        vetted_versions = oli['tags']
                        if len(v_check) > 0 and n in v_check['workflows'].keys():
                            vetted_versions = self.get_vetted_versions(n,
                                                                       oli['tags'],
                                                                       v_check,
                                                                       assay,
                                                                       assay_version)
                        if len(vetted_versions) > 1:
                            self.report[assay][assay_version][n] = list(vetted_versions)
                        elif len(vetted_versions) == 1:
                            copied_tags = copy.deepcopy(vetted_versions)
                            self.report[assay][assay_version][n] = str(copied_tags.pop())
        except:
            print("ERROR: Could not construct workflow report given the inputs")
