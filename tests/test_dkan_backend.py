# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import pytest

from udata.app import create_app
from udata.core.organization.factories import OrganizationFactory
from udata.harvest import actions
from udata.harvest.tests.factories import HarvestSourceFactory
from udata.models import Dataset
from udata.settings import Defaults, Testing
from udata.tests.plugin import drop_db


DKAN_TEST_INSTANCE = 'http://demo.getdkan.com'


class DkanSettings(Testing):
    PLUGINS = ['dkan']


@pytest.fixture(scope='module')
def app(request):
    '''Create an udata app once for the module. '''
    app = create_app(Defaults, override=DkanSettings)
    with app.app_context():
        drop_db(app)
    yield app
    with app.app_context():
        drop_db(app)


@pytest.fixture(scope='module')
def source(app):
    '''
    Create an harvest source for an organization.
    The source is created once for the module.
    '''
    with app.app_context():
        org = OrganizationFactory()
        return HarvestSourceFactory(backend='dkan',
                                    url=DKAN_TEST_INSTANCE,
                                    organization=org)


def test_dkan_demo_harvest(source, app):
    '''
    Harvest DKAN_TEST_INSTANCE and check some datasets are created
    '''
    with app.app_context():
        actions.run(source.slug)
        source.reload()
        job = source.get_last_job()

    assert len(job.items) > 0
    datasets = Dataset.objects.filter(organization=source.organization)
    assert len(job.items) == datasets.count()

    for dataset in datasets:
        assert len(dataset.resources) > 0
