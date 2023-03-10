import json
import pytest
import re
import requests
from subprocess import check_output

from urllib.parse import urljoin

from faker.providers import BaseProvider
from udata.utils import faker_provider, faker

RE_API_KEY = re.compile(r'apikey=(?P<apikey>[a-f0-9-]+)\s')
CKAN_URL = 'http://localhost:5000'
CKAN_WAIT_TIMEOUT = 120  # Max time to wait for CKAN being ready (in seconds)


class CkanError(ValueError):
    pass


class CkanClient(object):
    BASE_URL = CKAN_URL

    def __init__(self, apikey):
        self.apikey = apikey

    @property
    def headers(self):
        return {
            'Content-Type': 'application/json',
            'Authorization': self.apikey,
        }

    def get(self, url, **kwargs):
        return requests.get(url, headers=self.headers, **kwargs)

    def post(self, url, data, **kwargs):
        return requests.post(url, data=json.dumps(data), headers=self.headers,
                             **kwargs)

    def action_url(self, endpoint):
        path = '/'.join(['api/3/action', endpoint])
        return urljoin(self.BASE_URL, path)

    def action(self, endpoint, data=None, **kwargs):
        url = self.action_url(endpoint)
        if data:
            response = self.post(url, data, params=kwargs)
        else:
            response = self.get(url, params=kwargs)
        if not 200 <= response.status_code < 300:
            raise CkanError(response.text.strip('"'))
        return response.json()


@pytest.fixture(scope='session')
def wait_for_ckan():
    print('waiting for CKAN')
    while True:
        try:
            requests.get(CKAN_URL, timeout=CKAN_WAIT_TIMEOUT)
            print('CKAN is ready')
            return
        except requests.exceptions.Timeout:
            pass


# TODO: find a solution to replace paster
def docker_exec(cmd):
    return check_output(f'docker exec udata-ckan-ckan-1 ckan {cmd}', shell=True)

@pytest.fixture(scope='session')
def ckan_factory():
    def ckan():
        docker_exec('db clean --yes')
        docker_exec('db init')
        docker_exec('search-index rebuild')
        result = docker_exec('user show default')
        match = RE_API_KEY.search(str(result))
        apikey = match.group('apikey')
        return CkanClient(apikey)
    return ckan


@faker_provider
class UdataCkanProvider(BaseProvider):
    def unique_url(self):
        return '{0}?_={1}'.format(faker.uri(), faker.unique_string())
