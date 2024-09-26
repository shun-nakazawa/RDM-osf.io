# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from osf.utils.migrations import UpdateRegistrationSchemasAndSchemaBlocks


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0240_ensure_schema_mappings'),
    ]

    operations = [
        migrations.AddField(
            model_name='registrationschemablock',
            name='allow_additional_option',
            field=models.BooleanField(default=False),
        ),
        UpdateRegistrationSchemasAndSchemaBlocks(),
    ]
