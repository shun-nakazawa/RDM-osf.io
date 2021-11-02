import json
import uuid
import logging

import jwe
import jwt
import waffle

#from django.utils import timezone
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from api.base.authentication import drf
from api.base import exceptions, settings

from framework import sentry
from framework.auth import get_or_create_user
from framework.auth.core import get_user

from osf import features
from osf.models import Institution, UserExtendedData
from osf.exceptions import BlacklistedEmailError
from website.mails import send_mail, WELCOME_OSF4I
from website.settings import OSF_SUPPORT_EMAIL, DOMAIN, to_bool
from website.util.quota import update_default_storage

logger = logging.getLogger(__name__)


NEW_USER_NO_NAME = 'New User (no name)'

def send_welcome(user, request):
    send_mail(
        to_addr=user.username,
        mail=WELCOME_OSF4I,
        mimetype='html',
        user=user,
        domain=DOMAIN,
        osf_support_email=OSF_SUPPORT_EMAIL,
        storage_flag_is_active=waffle.flag_is_active(
            request,
            features.STORAGE_I18N,
        ),
        use_viewonlylinks=to_bool('USE_VIEWONLYLINKS', True),
    )


# This map defines how to find the secondary institution IdP which uses the shared SSO of a primary
# IdP. Each map entry has the following format.
#
#    '<ID of the primary institution A>': {
#        'criteria': 'attribute',
#        'attribute': '<the attribute name for identifying secondary institutions>',
#        'institutions': {
#            '<attribute value for identifying institution A1>': '<ID of secondary institution A1>',
#            '<attribute value for identifying institution A2>': '<ID of secondary institution A2>',
#            ...
#        },
#        ...
#    }
#
# Currently, the only active criteria is "attribute", which the primary institution IdP releases to
# OSF for us to identify the secondary institution. Another option is "emailDomain". For example:
#
#    '<ID of the primary institution B>': {
#        'criteria': 'emailDomain',
#        'institutions': {
#            '<the email domain for identifying institution B1>': '<ID of secondary institution B1',
#            '<the email domain for identifying institution B2>': '<ID of secondary institution B2',
#            ...
#        }
#        ...
#    }
#
INSTITUTION_SHARED_SSO_MAP = {
    'brown': {
        'criteria': 'attribute',
        'attribute': 'isMemberOf',
        'institutions': {
            'thepolicylab': 'thepolicylab',
        },
    },
}



