"""
   Functions for handling Olive data (this is different from what we use in workflowTracker)
"""
import glob
import os
import re
import subprocess
from os.path import basename
from re import Match

"""
   Find olives, return dict with lists of files
"""


def collect_olives(repo_dir: str, instance: str, blacklist: list, aliases: dict) -> list:
    olive_list = []
    if repo_dir and os.path.isdir(repo_dir):
        subdir = "/".join([repo_dir, instance])
        olive_files = glob.glob("/".join([subdir, "vidarr*.shesmu"]))
        if len(olive_files) == 0 and instance in aliases.keys():
            subdir = "/".join([repo_dir, "shesmu", aliases[instance]])
            olive_files = glob.glob("/".join([subdir, "vidarr*.shesmu"]))
        print(f'INFO: We have {len(olive_files)} .shesmu files for {instance}')
        if len(olive_files) > 0:
            olive_list = []
        for oli in olive_files:
            if len(blacklist) == 0 or basename(oli) not in blacklist:
                olive_list.append(oli)
    return olive_list


"""
   A simple subroutine for merging two hashes with Olive info
"""


def merge_info(existing_hash: dict, new_hash: dict) -> dict:
    if isinstance(existing_hash, dict) and len(existing_hash) != 0:
        new_hash['olives'].extend(existing_hash['olives'])
        new_hash['data_modules'] = new_hash['data_modules'].union(existing_hash['data_modules'])
        new_hash['code_modules'] = new_hash['code_modules'].union(existing_hash['code_modules'])
        new_hash['tags'] = new_hash['tags'].union(existing_hash['tags'])
    return new_hash


"""
   A utility function which takes a flat array as it's input and returns a nested dict
"""


def list_to_nested_dict(arr):
    nested = current = {}
    for key in arr[:-1]:
        current[key] = {}
        current = current[key]
    current[arr[-1]] = True
    return nested


"""
   Parse Olive: return a dict with tags names
   {
     olives = []
     tags = []
     checks = [NA|OK]
     names = []
   }
"""


def parse_olives(olive_files: list, check_pattern: re.Pattern[str]) -> list:
    """ Return a list of Olive data structure(s) """
    parsed_olives = []
    errors = 0
    ''' extract versions of the Workflow, names and modules'''
    for m_olive in olive_files:
        vetted_tags = []
        vetted_names = []
        config_checks = []
        try:
            check_ok = "NA"
            with open(m_olive, 'r') as of:
                olive_lines = of.readlines()
            ''' Search for Run blocks, register the wf name and tag'''
            for ol in olive_lines:
                '''Search for a check, if present set the next Run block to OK'''
                if re.search(check_pattern, ol):
                    check_ok = "OK"
                ''' Search for Run blocks, register the wf name and tag'''
                next_run = re.search(r"(\S+)_v(\d+_\d+_*\d*\w*)$", ol)
                if next_run is not None:
                    next_tag = next_run.group(2).replace("_", ".")
                    next_name = next_run.group(1)
                    next_name = re.sub(r'^.*::', '', next_name) # Remove all crap before the workflow name
                    if next_tag is not None:
                        vetted_tags.append(next_tag)
                    if next_name is not None:
                        vetted_names.append(next_name)
                    config_checks.append(check_ok)
                    check_ok = "NA"

        except FileNotFoundError:
            print(f'ERROR: Could not read from the olive {m_olive}')
            errors += 1

        run_index = 0
        for vn in vetted_names:
            if len(config_checks) < run_index + 1 or config_checks[run_index] == "NA":
                print(f'ERROR: config check for {vn} is not present in {m_olive}')
                errors += 1
            run_index += 1

        parsed_olives.append({'olives': [m_olive],
                              'tags': set(vetted_tags),
                              'checks': config_checks,
                              'names': set(vetted_names)})
    return [parsed_olives, errors]
