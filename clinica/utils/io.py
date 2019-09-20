# coding: utf8


def zip_nii(in_file, same_dir=False):
    from os import getcwd
    from os.path import abspath, join
    import gzip
    import shutil
    from nipype.utils.filemanip import split_filename
    from traits.trait_base import _Undefined

    if (in_file is None) or isinstance(in_file, _Undefined):
        return None

    if not isinstance(in_file, str):  # type(in_file) is list:
        return [zip_nii(f, same_dir) for f in in_file]

    orig_dir, base, ext = split_filename(str(in_file))

    # Already compressed
    if ext[-3:].lower() == ".gz":
        return in_file
    # Not compressed

    if same_dir:
        out_file = abspath(join(orig_dir, base + ext + '.gz'))
    else:
        out_file = abspath(join(getcwd(), base + ext + '.gz'))

    with open(in_file, 'rb') as f_in, gzip.open(out_file, 'wb') as f_out:
        shutil.copyfileobj(f_in, f_out)

    return out_file


def unzip_nii(in_file):
    from nipype.utils.filemanip import split_filename
    from nipype.algorithms.misc import Gunzip
    from traits.trait_base import _Undefined

    if (in_file is None) or isinstance(in_file, _Undefined):
        return None

    if not isinstance(in_file, str):  # type(in_file) is list:
        return [unzip_nii(f) for f in in_file]

    _, base, ext = split_filename(in_file)

    # Not compressed
    if ext[-3:].lower() != ".gz":
        return in_file
    # Compressed
    gunzip = Gunzip(in_file=in_file)
    gunzip.run()
    return gunzip.aggregate_outputs().out_file


def fix_join(path, *paths):
    # This workaround is used in pipelines like DWIPreprocessingUsingT1
    # In the workflow.connect part, you can use some function that are used as string, causing an import error
    import os
    return os.path.join(path, *paths)


def save_participants_sessions(participant_ids, session_ids, out_folder, out_file=None):
    """
    Save <participant_ids> <session_ids> in <out_folder>/<out_file> TSV file.
    """
    import os
    import errno
    import pandas
    from clinica.utils.stream import cprint

    assert(len(participant_ids) == len(session_ids))

    try:
        os.makedirs(out_folder)
    except OSError as e:
        if e.errno != errno.EEXIST:  # EEXIST: folder already exists
            raise e

    if out_file:
        tsv_file = os.path.join(out_folder, out_file)
    else:
        tsv_file = os.path.join(out_folder, 'participants.tsv')

    try:
        data = pandas.DataFrame({
            'participant_id': participant_ids,
            'session_id': session_ids,
        })
        data.to_csv(tsv_file, sep='\t', index=False, encoding='utf-8')
    except Exception as e:
        cprint("Impossible to save %s with pandas" % out_file)
        raise e


def get_subject_id(bids_or_caps_file):
    """
    Extracts "sub-<participant_id>_ses-<session_label>" from BIDS or CAPS file
    """
    import re

    m = re.search(r'(sub-[a-zA-Z0-9]+)/(ses-[a-zA-Z0-9]+)', bids_or_caps_file)

    if m is None:
        raise ValueError(
            'Input filename is not in a BIDS or CAPS compliant format.'
            ' It does not contain the subject and session information.')

    subject_id = m.group(1) + '_' + m.group(2)

    return subject_id


def extract_image_ids(bids_or_caps_files):
    """Extract image IDs (e.g. ['sub-CLNC01_ses-M00', 'sub-CLNC01_ses-M18']  from `bids_or_caps_files`."""
    import re
    id_bids_or_caps_files = [re.search(r'(sub-[a-zA-Z0-9]+)_(ses-[a-zA-Z0-9]+)', file).group()
                             for file in bids_or_caps_files]
    return id_bids_or_caps_files


