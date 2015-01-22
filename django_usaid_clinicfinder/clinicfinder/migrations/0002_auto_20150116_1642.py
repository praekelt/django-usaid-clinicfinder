# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django_hstore.fields


class Migration(migrations.Migration):

    dependencies = [
        ('clinicfinder', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='LBSRequest',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('search', django_hstore.fields.DictionaryField()),
                ('response', django_hstore.fields.DictionaryField(null=True, blank=True)),
                ('pointofinterest', models.ForeignKey(related_name='pointofinterest', to='clinicfinder.LookupPointOfInterest')),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.AlterField(
            model_name='lookuppointofinterest',
            name='location',
            field=models.ForeignKey(related_name='lookup_location', blank=True, to='clinicfinder.LookupLocation', null=True),
            preserve_default=True,
        ),
    ]
