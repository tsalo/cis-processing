"""
BIDS version: 1.2.1

Heuristics file for converting DIVA dicoms to BIDS dataset with heudiconv
Meant to be roughly ReproIn-compatible, minus the checks and balances built
into that system.
We're using this because there are some elements in our protocol that are not
supported in ReproIn yet.
"""
import os
import logging
import pathlib

LGR = logging.getLogger(__name__)


def create_key(template, outtype=('nii.gz',), annotation_classes=None):
    if template is None or not template:
        raise ValueError('Template must be a valid format string')
    return template, outtype, annotation_classes


def build_path(entities):
    """
    Build BIDS file path from entities with **NO** validation.
    You might ask why we wouldn't use BIDSLayout.build_path?
    Because some things (e.g., SWI) are not in the BIDS specification yet and
    pybids will raise an error.
    """
    FILENAME_KEY_ORDER = ['sub', 'ses', 'task', 'acq', 'ce', 'rec', 'dir', 'run',
                          'mod', 'recording', 'proc', 'space']
    REQUIRED_KEYS = ['sub', 'datatype', 'suffix', 'extension']
    assert all(entities.get(rk) for rk in REQUIRED_KEYS)
    maps = '_'.join('{}-{}'.format(k, entities.get(k)) for k in
                    FILENAME_KEY_ORDER if entities.get(k))

    filename = 'sub-{}'.format(entities['sub'])

    if entities.get('ses'):
        filename = '{}/ses-{}'.format(filename, entities['ses'])

    filename = '{fn}/{dt}/{maps}_{suff}.{ext}'.format(
        fn=filename,
        dt=entities['datatype'],
        maps=maps,
        suff=entities['suffix'],
        ext=entities['extension'])

    return filename


def generate_name(dcminfo, session=None):
    """
    Generate a heudiconv key from the series info.
    """
    # Grab relevant fields from header
    seq_name = dcminfo.series_description
    image_type = dcminfo.image_type

    # Get base entities
    name_fields = seq_name.split('_')

    # Grab value pairs but drop non-pairs
    value_pairs = name_fields[1:]
    value_pairs = [p.split('-') for p in value_pairs]
    value_pairs = [p for p in value_pairs if len(p) == 2]
    entities = dict(value_pairs)

    # Get those first two fields
    datatype, suffix = name_fields[0].split('-')
    entities['datatype'] = datatype
    entities['suffix'] = suffix

    # Adjust entities as needed
    entities['sub'] = '<subject>'  # <> to be cool with formatting

    # NOTE: May need some help/work here
    if session is not None:
        entities['ses'] = session

    entities['extension'] = 'nii.gz'
    if 'SBRef' in seq_name:
        entities['suffix'] = 'sbref'

    # The logic here could be expanded for field maps
    # (e.g., phasediff, phase1, phase2)
    if 'P' in image_type:
        entities['suffix'] = 'phase'

    path = build_path(entities)
    path = path.replace('<', '{').replace('>', '}')  # support format again

    # Drop the suffix, since the key doesn't want it
    path = path.replace(''.join(pathlib.Path(path).suffixes), '')
    return path


def infotodict(seqinfo):
    """Heuristic evaluator for determining which runs belong where

    allowed template fields - follow python string module:

    item: index within category
    subject: participant id
    seqitem: run number during scanning
    subindex: sub index within group
    """
    outtype = ('nii.gz')
    info = {}

    # Attempt to grab session from first scan
    first_scan_name = seqinfo[0].series_description
    ses_val = [val for val in first_scan_name.split('_') if val.startswith('ses-')]
    if ses_val:
        session = ses_val[0].split('-')[-1]
    else:
        session = None

    for i_run, run_seqinfo in enumerate(seqinfo):
        seqname = run_seqinfo.series_description

        if seqname.startswith('anat-scout'):
            print('Skipping "{}"'.format(seqname))
        else:
            key = generate_name(run_seqinfo, session=session)
            info[create_key(key, outtype=outtype)] = [run_seqinfo[2]]
    return info