def reorder_bids_or_caps_files(input_ids, bids_or_caps_files):
    """Reorder `bids_or_caps_files` with respect to `input_ids`."""
    id_bids_or_caps_files = extract_image_ids(bids_or_caps_files)
    indices = [id_bids_or_caps_files.index(input_ids[idx]) for idx in range(len(input_ids))]
    reordered_bids_or_caps_files = [bids_or_caps_files[i] for i in indices]
    return reordered_bids_or_caps_files


def check_bids_folder(bids_directory):
    """
    check_bids_folder function checks the following items:
        - bids_directory is a string
        - the provided path exists and is a directory
        - provided path is not a CAPS folder (BIDS and CAPS could be swapped by user). We simply check that there is
          not a folder called 'subjects' in the provided path (that exists in CAPS hierarchy)
        - provided folder is not empty
        - provided folder must contains at least one directory whose name starts with 'sub-'
    """
    from os.path import isdir, join
    from os import listdir
    from colorama import Fore
    from clinica.utils.exceptions import ClinicaBIDSError

    assert isinstance(bids_directory, str), 'Argument you provided to check_bids_folder() is not a string.'

    if not isdir(bids_directory):
        raise ClinicaBIDSError(Fore.RED + '\n[Error] The BIDS directory you gave is not a folder.\n' + Fore.RESET
                               + Fore.YELLOW + '\nError explanations:\n' + Fore.RESET
                               + ' - Clinica expected the following path to be a folder:' + Fore.BLUE + bids_directory
                               + Fore.RESET + '\n'
                               + ' - If you gave relative path, did you run Clinica on the good folder?')

    if isdir(join(bids_directory, 'subjects')):
        raise ClinicaBIDSError(Fore.RED + '\n[Error] The BIDS directory (' + bids_directory + ') you provided seems to '
                               + 'be a CAPS directory due to the presence of a \'subjects\' folder.' + Fore.RESET)

    if len(listdir(bids_directory)) == 0:
        raise ClinicaBIDSError(Fore.RED + '\n[Error] The BIDS directory you provided  is empty. (' + bids_directory
                               + ').' + Fore.RESET)

    if len([item for item in listdir(bids_directory) if item.startswith('sub-')]) == 0:
        raise ClinicaBIDSError(Fore.RED + '\n[Error] Your BIDS directory does not contains a single folder whose name '
                               + 'starts with \'sub-\'. Check that your folder follow BIDS standard' + Fore.RESET)


def check_caps_folder(caps_directory):
    """
    check_caps_folder function checks the following items:
        - caps_directory is a string
        - the provided path exists and is a directory
        - provided path is not a BIDS folder (BIDS and CAPS could be swapped by user). We simply check that there is
          not a folder whose name starts with 'sub-' in the provided path (that exists in BIDS hierarchy)
    Keep in mind that CAPS folder can be empty
    """
    from os import listdir
    import os
    from colorama import Fore
    from clinica.utils.exceptions import ClinicaCAPSError

    assert isinstance(caps_directory, str), 'Argument you provided to check_caps_folder() is not a string.'

    if not os.path.isdir(caps_directory):
        raise ClinicaCAPSError(Fore.RED + '\n[Error] The CAPS directory you gave is not a folder.\n' + Fore.RESET
                               + Fore.YELLOW + '\nError explanations:\n' + Fore.RESET
                               + ' - Clinica expected the following path to be a folder:' + Fore.BLUE + caps_directory
                               + Fore.RESET + '\n'
                               + ' - If you gave relative path, did you run Clinica on the good folder?')

    sub_folders = [item for item in listdir(caps_directory) if item.startswith('sub-')]
    if len(sub_folders) > 0:
        error_string = '\n[Error] Your CAPS directory contains at least one folder whose name ' \
                       + 'starts with \'sub-\'. Check that you did not swap BIDS and CAPS folders.\n' \
                       + ' Folder(s) found that match(es) BIDS architecture:\n'
        for dir in sub_folders:
            error_string += '\t' + dir + '\n'
        error_string += 'A CAPS directory has a folder \'subjects\' at its root, in which are stored the output ' \
                        + 'of the pipeline for each subject.'
        raise ClinicaCAPSError(error_string)


