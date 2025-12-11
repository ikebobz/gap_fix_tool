from .db import get_db_connection, validate_db_credentials
import uuid as uuid_lib

def insert_pmtct_record(data):
    credential_check = validate_db_credentials()
    if not credential_check['success']:
        return credential_check
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            record_uuid = str(uuid_lib.uuid4())
            
            query = """
            INSERT INTO pmtct_infant_pcr (
                visit_date,
                infant_hospital_number,
                anc_number,
                age_at_test,
                test_type,
                date_sample_collected,
                date_sample_sent,
                date_result_received_at_facility,
                date_result_received_by_caregiver,
                results,
                uuid,
                unique_uuid
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            """
            
            cursor.execute(query, (
                data.get('visit_date'),
                data.get('infant_hospital_number'),
                data.get('anc_number'),
                data.get('age_at_test'),
                data.get('test_type'),
                data.get('date_sample_collected'),
                data.get('date_sample_sent'),
                data.get('date_result_received_at_facility'),
                data.get('date_result_received_by_caregiver'),
                data.get('results'),
                record_uuid,
                data.get('unique_uuid') or record_uuid
            ))
            
            conn.commit()
            cursor.close()
            
            return {
                'success': True,
                'insert_count': 1,
                'uuid': record_uuid,
                'error': None
            }
            
    except Exception as e:
        return {
            'success': False,
            'error': f"Database error: {str(e)}",
            'rolled_back': True
        }

def insert_pmtct_batch(records):
    credential_check = validate_db_credentials()
    if not credential_check['success']:
        return credential_check
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            query = """
            INSERT INTO pmtct_infant_pcr (
                visit_date,
                infant_hospital_number,
                anc_number,
                age_at_test,
                test_type,
                date_sample_collected,
                date_sample_sent,
                date_result_received_at_facility,
                date_result_received_by_caregiver,
                results,
                uuid,
                unique_uuid
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            """
            
            insert_count = 0
            for data in records:
                record_uuid = str(uuid_lib.uuid4())
                cursor.execute(query, (
                    data.get('visit_date'),
                    data.get('infant_hospital_number'),
                    data.get('anc_number'),
                    data.get('age_at_test'),
                    data.get('test_type'),
                    data.get('date_sample_collected'),
                    data.get('date_sample_sent'),
                    data.get('date_result_received_at_facility'),
                    data.get('date_result_received_by_caregiver'),
                    data.get('results'),
                    record_uuid,
                    data.get('unique_uuid') or record_uuid
                ))
                insert_count += 1
            
            conn.commit()
            cursor.close()
            
            return {
                'success': True,
                'insert_count': insert_count,
                'error': None
            }
            
    except Exception as e:
        return {
            'success': False,
            'error': f"Database error: {str(e)}",
            'rolled_back': True
        }
