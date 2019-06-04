# -*- coding: utf-8 -*-

from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

from addons.googledrive.apps import GoogleDriveAddonConfig
from addons.iqbrims.utils import copy_node_auth
from website import settings as website_settings
from addons.iqbrims.apps import IQBRIMSAddonConfig
from osf.models.base import BaseModel, Guid
from osf.models import ExternalAccount, Institution, AbstractNode


class RdmAddonOption(BaseModel):
    provider = models.CharField(max_length=50, blank=False, null=False, db_index=True)
    is_forced = models.BooleanField(default=False)
    is_allowed = models.BooleanField(default=True)
    management_node = models.ForeignKey(AbstractNode, blank=True, null=True, default=None, on_delete=models.CASCADE,
                                        related_name='management_rdm_addon_option_set')
    organizational_node = models.ForeignKey(AbstractNode, blank=True, null=True, default=None, on_delete=models.CASCADE,
                                            related_name='organizational_rdm_addon_option_set')

    institution = models.ForeignKey(Institution, blank=False, null=False)
    external_accounts = models.ManyToManyField(ExternalAccount, blank=True)

    class Meta:
        unique_together = (('provider', 'institution'),)

    def get_management_node_guid(self):
        if self.management_node:
            return self.management_node._id
        else:
            return None

    def set_management_node_by_guid(self, guid, save=False):
        guid_obj = Guid.objects.get(_id=guid)
        node = guid_obj.referent
        if not isinstance(node, AbstractNode):
            raise TypeError('"guid" must be a guid of AbstractNode.')

        self.management_node = node
        if save:
            self.save()

    def unset_management_node(self, save=True):
        self.management_node = None
        if save:
            self.save()

    def get_organizational_node_guid(self):
        if self.organizational_node:
            return self.organizational_node._id
        else:
            return None

    def set_organizational_node_by_guid(self, guid, save=False):
        guid_obj = Guid.objects.get(_id=guid)
        node = guid_obj.referent
        if not isinstance(node, AbstractNode):
            raise TypeError('"guid" must be a guid of AbstractNode.')

        self.organizational_node = node
        if save:
            self.save()

    def unset_organizational_node(self, save=True):
        self.organizational_node = None
        if save:
            self.save()


class RdmAddonNoInstitutionOption(BaseModel):
    provider = models.CharField(max_length=50, blank=False, null=False, unique=True, db_index=True)
    is_forced = models.BooleanField(default=False)
    is_allowed = models.BooleanField(default=True)
    management_node = models.ForeignKey(AbstractNode, blank=True, null=True, default=None, on_delete=models.CASCADE,
                                        related_name='management_rdm_addon_no_institution_option_set')
    organizational_node = models.ForeignKey(AbstractNode, blank=True, null=True, default=None, on_delete=models.CASCADE,
                                            related_name='organizational_rdm_addon_no_institution_option_set')

    external_accounts = models.ManyToManyField(ExternalAccount, blank=True)


@receiver(post_save, sender=RdmAddonOption)
def change_iqbrims_addon_enabled(sender, instance, created, **kwargs):
    if IQBRIMSAddonConfig.short_name not in website_settings.ADDONS_AVAILABLE_DICT:
        return

    if instance.is_allowed and instance.management_node is not None:
        for node in AbstractNode.find_by_institutions(instance.institution):
            if instance.organizational_node:
                if instance.organizational_node.is_contributor(node.creator):
                    node.add_addon(IQBRIMSAddonConfig.short_name, auth=None, log=False)
                else:
                    node.delete_addon(IQBRIMSAddonConfig.short_name, auth=None)
            else:
                node.add_addon(IQBRIMSAddonConfig.short_name, auth=None, log=False)
    else:
        for node in AbstractNode.find_by_institutions(instance.institution):
            node.delete_addon(IQBRIMSAddonConfig.short_name, auth=None)


@receiver(post_save, sender=RdmAddonOption)
def setup_iqbrims_addon_auth_of_management_node(sender, instance, created, **kwargs):
    if IQBRIMSAddonConfig.short_name not in website_settings.ADDONS_AVAILABLE_DICT:
        return
    if GoogleDriveAddonConfig.short_name not in website_settings.ADDONS_AVAILABLE_DICT:
        return
    if instance.management_node is None:
        return
    if not (instance.is_allowed and instance.management_node is not None):
        return

    copy_node_addon = instance.management_node.get_addon(GoogleDriveAddonConfig.short_name)
    if copy_node_addon is not None:
        copy_node_auth(instance.management_node, copy_node_addon)
