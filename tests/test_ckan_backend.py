from datetime import date
import json
import pytest

from udata.app import create_app
from udata.core.organization.factories import OrganizationFactory
from udata.harvest import actions
from udata.harvest.tests.factories import HarvestSourceFactory
from udata.models import Dataset
from udata.settings import Defaults, Testing
from udata.core.spatial.factories import GeoZoneFactory
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

    fixtures = {
        i.get_closest_marker('ckan_data').args[0]
        for i in items if i.get_closest_marker('ckan_data')
    }

    for fixture in fixtures:
        values = request.getfixturevalue(fixture)
        data, kwargs = values if isinstance(values, tuple) else (values, {})
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
    marker = request.node.get_closest_marker('ckan_data')
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
    return Dataset.objects(harvest__remote_id=result['result']['id']).first()


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
        'last_modified': '2022-09-30',
        'created': '2022-09-29',
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
def known_spatial_text_name(app):
    with app.app_context():
        zone = GeoZoneFactory(validity=None)
    data = {
        'name': faker.unique_string(),
        'title': faker.sentence(),
        'notes': faker.paragraph(),
        'resources': [{'url': faker.unique_url()}],
        'extras': [{'key': 'spatial-text', 'value': zone.name}]
    }
    return data, {'zone': zone}


@pytest.fixture(scope='module')
def known_spatial_text_slug(app):
    with app.app_context():
        zone = GeoZoneFactory(validity=None)
    data = {
        'name': faker.unique_string(),
        'title': faker.sentence(),
        'notes': faker.paragraph(),
        'resources': [{'url': faker.unique_url()}],
        'extras': [{'key': 'spatial-text', 'value': zone.slug}]
    }
    return data, {'zone': zone}


@pytest.fixture(scope='module')
def multiple_known_spatial_text(app):
    name = faker.word()
    with app.app_context():
        GeoZoneFactory.create_batch(2, name=name, validity=None)
    data = {
        'name': faker.unique_string(),
        'title': faker.sentence(),
        'notes': faker.paragraph(),
        'resources': [{'url': faker.unique_url()}],
        'extras': [{'key': 'spatial-text', 'value': name}]
    }
    return data, {'name': name}


@pytest.fixture(scope='module')
def unknown_spatial_text():
    spatial = 'Somewhere'
    data = {
        'name': faker.unique_string(),
        'title': faker.sentence(),
        'notes': faker.paragraph(),
        'resources': [{'url': faker.unique_url()}],
        'extras': [{'key': 'spatial-text', 'value': spatial}]
    }
    return data, {'spatial': spatial}


@pytest.fixture(scope='module')
def spatial_uri():
    spatial = 'http://www.geonames.org/2111964'
    data = {
        'name': faker.unique_string(),
        'title': faker.sentence(),
        'notes': faker.paragraph(),
        'resources': [{'url': faker.unique_url()}],
        'extras': [{'key': 'spatial-uri', 'value': spatial}]
    }
    return data, {'spatial': spatial}


@pytest.fixture(scope='module')
def skipped_no_resources():
    return {
        'name': faker.unique_string(),
        'title': faker.sentence(),
        'notes': faker.paragraph(),
        'tags': [{'name': faker.unique_string()} for _ in range(3)],
    }


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


@pytest.fixture(scope='module')
def frequency_as_rdf_uri():
    data = {
        'name': faker.unique_string(),
        'title': faker.sentence(),
        'notes': faker.paragraph(),
        'resources': [{'url': faker.unique_url()}],
        'extras': [
            {'key': 'frequency', 'value': 'http://purl.org/cld/freq/daily'}
        ]
    }
    return data, {'expected': 'daily'}


@pytest.fixture(scope='module')
def frequency_as_exact_match():
    data = {
        'name': faker.unique_string(),
        'title': faker.sentence(),
        'notes': faker.paragraph(),
        'resources': [{'url': faker.unique_url()}],
        'extras': [{'key': 'frequency', 'value': 'daily'}]
    }
    return data, {'expected': 'daily'}


