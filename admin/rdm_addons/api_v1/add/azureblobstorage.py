# -*- coding: utf-8 -*-

import httplib

from django.core.exceptions import ValidationError
from framework.exceptions import HTTPError

from osf.models import ExternalAccount
from admin.rdm_addons.utils import get_rdm_addon_option

from addons.azureblobstorage.models import AzureBlobStorageProvider
from addons.azureblobstorage.utils import get_user_info, can_list


def add_account(json_request, institution_id, addon_name):
    _validate_request(json_request)
    access_key = json_request['access_key']
    secret_key = json_request['secret_key']

    _check_authentication(access_key, secret_key)
    account = _add_external_account(access_key, secret_key)
    _add_external_account_option(institution_id, addon_name, account)

    return {}, httplib.OK


def _add_external_account(access_key, secret_key):
    user_info = get_user_info(access_key, secret_key)
    provider = AzureBlobStorageProvider(account=None)

    try:
        account = ExternalAccount(
            provider=provider.short_name,
            provider_name=provider.name,
            oauth_key=access_key,
            oauth_secret=secret_key,
            provider_id=user_info['id'],
            display_name=user_info['display_name'],
        )
        account.save()
    except ValidationError:
        # ... or get the old one
        account = ExternalAccount.objects.get(
            provider=provider.short_name,
            provider_id=user_info['id']
        )
        if account.oauth_key != access_key or account.oauth_secret != secret_key:
            account.oauth_key = access_key
            account.oauth_secret = secret_key
            account.save()

    return account


def _add_external_account_option(institution_id, addon_name, account):
    rdm_addon_option = get_rdm_addon_option(institution_id, addon_name)
    if not rdm_addon_option.external_accounts.filter(id=account.id).exists():
        rdm_addon_option.external_accounts.add(account)


def _check_authentication(access_key, secret_key):
    if not get_user_info(access_key, secret_key):
        message = 'Unable to access account.\n'
        'Check to make sure that the above credentials are valid, '
        'and that they have permission to list buckets.'
        raise HTTPError(httplib.BAD_REQUEST, message)
    if not can_list(access_key, secret_key):
        message = 'Unable to list buckets.\n'' \
        ''Listing buckets is required permission that can be changed via IAM'
        raise HTTPError(httplib.BAD_REQUEST, message)


def _validate_request(json_request):
    if 'access_key' not in json_request or \
            not isinstance(json_request['access_key'], basestring) or \
            len(json_request['access_key']) == 0:
        raise HTTPError(httplib.BAD_REQUEST)
    if 'secret_key' not in json_request or \
            not isinstance(json_request['secret_key'], basestring) or \
            len(json_request['secret_key']) == 0:
        raise HTTPError(httplib.BAD_REQUEST)
