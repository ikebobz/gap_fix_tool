import pandas as pd
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def read_uuids_from_excel(file_path, column_name='person_uuid'):
    try:
        df = pd.read_excel(file_path)
        
        if column_name not in df.columns:
            return {
                'success': False,
                'error': f"Column '{column_name}' not found in Excel file.",
                'available_columns': list(df.columns),
                'uuids': None
            }
        
        uuids = df[column_name].dropna().unique().tolist()
        return {
            'success': True,
            'uuids': uuids,
            'count': len(uuids),
            'error': None
        }
    
    except FileNotFoundError:
        return {
            'success': False,
            'error': f"File '{file_path}' not found.",
            'uuids': None
        }
    except Exception as e:
        return {
            'success': False,
            'error': f"Error reading Excel file: {str(e)}",
            'uuids': None
        }

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

def execute_hiv_query(uuids):
    config = get_db_config()
    
    credential_check = validate_db_credentials()
    if not credential_check['success']:
        return credential_check
    
    conn = None
    cursor = None
    try:
        conn = psycopg2.connect(
            host=config['host'],
            port=config['port'],
            database=config['database'],
            user=config['user'],
            password=config['password']
        )
        
        cursor = conn.cursor()
        
        query = """
        with t as (
            select uuid as person_uuid from patient_person where uuid = ANY(%s)
        )

        insert into hiv_observation (created_date,created_by,facility_id,date_of_observation,person_uuid,type,uuid,data,archived,visit_id)
        select current_date,'add_verification_status',1759,current_date,person_uuid,'Client Verification',uuid_generate_v4(),
        '{"attempt": [{"comment": "", "outcome": "valid", "dateOfAttempt": "2025-08-25", "verificationStatus": "Records Verified", "verificationAttempts": "Biometric recapture"}]}',
        0,uuid_generate_v4()
        from t where person_uuid is not null;
        """
        
        update_query = """
        update hiv_status_tracker set status_date = '2009-01-31' where status_date = '0209-01-31';
        """
        
        cursor.execute(query, (uuids,))
        insert_count = cursor.rowcount
        
        cursor.execute(update_query)
        update_count = cursor.rowcount
        
        conn.commit()
        
        return {
            'success': True,
            'insert_count': insert_count,
            'update_count': update_count,
            'error': None
        }
        
    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        return {
            'success': False,
            'error': f"Database error: {str(e)}",
            'rolled_back': True
        }
    except Exception as e:
        if conn:
            conn.rollback()
        return {
            'success': False,
            'error': f"Unexpected error: {str(e)}",
            'rolled_back': True
        }
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