def bids_type_to_path(bids_type, bids_directory, participant_id, session_id):
    dict_bids_type_to_path = {
        # anat/
        "T1W_NII": "%s/%s/%s/anat/%s_%s*_T1w.(nii|nii.gz)" %
                   (bids_directory, participant_id, session_id, participant_id, session_id),
        # dwi/
        "DWI_BVAL": "%s/%s/%s/dwi/%s_%s*_dwi.bval" %
                    (bids_directory, participant_id, session_id, participant_id, session_id),
        "DWI_BVEC": "%s/%s/%s/dwi/%s_%s*_dwi.bvec" %
                    (bids_directory, participant_id, session_id, participant_id, session_id),
        "DWI_NII": "%s/%s/%s/dwi/%s_%s*_dwi.(nii|nii.gz)" %
                   (bids_directory, participant_id, session_id, participant_id, session_id),
        "DWI_JSON": "%s/%s/%s/dwi/%s_%s*_dwi.json" %
                    (bids_directory, participant_id, session_id, participant_id, session_id),
        # fmap/
        "FMAP_MAGNITUDE1_NII": "%s/%s/%s/dwi/%s_%s*_magnitude1.(nii|nii.gz)" %
                               (bids_directory, participant_id, session_id, participant_id, session_id),
        "FMAP_MAGNITUDE1_JSON": "%s/%s/%s/dwi/%s_%s*_magnitude1.json" %
                                (bids_directory, participant_id, session_id, participant_id, session_id),
        "FMAP_MAGNITUDE2_NII": "%s/%s/%s/dwi/%s_%s*_magnitude2.(nii|nii.gz)" %
                               (bids_directory, participant_id, session_id, participant_id, session_id),
        "FMAP_MAGNITUDE2_JSON": "%s/%s/%s/dwi/%s_%s*_magnitude2.json" %
                                (bids_directory, participant_id, session_id, participant_id, session_id),
        "FMAP_PHASEDIFF_NII": "%s/%s/%s/dwi/%s_%s*_phasediff.(nii|nii.gz)" %
                              (bids_directory, participant_id, session_id, participant_id, session_id),
        "FMAP_PHASEDIFF_JSON": "%s/%s/%s/dwi/%s_%s*_phasediff.json" %
                               (bids_directory, participant_id, session_id, participant_id, session_id),
        "FMAP_PHASE1_NII": "%s/%s/%s/dwi/%s_%s*_phase1.(nii|nii.gz)" %
                           (bids_directory, participant_id, session_id, participant_id, session_id),
        "FMAP_PHASE1_JSON": "%s/%s/%s/dwi/%s_%s*_phase1.json" %
                            (bids_directory, participant_id, session_id, participant_id, session_id),
        "FMAP_PHASE2_NII": "%s/%s/%s/dwi/%s_%s*_phase2.(nii|nii.gz)" %
                           (bids_directory, participant_id, session_id, participant_id, session_id),
        "FMAP_PHASE2_JSON": "%s/%s/%s/dwi/%s_%s*_phase2.json" %
                            (bids_directory, participant_id, session_id, participant_id, session_id),
        "FMAP_MAGNITUDE_NII": "%s/%s/%s/dwi/%s_%s*_magnitude.(nii|nii.gz)" %
                              (bids_directory, participant_id, session_id, participant_id, session_id),
        "FMAP_MAGNITUDE_JSON": "%s/%s/%s/dwi/%s_%s*_magnitude.json" %
                               (bids_directory, participant_id, session_id, participant_id, session_id),
        "FMAP_NII": "%s/%s/%s/dwi/%s_%s*_fieldmap.(nii|nii.gz)" %
                    (bids_directory, participant_id, session_id, participant_id, session_id),
        "FMAP_JSON": "%s/%s/%s/dwi/%s_%s*_fieldmap.json" %
                     (bids_directory, participant_id, session_id, participant_id, session_id),
    }
    return dict_bids_type_to_path[bids_type]


