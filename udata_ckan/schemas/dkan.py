from humanfriendly import parse_size
from voluptuous import (
    Schema, All, Any, Lower, DefaultTo, Optional
)
from udata.harvest.filters import (
    boolean, email, to_date, slug, normalize_string,
    is_url, empty_none, hash
)

from .ckan import RESOURCE_TYPES, tag


def dkan_to_date(value):
    value = value.replace('Date changed  ', '')
    return to_date(value)


def dkan_parse_size(value):
    return parse_size(value)


resource = {
    'id': basestring,
    'name': All(DefaultTo(''), basestring),
    'description': All(basestring, normalize_string),
    'format': All(basestring, Lower),
    'mimetype': Any(All(basestring, Lower), None),
    'size': All(basestring, dkan_parse_size),
    Optional('hash'): Any(All(basestring, hash), None),
    'created': All(basestring, to_date),
    'last_modified': Any(All(basestring, dkan_to_date), None),
    'url': All(basestring, is_url()),
    Optional('resource_type', default='dkan'): All(
        empty_none,
        DefaultTo('file'),
        basestring,
        Any(*RESOURCE_TYPES)
    ),
}

group = {
    'id': basestring,
    'description': basestring,
    'image_display_url': basestring,
    'title': basestring,
    'name': All(basestring, slug),
}

schema = Schema([{
    'id': basestring,
    'name': basestring,
    'title': basestring,
    'notes': Any(All(basestring, normalize_string), None),
    Optional('license_id', default=None): All(DefaultTo('not-specified'), basestring),
    Optional('license_title', default=None): Any(basestring, None),
    Optional('tags', default=list): [tag],
    'metadata_created': All(basestring, to_date),
    'metadata_modified': All(basestring, to_date),
    Optional('groups'): [Any(group, None)],
    'resources': [resource],
    Optional('extras', default=list): [{
        'key': basestring,
        'value': Any(basestring, int, float, boolean, dict, list),
    }],
    'private': boolean,
    'type': 'Dataset',
    Optional('author'): Any(basestring, None),
    Optional('author_email'): All(empty_none, Any(All(basestring, email), None)),
    'maintainer': Any(basestring, None),
    'maintainer_email': All(empty_none, Any(All(basestring, email), None)),
    'state': Any(basestring, None),
}], required=True, extra=True)