class InstitutionAuthentication(BaseAuthentication):
    """A dedicated authentication class for view ``InstitutionAuth``.

    The ``InstitutionAuth`` view and the ``InstitutionAuthentication`` class are only and should
    only be used by OSF CAS for institution login. Changing this class and related tests may break
    the institution login feature. Please check with @longzeC / @mattF / @brianG before making any
    changes.
    """

    media_type = 'text/plain'

    def authenticate(self, request):
        """
        Handle CAS institution authentication request.

        The JWT `data` payload is expected in the following structure:
        {
            "provider": {
                "idp":  "",
                "id":   "",
                "user": {
                    "username":     "",  # email or eppn
                    "fullname":     "",  # displayName
                    "familyName":   "",
                    "givenName":    "",
                    "middleNames":  "",
                    "suffix":       "",
                    "groups":       "",  # isMemberOf for mAP API v1
                    "eptid":        "",  # persistent-id for mAP API v1
                    "entitlement":  "",  # eduPersonEntitlement
                    "email":        "",  # mail
                    "organizationName": "",    # o
                    "organizationalUnit": "",  # ou
                }
            }
        }

        :param request: the POST request
        :return: user, None if authentication succeed
        :raises: AuthenticationFailed if authentication fails
        """

        # Verify / decrypt / decode the payload
        try:
            payload = jwt.decode(
                jwe.decrypt(request.body, settings.JWE_SECRET),
                settings.JWT_SECRET,
                options={'verify_exp': False},
                algorithm='HS256',
            )
        except (jwt.InvalidTokenError, TypeError, jwe.exceptions.MalformedData):
            raise AuthenticationFailed

        # Load institution and user data
        data = json.loads(payload['data'])
        provider = data['provider']
        institution = Institution.load(provider['id'])
        if not institution:
            message = 'Institution SSO Error: invalid institution ID [{}]'.format(provider['id'])
            logger.error(message)
            sentry.log_message(message)
            raise AuthenticationFailed(message)

        USE_EPPN = login_by_eppn()

        logger.info('---InstitutionAuthentication.authenticate.user:{}'.format(provider))

        username = provider['user'].get('username')
        fullname = provider['user'].get('fullname')
        given_name = provider['user'].get('givenName')
        family_name = provider['user'].get('familyName')
        middle_names = provider['user'].get('middleNames')
        suffix = provider['user'].get('suffix')
        department = provider['user'].get('department')
        entitlement = provider['user'].get('entitlement')
        email = provider['user'].get('email')
        organization_name = provider['user'].get('organizationName')
        organizational_unit = provider['user'].get('organizationalUnit')

        # Check secondary institutions which uses the SSO of primary ones
        secondary_institution = None
        if provider['id'] in INSTITUTION_SHARED_SSO_MAP:
            switch_map = INSTITUTION_SHARED_SSO_MAP[provider['id']]
            criteria_type = switch_map.get('criteria')
            if criteria_type == 'attribute':
                attribute_name = switch_map.get('attribute')
                attribute_value = provider['user'].get(attribute_name)
                if attribute_value:
                    secondary_institution_id = switch_map.get(
                        'institutions',
                        {},
                    ).get(attribute_value)
                    logger.info('Institution SSO: primary=[{}], secondary=[{}], '
                                'username=[{}]'.format(provider['id'], secondary_institution_id, username))
                    secondary_institution = Institution.load(secondary_institution_id)
                    if not secondary_institution:
                        # Log errors and inform Sentry but do not raise an exception if OSF fails
                        # to load the secondary institution from database
                        message = 'Institution SSO Error: invalid secondary institution [{}]; ' \
                                  'primary=[{}], username=[{}]'.format(attribute_value, provider['id'], username)
                        logger.error(message)
                        sentry.log_message(message)
                else:
                    # SSO from primary institution only
                    logger.info('Institution SSO: primary=[{}], secondary=[None], '
                                'username=[{}]'.format(provider['id'], username))
            else:
                message = 'Institution SSO Error: invalid criteria [{}]; ' \
                          'primary=[{}], username=[{}]'.format(criteria_type, provider['id'], username)
                logger.error(message)
                sentry.log_message(message)

        # Use given name and family name to build full name if it is not provided
        if given_name and family_name and not fullname:
            fullname = given_name + ' ' + family_name

        if USE_EPPN and not fullname:
            fullname = NEW_USER_NO_NAME

        # Non-empty full name is required. Fail the auth and inform sentry if not provided.
        if not fullname:
            message = 'Institution SSO Error: missing fullname ' \
                      'for user [{}] from institution [{}]'.format(username, provider['id'])
            logger.error(message)
            sentry.log_message(message)
            raise AuthenticationFailed(message)

        user = None
        created = False
        eppn = None

        if USE_EPPN:
            eppn = username
            if not eppn:
                message = 'Institution login failed: eppn required'
                sentry.log_message(message)
                raise AuthenticationFailed(message)

            # use user.eppn as primary-key in GakuNin RDM
            user = get_user(eppn=eppn, log=False)
            if user:
                created = False
            else:  # new user
                if email:
                    existing_user = get_user(email=email, log=False)
                    if existing_user and \
                       existing_user.eppn != eppn:  # suppose race-condition
                        email = None  # require other email address
                tmp_eppn = ('tmp_eppn_' + eppn).lower()
                if email:
                    username_tmp = email
                else:
                    username_tmp = tmp_eppn
                try:
                    # try to use email or tmp_eppn
                    user, created = get_or_create_user(
                        fullname, username_tmp,
                        reset_password=False,
                    )
                except BlacklistedEmailError:
                    if username_tmp == tmp_eppn:  # unexpected
                        raise
                    # email is Black Listed Email
                    email = None
                    # try to use tmp_eppn only
                    user, created = get_or_create_user(
                        fullname, tmp_eppn,
                        reset_password=False,
                    )
        else:
            user, created = get_or_create_user(fullname, username, reset_password=False)
        # Get an existing user or create a new one. If a new user is created, the user object is
        # confirmed but not registered,which is temporarily of an inactive status. If an existing
        # user is found, it is also possible that the user is inactive (e.g. unclaimed, disabled,
        # unconfirmed, etc.).

        # Existing but inactive users need to be either "activated" or failed the auth
        activation_required = False
        new_password_required = False
        if not created:
            try:
                drf.check_user(user)
                logger.info('Institution SSO: active user [{}]'.format(username))
            except exceptions.UnclaimedAccountError:
                # Unclaimed user (i.e. a user that has been added as an unregistered contributor)
                user.unclaimed_records = {}
                activation_required = True
                # Unclaimed users have an unusable password when being added as an unregistered
                # contributor. Thus a random usable password must be assigned during activation.
                new_password_required = True
                logger.warning('Institution SSO: unclaimed contributor [{}]'.format(username))
            except exceptions.UnconfirmedAccountError:
                if user.has_usable_password():
                    # Unconfirmed user from default username / password signup
                    user.email_verifications = {}
                    activation_required = True
                    # Unconfirmed users already have a usable password set by the creator during
                    # sign-up. However, it must be overwritten by a new random one so the creator
                    # (if he is not the real person) can not access the account after activation.
                    new_password_required = True
                    logger.warning('Institution SSO: unconfirmed user [{}]'.format(username))
                else:
                    # Login take-over has not been implemented for unconfirmed user created via
                    # external IdP login (ORCiD).
                    message = 'Institution SSO Error: SSO is not eligible for an unconfirmed account [{}] ' \
                              'created via IdP login'.format(username)
                    sentry.log_message(message)
                    logger.error(message)
                    return None, None
            except exceptions.DeactivatedAccountError:
                # Deactivated user: login is not allowed for deactivated users
                message = 'Institution SSO Error: SSO is not eligible for a deactivated account: [{}]'.format(username)
                sentry.log_message(message)
                logger.error(message)
                return None, None
            except exceptions.MergedAccountError:
                # Merged user: this shouldn't happen since merged users do not have an email
                message = 'Institution SSO Error: SSO is not eligible for a merged account: [{}]'.format(username)
                sentry.log_message(message)
                logger.error(message)
                return None, None
            except exceptions.InvalidAccountError:
                # Other invalid status: this shouldn't happen unless the user happens to be in a
                # temporary state. Such state requires more updates before the user can be saved
                # to the database. (e.g. `get_or_create_user()` creates a temporary-state user.)
                message = 'Institution SSO Error: SSO is not eligible for an inactive account [{}] ' \
                          'with an unknown or invalid status'.format(username)
                sentry.log_message(message)
                logger.error(message)
                return None, None
        else:
            logger.info('Institution SSO: new user [{}]'.format(username))

        # The `department` field is updated each login when it was changed.
        user_guid = user.guids.first()._id
        if department:
            if user.department != department:
                user.department = department
                user.save()
            logger.info('Institution SSO: user w/ dept: user=[{}], email=[{}], inst=[{}], '
                        'dept=[{}]'.format(user_guid, username, institution._id, department))
        else:
            logger.info('Institution SSO: user w/o dept: user=[{}], email=[{}], '
                        'inst=[{}]'.format(user_guid, username, institution._id))

        # Both created and activated accounts need to be updated and registered
        if created or activation_required:

            if given_name:
                user.given_name = given_name
            if family_name:
                user.family_name = family_name
            if middle_names:
                user.middle_names = middle_names
            if suffix:
                user.suffix = suffix

            # Users claimed or confirmed via institution SSO should have their full name updated
            if activation_required:
                user.fullname = fullname

            user.update_date_last_login()

            ## Relying on front-end validation until `accepted_tos` is added to the JWT payload
            #user.accepted_terms_of_service = timezone.now()
            if settings.USER_TIMEZONE:
                user.timezone = settings.USER_TIMEZONE

            if settings.USER_LOCALE:
                user.locale = settings.USER_LOCALE

            if entitlement:
                if 'GakuninRDMAdmin' in entitlement:
                    user.is_staff = True

            if USE_EPPN:
                user.eppn = eppn
                if email:
                    username = email
                    user.have_email = True
                else:
                    username = user.username
                    user.have_email = False
                    #user.unclaimed_records = {}
                if organization_name:
                    # Settings > Profile information > Employment > ...
                    #   organization_name (o) : Institution / Employer
                    #   organizational_unit (ou) : Department / Institute
                    job = {
                        'title': '',
                        'institution': organization_name,  # required
                        'department': '',
                        'location': '',
                        'startMonth': '',
                        'startYear': '',
                        'endMonth': '',
                        'endYear': '',
                        'ongoing': False,
                    }
                    if organizational_unit:
                        job['department'] = organizational_unit
                    user.jobs.append(job)
            else:
                user.eppn = None
                user.have_email = True
                ### username is email address

            # Register and save user
            password = str(uuid.uuid4()) if new_password_required else None
            user.register(username, password=password)
            user.save()

            # send confirmation email
            if user.have_email:
                send_welcome(user, request)
            ### the user is not available when have_email is False.

        ext, created = UserExtendedData.objects.get_or_create(user=user)
        # update every login.
        ext.set_idp_attr(
            {
                'eppn': eppn,
                'username': username,
                'fullname': fullname,
                'entitlement': entitlement,
                'email': email,
                'organization_name': organization_name,
                'organizational_unit': organizational_unit,
            },
        )

        # update every login.
        if USE_EPPN:
            for other in user.affiliated_institutions.exclude(id=institution.id):
                user.affiliated_institutions.remove(other)

        # Affiliate the user to the primary institution if not previously affiliated
        if not user.is_affiliated_with_institution(institution):
            user.affiliated_institutions.add(institution)
            user.save()
            update_default_storage(user)

        # update every login. (for mAP API v1)
        init_cloud_gateway_groups(user, provider)

        # Affiliate the user to the secondary institution if not previously affiliated
        if secondary_institution and not user.is_affiliated_with_institution(secondary_institution):
            user.affiliated_institutions.add(secondary_institution)
            user.save()

        return user, None