def caps_type_to_path(caps_type, caps_directory, participant_id, session_id):
    pipeline_to_path = {
        "t1-freesurfer": "%s/subjects/%s/%s/t1/freesurfer_cross_sectional/%s_%s" %
                         (caps_directory, participant_id, session_id, participant_id, session_id),
        "dwi-preprocessing": "%s/subjects/%s/%s/dwi/preprocessing" %
                             (caps_directory, participant_id, session_id),
    }
    dict_caps_type_to_path = {
        # t1-freesurfer
        "T1_FS_WM": "%s/mri/wm.seg.mgz" %
                    pipeline_to_path["t1-freesurfer"],
        "T1_FS_DESIKAN": "%s/mri/aparc+aseg.mgz" %
                         pipeline_to_path["t1-freesurfer"],
        "T1_FS_DESTRIEUX": "%s/mri/aparc.a2009s+aseg.mgz" %
                           pipeline_to_path["t1-freesurfer"],
        "T1_FS_BM": "%s/mri/brainmask.mgz" %
                    pipeline_to_path["t1-freesurfer"],
        "T1_FS_BE": "%s/mri/brain.mgz" %
                    pipeline_to_path["t1-freesurfer"],
        # dwi-preprocessing
        "DWI_PREPROC_BVAL": "%s/%s_%s*_dwi_space-(b0|T1w)_preproc.bval" %
                            (pipeline_to_path["dwi-preprocessing"], participant_id, session_id),
        "DWI_PREPROC_BVEC": "%s/%s_%s*_dwi_space-(b0|T1w)_preproc.bvec" %
                            (pipeline_to_path["dwi-preprocessing"], participant_id, session_id),
        "DWI_PREPROC_NII": "%s/%s_%s*_dwi_space-(b0|T1w)_preproc.(nii|nii.gz)" %
                           (pipeline_to_path["dwi-preprocessing"], participant_id, session_id),
        "DWI_PREPROC_BM": "%s/%s_%s*_dwi_space-(b0|T1w)_brainmask.(nii|nii.gz)" %
                          (pipeline_to_path["dwi-preprocessing"], participant_id, session_id),
    }
    return dict_caps_type_to_path[caps_type]


def bids_type_to_description(bids_type):
    dict_bids_type_to_description = {
        # anat/
        "T1W_NII": "T1 weighted image",
        # dwi/
        "DWI_BVAL": "bval file",
        "DWI_BVEC": "bvec file",
        "DWI_NII": "diffusion weighted image",
        "DWI_JSON": "DWI JSON file",
        # fmap/
        "FMAP_MAGNITUDE1_NII": "magnitude (1st) image",
        "FMAP_MAGNITUDE1_JSON": "magnitude (1st) JSON file",
        "FMAP_MAGNITUDE2_NII": "magnitude (2st) image",
        "FMAP_MAGNITUDE2_JSON": "magnitude (2st) JSON file",
        "FMAP_PHASEDIFF_NII": "phase difference image",
        "FMAP_PHASEDIFF_JSON": "phase difference JSON file",
        "FMAP_PHASE1_NII": "phase (1st) image",
        "FMAP_PHASE1_JSON": "phase (1st) JSON file",
        "FMAP_PHASE2_NII": "phase (2nd) image",
        "FMAP_PHASE2_JSON": "phase (2nd) JSON file",
        "FMAP_MAGNITUDE_NII": "magnitude image",
        "FMAP_MAGNITUDE_JSON": "magnitude JSON file",
        "FMAP_NII": "fieldmap image",
        "FMAP_JSON": "fieldmap JSON file",
    }
    return dict_bids_type_to_description[bids_type]