@pytest.fixture(scope='module')
def frequency_as_unknown_value():
    value = 'unkowwn-value'
    data = {
        'name': faker.unique_string(),
        'title': faker.sentence(),
        'notes': faker.paragraph(),
        'resources': [{'url': faker.unique_url()}],
        'extras': [{'key': 'frequency', 'value': value}]
    }
    return data, {'expected': value}


@pytest.fixture(scope='module')
def empty_extras():
    return {
        'name': faker.unique_string(),
        'title': faker.sentence(),
        'notes': faker.paragraph(),
        'resources': [{'url': faker.unique_url()}],
        'extras': [
            {'key': 'none', 'value': None},
            {'key': 'blank', 'value': ''},
            {'key': 'spaces', 'value': '  '},
        ]

    }


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
    assert dataset.harvest.remote_id == result['result']['id']
    assert dataset.harvest.domain == 'localhost'
    assert dataset.harvest.ckan_name == data['name']
    assert len(dataset.resources) == 1

    resource = dataset.resources[0]
    assert resource.url == resource_url


@pytest.mark.ckan_data('all_metadata')
def test_all_metadata(data, result):
    resource_data = data['resources'][0]
    resource_result = result['result']['resources'][0]

    dataset = dataset_for(result)
    assert dataset.title == data['title']
    assert dataset.description == data['notes']
    assert set(dataset.tags) == set([t['name'] for t in data['tags']])
    assert dataset.harvest.remote_id == result['result']['id']
    assert dataset.harvest.domain == 'localhost'
    assert dataset.harvest.ckan_name == data['name']
    assert len(dataset.resources) == 1

    resource = dataset.resources[0]
    assert resource.title == resource_data['name']
    assert resource.description == resource_data['description']
    assert resource.url == resource_data['url']
    # Use result because format is normalized by CKAN
    assert resource.format == resource_result['format'].lower()
    assert resource.mime == resource_data['mimetype']
    assert resource.harvest.created_at.date() == date(2022, 9, 29)
    assert resource.harvest.modified_at.date() == date(2022, 9, 30)


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
    assert dataset.harvest.remote_url == data['url']
    assert not hasattr(dataset.harvest, 'ckan_source')


@pytest.mark.ckan_data('ckan_url_is_a_string')
def test_ckan_url_is_string(ckan, data, result):
    dataset = dataset_for(result)
    expected_url = '{0}/dataset/{1}'.format(ckan.BASE_URL, data['name'])
    assert dataset.harvest.remote_url == expected_url
    assert dataset.harvest.ckan_source == data['url']


@pytest.mark.ckan_data('frequency_as_rdf_uri')
def test_can_parse_frequency_as_uri(result, kwargs):
    dataset = dataset_for(result)
    assert dataset.frequency == kwargs['expected']
    assert 'ckan:frequency' not in dataset.extras


@pytest.mark.ckan_data('frequency_as_exact_match')
def test_can_parse_frequency_as_exact_match(result, kwargs):
    dataset = dataset_for(result)
    assert dataset.frequency == kwargs['expected']
    assert 'ckan:frequency' not in dataset.extras


@pytest.mark.ckan_data('frequency_as_unknown_value')
def test_can_parse_frequency_as_unkown_value(result, kwargs):
    dataset = dataset_for(result)
    assert dataset.extras['ckan:frequency'] == kwargs['expected']
    assert dataset.frequency is None


@pytest.mark.ckan_data('empty_extras')
def test_skip_empty_extras(result):
    dataset = dataset_for(result)
    assert 'none' not in dataset.extras
    assert 'blank' not in dataset.extras
    assert 'spaces' not in dataset.extras


@pytest.mark.ckan_data('known_spatial_text_name')
def test_known_spatial_text_name(result, kwargs):
    zone = kwargs['zone']
    dataset = dataset_for(result)
    assert zone in dataset.spatial.zones
    assert 'ckan:spatial-text' not in dataset.extras


