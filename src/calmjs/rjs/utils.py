# -*- coding: utf-8 -*-
"""
Helper utilities.
"""

import logging

logger = logging.getLogger(__name__)


def dict_get(d, key):
    value = d[key] = d.get(key, {})
    return value


def dict_key_update_overwrite_check(d, target, mapping):
    keys = set(d[target].keys()) & set(mapping.keys())
    for key in keys:
        if d[target][key] != mapping[key]:
            logger.warning(
                "the value of %s['%s'] is being rewritten from '%s' to '%s'; "
                "configuration may be in an invalid state.",
                target, key, d[target][key], mapping[key],
            )

    # complaints are over, finish the job.
    d[target].update(mapping)
