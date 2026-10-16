# -*- coding: utf-8 -*-
"""
Parses the DSRC assessment `.md` file and generates:
1) a structured `.json` file, meant to be directly uploaded in the web platform
2) a neat template for easily adding score points per answer item

Contrairement à "assessment.py", ce script calcul la note final en ne comptabilisant pas 
les questions "non concerné". (L'autre methode de calcul attribuait d'office 50% de la note maximale)

"""

import sys
import os
import re
import json

# ---------------------------------------------------------------------------
# POLITIQUE "NON CONCERNE"
# ---------------------------------------------------------------------------
# Determine la valeur ecrite dans le bloc "non_concerned_recap" du fichier
# assessment json, pour chaque element ayant une reponse "non concerne".
#
#   "half"    : la moitie du maximum de l'element (comportement historique,
#               compatible avec la plateforme telle qu'elle tourne aujourd'hui).
#               L'organisation non concernee recoit la moitie des points.
#
#   "exclude" : zero. L'organisation ne recoit aucun point et la question est
#               retiree de son maximum. C'EST LA POLITIQUE CIBLE, mais elle
#               suppose que la plateforme ait ete adaptee au prealable.
#               NE PAS ACTIVER SANS VALIDATION DU DEVELOPPEUR PLATEFORME.
#
NON_CONCERNED_POLICY = "half"
# ---------------------------------------------------------------------------

from datetime import datetime
from pathlib import Path


def match_question_type(regex_string):
    """Link the description of the question type to a type of question in the database : radio or checkbox"""
    if "unique" in regex_string:
        return "radio"
    else:
        return "checkbox"


