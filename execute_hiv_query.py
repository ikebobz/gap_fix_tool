import pandas as pd
import psycopg2
from psycopg2 import sql
import os
from dotenv import load_dotenv
import sys

load_dotenv()

def read_uuids_from_excel(file_path, column_name='person_uuid'):
    try:
        df = pd.read_excel(file_path)
        
        if column_name not in df.columns:
            print(f"Error: Column '{column_name}' not found in Excel file.")
            print(f"Available columns: {list(df.columns)}")
            return None
        
        uuids = df[column_name].dropna().unique().tolist()
        print(f"Found {len(uuids)} unique UUIDs in Excel file")
        return uuids
    
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.")
        return None
    except Exception as e:
        print(f"Error reading Excel file: {e}")
        return None

def execute_hiv_query(uuids):
    db_host = os.getenv('DB_HOST', 'localhost')
    db_port = os.getenv('DB_PORT', '5432')
    db_name = os.getenv('DB_NAME', 'LAMISPLUS')
    db_user = os.getenv('DB_USER')
    db_password = os.getenv('DB_PASSWORD')
    
    if not db_user or not db_password:
        print("Error: Database credentials not found in environment variables.")
        print("Please set DB_USER and DB_PASSWORD in your .env file")
        return False
    
    conn = None
    cursor = None
    try:
        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            database=db_name,
            user=db_user,
            password=db_password
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
        
        print("\n--- Executing INSERT query ---")
        cursor.execute(query, (uuids,))
        insert_count = cursor.rowcount
        print(f"Inserted {insert_count} records into hiv_observation")
        
        print("\n--- Executing UPDATE query ---")
        cursor.execute(update_query)
        update_count = cursor.rowcount
        print(f"Updated {update_count} records in hiv_status_tracker")
        
        conn.commit()
        print("\n✓ Transaction committed successfully")
        
        return True
        
    except psycopg2.Error as e:
        print(f"Database error: {e}")
        if conn:
            conn.rollback()
            print("Transaction rolled back")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def main():
    excel_file = 'person_uuids.xlsx'
    
    if len(sys.argv) > 1:
        excel_file = sys.argv[1]
    
    if not os.path.exists(excel_file):
        print(f"Excel file '{excel_file}' not found.")
        print(f"Usage: python execute_hiv_query.py [excel_file_path]")
        print(f"Default file: person_uuids.xlsx")
        return
    
    print(f"Reading UUIDs from: {excel_file}")
    uuids = read_uuids_from_excel(excel_file)
    
    if uuids is None or len(uuids) == 0:
        print("No valid UUIDs found. Exiting.")
        return
    
    print(f"\nUUIDs to process: {uuids}")
    
    response = input(f"\nProceed with database operation for {len(uuids)} UUIDs? (yes/no): ")
    if response.lower() not in ['yes', 'y']:
        print("Operation cancelled.")
        return
    
    success = execute_hiv_query(uuids)
    
    if success:
        print("\n✓ All operations completed successfully!")
    else:
        print("\n✗ Operation failed. Please check the error messages above.")

if __name__ == "__main__":
    main()
