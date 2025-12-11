import psycopg2
import os
from dotenv import load_dotenv
from contextlib import contextmanager

load_dotenv()

def get_db_config():
    return {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': os.getenv('DB_PORT', '5432'),
        'database': os.getenv('DB_NAME', 'LAMISPLUS'),
        'user': os.getenv('DB_USER'),
        'password': os.getenv('DB_PASSWORD')
    }

def validate_db_credentials():
    config = get_db_config()
    if not config['user'] or not config['password']:
        return {
            'success': False,
            'error': 'Database credentials not found. Please set DB_USER and DB_PASSWORD in your .env file'
        }
    return {'success': True, 'error': None}

@contextmanager
def get_db_connection():
    config = get_db_config()
    conn = None
    try:
        conn = psycopg2.connect(
            host=config['host'],
            port=config['port'],
            database=config['database'],
            user=config['user'],
            password=config['password']
        )
        yield conn
    finally:
        if conn:
            conn.close()
