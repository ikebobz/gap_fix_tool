import pandas as pd
from .db import get_db_connection, validate_db_credentials

def execute_custom_query(query, params=None):
    credential_check = validate_db_credentials()
    if not credential_check['success']:
        return credential_check
    
    try:
        with get_db_connection() as conn:
            if params:
                df = pd.read_sql_query(query, conn, params=params)
            else:
                df = pd.read_sql_query(query, conn)
            
            return {
                'success': True,
                'data': df,
                'row_count': len(df),
                'error': None
            }
            
    except Exception as e:
        return {
            'success': False,
            'data': None,
            'error': f"Query error: {str(e)}"
        }

def execute_custom_query_with_uuids(query, uuids):
    credential_check = validate_db_credentials()
    if not credential_check['success']:
        return credential_check
    
    try:
        with get_db_connection() as conn:
            df = pd.read_sql_query(query, conn, params={'uuids': tuple(uuids)})
            
            return {
                'success': True,
                'data': df,
                'row_count': len(df),
                'error': None
            }
            
    except Exception as e:
        return {
            'success': False,
            'data': None,
            'error': f"Query error: {str(e)}"
        }

def execute_dml_with_uuids(query, uuids):
    credential_check = validate_db_credentials()
    if not credential_check['success']:
        return credential_check
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            modified_query = query.replace("%(uuids)s", "%s")
            cursor.execute(modified_query, (uuids,))
            row_count = cursor.rowcount
            
            conn.commit()
            cursor.close()
            
            return {
                'success': True,
                'row_count': row_count,
                'error': None
            }
            
    except Exception as e:
        return {
            'success': False,
            'row_count': 0,
            'error': f"Query error: {str(e)}"
        }

def execute_hiv_enrollment_update(updates):
    credential_check = validate_db_credentials()
    if not credential_check['success']:
        return credential_check
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            row_count = 0
            
            for house_hold_number, ovc_number, unique_id in updates:
                cursor.execute("""
                    UPDATE hiv_enrollment 
                    SET house_hold_number = %s, ovc_number = %s 
                    WHERE unique_id = %s
                """, (house_hold_number, ovc_number, unique_id))
                row_count += cursor.rowcount
            
            conn.commit()
            cursor.close()
            
            return {
                'success': True,
                'row_count': row_count,
                'error': None
            }
            
    except Exception as e:
        return {
            'success': False,
            'row_count': 0,
            'error': f"Query error: {str(e)}"
        }


def execute_tb_completion_update(updates):
    """Update hiv_art_pharmacy.ipt for TB completion based on hospital_number."""
    credential_check = validate_db_credentials()
    if not credential_check['success']:
        return credential_check
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            row_count = 0
            
            update_sql = """
                UPDATE hiv_art_pharmacy AS h
                SET ipt = jsonb_set(
                    jsonb_set(
                        h.ipt,
                        '{dateCompleted}',
                        to_jsonb(%(new_date)s::text),
                        true
                    ),
                    '{completionStatus}',
                    '"Completed"',
                    true
                )
                FROM patient_person AS p
                WHERE h.person_uuid = p.uuid
                  AND p.hospital_number = %(hosp_num)s
                  AND h.ipt->>'type' ILIKE %(type_pattern)s
            """
            
            for hosp_num, new_date in updates:
                cursor.execute(update_sql, {
                    'new_date': new_date, 
                    'hosp_num': hosp_num, 
                    'type_pattern': '%nitiation%'
                })
                row_count += cursor.rowcount
            
            conn.commit()
            cursor.close()
            
            return {
                'success': True,
                'row_count': row_count,
                'error': None
            }
    except Exception as e:
        return {
            'success': False,
            'row_count': 0,
            'error': f"Query error: {str(e)}"
        }
