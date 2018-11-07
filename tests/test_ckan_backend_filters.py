import pytest

from udata.harvest import actions
from udata.harvest.tests.factories import HarvestSourceFactory
from udata.models import Dataset
from udata.utils import faker


pytestmark = [
    pytest.mark.usefixtures('clean_db'),
    pytest.mark.options(PLUGINS=['ckan']),
]


@pytest.fixture
def ckan(ckan_factory):
    '''Instanciate a clean CKAN instance once for this module. '''
    return ckan_factory()


def package_factory(ckan, **kwargs):
    data = {
        'name': faker.unique_string(),
        'title': faker.sentence(),
        'notes': faker.paragraph(),
        'resources': [{'url': faker.unique_url()}],
    }
    data.update(kwargs)
    response = ckan.action('package_create', data)
    return response['result']


def test_include_org_filter(ckan):
    # create 2 organizations with 2 datasets each
    org = ckan.action('organization_create', {'name': 'org-1'})['result']
    included_ids = [d['id'] for d in [
        package_factory(ckan, owner_org=org['id']),
        package_factory(ckan, owner_org=org['id']),
    ]]
    org2 = ckan.action('organization_create', {'name': 'org-2'})['result']
    package_factory(ckan, owner_org=org2['id'])
    package_factory(ckan, owner_org=org2['id'])

    source = HarvestSourceFactory(backend='ckan', url=ckan.BASE_URL, config={
        'filters': [{'key': 'organization', 'value': org['name']}]
    })

    actions.run(source.slug)
    source.reload()

    job = source.get_last_job()
    assert len(job.items) == len(included_ids)

    for dataset in Dataset.objects:
        assert dataset.extras['harvest:remote_id'] in included_ids


def test_exclude_org_filter(ckan):
    # create 2 organizations with 2 datasets each
    org = ckan.action('organization_create', {'name': 'org-1'})['result']
    included_ids = [d['id'] for d in [
        package_factory(ckan, owner_org=org['id']),
        package_factory(ckan, owner_org=org['id']),
    ]]
    org2 = ckan.action('organization_create', {'name': 'org-2'})['result']
    excluded_ids = [d['id'] for d in [
        package_factory(ckan, owner_org=org2['id']),
        package_factory(ckan, owner_org=org2['id']),
    ]]

    source = HarvestSourceFactory(backend='ckan', url=ckan.BASE_URL, config={
        'filters': [{'key': 'organization', 'value': org2['name'], 'type': 'exclude'}]
    })

    actions.run(source.slug)
    source.reload()

    job = source.get_last_job()
    assert len(job.items) == len(included_ids)

    for dataset in Dataset.objects:
        assert dataset.extras['harvest:remote_id'] in included_ids
        assert dataset.extras['harvest:remote_id'] not in excluded_ids


def test_tag_filter(ckan):
    # create 2 datasets with a different tag each
    tag = faker.word()
    package = package_factory(ckan, tags=[{'name': tag}])
    package_factory(ckan, tags=[{'name': faker.word()}])

    source = HarvestSourceFactory(backend='ckan', url=ckan.BASE_URL, config={
        'filters': [{'key': 'tags', 'value': tag}]
    })

    actions.run(source.slug)
    source.reload()

    job = source.get_last_job()
    assert len(job.items) == 1
    assert Dataset.objects.count() == 1
    assert Dataset.objects.first().extras['harvest:remote_id'] == package['id']


def test_exclude_tag_filter(ckan):
    # create 2 datasets with a different tag each
    tag = faker.word()
    package_factory(ckan, tags=[{'name': tag}])
    included = package_factory(ckan, tags=[{'name': faker.word()}])

    source = HarvestSourceFactory(backend='ckan', url=ckan.BASE_URL, config={
        'filters': [{'key': 'tags', 'value': tag, 'type': 'exclude'}]
    })

    actions.run(source.slug)
    source.reload()

    job = source.get_last_job()
    assert len(job.items) == 1
    assert Dataset.objects.count() == 1
    assert Dataset.objects.first().extras['harvest:remote_id'] == included['id']


def test_can_have_multiple_filters(ckan):
    # create 2 organizations with 2 datasets each
    org = ckan.action('organization_create', {'name': 'org-1'})['result']
    package = package_factory(ckan, owner_org=org['id'], tags=[{'name': 'tag-1'}])
    package_factory(ckan, owner_org=org['id'], tags=[{'name': 'tag-2'}])
    org2 = ckan.action('organization_create', {'name': 'org-2'})['result']
    package_factory(ckan, owner_org=org2['id'], tags=[{'name': 'tag-1'}]),
    package_factory(ckan, owner_org=org2['id'], tags=[{'name': 'tag-2'}]),

    source = HarvestSourceFactory(backend='ckan', url=ckan.BASE_URL, config={
        'filters': [
            {'key': 'organization', 'value': org['name']},
            {'key': 'tags', 'value': 'tag-2', 'type': 'exclude'},
        ]
    })

    actions.run(source.slug)
    source.reload()

    job = source.get_last_job()
    assert len(job.items) == 1
    assert Dataset.objects.count() == 1
    assert Dataset.objects.first().extras['harvest:remote_id'] == package['id']