@pytest.mark.ckan_data('known_spatial_text_slug')
def test_known_spatial_text_slug(result, kwargs):
    zone = kwargs['zone']
    dataset = dataset_for(result)
    assert zone in dataset.spatial.zones
    assert 'ckan:spatial-text' not in dataset.extras


@pytest.mark.ckan_data('multiple_known_spatial_text')
def test_store_unsure_spatial_text_as_extra(result, kwargs):
    dataset = dataset_for(result)
    assert dataset.extras['ckan:spatial-text'] == kwargs['name']
    assert dataset.spatial is None


@pytest.mark.ckan_data('unknown_spatial_text')
def test_keep_unknown_spatial_text_as_extra(result, kwargs):
    dataset = dataset_for(result)
    assert dataset.extras['ckan:spatial-text'] == kwargs['spatial']
    assert dataset.spatial is None


@pytest.mark.ckan_data('spatial_uri')
def test_keep_unknown_spatial_uri_as_extra(result, kwargs):
    dataset = dataset_for(result)
    assert dataset.extras['ckan:spatial-uri'] == kwargs['spatial']
    assert dataset.spatial is None


##############################################################################
#                       Edge cases manually written                          #
##############################################################################
def test_minimal_ckan_response(rmock):
    '''CKAN Harvester should accept the minimum dataset payload'''
    CKAN_URL = 'https://harvest.me/'
    API_URL = '{}api/3/action/'.format(CKAN_URL)
    PACKAGE_LIST_URL = '{}package_list'.format(API_URL)
    PACKAGE_SHOW_URL = '{}package_show'.format(API_URL)

    name = faker.unique_string()
    json = {
        'success': True,
        'result': {
            'id': faker.uuid4(),
            'name': name,
            'title': faker.sentence(),
            'maintainer': faker.name(),
            'tags': [],
            'private': False,
            'maintainer_email': faker.email(),
            'license_id': None,
            'metadata_created': faker.iso8601(),
            'organization': None,
            'metadata_modified': faker.iso8601(),
            'author': None,
            'author_email': None,
            'notes': faker.paragraph(),
            'license_title': None,
            'state': None,
            'type': 'dataset',
            'resources': [],
            # extras and revision_id are not always present so we exclude them
            # from the minimal payload
        }
    }
    source = HarvestSourceFactory(backend='ckan', url=CKAN_URL)
    rmock.get(PACKAGE_LIST_URL, json={'success': True, 'result': [name]}, status_code=200,
              headers={'Content-Type': 'application/json'})
    rmock.get(PACKAGE_SHOW_URL, json=json, status_code=200,
              headers={'Content-Type': 'application/json'})
    actions.run(source.slug)
    source.reload()
    assert source.get_last_job().status == 'done'


def test_flawed_ckan_response(rmock):
    '''CKAN Harvester should report item error with id == remote_id in item'''
    CKAN_URL = 'https://harvest.me/'
    API_URL = '{}api/3/action/'.format(CKAN_URL)
    PACKAGE_LIST_URL = '{}package_list'.format(API_URL)
    PACKAGE_SHOW_URL = '{}package_show'.format(API_URL)

    name = faker.unique_string()
    _id = faker.uuid4()
    # flawed response, missing way too much required attrs
    json = {
        'success': True,
        'result': {
            'id': _id,
            'name': name,
        }
    }
    source = HarvestSourceFactory(backend='ckan', url=CKAN_URL)
    rmock.get(PACKAGE_LIST_URL, json={'success': True, 'result': [name]}, status_code=200,
              headers={'Content-Type': 'application/json'})
    rmock.get(PACKAGE_SHOW_URL, json=json, status_code=200,
              headers={'Content-Type': 'application/json'})
    actions.run(source.slug)
    source.reload()
    assert source.get_last_job().status == 'done-errors'
    assert source.get_last_job().items[0].remote_id == _id
