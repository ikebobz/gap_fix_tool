from .db import get_db_connection, validate_db_credentials

def execute_verification_query(uuids):
    credential_check = validate_db_credentials()
    if not credential_check['success']:
        return credential_check
    
    try:
        with get_db_connection() as conn:
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
            cursor.close()
            
            return {
                'success': True,
                'insert_count': insert_count,
                'update_count': update_count,
                'error': None
            }
            
    except Exception as e:
        return {
            'success': False,
            'error': f"Database error: {str(e)}",
            'rolled_back': True
        }