class Assessment:
    def __init__(
            self,
            filename_fr=None,
            filename_en=None,
            version=None,
            previous_assessment_version=None,
            name_fr=None,
            name_en=None,
            prev_scores_assessment_version=None,
            prev_scores_filename=None,
    ):

        # Misc.
        self.directory = os.path.dirname(sys.argv[0])

        # Initialize basic descriptors
        self.filename_fr = filename_fr
        self.filename_en = filename_en
        self.raw_assessment_fr_filepath = f"input_files/{self.filename_fr}"
        self.raw_assessment_en_filepath = f"input_files/{self.filename_en}"
        if not os.path.isfile(self.raw_assessment_fr_filepath):
            print(f"File path {self.raw_assessment_fr_filepath} does not exist. Exiting...")
            sys.exit()
        if not os.path.isfile(self.raw_assessment_en_filepath):
            print(f"File path {self.raw_assessment_en_filepath} does not exist. Exiting...")
            sys.exit()
        self.version = version
        self.previous_assessment_version = previous_assessment_version
        self.name_fr = name_fr
        self.name_en = name_en

        # Initialize upgrade table related infos
        self.upgrade_table_filename = f"assessment-{self.version}_upgrade_table.json"
        self.upgrade_table_filepath = Path.cwd() / "input_files" / self.upgrade_table_filename
        if not os.path.isfile(self.upgrade_table_filepath):
            print(f"Upgrade table filepath {self.upgrade_table_filepath} does not exist. Exiting...")
            sys.exit()

        # Initialize old scoring related infos
        self.prev_scores_assessment_version = prev_scores_assessment_version
        self.prev_scores_filename = prev_scores_filename
        self.prev_scores_filepath = Path.cwd() / "processed_files" / self.prev_scores_filename
        if not os.path.isfile(self.prev_scores_filepath):
            print(f"Previous scores filepath {self.prev_scores_filepath} does not exist. Exiting...")
            sys.exit()

        # Initialize dictionary to store results from parsing the raw assessment
        self.dict = {}
        self.dictionarize_raw_assessment()

        # Attributes related to processing
        self.assessment_json_version_filename = f"assessment-{self.version}.json"
        self.assessment_json_version_filepath = f"processed_files/{self.assessment_json_version_filename}"
        self.scoring_template_filename = f"scoring_template-{self.version}.txt"
        self.scoring_template_filepath = f"intermediary_files/{self.scoring_template_filename}"
        self.scoring_version = None
        self.scoring_json_version_filename = None
        self.scoring_json_version_filepath = None

    def dictionarize_raw_assessment(self):

        self.dict["version"] = self.version
        self.dict["previous_assessment_version"] = self.previous_assessment_version
        self.dict["name_fr"] = self.name_fr
        self.dict["name_en"] = self.name_en
        now = datetime.now()
        self.dict["timestamp"] = now.strftime("%d-%b-%Y (%H:%M:%S.%f)")
        self.dict["sections"] = {}

        with open(self.raw_assessment_fr_filepath, 'r', encoding="utf-8") as file_fr, \
             open(self.raw_assessment_en_filepath, 'r', encoding="utf-8") as file_en:
            raw_fr = file_fr.read()
            raw_en = file_en.read()
        # Capture all sections of the assessment, first FR then EN
        r_section = r"[\#]{3,}\s[Section]+\s(?P<section_id>[0-9]+)[\-\s]+(?P<title>.+)\n\n?[*\[]{3}(?P<keyword>.*)[" \
                    r"*\]]{3}\n\n(?P<description>(.|\n)+?)\n\n\["
        match_each_fr_sections = re.findall(r_section, raw_fr)
        # print(match_each_fr_sections)  # DEBUG
        match_each_en_sections = re.findall(r_section, raw_en)
        # print(match_each_en_sections)  # DEBUG

        # The sections of the French file are covered, we suppose that this is the same order in the English file
        for i, fr_section_data in enumerate(match_each_fr_sections):
            en_section_data = match_each_en_sections[i]
            # Test if the French section is also in the English file, based on the numbering
            # The data of the both sections are saved in the dict
            if fr_section_data[0] == en_section_data[0]:
                self.dict["sections"]["section " + fr_section_data[0]] = {
                    "order_id": fr_section_data[0],
                    "name_fr": fr_section_data[1],
                    "name_en": en_section_data[1],
                    "keyword_fr": fr_section_data[2],
                    "keyword_en": en_section_data[2],
                    "description_fr": fr_section_data[3],
                    "description_en": en_section_data[3],
                    "elements": {}
                }
            else:
                print(f"The section {fr_section_data[0]} does not exist in the English file. Exiting...")
                sys.exit()

        # Capture all assessment elements
        r_element = r"(Q[0-9.]{3}(.|\n)+?---\n)"
        match_each_fr_element = re.findall(r_element, raw_fr)
        # print(match_each_fr_element)  # DEBUG
        match_each_en_element = re.findall(r_element, raw_en)
        # print(match_each_en_element)  # DEBUG

        # Regex for the element
        r_element_id = r"Q(?P<section_id>[0-9])\.(?P<evaluation_item_id>[0-9])\s:"
        r_element_title = r"Q[0-9.]{3,5}\s:\s\*\*(?P<title>.+)\*\*"
        r_element_condition = r"_\(Condition\s:\sR[0-9.]{3,5}\s\<\>\s(?P<item_id>[0-9a-z.]{5,8})\)_"
        r_element_question_text = r"(?P<question_text>.*(\s?:|\s?\?|\.))\n\nR[0-9.]{3}"
        r_element_type = r"_\((?P<answer_type>Type.+)\)_"
        r_element_answer_hint = r"_\((?P<answer_hint>(Sélectionner|Select).+)\)_"
        r_element_risk_domain = r"_\((Domaine de risque spécifique : |Specific risk domain: )(" \
                                r"?P<risk_domain>.+)\)_\n\n-\s\["
        r_element_answer_items = r"-\s\[\s]\s(?P<answer_item_id>\d{1,2}.\d{1,2}.\D)\s" \
                                 r"(?P<answer_item_text>[^\|\n]+)(\s\|\s_\((?P<answer_item_type>.+)\)_)?\n"
        r_element_explanation = r"(Expl[0-9.]+)\s:<\/summary>\n\n(?P<expl>(.|\n)+?)\n\n<"
        r_element_resources = r"(Ress?ources[0-9.]+)\s:<\/summary>\n\n(?P<resource>(.|\n)+?)<"
        r_resource_items = r"-\s\((?P<type>.+?)\)\s(?P<text>.+)\n"

        for el_fr, el_en in zip(match_each_fr_element, match_each_en_element):

            # Capture each component of the element
            match_id_fr = re.search(r_element_id, el_fr[0])
            match_id_en = re.search(r_element_id, el_en[0])

            # If one of the groups has no match_id, breaks the process
            if not match_id_fr.group('evaluation_item_id'):
                print("One element in the French file has no match_id. Exiting...")
                sys.exit()
            if not match_id_en.group('evaluation_item_id'):
                print("One element in the English file has no match_id. Exiting...")
                sys.exit()

            # If the ids do not match between the French and English versions, no need to go further
            if match_id_fr.group('evaluation_item_id') != match_id_en.group('evaluation_item_id'):
                print(f"The French match_id {match_id_fr} and the English one "
                      f"{match_id_en} do not match for an element. Exiting...")
                sys.exit()

            # If the sys didn't exist, we can save the element data
            # French part
            match_title_fr = re.search(r_element_title, el_fr[0])
            match_condition_fr = re.search(r_element_condition, el_fr[0])
            match_question_text_fr = re.search(r_element_question_text, el_fr[0])
            match_answer_type_fr = re.search(r_element_type, el_fr[0])
            match_answer_hint_fr = re.search(r_element_answer_hint, el_fr[0])  # Not used
            match_risk_domain_fr = re.search(r_element_risk_domain, el_fr[0])
            match_answer_items_fr = re.findall(r_element_answer_items, el_fr[0])
            match_explanation_fr = re.search(r_element_explanation, el_fr[0])
            match_resources_fr = re.search(r_element_resources, el_fr[0])
            match_resource_items_fr = []
            if match_resources_fr:
                match_resource_items_fr = re.findall(r_resource_items, match_resources_fr.group('resource'))

            # English part, catch only texts with translation (name, question_text, risk_domain and explanation)
            # and the items and the resources
            match_title_en = re.search(r_element_title, el_en[0])
            match_question_text_en = re.search(r_element_question_text, el_en[0])
            match_risk_domain_en = re.search(r_element_risk_domain, el_en[0])
            match_answer_items_en = re.findall(r_element_answer_items, el_en[0])
            match_explanation_en = re.search(r_element_explanation, el_en[0])
            match_resources_en = re.search(r_element_resources, el_en[0])
            match_resource_items_en = []
            if match_resources_en:
                match_resource_items_en = re.findall(r_resource_items, match_resources_en.group('resource'))

            # elem_id = match_id_fr.group('section_id') + "." + match_id_fr.group('evaluation_item_id')  # DEBUG
            # print(elem_id, 'n/a' if not match_title_fr else match_title_fr.group('title'))  # DEBUG
            # print(elem_id, 'n/a' if not match_condition else match_condition.group('item_id'))  # DEBUG
            # print(elem_id, 'n/a' if not match_question_text else match_question_text.group('question_text'))  # DEBUG
            # print(elem_id, 'n/a' if not match_answer_type else match_answer_type.group('answer_type'))  # DEBUG
            # print(elem_id, 'n/a' if not match_answer_hint else match_answer_hint.group('answer_hint'))  # DEBUG
            # print(elem_id, 'n/a' if not match_answer_items else match_answer_items)  # DEBUG
            # print(elem_id, 'n/a' if not match_explanation else match_explanation.group('expl'))  # DEBUG
            # print(elem_id, 'n/a' if not match_resources else match_resources.group('resource'))  # DEBUG

            # Populate the dictionary in the corresponding section
            # Calculate the value to add
            section = "section " + match_id_fr.group('section_id')
            evaluation_item = "element " + match_id_fr.group('evaluation_item_id')

            self.dict["sections"][section]["elements"][evaluation_item] = {
                'order_id': 'n/a' if not match_id_fr else match_id_fr.group('evaluation_item_id'),
                'name_fr': 'n/a' if not match_title_fr else match_title_fr.group('title'),
                'name_en': 'n/a' if not match_title_en else match_title_en.group('title'),
                'condition': 'n/a' if not match_condition_fr else match_condition_fr.group('item_id'),
                'question_text_fr': 'n/a' if not match_question_text_fr else match_question_text_fr.group('question_text'),
                'question_text_en': 'n/a' if not match_question_text_en else match_question_text_en.group('question_text'),
                'question_type': 'n/a' if not match_answer_type_fr else match_question_type(match_answer_type_fr.group('answer_type')),
                'answer_hint': 'n/a' if not match_answer_hint_fr else match_answer_hint_fr.group('answer_hint'),
                'risk_domain_fr': 'n/a' if not match_risk_domain_fr else match_risk_domain_fr.group('risk_domain'),
                'risk_domain_en': 'n/a' if not match_risk_domain_en else match_risk_domain_en.group('risk_domain'),
                'explanation_text_fr': 'n/a' if not match_explanation_fr else match_explanation_fr.group('expl'),
                'explanation_text_en': 'n/a' if not match_explanation_en else match_explanation_en.group('expl'),
                'resources': {},
                'answer_items': {},
            }

            # Resources
            if len(match_resource_items_en) != len(match_resource_items_fr):
                print(f"You do not have the same number of resources in the English "
                      f"file ({len(match_resource_items_en)}) and French file ({len(match_resource_items_fr)}) "
                      f"for the element Q{match_id_fr.group('section_id')}.{match_id_fr.group('evaluation_item_id')}")
                sys.exit()

            for i, (resource_fr, resource_en) in enumerate(zip(match_resource_items_fr, match_resource_items_en)):
                self.dict["sections"][section]["elements"][evaluation_item]['resources'][i] = {
                    'resource_type': resource_fr[0],
                    'resource_text_fr': resource_fr[1],
                    'resource_text_en': resource_en[1],
                }

            # Answer items
            if len(match_answer_items_fr) != len(match_answer_items_en):
                print(f"You do not have the same number of answer items in the English "
                      f"file ({len(match_answer_items_en)}) and French file ({len(match_answer_items_en)}) "
                      f"for the element Q{match_id_fr.group('section_id')}.{match_id_fr.group('evaluation_item_id')}")
                sys.exit()

            for (item_fr, item_en) in zip(match_answer_items_fr, match_answer_items_en):
                is_concerned_switch = 1 if item_fr[3] else 0
                self.dict["sections"][section]["elements"][evaluation_item]['answer_items'][item_fr[0]] = {
                    'order_id': item_fr[0][-1],
                    'answer_text_fr': item_fr[1],
                    'answer_text_en': item_en[1],
                    'is_concerned_switch': is_concerned_switch,  # Boolean, responsible for the intra element conditions
                }

    def dump_to_json_file(self):
        """Generate the .json file of the assessment"""

        with open(self.assessment_json_version_filepath, 'w', encoding="utf-8") as fp:
            json.dump(self.dict, fp, ensure_ascii=False, indent=4, separators=(',', ': '), sort_keys=False)

    def create_scoring_template(self):
        """Create a neat, easy-to-read and easy-to-write-in scoring template"""

        # Initialize key elements
        txt_lines = []
        sections_dict = self.dict["sections"]
        nb_sections = len(sections_dict)

        txt_lines.append(f'Assessment version : [{self.version}]\n')
        txt_lines.append("Scoring version : [1]\n")
        txt_lines.append("\n")

        # Indicate old scores infos in the scoring template for the new assessment
        txt_lines.append(f"Pre-filled score values are fetched from {self.prev_scores_filename}\n")
        txt_lines.append(f"(only for answer items set to 1 in {self.upgrade_table_filename} vs. version"
                         f" {self.prev_scores_assessment_version})\n")
        txt_lines.append(f"(answer items not set to 1 are pre-filled with '....' so you can identify them quickly)\n")
        txt_lines.append("\n")

        print(f"Now opening the upgrade table for your new assessment (version {self.version})")
        with open(self.prev_scores_filepath, "r", encoding="utf-8") as prev_scoring_file, \
                open(self.upgrade_table_filepath, "r", encoding="utf-8") as upgrade_table_file:
            prev_scores = json.load(prev_scoring_file)
            upgrade_table = json.load(upgrade_table_file)

            # Start filling in the template by looping over sections
            for i in range(1, nb_sections+1):
                section_idx = "section " + str(i)
                txt_lines.append(f'# {section_idx} - {sections_dict[section_idx]["name_fr"]}\n')
                txt_lines.append("\n")

                # Within a given section, loop over elements
                elements_dict = sections_dict[section_idx]["elements"]
                nb_elements = len(elements_dict)
                for j in range(1, nb_elements+1):
                    element_idx = "element " + str(j)
                    txt_lines.append(f'## Q{i}.{j} - {elements_dict[element_idx]["name_fr"]}\n')

                    # Within a given element, loop over answer items
                    items_dict = elements_dict[element_idx]["answer_items"]
                    for k, v in items_dict.items():
                        # Fetch score value of previous version to facilitate completion
                        pre_fill = '....'
                        upgrade_value = upgrade_table["diff_per_version"][
                            self.prev_scores_assessment_version]["answer_items"][k]
                        if upgrade_value == 1:
                            pre_fill = prev_scores[k]
                        elif upgrade_value != "no_fetch" and upgrade_value in prev_scores:
                            # upgrade_value designates a different corresponding item to fetch
                            pre_fill = prev_scores[upgrade_value]
                        if v["is_concerned_switch"] == 1:
                            pre_fill = '-nc-'
                        txt_lines.append(f'{pre_fill} [{k}] {v["answer_text_fr"]}\n')

                    txt_lines.append("\n")

                txt_lines.append("\n")

        # Create the scoring template text file
        with open(self.scoring_template_filepath, 'w', encoding="utf-8") as f:
            f.writelines(txt_lines)

    def process_scoring_template_to_json(self):

        # Initialize a dictionary
        temp_dict = {}

        # Check if there is indeed the scoring template with the standardized name, in the /intermediary_files folder
        if not os.path.isfile(self.scoring_template_filepath):
            print(f"File path {self.scoring_template_filepath} does not exist. Exiting...")
            sys.exit()

        with open(self.scoring_template_filepath, "r", encoding="utf-8") as fp:
            raw = fp.read()

            # Capture and fill the version numbers the user has filled in
            assessment_version = re.search(r"Assessment\sversion\s:\s\[(?P<version_nb>.+)\]", raw).group("version_nb")
            if assessment_version != self.version:
                raise Warning(f"Careful here! You are processing a scoring template indicating assessment version "
                              f"{assessment_version}, but you are currently operating with an Assessment instance "
                              f"which version is {self.version}")
            self.scoring_version = re.search(r"Scoring\sversion\s:\s\[(?P<version_nb>.+)\]", raw).group("version_nb")

            # Capture all answer items, their scoring config, and add items ids as keys and weights as values
            all_answer_items = re.findall(
                r"(?P<nb_points>\d{1,2}.?\d{0,2}|-nc-)\s\[(?P<item_id>\d{1,2}.\d{1,2}.\D)\]", raw)
            for item in all_answer_items:
                nb_points = 0 if item[0] == '-nc-' else item[0]
                temp_dict[item[1]] = str(nb_points)  # We need the values as string for the import in the platform

        # Generate the .json file of the assessment
        self.scoring_json_version_filename = f"assessment-{assessment_version}_scoring-{self.scoring_version}.json"
        self.scoring_json_version_filepath = f"processed_files/{self.scoring_json_version_filename}"
        with open(self.scoring_json_version_filepath, 'w', encoding="utf-8") as fp:
            json.dump(temp_dict, fp, ensure_ascii=False, indent=4, separators=(',', ': '), sort_keys=False)

    def enrich_assessment_with_scoring_recap(self):

        self.dict["enriched_with_scoring"] = {"scoring_version": self.scoring_version,
                                              "total_max_score": 0,
                                              "recap_per_section": {},
                                              }
        with open(self.scoring_json_version_filepath, 'r', encoding="utf-8") as scoring_file:

            scoring = json.load(scoring_file)

            for k, v in scoring.items():

                # First, delinearize the answer_item_id
                parse_k = re.search(r"(?P<s_id>\d{1,2}).(?P<e_id>\d{1,2}).(?P<a_id>\D)", k)
                section_id = parse_k.group("s_id")
                element_id = parse_k.group("e_id")

                # Second, convert the scoring value from string to float
                score_value = float(v)

                # Then we add it to the assessment (for the enriched version)
                self.dict["sections"]["section "+section_id]["elements"]["element "+element_id]["answer_items"][k][
                    "score_value"] = score_value

            # Now that we have the score values for each answer item, we'll compute the max score per element
            # There is a trick to compute this "max score" though: ...
            # ... for elements with multiple answers possible, it is the sum
            # ... but for elements with a unique answer, it is the max

            total_max_score = 0

            sections_dict = self.dict["sections"]
            nb_sections = len(sections_dict)
            for i in range(1, nb_sections+1):
                section_idx = "section " + str(i)
                section_max_score = 0

                elements_dict = sections_dict[section_idx]["elements"]
                nb_elements = len(elements_dict)
                for j in range(1, nb_elements+1):
                    element_idx = "element " + str(j)
                    element_max_score = 0
                    element_type = elements_dict[element_idx]["question_type"]

                    items_dict = elements_dict[element_idx]["answer_items"]
                    for k, v in items_dict.items():
                        try:
                            if element_type == "checkbox":
                                    element_max_score += v["score_value"]
                            elif element_type == "radio":
                                element_max_score = max(element_max_score, v["score_value"])
                        except KeyError:
                            continue

                    elements_dict[element_idx]["element_max_score"] = element_max_score
                    section_max_score += element_max_score

                sections_dict[section_idx]["section_max_score"] = section_max_score
                self.dict["enriched_with_scoring"]["recap_per_section"][section_idx] = section_max_score
                total_max_score += section_max_score

            self.dict["enriched_with_scoring"]["total_max_score"] = total_max_score

        with open(self.assessment_json_version_filepath, 'w', encoding="utf-8") as fp:
            json.dump(self.dict, fp, ensure_ascii=False, indent=4, separators=(',', ': '), sort_keys=False)



