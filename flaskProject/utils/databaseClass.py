import os
#这个文件是数据库的配置设置
# class Config:
#     SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'mysql+pymysql://root:root@localhost/dg_db_website')
#     SQLALCHEMY_TRACK_MODIFICATIONS = False

# ！！！！下面是数据库封装增删查改的一个模板
# utils/databaseClass.py
import pymysql
from flask import current_app
from contextlib import contextmanager
from pymysql.cursors import DictCursor


class MySQLDatabase:
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        """初始化数据库配置"""
        app.config.setdefault('MYSQL_HOST', 'localhost')
        app.config.setdefault('MYSQL_PORT', 3306)
        app.config.setdefault('MYSQL_USER', 'root')
        app.config.setdefault('MYSQL_PASSWORD', 'root')
        app.config.setdefault('MYSQL_DB', 'dg_db_website')
        app.config.setdefault('MYSQL_CHARSET', 'utf8mb4')

    @contextmanager
    def get_connection(self):
        """获取数据库连接（上下文管理器）"""
        conn = pymysql.connect(
            host=current_app.config['MYSQL_HOST'],
            port=current_app.config['MYSQL_PORT'],
            user=current_app.config['MYSQL_USER'],
            password=current_app.config['MYSQL_PASSWORD'],
            database=current_app.config['MYSQL_DB'],
            charset=current_app.config['MYSQL_CHARSET'],
            cursorclass=DictCursor
        )
        try:
            yield conn
        finally:
            conn.close()

    def execute(self, sql, params=None, fetch=False):
        """
        执行SQL语句
        :param sql: SQL语句字符串
        :param params: 参数(元组/列表/字典)
        :param fetch: 是否获取查询结果
        :return: 查询结果或影响行数
        """
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params or ())
                if fetch:
                    result = cursor.fetchall()
                else:
                    conn.commit()
                    result = cursor.rowcount
                return result

    def query_all(self, sql, params=None):
        """查询多条记录"""
        return self.execute(sql, params, fetch=True)

    def query_one(self, sql, params=None):
        """查询单条记录"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params or ())
                return cursor.fetchone()

    def insert(self, sql, params=None):
        """插入数据"""
        return self.execute(sql, params)

    def update(self, sql, params=None):
        """更新数据"""
        return self.execute(sql, params)

    def delete(self, sql, params=None):
        """删除数据"""
        return self.execute(sql, params)


from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import ForeignKey

db = SQLAlchemy()


class EquipmentArchive(db.Model):
    __tablename__ = 'equipment_archive'
    equipment_id = db.Column(db.String(50), primary_key=True)
    model = db.Column(db.String(100))

    # 定义一对多关系（主表）
    maintenance_records = db.relationship(
        'MaintenanceRecord',
        backref='equipment',
        cascade='all, delete-orphan',  # ORM级联删除
        passive_deletes=True  # 依赖数据库级联
    )


class MaintenanceRecord(db.Model):
    __tablename__ = 'maintenance_record'
    id = db.Column(db.Integer, primary_key=True)
    equipment_id = db.Column(
        db.String(50),
        ForeignKey('equipment_archive.equipment_id', ondelete='CASCADE'),  # 数据库级联
        nullable=False
    )
    details = db.Column(db.Text)


