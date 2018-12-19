# -*- coding: utf-8 -*-

import httplib

from furl import furl
import requests

from django.core.exceptions import ValidationError
from framework.exceptions import HTTPError

from osf.models import ExternalAccount
from admin.rdm_addons.utils import get_rdm_addon_option

import owncloud
from addons.owncloud.models import OwnCloudProvider
from addons.owncloud import settings


def add_account(json_request, institution_id, addon_name):
    """
        Verifies new external account credentials and adds to user's list

        This view expects `host`, `username` and `password` fields in the JSON
        body of the request.
    """
    _validate_request(json_request)
    host_url = json_request['host']
    username = json_request['username']
    password = json_request['password']

    # Ensure that ownCloud uses https
    host = furl()
    host.host = host_url.rstrip('/').replace('https://', '').replace('http://', '')
    host.scheme = 'https'

    _check_authentication(host, username, password)
    account = _add_external_account(host, username, password)
    _add_external_account_option(institution_id, addon_name, account)

    return {}, httplib.OK


def _add_external_account(host, username, password):
    provider = OwnCloudProvider(account=None, host=host.url,
                                username=username, password=password)

    try:
        provider.account.save()
    except ValidationError:
        # ... or get the old one
        provider.account = ExternalAccount.objects.get(
            provider=provider.short_name,
            # TODO: Why apply `lower` ?
            # In BasicAuthProviderMixin, do not apply `lower`
            provider_id='{}:{}'.format(host.url, username).lower()
        )
        if provider.account.oauth_key != password:
            provider.account.oauth_key = password
            provider.account.save()

    return provider.account


def _add_external_account_option(institution_id, addon_name, account):
    rdm_addon_option = get_rdm_addon_option(institution_id, addon_name)
    if not rdm_addon_option.external_accounts.filter(id=account.id).exists():
        rdm_addon_option.external_accounts.add(account)


def _check_authentication(host, username, password):
    try:
        oc = owncloud.Client(host.url, verify_certs=settings.USE_SSL)
        oc.login(username, password)
        oc.logout()
    except requests.exceptions.ConnectionError:
        raise HTTPError(httplib.SERVICE_UNAVAILABLE)
    except owncloud.owncloud.HTTPResponseError:
        raise HTTPError(httplib.UNAUTHORIZED)


def _validate_request(json_request):
    if 'host' not in json_request or \
            not isinstance(json_request['host'], basestring) or \
            len(json_request['host']) == 0:
        raise HTTPError(httplib.BAD_REQUEST)
    if 'username' not in json_request or \
            not isinstance(json_request['host'], basestring) or \
            len(json_request['host']) == 0:
        raise HTTPError(httplib.BAD_REQUEST)
    if 'password' not in json_request or \
            not isinstance(json_request['host'], basestring) or \
            len(json_request['host']) == 0:
        raise HTTPError(httplib.BAD_REQUEST)
