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
def collect_olives(repo_dir: str, instances_list: list, blacklist: list, aliases: dict) -> dict:
    olive_hash = {}
    if repo_dir and os.path.isdir(repo_dir):
        for inst in instances_list:
            subdir = "/".join([repo_dir, inst])
            olive_files = glob.glob("/".join([subdir, "vidarr*.shesmu"]))
            if len(olive_files) == 0 and inst in aliases.keys():
                subdir = "/".join([repo_dir, "shesmu", aliases[inst]])
                olive_files = glob.glob("/".join([subdir, "vidarr*.shesmu"]))
            print(f'INFO: We have {len(olive_files)} .shesmu files for {inst}')
            if len(olive_files) > 0:
                olive_hash[inst] = []
            for oli in olive_files:
                if len(blacklist) == 0 or basename(oli) not in blacklist:
                    olive_hash[inst].append(oli)
    return olive_hash


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
   Parse Olive: return a dict with tags names and checks
   {
     olives = []
     tags = []
     checks = {}
     names = []
   }
"""


#TODO: we may need to make sure each olive goes into separate slot (as files may have multiple olives inside)
def parse_olives(olive_files: list, check_pattern: re.Pattern[str]) -> list:
    """ Return a list of Olive data structure(s) """
    parsed_olives = []
    ''' extract versions of the Workflow, names and modules'''
    for m_olive in olive_files:
        vetted_tags = []
        vetted_names = []
        config_checks = {}
        try:
            run_lines = subprocess.check_output(f"grep 'Run ' '{m_olive}'", shell=True).decode().strip()
            run_lines = run_lines.split("\n")
            if not isinstance(run_lines, list):
                run_lines = [run_lines]
        except subprocess.CalledProcessError:
            print(f'WARNING: No Run lines in the Olive {m_olive}')
            run_lines = []

        try:
            check_lines = subprocess.check_output(f"grep -E 'assay_info|project_info' '{m_olive}'",
                                                  shell=True).decode().strip()
            check_lines = check_lines.split("\n")
            for c in check_lines:
                matcher: Match[str] | None = re.search(check_pattern, c)
                if matcher and matcher.groupdict() and matcher.groupdict()['check']:
                    checker = list_to_nested_dict(matcher.groupdict()['check'].split('.'))
                    config_checks.update(checker)
        except subprocess.CalledProcessError:
            print(f'WARNING: No Config Checks in the Olive {m_olive}')

        for rl in run_lines:
            next_tag = re.search(r"v(\d+_\d+_*\d*\w*)$", rl)
            next_name = re.search(r"(\S+)_v\d+_\d+_*\d*\w*$", rl)
            if next_tag is not None:
                vetted_tags.append(next_tag.group(1).replace("_", "."))
            if next_name is not None:
                vetted_names.append(next_name.group(1))

        parsed_olives.append({'olives': [m_olive],
                              'tags': set(vetted_tags),
                              'checks': config_checks,
                              'names': set(vetted_names)})
    return parsed_olives
