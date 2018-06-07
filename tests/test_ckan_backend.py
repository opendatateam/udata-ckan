# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json
import pytest

from udata.app import create_app
from udata.core.organization.factories import OrganizationFactory
from udata.harvest import actions
from udata.harvest.tests.factories import HarvestSourceFactory
from udata.models import Dataset
from udata.settings import Defaults, Testing
from udata.tests.plugin import drop_db
from udata.utils import faker


class CkanSettings(Testing):
    PLUGINS = ['ckan']


##############################################################################
#                              Module fixtures                               #
#                                                                            #
# This module behave like a single CKAN harvest run.                         #
# CKAN and udata DB are instanciated once for the whole module to speedup    #
# tests.                                                                     #
##############################################################################

@pytest.fixture(scope='module')
def ckan(ckan_factory):
    '''Instanciate a clean CKAN instance once for this module. '''
    return ckan_factory()


@pytest.fixture(scope='module')
def app(request):
    '''Create an udata app once for the module. '''
    app = create_app(Defaults, override=CkanSettings)
    with app.app_context():
        drop_db(app)
    yield app
    with app.app_context():
        drop_db(app)


@pytest.fixture(scope='module')
def source(app, ckan):
    '''
    Create an harvest source for an organization.
    The source is ctreated once for the module.
    '''
    with app.app_context():
        org = OrganizationFactory()
        return HarvestSourceFactory(backend='ckan',
                                    url=ckan.BASE_URL,
                                    organization=org)


@pytest.fixture(scope='module', autouse=True)
def feed_ckan_and_harvest(request, source, ckan, app):
    '''
    This fixture feed CKAN with data from data fixtures,
    then perform the harvesting and return the data and
    results for this module tests
    '''
    module = request.module
    session = request.session
    items = [item for item in session.items if item.module == module]
    rundata = {}

    fixtures = [i.get_marker('ckan_data').args[0] for i in items]

    for fixture in fixtures:
        data, kwargs = request.getfixturevalue(fixture)
        result = ckan.action('package_create', data)
        rundata[fixture] = data, result, kwargs

    with app.app_context():
        actions.run(source.slug)
        source.reload()
        job = source.get_last_job()
        assert len(job.items) == len(fixtures)

    return rundata


##############################################################################
#                       Method fixtures and helpers                          #
##############################################################################

@pytest.fixture
def data_name(request):
    marker = request.node.get_marker('ckan_data')
    return marker.args[0]


@pytest.fixture
def data(feed_ckan_and_harvest, data_name):
    return feed_ckan_and_harvest[data_name][0]


@pytest.fixture
def result(feed_ckan_and_harvest, data_name):
    return feed_ckan_and_harvest[data_name][1]


@pytest.fixture
def kwargs(feed_ckan_and_harvest, data_name):
    return feed_ckan_and_harvest[data_name][2]


def job_item_for(job, result):
    '''Get the job item for a given result'''
    remote_id = result['result']['id']
    return [i for i in job.items if i.remote_id == remote_id][0]


def dataset_for(result):
    '''Get the dataset associated to a given result'''
    params = {'extras__harvest:remote_id': result['result']['id']}
    return Dataset.objects(**params).first()


##############################################################################
#                                Data Fixtures                               #
# These are functions () -> (dict, Any)                                      #
# The 1st dict is the ckan package_create API payload                        #
# The 2nd argument can ben whatever needs to be given to the test function   #
##############################################################################

@pytest.fixture(scope='module')
def minimal():
    resource_url = faker.unique_url()
    data = {
        'name': faker.unique_string(),
        'title': faker.sentence(),
        'notes': faker.paragraph(),
        'resources': [{'url': resource_url}],
    }
    return data, {'resource_url': resource_url}


@pytest.fixture(scope='module')
def all_metadata():
    resource_data = {
        'name': faker.sentence(),
        'description': faker.paragraph(),
        'url': faker.unique_url(),
        'mimetype': faker.mime_type(),
        'format': faker.file_extension(),
    }
    data = {
        'name': faker.unique_string(),
        'title': faker.sentence(),
        'notes': faker.paragraph(),
        'tags': [{'name': faker.unique_string()} for _ in range(3)],
        'resources': [resource_data],
    }
    return data, {'resource_data': resource_data}


@pytest.fixture(scope='module')
def spatial_geom_polygon():
    polygon = faker.polygon()
    data = {
        'name': faker.unique_string(),
        'title': faker.sentence(),
        'notes': faker.paragraph(),
        'resources': [{'url': faker.unique_url()}],
        'extras': [{'key': 'spatial', 'value': json.dumps(polygon)}]
    }
    return data, {'polygon': polygon}


