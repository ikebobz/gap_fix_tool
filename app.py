import streamlit as st
import tempfile
import os
import pandas as pd
from datetime import date, datetime
from services import (
    validate_db_credentials,
    read_uuids_from_excel,
    read_excel_file,
    execute_verification_query,
    execute_lab_sync,
    insert_pmtct_record,
    insert_pmtct_batch
)
from services.lab_results import execute_lab_sync_filtered

st.set_page_config(
    page_title="LAMISPLUS Data Tools",
    page_icon="🏥",
    layout="wide"
)

st.title("🏥 LAMISPLUS Data Tools")
st.markdown("Multi-purpose data import and sync utilities for LAMISPLUS database")

credential_check = validate_db_credentials()
db_configured = credential_check['success']

if db_configured:
    st.success("✓ Database credentials configured")
else:
    st.warning("⚠️ Preview Mode - Database not configured")
    with st.expander("Setup Instructions", expanded=False):
        st.markdown("""
        Create a `.env` file with:
        ```
        DB_HOST=your_host
        DB_PORT=5432
        DB_NAME=LAMISPLUS
        DB_USER=your_username
        DB_PASSWORD=your_password
        ```
        Then restart the application.
        """)

st.markdown("---")

def parse_date_value(value):
    if value is None or pd.isna(value):
        return None
    if isinstance(value, (date, datetime)):
        return value.date() if isinstance(value, datetime) else value
    if isinstance(value, (int, float)) and not pd.isna(value):
        try:
            return datetime.fromordinal(datetime(1900, 1, 1).toordinal() + int(value) - 2).date()
        except:
            pass
    try:
        parsed = pd.to_datetime(value, errors='coerce')
        if pd.notna(parsed):
            return parsed.date()
    except:
        pass
    return None

def normalize_string(value):
    if value is None or pd.isna(value):
        return None
    result = ' '.join(str(value).split()).strip()
    return result if result else None

TEST_TYPE_OPTIONS = {
    'First PCR': 'INFANT_TESTING_PCR_1ST_PCR_4-6_WEEKS_OF_AGE_OR_1ST_CONTACT',
    'Second PCR': 'INFANT_TESTING_PCR_2ND_PCR_12_WEEKS_AFTER_CESSATION_OF_BREASTFEEDING_OR_AS_INDICATED'
}
TEST_TYPE_VALUES = set(TEST_TYPE_OPTIONS.values())

AGE_AT_TEST_OPTIONS = {
    'Less than 72hours': 'CHILD_TEST_AGE_<_72_HRS',
    'Less than 2 months': '2ND_PCR_CHILD_TEST_AGE_<_2_MONTHS',
    '2 -12 months': '2ND_PCR_CHILD_TEST_AGE_2-12_MONTHS',
    'Greater than 12 months': '2ND_PCR_CHILD_TEST_AGE_>_12_MONTHS'
}
AGE_AT_TEST_VALUES = set(AGE_AT_TEST_OPTIONS.values())

VALID_RESULTS = {'positive', 'negative', 'indeterminate', 'pending'}

def validate_test_type(value):
    if not value:
        return None, "Missing test_type"
    normalized = normalize_string(value)
    if not normalized:
        return None, "Empty test_type"
    if normalized in TEST_TYPE_VALUES:
        return normalized, None
    for label, val in TEST_TYPE_OPTIONS.items():
        if normalized.lower() == label.lower():
            return val, None
    return None, f"Invalid test_type '{normalized}' (allowed: First PCR, Second PCR)"

def validate_results(value):
    if not value:
        return None, "Missing results"
    normalized = normalize_string(value)
    if not normalized:
        return None, "Empty results"
    if normalized.lower() in VALID_RESULTS:
        return normalized.title(), None
    return None, f"Invalid results '{normalized}' (allowed: Positive, Negative, Indeterminate, Pending)"

def validate_age_at_test(value):
    if not value:
        return None, "Missing age_at_test"
    normalized = normalize_string(value)
    if not normalized:
        return None, "Empty age_at_test"
    if normalized in AGE_AT_TEST_VALUES:
        return normalized, None
    for label, val in AGE_AT_TEST_OPTIONS.items():
        if normalized.lower() == label.lower():
            return val, None
    return None, f"Invalid age_at_test '{normalized}' (allowed: Less than 72hours, Less than 2 months, 2 -12 months, Greater than 12 months)"

tab1, tab2, tab3 = st.tabs([
    "📋 Client Verification Import",
    "🔬 Fix Lab Result Round Off Error", 
    "👶 PMTCT Infant PCR"
])

