# -*- coding: utf-8 -*-
# Generated by Django 1.11.7 on 2018-02-01 17:05
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('geniusalt', '0003_authtoken'),
    ]

    operations = [
        migrations.RenameField(
            model_name='node',
            old_name='installed_instances',
            new_name='bind_instances',
        ),
        migrations.RenameField(
            model_name='node',
            old_name='installed_modules',
            new_name='bind_modules',
        ),
    ]