@pytest.fixture(scope='module')
def spatial_geom_multipolygon():
    multipolygon = faker.multipolygon()
    data = {
        'name': faker.unique_string(),
        'title': faker.sentence(),
        'notes': faker.paragraph(),
        'resources': [{'url': faker.unique_url()}],
        'extras': [{'key': 'spatial', 'value': json.dumps(multipolygon)}]
    }
    return data, {'multipolygon': multipolygon}


@pytest.fixture(scope='module')
def skipped_no_resources():
    return {
        'name': faker.unique_string(),
        'title': faker.sentence(),
        'notes': faker.paragraph(),
        'tags': [{'name': faker.unique_string()} for _ in range(3)],
    }, None


@pytest.fixture(scope='module')
def ckan_url_is_url():
    url = faker.unique_url()
    data = {
        'name': faker.unique_string(),
        'title': faker.sentence(),
        'notes': faker.paragraph(),
        'resources': [{'url': faker.unique_url()}],
        'url': url
    }
    return data, {'url': url}


@pytest.fixture(scope='module')
def ckan_url_is_a_string():
    url = faker.sentence()
    data = {
        'name': faker.unique_string(),
        'title': faker.sentence(),
        'notes': faker.paragraph(),
        'resources': [{'url': faker.unique_url()}],
        'url': url
    }
    return data, {'url': url}


##############################################################################
#                                     Tests                                  #
#                                                                            #
# They are using the `ckan_data` marker to specify the data fixture          #
# they rely on. This allows `data`, `result` and `kwargs` fixtures to be     #
# populated with the associated data harvest data                            #
##############################################################################

@pytest.mark.ckan_data('minimal')
def test_minimal_metadata(data, result, kwargs):
    resource_url = kwargs['resource_url']

    dataset = dataset_for(result)
    assert dataset.title == data['title']
    assert dataset.description == data['notes']
    assert dataset.extras['harvest:remote_id'] == result['result']['id']
    assert dataset.extras['harvest:domain'] == 'localhost'
    assert dataset.extras['ckan:name'] == data['name']
    assert len(dataset.resources) == 1

    resource = dataset.resources[0]
    assert resource.url == resource_url


@pytest.mark.ckan_data('all_metadata')
def test_all_metadata(data, result):
    resource_data = data['resources'][0]

    dataset = dataset_for(result)
    assert dataset.title == data['title']
    assert dataset.description == data['notes']
    assert set(dataset.tags) == set([t['name'] for t in data['tags']])
    assert dataset.extras['harvest:remote_id'] == result['result']['id']
    assert dataset.extras['harvest:domain'] == 'localhost'
    assert dataset.extras['ckan:name'] == data['name']
    assert len(dataset.resources) == 1

    resource = dataset.resources[0]
    assert resource.title == resource_data['name']
    assert resource.description == resource_data['description']
    assert resource.url == resource_data['url']
    assert resource.format == resource_data['format']
    assert resource.mime == resource_data['mimetype']


@pytest.mark.ckan_data('spatial_geom_polygon')
def test_geospatial_geom_polygon(result, kwargs):
    polygon = kwargs['polygon']
    dataset = dataset_for(result)

    assert dataset.spatial.geom == {
        'type': 'MultiPolygon',
        'coordinates': [polygon['coordinates']]
    }


@pytest.mark.ckan_data('spatial_geom_multipolygon')
def test_geospatial_geom_multipolygon(result, kwargs):
    multipolygon = kwargs['multipolygon']

    dataset = dataset_for(result)
    assert dataset.spatial.geom == multipolygon


@pytest.mark.ckan_data('skipped_no_resources')
def test_skip_no_resources(source, result):
    job = source.get_last_job()
    item = job_item_for(job, result)

    assert item.status == 'skipped'
    assert dataset_for(result) is None


@pytest.mark.ckan_data('ckan_url_is_url')
def test_ckan_url_is_url(data, result):
    dataset = dataset_for(result)
    assert dataset.extras['remote_url'] == data['url']
    assert 'ckan:source' not in dataset.extras


@pytest.mark.ckan_data('ckan_url_is_a_string')
def test_ckan_url_is_string(ckan, data, result):
    dataset = dataset_for(result)
    expected_url = '{0}/dataset/{1}'.format(ckan.BASE_URL, data['name'])
    assert dataset.extras['remote_url'] == expected_url
    assert dataset.extras['ckan:source'] == data['url']