with tab1:
    st.subheader("Client Verification Status Import")
    st.markdown("Import client verification records into the `hiv_observation` table and fix date errors in `hiv_status_tracker`.")
    
    uploaded_file = st.file_uploader(
        "Upload Excel file with person_uuid column",
        type=['xlsx'],
        key="verification_upload",
        help="The file must contain a column named 'person_uuid'"
    )
    
    if uploaded_file is not None:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_file_path = tmp_file.name
        
        st.success(f"✓ File uploaded: {uploaded_file.name}")
        
        result = read_uuids_from_excel(tmp_file_path)
        os.unlink(tmp_file_path)
        
        if result['success']:
            st.metric("UUIDs Found", result['count'])
            
            with st.expander("View UUIDs", expanded=False):
                for idx, uuid in enumerate(result['uuids'][:50], 1):
                    st.code(f"{idx}. {uuid}", language=None)
                if result['count'] > 50:
                    st.info(f"... and {result['count'] - 50} more")
            
            st.info("""
            **Operations:**
            - Insert verification records into `hiv_observation`
            - Fix dates in `hiv_status_tracker` (0209 → 2009)
            """)
            
            if db_configured:
                if st.button("Execute Verification Import", type="primary", key="verify_btn"):
                    with st.spinner("Executing..."):
                        exec_result = execute_verification_query(result['uuids'])
                    
                    if exec_result['success']:
                        st.success("✅ Completed successfully!")
                        col1, col2 = st.columns(2)
                        col1.metric("Records Inserted", exec_result['insert_count'])
                        col2.metric("Dates Fixed", exec_result['update_count'])
                        st.balloons()
                    else:
                        st.error(f"❌ Failed: {exec_result['error']}")
            else:
                st.button("Execute Verification Import", type="primary", disabled=True, key="verify_btn_disabled")
                st.caption("⚠️ Configure database to enable")
        else:
            st.error(f"❌ {result['error']}")
            if result.get('available_columns'):
                st.warning(f"Available columns: {', '.join(result['available_columns'])}")
    else:
        st.info("👆 Upload an Excel file to begin")

with tab2:
    st.subheader("Lab Result Sync")
    st.markdown("Sync test results from `lims_result` to `laboratory_result` table.")
    
    st.info("""
    **What this does:**
    - Finds records where `test_result` differs from `result_reported`
    - Updates `laboratory_result.result_reported` with the correct `test_result` value
    - Only processes numeric results (matching pattern `\\d+\\.\\d+`)
    """)
    
    with st.expander("View SQL Query", expanded=False):
        st.code("""
WITH s AS (
    SELECT test_result, result_reported, lr.uuid 
    FROM lims_result lmr 
    INNER JOIN laboratory_result lr ON lr.test_id = lmr.test_id 
    WHERE test_result ~ '\\d+\\.\\d+' AND test_result <> result_reported
)
UPDATE laboratory_result r 
SET result_reported = test_result 
FROM s
WHERE r.uuid = s.uuid
        """, language="sql")
    
    lab_file = st.file_uploader(
        "Upload Excel file with UUIDs to filter (optional)",
        type=['xlsx'],
        key="lab_upload",
        help="Optional: Limit sync to specific UUIDs. Leave empty to sync all mismatched results."
    )
    
    lab_uuids = None
    if lab_file is not None:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
            tmp_file.write(lab_file.getvalue())
            tmp_file_path = tmp_file.name
        
        result = read_uuids_from_excel(tmp_file_path, column_name='uuid')
        if not result['success']:
            result = read_uuids_from_excel(tmp_file_path, column_name='person_uuid')
        os.unlink(tmp_file_path)
        
        if result['success']:
            lab_uuids = result['uuids']
            st.success(f"✓ File uploaded: {lab_file.name}")
            st.metric("UUIDs to filter", result['count'])
        else:
            st.warning(f"Could not read UUIDs: {result['error']}")
            st.info("Proceeding without UUID filter - will sync all mismatched results")
    
    if db_configured:
        if st.button("🔄 Run Lab Result Sync", type="primary", key="lab_sync_btn"):
            with st.spinner("Syncing lab results..."):
                if lab_uuids:
                    exec_result = execute_lab_sync_filtered(lab_uuids)
                else:
                    exec_result = execute_lab_sync()
            
            if exec_result['success']:
                st.success("✅ Lab sync completed successfully!")
                st.metric("Records Updated", exec_result['update_count'])
                if exec_result['update_count'] > 0:
                    st.balloons()
            else:
                st.error(f"❌ Failed: {exec_result['error']}")
    else:
        st.button("🔄 Run Lab Result Sync", type="primary", disabled=True, key="lab_sync_btn_disabled")
        st.caption("⚠️ Configure database to enable")

