# configScanner
These scripts are for getting information from Bitbucket analysis-config repository. They read
olive files and assay configuration file combining this information and presenting a list of 
workflows which would run for a given assay given exisiting settings. Reported data may be used
for tracking any versions of workflows ran for a given assay/version combination.

reports are in .json and .html formats. Developed in Python 3.12, these script should run with older
(3.10+) python libraries as well.

![HTML output](docs/Screenshot_configScanner.png)

# Installation

Designed to be modularized, configScanner should be used on Univa network-enabled nodes as a module
However, if you want to install it locally the first thing to do is 

```
   pip install -r requirements.txt
```

configScanner uses a few modules which are not a part of regular python installation.

# Captured Information

We scan the olives for two things - 

* Run tags (workflow alias and it's version) and 
* check performed on assay_info.jsonconfig file 

The supplied .toml file specifies regex patterns to use when searching for assay configuration checks.

assay_info.jsonconfig file is also scanned and analyzed. The final report indicates which workflows 
would run given a particular assay/version combination with the following benefits:

* Ability to see which unwanted workflows are enabled for an assay
* Spotting problems with checks in olives
* Data to use with downstream reporting/analysis

# Running the script

The script can be run as

```
  python3 runConfigScanner.py 

```

# Full list of Options

Following options are available:

* -s Settings file in TOML format (Default is config.toml)
* -o Output base name, for data dump (Default is enabled_workflows)
* -c Staging config name, default is assay_staging.jsonconfig
* -p Output HTML page basename (Default is running_workflows)
* -j Path to JavaScript file for embedding into HTML report page (default is js/dropDown.js)
* -l Path to log file which configScanner writes into (this is optional but if passed, will be linked to in the html report)

Settings file specify various configuration parameters and at this point has 4 sections:

* data        - information related to repos for olives
* instances   - this is to specify our shesmu instances (clinical and research) - there may be changes in a future
* prefixes    - this allows to separate instance-specific configurations (research and clinical)
* checks      - regex patterns for finding assay_info checks in olives

Script will run collecting workflow names (aliases) as they are used in olives, then it will proceed to analyze this information
together with assay settings. After bringing all of these data together, the script will output .json and .html reports

# Workflow version control

Workflow version control is designed around checking and [manually] updating assay_info.jsonconfig file. The current format
is a simplified version of previously used project_info.jsonconfig file, but now it may be used for controlling version of 
workflows for selected assays/olive combinations

![Version control file](docs/Screenshot_workflowVersions.png)

The logic of version control can be also summarized as the following flowchart:

![Version control schema](docs/Screenshot_workflowVersionsFlowchart.png)

As the diagram shows, we may have a situation when a new workflow appears in production environment we are 
scanning. In this case the workflow version will be registered with all assays which are running it in a
staging config file, changes must be transferred manually into the version-controlled assay_info.jsonconfig file.
If there is no entry for a newly deployed workflow in existing configuration, [flask UI](https://github.com/oicr-gsi/flask_ui) should be used to
enable the workflow where appropriate.

# Running as a cron job

The main goal here is to run automatic updates, and the most practical way to do it is to use crontab.
