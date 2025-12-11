import sys
import os
from services import read_uuids_from_excel, execute_verification_query, validate_db_credentials

def main():
    excel_file = 'person_uuids.xlsx'
    
    if len(sys.argv) > 1:
        excel_file = sys.argv[1]
    
    if not os.path.exists(excel_file):
        print(f"Excel file '{excel_file}' not found.")
        print(f"Usage: python execute_hiv_query.py [excel_file_path]")
        print(f"Default file: person_uuids.xlsx")
        return
    
    credential_check = validate_db_credentials()
    if not credential_check['success']:
        print("Error: " + credential_check['error'])
        return
    
    print(f"Reading UUIDs from: {excel_file}")
    result = read_uuids_from_excel(excel_file)
    
    if not result['success']:
        print(f"Error: {result['error']}")
        if result.get('available_columns'):
            print(f"Available columns: {result['available_columns']}")
        return
    
    uuids = result['uuids']
    
    if len(uuids) == 0:
        print("No valid UUIDs found. Exiting.")
        return
    
    print(f"Found {result['count']} unique UUIDs in Excel file")
    print(f"\nUUIDs to process:")
    for idx, uuid in enumerate(uuids[:10], 1):
        print(f"  {idx}. {uuid}")
    if len(uuids) > 10:
        print(f"  ... and {len(uuids) - 10} more")
    
    response = input(f"\nProceed with database operation for {len(uuids)} UUIDs? (yes/no): ")
    if response.lower() not in ['yes', 'y']:
        print("Operation cancelled.")
        return
    
    print("\n--- Executing verification import ---")
    exec_result = execute_verification_query(uuids)
    
    if exec_result['success']:
        print(f"Inserted {exec_result['insert_count']} records into hiv_observation")
        print(f"Updated {exec_result['update_count']} records in hiv_status_tracker")
        print("\n✓ Transaction committed successfully")
        print("\n✓ All operations completed successfully!")
    else:
        print(f"\n✗ Operation failed: {exec_result['error']}")
        if exec_result.get('rolled_back'):
            print("⚠️  Transaction was rolled back. No changes were made to the database.")

if __name__ == "__main__":
    main()