def login_by_eppn():
    return settings.LOGIN_BY_EPPN

def init_cloud_gateway_groups(user, provider):
    if not hasattr(settings, 'CLOUD_GATEWAY_ISMEMBEROF_PREFIX'):
        return
    prefix = settings.CLOUD_GATEWAY_ISMEMBEROF_PREFIX
    if not prefix:
        return

    eptid = provider['user'].get('eptid')
    if not eptid:
        return  # Cloud Gateway may not be alive.

    # set ePTID (eduPersonTargetedID, persistent-id)
    user.eptid = eptid

    debug = False
    #debug = True

    if debug:
        groups_str = ''
        if user.eppn == 'test002@nii.ac.jp':
            groups_str = 'https://sptest.cg.gakunin.jp/gr/group1;https://sptest.cg.gakunin.jp/gr/group1/admin;https://sptest.cg.gakunin.jp/gr/group2;https://sptest.cg.gakunin.jp/gr/group2/admin;https://sptest.cg.gakunin.jp/gr/group3'
        elif user.eppn == 'test003@nii.ac.jp':
            groups_str = 'https://sptest.cg.gakunin.jp/gr/group1;https://sptest.cg.gakunin.jp/gr/group1/admin;https://sptest.cg.gakunin.jp/gr/group2'
    else:
        groups_str = provider['user'].get('groups')
        if groups_str is None:
            groups_str = ''

    # clear groups
    user.cggroups.clear()
    user.cggroups_admin.clear()
    user.cggroups_sync.clear()
    user.cggroups_initialized = False  # for framework/auth/decorators.py

    # set groups
    import re
    patt_prefix = re.compile('^' + prefix)
    patt_admin = re.compile('(.+)/admin$')
    for group in groups_str.split(';'):
        if patt_prefix.match(group):
            groupname = patt_prefix.sub('', group)
            if groupname is None or groupname == '':
                continue
            m = patt_admin.search(groupname)
            if m:  # is admin
                user.add_group_admin(m.group(1))
            else:
                user.add_group(groupname)
    user.save()