with tab3:
    st.subheader("PMTCT Infant PCR Data Entry")
    st.markdown("Insert infant PCR records into the `pmtct_infant_pcr` table.")
    
    pmtct_mode = st.radio(
        "Entry Mode",
        ["📝 Single Record Form", "📊 Bulk Import from Excel"],
        horizontal=True
    )
    
    if pmtct_mode == "📝 Single Record Form":
        with st.form("pmtct_form"):
            st.markdown("### Patient Information")
            col1, col2 = st.columns(2)
            
            with col1:
                infant_hospital_number = st.text_input(
                    "Infant Hospital Number *",
                    placeholder="Enter hospital number"
                )
                anc_number = st.text_input(
                    "ANC Number",
                    placeholder="Enter ANC number"
                )
                age_at_test_label = st.selectbox(
                    "Age at Test *",
                    options=[""] + list(AGE_AT_TEST_OPTIONS.keys()),
                    index=0
                )
            
            with col2:
                visit_date = st.date_input(
                    "Visit Date *",
                    value=date.today()
                )
                test_type_label = st.selectbox(
                    "Test Type *",
                    options=[""] + list(TEST_TYPE_OPTIONS.keys()),
                    index=0
                )
                results = st.selectbox(
                    "Results *",
                    options=["", "Positive", "Negative", "Indeterminate", "Pending"],
                    index=0
                )
            
            st.markdown("### Sample Dates")
            col1, col2 = st.columns(2)
            
            with col1:
                date_sample_collected_str = st.text_input(
                    "Date Sample Collected (YYYY-MM-DD)",
                    placeholder="Leave blank if not applicable"
                )
                date_sample_sent_str = st.text_input(
                    "Date Sample Sent (YYYY-MM-DD)",
                    placeholder="Leave blank if not applicable"
                )
            
            with col2:
                date_result_received_facility_str = st.text_input(
                    "Date Result Received at Facility (YYYY-MM-DD)",
                    placeholder="Leave blank if not applicable"
                )
                date_result_received_caregiver_str = st.text_input(
                    "Date Result Received by Caregiver (YYYY-MM-DD)",
                    placeholder="Leave blank if not applicable"
                )
            
            st.markdown("### Identifiers")
            unique_uuid = st.text_input(
                "Unique UUID (optional)",
                placeholder="Leave blank to auto-generate"
            )
            
            submitted = st.form_submit_button("💾 Save PMTCT Record", type="primary", disabled=not db_configured)
            
            if not db_configured:
                st.caption("⚠️ Configure database to enable")
            
            if submitted and db_configured:
                if not infant_hospital_number:
                    st.error("❌ Infant Hospital Number is required")
                elif not test_type_label:
                    st.error("❌ Test Type is required")
                elif not age_at_test_label:
                    st.error("❌ Age at Test is required")
                elif not results:
                    st.error("❌ Results is required")
                else:
                    test_type_value = TEST_TYPE_OPTIONS.get(test_type_label)
                    age_at_test_value = AGE_AT_TEST_OPTIONS.get(age_at_test_label)
                    
                    record_data = {
                        'visit_date': visit_date,
                        'infant_hospital_number': infant_hospital_number,
                        'anc_number': anc_number or None,
                        'age_at_test': age_at_test_value,
                        'test_type': test_type_value,
                        'date_sample_collected': parse_date_value(date_sample_collected_str),
                        'date_sample_sent': parse_date_value(date_sample_sent_str),
                        'date_result_received_at_facility': parse_date_value(date_result_received_facility_str),
                        'date_result_received_by_caregiver': parse_date_value(date_result_received_caregiver_str),
                        'results': results,
                        'unique_uuid': unique_uuid or None
                    }
                    
                    with st.spinner("Saving record..."):
                        exec_result = insert_pmtct_record(record_data)
                    
                    if exec_result['success']:
                        st.success(f"✅ Record saved successfully!")
                        st.info(f"Generated UUID: `{exec_result['uuid']}`")
                        st.balloons()
                    else:
                        st.error(f"❌ Failed: {exec_result['error']}")
    
    else:
        st.markdown("### Bulk Import from Excel")
        st.info("""
        **Required columns in Excel file:**
        - `infant_hospital_number` (required)
        - `visit_date` (required, format: YYYY-MM-DD)
        - `test_type` (required: First PCR or Second PCR)
        - `age_at_test` (required: Less than 72hours, Less than 2 months, 2 -12 months, Greater than 12 months)
        - `results` (required)
        
        **Optional columns:**
        - `anc_number`, `date_sample_collected`, `date_sample_sent`
        - `date_result_received_at_facility`, `date_result_received_by_caregiver`, `unique_uuid`
        """)
        
        pmtct_file = st.file_uploader(
            "Upload Excel file with PMTCT data",
            type=['xlsx'],
            key="pmtct_bulk_upload"
        )
        
        if pmtct_file is not None:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
                tmp_file.write(pmtct_file.getvalue())
                tmp_file_path = tmp_file.name
            
            result = read_excel_file(tmp_file_path)
            os.unlink(tmp_file_path)
            
            if result['success']:
                df = result['dataframe']
                st.success(f"✓ File uploaded: {pmtct_file.name}")
                st.metric("Records Found", result['row_count'])
                
                required_cols = ['infant_hospital_number', 'visit_date', 'test_type', 'age_at_test', 'results']
                missing_cols = [col for col in required_cols if col not in df.columns]
                
                if missing_cols:
                    st.error(f"❌ Missing required columns: {', '.join(missing_cols)}")
                    st.info(f"Available columns: {', '.join(result['columns'])}")
                else:
                    st.markdown("**Preview (first 5 rows):**")
                    st.dataframe(df.head(), use_container_width=True)
                    
                    if db_configured:
                        if st.button("📥 Import All Records", type="primary", key="pmtct_bulk_btn"):
                            records = []
                            errors = []
                            
                            for idx, row in df.iterrows():
                                row_errors = []
                                hospital_num = normalize_string(row.get('infant_hospital_number'))
                                visit_dt = parse_date_value(row.get('visit_date'))
                                
                                test_t, test_err = validate_test_type(row.get('test_type'))
                                age_val, age_err = validate_age_at_test(row.get('age_at_test'))
                                result_val, result_err = validate_results(row.get('results'))
                                
                                if not hospital_num:
                                    row_errors.append("Missing infant_hospital_number")
                                if test_err:
                                    row_errors.append(test_err)
                                if age_err:
                                    row_errors.append(age_err)
                                if result_err:
                                    row_errors.append(result_err)
                                if not visit_dt:
                                    row_errors.append("Invalid or missing visit_date")
                                
                                if row_errors:
                                    errors.append(f"Row {idx+2}: {'; '.join(row_errors)}")
                                    continue
                                
                                record = {
                                    'visit_date': visit_dt,
                                    'infant_hospital_number': hospital_num,
                                    'anc_number': normalize_string(row.get('anc_number')),
                                    'age_at_test': age_val,
                                    'test_type': test_t,
                                    'date_sample_collected': parse_date_value(row.get('date_sample_collected')),
                                    'date_sample_sent': parse_date_value(row.get('date_sample_sent')),
                                    'date_result_received_at_facility': parse_date_value(row.get('date_result_received_at_facility')),
                                    'date_result_received_by_caregiver': parse_date_value(row.get('date_result_received_by_caregiver')),
                                    'results': result_val,
                                    'unique_uuid': normalize_string(row.get('unique_uuid'))
                                }
                                records.append(record)
                            
                            if errors:
                                st.warning(f"⚠️ {len(errors)} rows have validation errors and will be skipped:")
                                with st.expander("View errors"):
                                    for err in errors[:20]:
                                        st.text(err)
                                    if len(errors) > 20:
                                        st.text(f"... and {len(errors) - 20} more")
                            
                            if records:
                                with st.spinner(f"Importing {len(records)} valid records..."):
                                    exec_result = insert_pmtct_batch(records)
                                
                                if exec_result['success']:
                                    st.success(f"✅ Successfully imported {exec_result['insert_count']} records!")
                                    st.balloons()
                                else:
                                    st.error(f"❌ Failed: {exec_result['error']}")
                            else:
                                st.error("❌ No valid records to import after validation")
                    else:
                        st.button("📥 Import All Records", type="primary", disabled=True, key="pmtct_bulk_btn_disabled")
                        st.caption("⚠️ Configure database to enable")
            else:
                st.error(f"❌ {result['error']}")
        else:
            st.info("👆 Upload an Excel file to begin bulk import")

st.markdown("---")
st.markdown("### 💡 Tips")
with st.expander("Database Requirements"):
    st.markdown("""
    **Required PostgreSQL Extension:**
    ```sql
    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
    ```
    
    **Tables used by this application:**
    - `patient_person` - Client verification
    - `hiv_observation` - Client verification
    - `hiv_status_tracker` - Client verification
    - `lims_result` - Lab result sync
    - `laboratory_result` - Lab result sync
    - `pmtct_infant_pcr` - PMTCT data entry
    """)