def caps_type_to_description(caps_type):
    dict_caps_type_to_description = {
        # t1-freesurfer
        "T1_FS_WM": "white matter segmentation",
        "T1_FS_DESIKAN": "Desikan parcellation",
        "T1_FS_DESTRIEUX": "Destrieux parcellation",
        "T1_FS_BM": "T1w brainmask",
        "T1_FS_BE": "brain extracted T1w",
        # dwi-preprocessing
        "DWI_PREPROC_BVAL": "preprocessed bval",
        "DWI_PREPROC_BVEC": "preprocessed bvec",
        "DWI_PREPROC_NII": "preprocessed DWI",
        "DWI_PREPROC_BM": "b0 brainmask",
    }
    return dict_caps_type_to_description[caps_type]


def check_input_bids_files(list_bids_files, bids_type, bids_directory, participant_ids, session_ids):
    import collections
    from colorama import Fore

    subject_ids = [participant_ids[i] + '_' + session_ids[i] for i in range(len(participant_ids))]

    id_bids_files = extract_image_ids(list_bids_files)

    id_duplicated_files = [item for item, count in collections.Counter(id_bids_files).items() if count > 1]

    id_missing_files = list(set(subject_ids) - set(id_bids_files))

    error_message = ""
    if id_missing_files:
        error_message += (
            "\n%s[Error] Clinica could not find %s file in BIDS directory for the following subject(s):%s\n" %
            (Fore.RED, bids_type_to_description(bids_type), Fore.RESET)
        )
        for id_missing_file in id_missing_files:
            participant_id = id_missing_file.split('_')[0]
            session_id = id_missing_file.split('_')[1]
            bids_path = bids_type_to_path(bids_type, bids_directory, participant_id, session_id)
            error_message += (
                "* %s%s%s. Expected path: %s\n" %
                (Fore.BLUE, id_missing_file.replace('_', '|'), Fore.RESET, bids_path)
            )
        error_message += (
            "%s* Error explanations:\n"
            " - Did the subject(s) have the acquisition?%s\n" %
            (Fore.YELLOW, Fore.RESET)
        )

    if id_duplicated_files:
        error_message += (
            "\n%s[Error] Clinica found multiple %s files in BIDS directory for the following subject(s):%s" %
            (Fore.RED, bids_type_to_description(bids_type), Fore.RESET)
        )
        for id_duplicated_file in id_duplicated_files:
            error_message += (
                "\n* %s%s%s. Found files:\n%s" % (
                    Fore.BLUE, id_duplicated_file.replace('_', '|'), Fore.RESET,
                    '\n'.join('- ' + s for s in list_bids_files if id_duplicated_file in s)
                    ))
        error_message += (
            "\n%s* Error explanations:\n"
            " - Clinica expected to find a single file in BIDS directory for each subject.\n"
            " - If you have different runs and/or acquisitions on the same folder, Clinica can not handle this situation.%s\n" %
            (Fore.YELLOW, Fore.RESET)
        )
    return error_message


def check_input_caps_files(list_caps_files, caps_type, pipeline_name, caps_directory, participant_ids, session_ids):
    import collections
    from colorama import Fore

    subject_ids = [participant_ids[i] + '_' + session_ids[i] for i in range(len(participant_ids))]

    id_caps_files = extract_image_ids(list_caps_files)

    id_duplicated_files = [item for item, count in collections.Counter(id_caps_files).items() if count > 1]

    id_missing_files = list(set(subject_ids) - set(id_caps_files))

    error_message = ""
    if id_missing_files:
        error_message += (
            "\n%s[Error] Clinica could not find %s file in CAPS directory for the following subject(s):%s\n" %
            (Fore.RED, caps_type_to_description(caps_type), Fore.RESET)
        )
        for id_missing_file in id_missing_files:
            participant_id = id_missing_file.split('_')[0]
            session_id = id_missing_file.split('_')[1]
            caps_path = caps_type_to_path(caps_type, caps_directory, participant_id, session_id)
            error_message += (
                "* %s%s%s. Expected path: %s\n" %
                (Fore.BLUE, id_missing_file.replace('_', '|'), Fore.RESET, caps_path)
            )
        error_message += (
            "%s* Error explanations:\n"
            " - Did you run the %s pipeline on the subject(s)?%s\n" %
            (Fore.YELLOW, pipeline_name, Fore.RESET)
        )

    if id_duplicated_files:
        error_message += (
            "\n%s[Error] Clinica found multiple %s files in CAPS directory for the following subject(s):%s" %
            (Fore.RED, caps_type_to_description(caps_type), Fore.RESET)
        )
        for id_duplicated_file in id_duplicated_files:
            error_message += (
                "\n* %s%s%s. Found files:\n%s" % (
                    Fore.BLUE, id_duplicated_file.replace('_', '|'), Fore.RESET,
                    '\n'.join('- ' + s for s in list_caps_files if id_duplicated_file in s)
                    ))
        error_message += (
            "\n%s* Error explanations:\n"
            " - Clinica expected to find a single file in CAPS directory for each subject.\n"
            " - Did you duplicate files in CAPS directory?%s\n" %
            (Fore.YELLOW, Fore.RESET)
        )
    if not error_message:
        list_caps_files = reorder_bids_or_caps_files(subject_ids, list_caps_files)

    return error_message


