# coding: utf-8

from json import loads
from requests import Session
from requests.exceptions import ReadTimeout, ConnectionError

from corecli.api.app import AppMixin
from corecli.api.pod import PodMixin
from corecli.api.container import ContainerMixin
from corecli.api.network import NetworkMixin
from corecli.api.action import ActionMixin
from corecli.api.mimiron import MimironMixin


class CoreAPIError(Exception):

    def __init__(self, code, message):
        self.code = code
        self.message = message


class CoreAPI(AppMixin, PodMixin, ContainerMixin, NetworkMixin, ActionMixin, MimironMixin):

    def __init__(self, host, version='v1', timeout=None, username='', password='', auth_token=''):
        self.host = host
        self.version = version
        self.timeout = timeout
        # 在CoreAPI初始化之前，去SSO取了username回来
        self.username = username
        self.password = password #待会看看没有用到就吧这个删掉吧
        self.auth_token = auth_token

        self.base = '%s/api/%s' % (self.host, version)
        self.session = Session()
        self.session.headers.update({'X-Neptulon-Token': auth_token})

    def _do(self, path, method='GET', params=None, data=None, json=None, expected_code=200):
        """非stream返回"""
        if params is None:
            params = {}
        if data is None:
            data = {}
        params.setdefault('start', 0)
        params.setdefault('limit', 100)
        url = self.base + path

        try:
            resp = self.session.request(method=method, url=url, data=data, json=json, timeout=self.timeout)
            rv = resp.json()

            if resp.status_code != expected_code:
                raise CoreAPIError(resp.status_code, rv.get('error', 'Unknown error'))
            return rv
        except ReadTimeout:
            raise CoreAPIError(0, 'Read timeout')
        except ConnectionError:
            raise CoreAPIError(0, 'ConnectionError, is citadel correctly set?')

    def _do_stream(self, path, method='GET', params=None, data=None, json=None, expected_code=200):
        """stream的返回, 外部只需要iter这个返回值就行."""
        if params is None:
            params = {}
        if data is None:
            data = {}
        params.setdefault('start', 0)
        params.setdefault('limit', 100)
        url = self.base + path

        try:
            resp = self.session.request(method=method, url=url, data=data, json=json, timeout=self.timeout, stream=True)
            if resp.status_code != expected_code:
                rv = resp.json()
                raise CoreAPIError(resp.status_code, rv.get('error', 'Unknown error'))

            for line in resp.iter_lines():
                try:
                    yield loads(line)
                except ValueError as e:
                    raise CoreAPIError(0, 'Error when unmarshal JSON, error: %s, line: %s' % (e.message, line))
        except ReadTimeout:
            raise CoreAPIError(0, 'Read timeout')
        except ConnectionError:
            raise CoreAPIError(0, 'ConnectionError, is citadel correctly set?')
