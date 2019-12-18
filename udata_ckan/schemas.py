from humanfriendly import parse_size
from voluptuous import (
    Schema, All, Any, Lower, Coerce, DefaultTo, Optional
)
from udata.harvest.filters import (
    boolean, email, to_date, slug, normalize_tag, normalize_string,
    is_url, empty_none, hash
)

RESOURCE_TYPES = ('file', 'file.upload', 'api', 'documentation',
                  'image', 'visualization')


resource = {
    'id': basestring,
    'position': int,
    'name': All(DefaultTo(''), basestring),
    'description': All(basestring, normalize_string),
    'format': All(basestring, Lower),
    'mimetype': Any(All(basestring, Lower), None),
    'size': Any(Coerce(int), None),
    'hash': Any(All(basestring, hash), None),
    'created': All(basestring, to_date),
    'last_modified': Any(All(basestring, to_date), None),
    'url': All(basestring, is_url()),
    'resource_type': All(empty_none,
                         DefaultTo('file'),
                         basestring,
                         Any(*RESOURCE_TYPES)
                         ),
}

tag = {
    'id': basestring,
    Optional('vocabulary_id'): Any(basestring, None),
    Optional('display_name'): basestring,
    'name': All(basestring, normalize_tag),
    Optional('state'): basestring,
}

organization = {
    'id': basestring,
    'description': basestring,
    'created': All(basestring, to_date),
    'title': basestring,
    'name': All(basestring, slug),
    'revision_timestamp': All(basestring, to_date),
    'is_organization': boolean,
    'state': basestring,
    'image_url': basestring,
    'revision_id': basestring,
    'type': 'organization',
    'approval_status': 'approved'
}

schema = Schema({
    'id': basestring,
    'name': basestring,
    'title': basestring,
    'notes': Any(All(basestring, normalize_string), None),
    'license_id': All(DefaultTo('not-specified'), basestring),
    'license_title': Any(basestring, None),
    'tags': [tag],

    'metadata_created': All(basestring, to_date),
    'metadata_modified': All(basestring, to_date),
    'organization': Any(organization, None),
    'resources': [resource],
    'revision_id': basestring,
    Optional('extras', default=list): [{
        'key': basestring,
        'value': Any(basestring, int, float, boolean, dict, list),
    }],
    'private': boolean,
    'type': 'dataset',
    'author': Any(basestring, None),
    'author_email': All(empty_none, Any(All(basestring, email), None)),
    'maintainer': Any(basestring, None),
    'maintainer_email': All(empty_none, Any(All(basestring, email), None)),
    'state': Any(basestring, None),
}, required=True, extra=True)


def dkan_to_date(value):
    value = value.replace('Date changed  ', '')
    return to_date(value)


def dkan_parse_size(value):
    return parse_size(value)


dkan_resource = {
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

dkan_group = {
    'id': basestring,
    'description': basestring,
    'image_display_url': basestring,
    'title': basestring,
    'name': All(basestring, slug),
}

dkan_schema = Schema([{
    'id': basestring,
    'name': basestring,
    'title': basestring,
    'notes': Any(All(basestring, normalize_string), None),
    Optional('license_id', default=None): All(DefaultTo('not-specified'), basestring),
    Optional('license_title', default=None): Any(basestring, None),
    Optional('tags', default=list): [tag],

    'metadata_created': All(basestring, to_date),
    'metadata_modified': All(basestring, to_date),
    Optional('groups'): [Any(dkan_group, None)],
    'resources': [dkan_resource],
    # 'revision_id': basestring,
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
