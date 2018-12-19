# -*- coding: utf-8 -*-

import httplib

from django.core.exceptions import ValidationError
from framework.exceptions import HTTPError

from osf.models import ExternalAccount
from admin.rdm_addons.utils import get_rdm_addon_option

from addons.dataverse.models import DataverseProvider
from addons.dataverse import client


def add_account(json_request, institution_id, addon_name):
    _validate_request(json_request)
    host = json_request['host']
    api_token = json_request['api_token']

    _check_authentication(host, api_token)
    account = _add_external_account(host, api_token)
    _add_external_account_option(institution_id, addon_name, account)

    return {}, httplib.OK


def _add_external_account(host, api_token):
    provider = DataverseProvider()

    try:
        provider.account = ExternalAccount(
            provider=provider.short_name,
            provider_name=provider.name,
            display_name=host,
            oauth_key=host,
            oauth_secret=api_token,
            provider_id=api_token,
        )
        provider.account.save()
    except ValidationError:
        # ... or get the old one
        provider.account = ExternalAccount.objects.get(
            provider=provider.short_name,
            provider_id=api_token
        )
        # TODO: Why do not save ?

    return provider.account


def _add_external_account_option(institution_id, addon_name, account):
    rdm_addon_option = get_rdm_addon_option(institution_id, addon_name)
    if not rdm_addon_option.external_accounts.filter(id=account.id).exists():
        rdm_addon_option.external_accounts.add(account)


def _check_authentication(host, api_token):
    client.connect_or_error(host, api_token)


def _validate_request(json_request):
    if 'host' not in json_request or \
            not isinstance(json_request['host'], basestring) or \
            len(json_request['host']) == 0:
        raise HTTPError(httplib.BAD_REQUEST)
    if 'api_token' not in json_request or \
            not isinstance(json_request['api_token'], basestring) or \
            len(json_request['api_token']) == 0:
        raise HTTPError(httplib.BAD_REQUEST)
