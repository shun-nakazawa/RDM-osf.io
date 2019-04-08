# -*- coding: utf-8 -*-
# Generated by Django 1.11.15 on 2019-04-08 00:52
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0162_remove_basefilenode_versions'),
    ]

    operations = [
        migrations.AddField(
            model_name='basefilenode',
            name='versions',
            field=models.ManyToManyField(through='osf.BaseFileVersionsThrough', to='osf.FileVersion'),
        ),
    ]
