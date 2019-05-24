# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json
import logging

from datetime import datetime
from uuid import UUID
from urlparse import urljoin

from voluptuous import (
    Schema, All, Any, Lower, Coerce, DefaultTo, Optional
)

from udata import uris
from udata.i18n import lazy_gettext as _
from udata.core.dataset.rdf import frequency_from_rdf
from udata.models import (
    db, Resource, License, SpatialCoverage, GeoZone,
    UPDATE_FREQUENCIES,
)
from udata.utils import get_by, daterange_start, daterange_end

from udata.harvest.backends.base import BaseBackend, HarvestFilter
from udata.harvest.exceptions import HarvestException, HarvestSkipException
from udata.harvest.filters import (
    boolean, email, to_date, slug, normalize_tag, normalize_string,
    is_url, empty_none, hash
)

log = logging.getLogger(__name__)

RESOURCE_TYPES = ('file', 'file.upload', 'api', 'documentation',
                  'image', 'visualization')

ALLOWED_RESOURCE_TYPES = ('file', 'file.upload', 'api', 'metadata')

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
    'vocabulary_id': Any(basestring, None),
    'display_name': basestring,
    'name': All(basestring, normalize_tag),
    'state': basestring,
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


class CkanBackend(BaseBackend):
    display_name = 'CKAN'
    filters = (
        HarvestFilter(_('Organization'), 'organization', str,
                      _('A CKAN Organization name')),
        HarvestFilter(_('Tag'), 'tags', str, _('A CKAN tag name')),
    )

    def get_headers(self):
        headers = super(CkanBackend, self).get_headers()
        headers['content-type'] = 'application/json'
        if self.config.get('apikey'):
            headers['Authorization'] = self.config['apikey']
        return headers

    def action_url(self, endpoint):
        path = '/'.join(['api/3/action', endpoint])
        return urljoin(self.source.url, path)

    def dataset_url(self, name):
        path = '/'.join(['dataset', name])
        return urljoin(self.source.url, path)

    def get_action(self, endpoint, fix=False, **kwargs):
        url = self.action_url(endpoint)
        if fix:
            response = self.post(url, '{}', params=kwargs)
        else:
            response = self.get(url, params=kwargs)

        content_type = response.headers.get('Content-Type', '')
        mime_type = content_type.split(';', 1)[0]

        if mime_type == 'application/json':  # Standard API JSON response
            data = response.json()
            # CKAN API always returns 200 even on errors
            # Only the `success` property allows to detect errors
            if data.get('success', False):
                return data
            else:
                error = data.get('error')
                if isinstance(error, dict):
                    # Error object with message
                    msg = error.get('message', 'Unknown error')
                    if '__type' in error:
                        # Typed error
                        msg = ': '.join((error['__type'], msg))
                else:
                    # Error only contains a message
                    msg = error
                raise HarvestException(msg)

        elif mime_type == 'text/html':  # Standard html error page
            raise HarvestException('Unknown Error: {} returned HTML'.format(url))
        else:
            # If it's not HTML, CKAN respond with raw quoted text
            msg = response.text.strip('"')
            raise HarvestException(msg)

    def get_status(self):
        url = urljoin(self.source.url, '/api/util/status')
        response = self.get(url)
        return response.json()

    def initialize(self):
        '''List all datasets for a given ...'''
        fix = False  # Fix should be True for CKAN < '1.8'

        filters = self.config.get('filters', [])
        if len(filters) > 0:
            # Build a q search query based on filters
            # use package_search because package_list doesn't allow filtering
            # use q parameters because fq is broken with multiple filters
            params = []
            for f in filters:
                param = '{key}:{value}'.format(**f)
                if f.get('type') == 'exclude':
                    param = '-' + param
                params.append(param)
            q = ' AND '.join(params)
            # max out rows count to 1000 as per
            # https://docs.ckan.org/en/latest/api/#ckan.logic.action.get.package_search
            response = self.get_action('package_search', fix=fix, q=q, rows=1000)
            names = [r['name'] for r in response['result']['results']]
        else:
            response = self.get_action('package_list', fix=fix)
            names = response['result']
        if self.max_items:
            names = names[:self.max_items]
        for name in names:
            self.add_item(name)

    def process(self, item):
        response = self.get_action('package_show', id=item.remote_id)
        data = self.validate(response['result'], schema)

        # Fix the remote_id: use real ID instead of not stable name
        item.remote_id = data['id']

        # Skip if no resource
        if not len(data.get('resources', [])):
            msg = 'Dataset {0} has no record'.format(item.remote_id)
            raise HarvestSkipException(msg)

        dataset = self.get_dataset(item.remote_id)

        # Core attributes
        if not dataset.slug:
            dataset.slug = data['name']
        dataset.title = data['title']
        dataset.description = data['notes']

        # Detect license
        default_license = dataset.license or License.default()
        dataset.license = License.guess(data['license_id'],
                                        data['license_title'],
                                        default=default_license)

        dataset.tags = [t['name'] for t in data['tags'] if t['name']]

        dataset.created_at = data['metadata_created']
        dataset.last_modified = data['metadata_modified']

        dataset.extras['ckan:name'] = data['name']

        temporal_start, temporal_end = None, None
        spatial_geom, spatial_zone = None, None

        for extra in data['extras']:
            key = extra['key']
            value = extra['value']
            if value is None or (
                isinstance(value, basestring) and not value.strip()
            ):
                # Skip empty extras
                continue
            elif key == 'spatial':
                # GeoJSON representation (Polygon or Point)
                spatial_geom = json.loads(value)
            elif key == 'spatial-text':
                # Textual representation of the extent / location
                qs = GeoZone.objects(db.Q(name=value) | db.Q(slug=value))
                qs = qs.valid_at(datetime.now())
                if qs.count() == 1:
                    spatial_zone = qs.first()
                else:
                    dataset.extras['ckan:spatial-text'] = value
                    log.debug('spatial-text value not handled: %s', value)
            elif key == 'spatial-uri':
                # Linked Data URI representing the place name
                dataset.extras['ckan:spatial-uri'] = value
                log.debug('spatial-uri value not handled: %s', value)
            elif key == 'frequency':
                # Update frequency
                freq = frequency_from_rdf(value)
                if freq:
                    dataset.frequency = freq
                elif value in UPDATE_FREQUENCIES:
                    dataset.frequency = value
                else:
                    dataset.extras['ckan:frequency'] = value
                    log.debug('frequency value not handled: %s', value)
            # Temporal coverage start
            elif key == 'temporal_start':
                temporal_start = daterange_start(value)
            # Temporal coverage end
            elif key == 'temporal_end':
                temporal_end = daterange_end(value)
            else:
                dataset.extras[extra['key']] = value

        if spatial_geom or spatial_zone:
            dataset.spatial = SpatialCoverage()

        if spatial_zone:
            dataset.spatial.zones = [spatial_zone]

        if spatial_geom:
            if spatial_geom['type'] == 'Polygon':
                coordinates = [spatial_geom['coordinates']]
            elif spatial_geom['type'] == 'MultiPolygon':
                coordinates = spatial_geom['coordinates']
            else:
                raise HarvestException('Unsupported spatial geometry')
            dataset.spatial.geom = {
                'type': 'MultiPolygon',
                'coordinates': coordinates
            }

        if temporal_start and temporal_end:
            dataset.temporal_coverage = db.DateRange(
                start=temporal_start,
                end=temporal_end,
            )

        # Remote URL
        if data.get('url'):
            try:
                url = uris.validate(data['url'])
            except uris.ValidationError:
                dataset.extras['remote_url'] = self.dataset_url(data['name'])
                dataset.extras['ckan:source'] = data['url']
            else:
                dataset.extras['remote_url'] = url

        # Resources
        for res in data['resources']:
            if res['resource_type'] not in ALLOWED_RESOURCE_TYPES:
                continue
            try:
                resource = get_by(dataset.resources, 'id', UUID(res['id']))
            except Exception:
                log.error('Unable to parse resource ID %s', res['id'])
                continue
            if not resource:
                resource = Resource(id=res['id'])
                dataset.resources.append(resource)
            resource.title = res.get('name', '') or ''
            resource.description = res.get('description')
            resource.url = res['url']
            resource.filetype = 'remote'
            resource.format = res.get('format')
            resource.mime = res.get('mimetype')
            resource.hash = res.get('hash')
            resource.created = res['created']
            resource.modified = res['last_modified']
            resource.published = resource.published or resource.created

        return dataset
