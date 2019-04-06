# -*- coding: utf-8 -*-
#
# MAPCore class: mAP Core API handling
#
# @COPYRIGHT@
#

import os
import sys
import json
import time
import datetime
import json
import re
import logging
import hashlib
import requests
import urllib

from datetime import datetime as dt
from website import settings

#
# Global settings.
#
logger = logging.getLogger(__name__)
logger.setLevel(10)
stdout = logging.StreamHandler()
logger.addHandler(stdout)

map_hostname      = settings.MAPCORE_HOSTNAME
map_authcode_path = settings.MAPCORE_AUTHCODE_PATH
map_token_path    = settings.MAPCORE_TOKEN_PATH
map_refresh_path  = settings.MAPCORE_REFRESH_PATH
map_api_path      = settings.MAPCORE_API_PATH
map_clientid      = settings.MAPCORE_CLIENTID
map_secret        = settings.MAPCORE_SECRET
map_redirect      = settings.MAPCORE_REDIRECT
map_authcode_magic = settings.MAPCORE_AUTHCODE_MAGIC

class MAPCore:

    MODE_MEMBER = 0     # Ordinary member
    MODE_ADMIN = 2      # Administrator member

    user = False
    client_id = False
    client_secret = False

    #
    # Constructor.
    #
    def __init__(self, user):
        self.user = user
        self.client_id = settings.MAPCORE_CLIENTID
        self.client_secret = settings.MAPCORE_SECRET

    #
    # Refresh access token.
    #
    def refresh_token(self):

        logger.debug("MAPCore::refresh_token:")

        url = map_hostname + map_refresh_path
        basic_auth = ( self.client_id, self.client_secret )
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8'
        }
        params = {
            "grant_type": "refresh_token",
            "refresh_token": self.user.map_profile.oauth_refresh_token
        }
        params = urllib.urlencode(params)
        logger.debug("  params=" + params)

        r = requests.post(url, auth = basic_auth, headers = headers, data = params)
        if r.status_code != requests.codes.ok:
            logger.info("MAPCore::refresh_token: Refreshing token failed: status_code=" + str(r.status_code))

        j = r.json();
        if "error" in j:
            logger.info("MAPCore::refresh_token: Refreshing token failed: " + j["error"])
            if "error_description" in j:
                logger.info("MAPCore::refresh_token: Refreshing token failed: " + j["error_description"])
            return False
        logger.debug("  New access_token: " + j["access_token"])
        logger.debug("  New refresh_token: " + j["refresh_token"])

        self.user.map_profile.oauth_access_token = j["access_token"]
        self.user.map_profile.oauth_refresh_token = j["refresh_token"]

        #
        # Update database.
        #
        self.user.map_profile.oauth_refresh_time = dt.utcnow()
        self.user.map_profile.save()
        self.user.save()

        return True

    #
    # Get API version.
    #
    def get_api_version(self):

        logger.debug("MAPCore::get_api_version:")

        count = 0
        while count < 2:
            time_stamp, signature = self.calc_signature()

            url = map_hostname + map_api_path + "/version"
            payload = { 'time_stamp': time_stamp, 'signature': signature }
            headers = { "Authorization": "Bearer " + self.user.map_profile.oauth_access_token }

            r = requests.get(url, headers = headers, params = payload)
            j = self.check_result(r)
            if j != False:
                return j

            if self.is_token_expired(r):
                if self.refresh_token() == False:
                    return False
                count += 1
            else:
                return False

        return False

    #
    # Get group information by group name.
    #
    def get_group_by_name(self, group_name):

        logger.debug("MAPCore::get_group_by_name (group_name=" + group_name + ")")

        count = 0
        while count < 2:
            time_stamp, signature = self.calc_signature()

            url = map_hostname + map_api_path + "/mygroup"
            payload = {
                'time_stamp': time_stamp,
                'signature': signature,
                'searchWord': group_name.encode('utf-8')
            }
            headers = { "Authorization": "Bearer " + self.user.map_profile.oauth_access_token }

            r = requests.get(url, headers = headers, params = payload)
            j = self.check_result(r)
            if j != False:
                if len(j["result"]["groups"]) != 1:
                    logger.debug("  No or multiple group(s) matched")
                    return False
                return j

            if self.is_token_expired(r):
                if self.refresh_token() == False:
                    return False
                count += 1
            else:
                return False

        return False

    #
    # Get group information by group key.
    #
    def get_group_by_key(self, group_key):

        logger.debug("MAPCore::get_group_by_key (group_key=" + group_key + ")")

        count = 0
        while count < 2:
            time_stamp, signature = self.calc_signature()

            url = map_hostname + map_api_path + "/group/" + group_key
            payload = { 'time_stamp': time_stamp, 'signature': signature }
            headers = { "Authorization": "Bearer " + self.user.map_profile.oauth_access_token }

            r = requests.get(url, headers = headers, params = payload)
            j = self.check_result(r)
            if j != False:
                if len(j["result"]["groups"]) != 1:
                    logger.debug("  No or multiple group(s) matched")
                    return False
                return j

            if self.is_token_expired(r):
                if self.refresh_token() == False:
                    return False
                count += 1
            else:
                return False

        return False

    #
    # Create new group, and make it public, active and open_member.
    #
    def create_group(self, group_name):

        logger.debug("MAPCore::create_group (group_name=" + group_name + ")")

        #
        # Create new group named "group_name".
        #
        count = 0
        while count < 2:
            time_stamp, signature = self.calc_signature()

            params = { }
            params["request"] = {
                "time_stamp": time_stamp,
                "signature": signature
            }
            params["parameter"] = {
                "group_name": group_name,
                "group_name_en": group_name
            }
            params = json.dumps(params).encode('utf-8')

            url = map_hostname + map_api_path + "/group"
            headers = {
                "Authorization": "Bearer " + self.user.map_profile.oauth_access_token,
                "Content-Type": "application/json; charset=utf-8",
                "Content-Length": str(len(params))
            }

            r = requests.post(url, headers = headers, data = params)
            j = self.check_result(r)
            if j != False:
                group_key = j["result"]["groups"][0]["group_key"]
                logger.debug("  New geoup has been created (group_key=" + group_key + ")")

                #
                # Change mode of group last created.
                #
                j = self.edit_group(group_key, group_name, group_name)
                return j

            if self.is_token_expired(r):
                if self.refresh_token() == False:
                    return False
                count += 1
            else:
                return False

        return False

    #
    # Change group properties.
    #
    def edit_group(self, group_key, group_name, introduction):

        logger.debug("MAPCore::edit_group (group_name=" + group_name + ", introduction=" + introduction + ")")

        count = 0
        while count < 2:
            time_stamp, signature = self.calc_signature()

            params = { }
            params["request"] = {
                "time_stamp": time_stamp,
                "signature": signature
            }
            params["parameter"] = {
                "group_name": group_name,
                "group_name_en": group_name,
                "introduction": introduction,
                "introduction_en": introduction,
                "public": 1,
                "active": 1,
                "open_member": 1
            }
            params = json.dumps(params).encode('utf-8')

            url = map_hostname + map_api_path + "/group/" + group_key
            headers = {
                "Authorization": "Bearer " + self.user.map_profile.oauth_access_token,
                "Content-Type": "application/json; charset=utf-8",
                "Content-Length": str(len(params))
            }

            r = requests.post(url, headers = headers, data = params)
            j = self.check_result(r)
            if j != False:
                return j

            if self.is_token_expired(r):
                if self.refresh_token() == False:
                    return False
                count += 1
            else:
                return False

        return False

    #
    # Get member of group.
    #
    def get_group_members(self, group_key):

        logger.debug("MAPCore::get_group_members (group_key=" + group_key + ")")

        count = 0
        while count < 2:
            time_stamp, signature = self.calc_signature()

            url = map_hostname + map_api_path + "/member/" + group_key
            payload = { 'time_stamp': time_stamp, 'signature': signature }
            headers = { "Authorization": "Bearer " + self.user.map_profile.oauth_access_token }

            r = requests.get(url, headers = headers, params = payload)
            j = self.check_result(r)
            if j != False:
                return j

            if self.is_token_expired(r):
                if self.refresh_token() == False:
                    return False
                count += 1
            else:
                return False

        return False

    #
    # Get joined group list.
    #
    def get_my_groups(self):

        logger.debug("MAPCore::get_my_groups:")

        count = 0
        while count < 2:
            time_stamp, signature = self.calc_signature()

            url = map_hostname + map_api_path + "/mygroup"
            payload = { 'time_stamp': time_stamp, 'signature': signature }
            headers = { "Authorization": "Bearer " + self.user.map_profile.oauth_access_token }

            r = requests.get(url, headers = headers, params = payload)
            j = self.check_result(r)
            if j != False:
                return j

            if self.is_token_expired(r):
                if self.refresh_token() == False:
                    return False
                count += 1
            else:
                return False

        return False

    #
    # Add to group.
    #
    def add_to_group(self, group_key, eppn, admin):

        logger.debug("MAPCore::add_to_group (group_key=" + group_key + ", eppn=" + eppn + ", admin=" + str(admin) + ")")

        count = 0
        while count < 2:
            time_stamp, signature = self.calc_signature()

            params = { }
            params["request"] = {
                "time_stamp": time_stamp,
                "signature": signature
            }
            params["parameter"] = {
                "admin": admin
            }
            params = json.dumps(params).encode('utf-8')

            url = map_hostname + map_api_path + "/member/" + group_key + "/" + eppn
            headers = {
                "Authorization": "Bearer " + self.user.map_profile.oauth_access_token,
                "Content-Type": "application/json; charset=utf-8",
                "Content-Length": str(len(params))
            }

            r = requests.post(url, headers = headers, data = params)
            j = self.check_result(r)
            if j != False:
                return j

            if self.is_token_expired(r):
                if self.refresh_token() == False:
                    return False
                count += 1
            else:
                return False

        return False

    #
    # Remove from group.
    #
    def remove_from_group(self, group_key, eppn):

        logger.debug("MAPCore::remove_from_group (group_key=" + group_key + ", eppn=" + eppn + ")")

        count = 0
        while count < 2:
            time_stamp, signature = self.calc_signature()

            url = map_hostname + map_api_path + "/member/" + group_key + "/" + eppn
            payload = { 'time_stamp': time_stamp, 'signature': signature }
            headers = { "Authorization": "Bearer " + self.user.map_profile.oauth_access_token }

            r = requests.delete(url, headers = headers, params = payload)
            j = self.check_result(r)
            if j != False:
                return j

            if self.is_token_expired(r):
                if self.refresh_token() == False:
                    return False
                count += 1
            else:
                return False

        return False

    #
    # Edit member.
    #
    def edit_member(self, group_key, eppn, admin):

        logger.debug("MAPCore::edit_member (group_key=" + group_key + ", eppn=" + eppn + ", admin=" + str(admin) + ")")

        j = self.remove_from_group(group_key, eppn)
        if j == False:
            return False

        j = self.add_to_group(group_key, eppn, admin)

        return j

    #
    # Calculate API signature.
    #
    def calc_signature(self):

        time_stamp = str(int(time.time()))
        s = self.client_secret + self.user.map_profile.oauth_access_token + time_stamp

        digest = hashlib.sha256(s.encode('utf-8')).hexdigest()
        return time_stamp, digest

    #
    # Check API result status.
    # If any error occurs, a False will be returned.
    #
    def check_result(self, result):

        if result.status_code != requests.codes.ok:
            s = result.headers["WWW-Authenticate"]
            logger.info("MAPCore::check_result: status_code=" + str(result.status_code))
            logger.info("MAPCore::check_result: WWW-Authenticate=" + s)

            return False

        j = result.json()
        if j["status"]["error_code"] != 0:
            logger.info("MAPCore::check_result: error_code=" + str(j["status"]["error_code"]))
            logger.info("MAPCore::check_result: error_msg=" + j["status"]["error_msg"])
            return False

        return j

    def is_token_expired(self, result):

        if result.status_code != requests.codes.ok:
            s = result.headers["WWW-Authenticate"]
            if s.find("Access token expired") != -1:
                return True
            else:
                return False
        return False
