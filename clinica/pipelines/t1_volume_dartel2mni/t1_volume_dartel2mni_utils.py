# coding: utf8


def prepare_flowfields(flow_fields, tissues):
    return [[f] * (len(tissues) + 1) for f in flow_fields]


def join_smoothed_files(smoothed_normalized_files):
    """Join outputs."""
    return [
        [x for smooth in subject for x in smooth]
        for subject in zip(*smoothed_normalized_files)
    ]

def concatenate_normalized_files(normalized_tissues_files, normalized_t1w_files):
    """Concatenate normalized t1w and tissues outputs"""
    return normalized_tissues_files.extend(normalized_t1w_files)