from .db import get_db_connection, validate_db_credentials

def execute_eac_fix():
    credential_check = validate_db_credentials()
    if not credential_check['success']:
        return credential_check
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            query = """
            UPDATE hiv_eac eac 
            SET archived = 5 
            WHERE NOT EXISTS (
                SELECT * FROM hiv_eac_session hes 
                WHERE eac_id = eac.uuid
            )
            """
            
            cursor.execute(query)
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

def execute_eac_fix_filtered(uuids):
    credential_check = validate_db_credentials()
    if not credential_check['success']:
        return credential_check
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            query = """
            UPDATE hiv_eac eac 
            SET archived = 5 
            WHERE NOT EXISTS (
                SELECT * FROM hiv_eac_session hes 
                WHERE eac_id = eac.uuid
            )
            AND eac.uuid = ANY(%s)
            """
            
            cursor.execute(query, (uuids,))
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
