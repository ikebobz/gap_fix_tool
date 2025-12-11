from .db import get_db_connection, validate_db_credentials

def execute_lab_sync():
    credential_check = validate_db_credentials()
    if not credential_check['success']:
        return credential_check
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            query = r"""
            with s as (
                select test_result, result_reported, lr.uuid 
                from lims_result lmr 
                inner join laboratory_result lr on lr.test_id = lmr.test_id 
                where test_result ~ '\d+\.\d+' and test_result <> result_reported
            )
            update laboratory_result r 
            set result_reported = test_result 
            from s
            where r.uuid = s.uuid
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

def execute_lab_sync_filtered(uuids):
    credential_check = validate_db_credentials()
    if not credential_check['success']:
        return credential_check
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            query = r"""
            with s as (
                select test_result, result_reported, lr.uuid 
                from lims_result lmr 
                inner join laboratory_result lr on lr.test_id = lmr.test_id 
                where test_result ~ '\d+\.\d+' 
                and test_result <> result_reported
                and lr.uuid = ANY(%s)
            )
            update laboratory_result r 
            set result_reported = test_result 
            from s
            where r.uuid = s.uuid
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

def preview_lab_sync():
    credential_check = validate_db_credentials()
    if not credential_check['success']:
        return credential_check
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            query = r"""
            select test_result, result_reported, lr.uuid 
            from lims_result lmr 
            inner join laboratory_result lr on lr.test_id = lmr.test_id 
            where test_result ~ '\d+\.\d+' and test_result <> result_reported
            LIMIT 100
            """
            
            cursor.execute(query)
            rows = cursor.fetchall()
            cursor.close()
            
            return {
                'success': True,
                'count': len(rows),
                'preview': rows,
                'error': None
            }
            
    except Exception as e:
        return {
            'success': False,
            'error': f"Database error: {str(e)}",
            'preview': None
        }
