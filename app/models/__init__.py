#!/usr/bin/env python3
"""
Модели базы данных
"""

from app.models.db import db
from app.models.user import User
from app.models.document import Document
from app.models.activity_log import ActivityLog

__all__ = ['db', 'User', 'Document', 'ActivityLog']
