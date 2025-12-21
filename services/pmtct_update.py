from .db import get_db_connection, validate_db_credentials

def execute_pmtct_value_update(patient_id, old_value, new_value):
    credential_check = validate_db_credentials()
    if not credential_check['success']:
        return credential_check
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            query = """
            UPDATE pmtct_infant_pcr 
            SET results = %s 
            WHERE person_uuid = %s 
            AND results = %s
            """
            
            cursor.execute(query, (new_value, patient_id, old_value))
            update_count = cursor.rowcount
            
            conn.commit()
            cursor.close()
            
            return {
                'success': True,
                'update_count': update_count,
                'error': None
            }
            
    except Exception as e:
        return {
            'success': False,
            'error': f"Database error: {str(e)}",
            'rolled_back': True
        }
