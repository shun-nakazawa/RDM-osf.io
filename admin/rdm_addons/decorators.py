import functools
import httplib

from flask import request

from framework.exceptions import HTTPError

from website.util.sanitize import escape_html
from admin.rdm_addons.utils import get_rdm_addon_option
from admin.rdm.utils import get_institution_id


def must_be_rdm_addons_allowed(addon_short_name=None):
    def wrapper(func):
        @functools.wraps(func)
        def wrapped(*args, **kwargs):
            if 'auth' not in kwargs:
                raise HTTPError(httplib.UNAUTHORIZED)

            if addon_short_name is None:
                if 'service_name' not in kwargs:
                    raise HTTPError(httplib.BAD_REQUEST)
                else:
                    _addon_short_name = kwargs['service_name']
            else:
                _addon_short_name = addon_short_name

            auth = kwargs['auth']
            institution_id = get_institution_id(auth.user)

            rdm_addon_option = get_rdm_addon_option(institution_id, _addon_short_name)

            if not rdm_addon_option.is_allowed:
                return {
                   'message': ('Unable to access account.\n'
                               'You are prohibited from using this add-on.')
                }, httplib.FORBIDDEN

            return func(*args, **kwargs)

        return wrapped

    return wrapper


def must_be_rdm_addons_allowed_all(func):
    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        if 'auth' not in kwargs:
            return func(*args, **kwargs)

        auth = kwargs['auth']
        institution_id = get_institution_id(auth.user)

        config = escape_html(request.get_json())

        for addon_name, enabled in config.iteritems():
            rdm_addon_option = get_rdm_addon_option(institution_id, addon_name)

            if not rdm_addon_option.is_allowed:
                return {
                           'message': ('Unable to access account.\n'
                                       'You are prohibited from using this add-on.')
                       }, httplib.FORBIDDEN

        return func(*args, **kwargs)

    return wrapped
