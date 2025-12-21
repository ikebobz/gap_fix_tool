from .db import get_db_connection, validate_db_credentials

def execute_testing_setting_update(patient_id, new_value):
    credential_check = validate_db_credentials()
    if not credential_check['success']:
        return credential_check
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            query = """
            WITH x AS (
                SELECT hrs.testing_setting, hrs.uuid 
                FROM hts_risk_stratification hrs 
                INNER JOIN hts_client hc ON hc.risk_stratification_code = hrs.code
                WHERE hc.person_uuid = %s
            )
            UPDATE hts_risk_stratification h 
            SET testing_setting = %s
            FROM x 
            WHERE h.uuid = x.uuid
            """
            
            cursor.execute(query, (patient_id, new_value))
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
