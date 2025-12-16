#!/usr/bin/env python3
"""
Модель обработанного документа
"""

from datetime import datetime
from app.models.db import db


class Document(db.Model):
    """Модель обработанного документа"""
    
    __tablename__ = 'documents'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    task_id = db.Column(db.String(100), unique=True, nullable=False, index=True)
    original_filename = db.Column(db.String(255), nullable=False)
    scenario_id = db.Column(db.String(100), nullable=False)
    ai_provider = db.Column(db.String(50), nullable=False)
    
    # Пути к файлам
    json_file = db.Column(db.String(255), nullable=True)
    excel_file = db.Column(db.String(255), nullable=True)
    
    # Размеры файлов
    json_size = db.Column(db.Integer, default=0)
    excel_size = db.Column(db.Integer, default=0)
    
    # Метрики обработки
    prompt_size = db.Column(db.Integer, default=0)
    tokens_used = db.Column(db.Integer, default=0)
    processing_time = db.Column(db.Float, default=0.0)  # в секундах
    
    # Статус
    status = db.Column(db.String(50), default='completed', nullable=False)  # completed, error, cancelled
    error_message = db.Column(db.Text, nullable=True)
    
    # Временные метки
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    def __repr__(self):
        return f'<Document {self.task_id} by User {self.user_id}>'