# NOUVEAU CODE DE 202609 ---
# On veut changer la maniere de calculer la note finale,
# pour ne pas compter les questions "non concerné"

    def enrich_assessment_with_non_concerned_recap(self):

        temp_non_concerned = {}
        temp_conditional = {}

        # Loop over sections
        sections_dict = self.dict["sections"]
        nb_sections = len(sections_dict)
        for i in range(1, nb_sections + 1):
            section_idx = "section " + str(i)

            # Loop over elements
            elements_dict = sections_dict[section_idx]["elements"]
            nb_elements = len(elements_dict)
            for j in range(1, nb_elements + 1):
                element_idx = "element " + str(j)
                element_has_nc = False
                element_is_conditional = True if elements_dict[element_idx]["condition"] != "n/a" else False

                # Loop over answer items to detect "NC" switches
                items_dict = elements_dict[element_idx]["answer_items"]
                for k, v in items_dict.items():
                    if v["is_concerned_switch"] == 1:
                        element_has_nc = True

                # Valeur transmise a la plateforme, selon NON_CONCERNED_POLICY
                max_score = elements_dict[element_idx]["element_max_score"]
                if NON_CONCERNED_POLICY == "exclude":
                    nc_value = 0.0
                else:
                    nc_value = max_score / 2.0

                if element_has_nc:
                    temp_non_concerned[f"{i}.{j}"] = round(nc_value, 3)
                if element_is_conditional:
                    temp_conditional[f"{i}.{j}"] = round(nc_value, 3)

        # Noms de clés conservés à l'identique de la version 202301, attendus par la plateforme
        self.dict["non_concerned_recap"] = {
            "non_concerned_in_element": temp_non_concerned,
            "conditional_elements": temp_conditional,
        }

        with open(self.assessment_json_version_filepath, 'w', encoding="utf-8") as fp:
            json.dump(self.dict, fp, ensure_ascii=False, indent=4, separators=(',', ': '), sort_keys=False)
