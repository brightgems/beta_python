# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0082_auto_20161214_1318'),
    ]

    operations = [
        migrations.AddField(
            model_name='ticker',
            name='latest_tick',
            field=models.FloatField(default=0),
        ),
    ]
