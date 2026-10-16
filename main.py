# -*- coding: utf-8 -*-
"""
Editable script to process the raw .md versions of the assessment
"""

import assessment

# ---------------------------------------------------------------------------------
#%% Preliminary cell - Configure here the information for the processing to perform
# ---------------------------------------------------------------------------------

# Filenames, assessment names, version and previous version numbers
ASSESSMENT_MD_VERSION_FILENAME_FR = "assessment-202609-fr.md"  # Filename in FR
ASSESSMENT_MD_VERSION_FILENAME_EN = "assessment-202609-en.md"  # Filename in EN
ASSESSMENT_VERSION = "202609"  # Version number
ASSESSMENT_PREVIOUS_VERSION = (
    "202301"  # Version number of the previous assessment version
)
ASSESSMENT_NAME_FR = "Evaluation Labelia - IA responsable et de confiance - version 2026"  # Name in FR
ASSESSMENT_NAME_EN = "Labelia Assessment - Responsible and Trustworthy AI - release 2026"  # Name in EN

# Assessment version and associated scoring to use to pre-fill the scoring template
ASSESSMENT_VERSION_TO_PREFILL_SCORING_TEMPLATE = (
    "202301"  # Used to fetch and copy elements and answer items
)
SCORING_FILENAME_TO_PREFILL_SCORING_TEMPLATE = (
    "assessment-202301_scoring-1.json"  # Used to fetch and copy score values
)

# --------------------------------------------------------------------------------------
#%% First cell - Instantiate assessment, process it to .json and create scoring template
# --------------------------------------------------------------------------------------

# Instantiate a new assessment object
new_assessment = assessment.Assessment(
    ASSESSMENT_MD_VERSION_FILENAME_FR,
    ASSESSMENT_MD_VERSION_FILENAME_EN,
    ASSESSMENT_VERSION,
    ASSESSMENT_PREVIOUS_VERSION,
    ASSESSMENT_NAME_FR,
    ASSESSMENT_NAME_EN,
    ASSESSMENT_VERSION_TO_PREFILL_SCORING_TEMPLATE,
    SCORING_FILENAME_TO_PREFILL_SCORING_TEMPLATE,
)

# Create the .json file for the new assessment
new_assessment.dump_to_json_file()

# Create its scoring template (pre-filled with scoring config from a previous version)
new_assessment.create_scoring_template()

print("--- Le fichier scoring_template est créé et doit être rempli en cas de modification du barême")

# --------------------------------------------------------------------
#%% Second cell - Process scoring template (launch it when filled in!)
# --------------------------------------------------------------------

new_assessment.process_scoring_template_to_json()
new_assessment.enrich_assessment_with_scoring_recap()
new_assessment.enrich_assessment_with_non_concerned_recap()

print("Les fichiers ont été générés en fonction des nouvelles réponses du barême. Il faut maintenant vérifier les fichiers générés et les valider avant de les publier sur le référentiel.")

# %%
