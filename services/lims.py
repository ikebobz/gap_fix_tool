from .db import get_db_connection, validate_db_credentials

def execute_recall_sample(manifest_id):
    credential_check = validate_db_credentials()
    if not credential_check['success']:
        return credential_check
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            delete_samples_query = """
            DELETE FROM lims_sample 
            WHERE manifest_record_id IN (
                SELECT id FROM lims_manifest WHERE manifest_id = %s
            )
            """
            cursor.execute(delete_samples_query, (manifest_id,))
            samples_deleted = cursor.rowcount
            
            delete_manifest_query = """
            DELETE FROM lims_manifest 
            WHERE manifest_id = %s
            """
            cursor.execute(delete_manifest_query, (manifest_id,))
            manifests_deleted = cursor.rowcount
            
            conn.commit()
            cursor.close()
            
            return {
                'success': True,
                'samples_deleted': samples_deleted,
                'manifests_deleted': manifests_deleted,
                'error': None
            }
            
    except Exception as e:
        return {
            'success': False,
            'error': f"Database error: {str(e)}",
            'rolled_back': True
        }
