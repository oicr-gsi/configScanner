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
   Parse Olive: return a dict with tags names and checks
   {
     olives = []
     tags = []
     checks = {}
     names = []
   }
"""
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
                if matcher and matcher.groupdict():
                    if matcher.groupdict()['workflow'] and matcher.groupdict()['version']:
                        checker = {matcher.groupdict()['workflow']: matcher.groupdict()['version']}
                        config_checks.update(checker)
        except subprocess.CalledProcessError:
            print(f'WARNING: No Config Checks in the Olive {m_olive}')

        for rl in run_lines:
            next_run = re.search(r"(\S+)_v(\d+_\d+_*\d*\w*)$", rl)
            if next_run is None:
                continue
            next_tag = next_run.group(2).replace("_", ".")
            next_name = next_run.group(1)
            if next_tag is not None:
                vetted_tags.append(next_tag)
            if next_name is not None:
                vetted_names.append(next_name)
                if next_name in config_checks.keys():
                    if next_tag and next_tag != config_checks[next_name]:
                        print(f'ERROR: config check for {next_name} not using correct version in  {m_olive}')

        parsed_olives.append({'olives': [m_olive],
                              'tags': set(vetted_tags),
                              'checks': config_checks,
                              'names': set(vetted_names)})
    return parsed_olives
