# Processing scripts for the RTDS assessment

## Introduction

This library provides several scripts enabling to:

- Parse the raw version of the French and English assessment and create a single structured object capturing all its properties
- Generate a scoring template easy-to-read and easy-to-fill-in
- Parse the scoring template once completed and create a structure scoring object
- Leverage the upgrade table and the scoring to compute summaries of:
  - the total max score configured per section
  - the evaluation elements conditional to others
  - the evaluation elements having a dedicated non-concerned answer item

## Instructions

### Standard use - Complete processing

1. Fetch the remote version of the repository with `git fetch <remote_name>` and `git pull <remote_name> master` if needed, and checkout to a new branch (for example `git checkout -b process-new-assessment-version`)

1. Prepare the new assessments (both French version and English version) you would like to process and place in folder `input_files`:

   - the raw assessments. They are expected to be `.md` files (although any text file format should probably work)
   - add the language code suffix (`-fr` and `-en`) to the raw assessments. ex: `assessment-0.63-fr.md`, `assessment-0.63-en.md`
   - its upgrade table. It is expected to be a `.json` file following a strict structure (see already existing ones)

1. Determine a previous version of the assessment and of its associated scoring you wish to use to pre-fill your scoring template for the new assessment you want to process.

1. Check and complete or amend the parameters of the processing in `main.py`. You have to specify both the English name and the French name.

   ```python
   ASSESSMENT_MD_VERSION_FILENAME_FR = 'assessment-0.61-fr.md'
   ASSESSMENT_MD_VERSION_FILENAME_EN = 'assessment-0.61-en.md'
   ASSESSMENT_VERSION = '0.61'
   ASSESSMENT_PREVIOUS_VERSION = '0.6'  # previous version of the assessment
   ASSESSMENT_NAME_FR = 'Evaluation Data Science Responsable et de Confiance'
   ASSESSMENT_NAME_EN = 'Responsible and Trustworthy Data Science Assessment'
   ASSESSMENT_VERSION_TO_PREFILL_SCORING_TEMPLATE = '0.6'  # version used to pre-fill the scoring template
   OLD_SCORING_FILENAME = 'assessment-0.6_scoring-1.json'  # scoring reference of that version
   ```

   Then execute the corresponding cell of `main.py`.

1. Execute the first cell of `main.py`. It will create:

   - the `.json` version of the assessment in folder `/processed_files`
   - the `.txt` scoring template in folder `/intermediary_files`

1. Fill-in the scoring template. If you configured previous versions correctly your template should be pre-filled, and only answer items which cannot be fetched from the previous version are prefixed with `....` so that you can identify them quickly. See "Values for upgrade_status" below to control what gets fetched.

   > Note: **Make sure you save your file**.

   > Warning: re-running the first cell overwrites the scoring template. Back it up before re-running, or instantiate the `Assessment` object on its own (see "Processing only a new scoring template").

1. Execute the second cell of `main.py`. It will:

   - create the `.json` version of the scoring
   - update the `.json` version of the assessment with the summaries

1. Check the summaries at the end of the `.json` version of the assessment, and verify if it is coherent.

1. Commit the newly processed files and push them to the remote:

   ```bash
   git add .
   git commit -m "Process version XX of the assessment"
   git push <remote_name> process-new-assessment
   ```

### Processing only a new scoring template

If you only need to update the scoring template for an assessment already processed, proceed as follow:

1. Update the scoring template and be very careful to increment the scoring version (second line of the scoring template)

1. Then execute partially `main.py` as follow:

   1. Run the preliminary cell and the instantiation of the `Assessment` object:

      ```python
      new_assessment = assessment.Assessment(...)
      ```

   1. Then run the second cell:

      ```python
      new_assessment.process_scoring_template_to_json()
      new_assessment.enrich_assessment_with_scoring_recap()
      new_assessment.enrich_assessment_with_non_concerned_recap()
      ```

1. You should be good to go. Don't forget to commit your new scoring and updated structured assessment, and push them to the remote.

### Elements on upgrade tables

Keeping a complete history of differences between versions within a single upgrade table is not needed. It proves useful when it is desired to explicitly document the differences between a given new version and multiple previous ones.

Below are listed the different values possible for certain syntax elements, and some writing rules to keep an homogeneous style:

#### Values for upgrade_status of elements and for answer items

- 1: when to be kept
- "no_fetch": when not to be kept
- "2.3": indicating a different corresponding element or item to fetch

The third form is what you need whenever answer items are shifted, for instance when a
"not concerned" item is inserted at the top of an element, or when an element is moved to
another section. Mapping `"1.7.b": "1.7.a"` tells the scripts that the new item `1.7.b`
corresponds to the former `1.7.a`: its score value is pre-filled in the scoring template,
and organisations keep their previous answer. Using `"no_fetch"` instead would force them
to answer the element again from scratch.

#### Values for "pastilles"

- Inchangé / Unchanged
- Mis à jour / Updated
- Nouveau / New

#### Values for "editos"

- Write change editos as sentences ending with a period "."

### Non-concerned policy

The constant `NON_CONCERNED_POLICY`, at the top of `assessment.py`, determines the value
written in the `non_concerned_recap` block of the assessment json, for each element having
a dedicated "not concerned" answer item.

- `"half"`: half of the element max score. This is the historical behaviour and the
  default. The platform grants that amount to a non-concerned organisation and removes it
  from the score it can reach.
- `"exclude"`: zero. The organisation is granted no points and the element is removed from
  its maximum.

**`"exclude"` requires the platform scoring logic to be adapted first.** As it currently
stands, the platform uses this single value both to grant points and to reduce the reachable
maximum. Setting it to zero without changing the platform would penalise non-concerned
organisations rather than leaving them unaffected. Keep `"half"` until the platform side
has been updated accordingly.

### Files to upload to the platform

Three files, all carrying the same version number in their name:

- `processed_files/assessment-<version>.json`
- `processed_files/assessment-<version>_scoring-<n>.json`
- `input_files/assessment-<version>_upgrade_table.json`

Before uploading, check in the assessment json that `non_concerned_recap` holds the keys
`non_concerned_in_element` and `conditional_elements`. These names are the ones the platform
expects; renaming them silently breaks the score computation.