def extract_crash_files_from_log_file(filename):
    """Extract crash files (*.pklz) from `filename`.
    """
    import os
    import re

    assert(os.path.isfile(filename))

    log_file = open(filename, "r")
    crash_files = []
    for line in log_file:
        if re.match("(.*)crashfile:(.*)", line):
            crash_files.append(line.replace('\t crashfile:', '').replace('\n', ''))

    return crash_files


def get_subject_session_list(input_dir, ss_file=None, is_bids_dir=True, use_session_tsv=False):
    """Parses a BIDS or CAPS directory to get the subjects and sessions.

    This function lists all the subjects and sessions based on the content of
    the BIDS or CAPS directory or (if specified) on the provided
    subject-sessions TSV file.

    Args:
        input_dir: A BIDS or CAPS directory path.
        ss_file: A subjects-sessions file (.tsv format).
        is_bids_dir: Indicates if input_dir is a BIDS or CAPS directory
        use_session_tsv (boolean): Specify if the list uses the sessions listed in the sessions.tsv files

    Returns:
        subjects: A subjects list.
        sessions: A sessions list.
    """
    import clinica.iotools.utils.data_handling as cdh
    import pandas as pd
    import tempfile
    from time import time, strftime, localtime
    import os
    from colorama import Fore
    from clinica.utils.exceptions import ClinicaException

    if not ss_file:
        output_dir = tempfile.mkdtemp()
        timestamp = strftime('%Y%m%d_%H%M%S', localtime(time()))
        tsv_file = '%s_subjects_sessions_list.tsv' % timestamp
        ss_file = os.path.join(output_dir, tsv_file)

        cdh.create_subs_sess_list(
            input_dir=input_dir,
            output_dir=output_dir,
            file_name=tsv_file,
            is_bids_dir=is_bids_dir,
            use_session_tsv=use_session_tsv)

    if not os.path.isfile(ss_file):
        raise ClinicaException(
            "\n%s[Error] The TSV file you gave is not a file.%s\n"
            "\n%sError explanations:%s\n"
            " - Clinica expected the following path to be a file: %s%s%s\n"
            " - If you gave relative path, did you run Clinica on the good folder?" %
            (Fore.RED, Fore.RESET,
             Fore.YELLOW, Fore.RESET,
             Fore.BLUE, ss_file, Fore.RESET)
        )
    ss_df = pd.io.parsers.read_csv(ss_file, sep='\t')
    if 'participant_id' not in list(ss_df.columns.values):
        raise Exception('No participant_id column in TSV file.')
    if 'session_id' not in list(ss_df.columns.values):
        raise Exception('No session_id column in TSV file.')
    subjects = list(ss_df.participant_id)
    sessions = list(ss_df.session_id)

    # Remove potential whitespace in participant_id or session_id
    return [ses.strip(' ') for ses in sessions], [sub.strip(' ') for sub in subjects]
