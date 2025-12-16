#!/usr/bin/env python3
"""
Модель лога активности пользователей
"""

from datetime import datetime
from app.models.db import db


class ActivityLog(db.Model):
    """Модель лога активности"""
    
    __tablename__ = 'activity_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)  # NULL для неавторизованных
    username = db.Column(db.String(80), nullable=True)  # Для неавторизованных пользователей
    ip_address = db.Column(db.String(45), nullable=True)  # IPv4 или IPv6
    action = db.Column(db.String(100), nullable=False, index=True)  # upload, download, login, register, etc.
    details = db.Column(db.Text, nullable=True)  # Дополнительная информация (JSON)
    task_id = db.Column(db.String(100), nullable=True, index=True)  # Если связано с обработкой
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    def __repr__(self):
        return f'<ActivityLog {self.action} by {self.username or "anonymous"} at {self.created_at}>'
