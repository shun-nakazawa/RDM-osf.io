# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from osf.utils.migrations import UpdateRegistrationSchemasAndSchemaBlocks


def migrate_erad_haibunkikan_short_name(*args):
    from addons.metadata.models import ERadRecord, ERAD_HAIBUNKIKAN_SHORT_NAME_MAP
    for record in ERadRecord.objects.all():
        record.haibunkikan_short_name = ERAD_HAIBUNKIKAN_SHORT_NAME_MAP.get(record.haibunkikan_cd, None)
        record.save()


def noop(*args):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('addons_metadata', '0012_registrationreportformat_order'),
    ]

    operations = [
        migrations.AddField(
            model_name='eradrecord',
            name='haibunkikan_short_name',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.RunPython(migrate_erad_haibunkikan_short_name, noop),
        UpdateRegistrationSchemasAndSchemaBlocks(),
    ]
