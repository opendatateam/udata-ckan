# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.models import db, Dataset

Dataset.extras.register('ckan:name', db.StringField)
Dataset.extras.register('ckan:source', db.StringField)
