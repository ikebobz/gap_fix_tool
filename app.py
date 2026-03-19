import streamlit as st
import tempfile
import os
import pandas as pd
from datetime import date, datetime, timedelta
import requests
import zipfile
import glob
import json
from dotenv import dotenv_values
from psycopg2.extras import RealDictCursor
from services.db import get_db_connection
from services import (
    validate_db_credentials,
    read_uuids_from_excel,
    read_excel_file,
    execute_verification_query,
    execute_lab_sync,
    insert_pmtct_record,
    insert_pmtct_batch,
    execute_eac_fix,
    execute_testing_setting_update,
    execute_hide_hts_entries,
    execute_update_test_result,
    execute_recall_sample,
    execute_custom_query,
    execute_custom_query_with_uuids,
    execute_dml_with_uuids,
    execute_hiv_enrollment_update,
    execute_tb_completion_update
)
from io import BytesIO
from services.lab_results import execute_lab_sync_filtered

st.set_page_config(
    page_title="LAMISPLUS Gap Resolution Tool",
    page_icon="attached_assets/logo_1768081198791.png",
    layout="wide"
)

st.title("🏥 LAMISPLUS Gap Resolution Tool")
st.markdown("Multi-purpose data quality resolution tool for LAMISPLUS")

def build_environment_snapshot():
    env_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    file_values = dotenv_values(env_file_path)
    env_rows = []
    for key, value in sorted(file_values.items(), key=lambda item: item[0].lower()):
        env_rows.append({
            "Variable": key,
            "Value": value if value not in (None, "") else "<empty>"
        })
    return pd.DataFrame(env_rows), env_file_path

env_df, env_file = build_environment_snapshot()

if "startup_env_logged" not in st.session_state:
    print(f"\n=== .env Variables (Startup Snapshot) [{env_file}] ===")
    for _, row in env_df.iterrows():
        print(f"{row['Variable']}: {row['Value']}")
    print("=== End .env Variables ===\n")
    st.session_state["startup_env_logged"] = True

with st.expander("🧾 Environment Variables (Startup)", expanded=True):
    st.markdown(f"Human-readable list of variables defined in {env_file}.")
    st.dataframe(env_df, use_container_width=True, height=360)
    st.caption(f"Total variables from .env: {len(env_df)}")

configured_port = os.getenv("APP_PORT") or os.getenv("STREAMLIT_SERVER_PORT") or "8501"
current_port = st.get_option("server.port")
st.info(f"Configured app port (.env): {configured_port} | Running port: {current_port}")

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
        APP_PORT=8502
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

RESULTS_OPTIONS = {
    'Positive': 'INFANT_PCR_RESULT_POSITIVE',
    'Negative': 'INFANT_PCR_RESULT_NEGATIVE'
}
RESULTS_VALUES = set(RESULTS_OPTIONS.values())

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
    if normalized in RESULTS_VALUES:
        return normalized, None
    for label, val in RESULTS_OPTIONS.items():
        if normalized.lower() == label.lower():
            return val, None
    return None, f"Invalid results '{normalized}' (allowed: Positive, Negative)"

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

tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "📋 Client Verification Import",
    "🔬 Lab Related Issues",
    "🔧 Fix EAC",
    "👶 PMTCT Issues",
    "📝 Custom Query",
    "🩸 HIV Enrollment",
    "🦠 TB Related Issues",
    "📋 NDR issues"
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
    lab_page = st.radio(
        "Select Function",
        ["🔄 Fix Lab Result Round Off Error", "🗑️ Recall samples sent to wrong PCR"],
        horizontal=True,
        key="lab_page_selector"
    )
    
    if lab_page == "🔄 Fix Lab Result Round Off Error":
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
    
    else:
        st.subheader("Recall Samples Sent to Wrong PCR")
        st.markdown("Delete sample and manifest records for incorrectly routed samples.")
        
        st.info("""
        **What this does:**
        - Deletes all samples linked to the specified manifest ID
        - Deletes the manifest record itself
        - Use this to recall samples that were sent to the wrong PCR lab
        """)
        
        with st.expander("View SQL Queries", expanded=False):
            st.code("""
-- Delete samples linked to manifest
DELETE FROM lims_sample 
WHERE manifest_record_id IN (
    SELECT id FROM lims_manifest WHERE manifest_id = [Sample ID]
);

-- Delete the manifest
DELETE FROM lims_manifest 
WHERE manifest_id = [Sample ID];
            """, language="sql")
        
        sample_id = st.text_input(
            "Sample ID *",
            placeholder="Enter manifest_id",
            key="recall_sample_id"
        )
        
        if db_configured:
            if st.button("🗑️ Recall", type="primary", key="recall_btn"):
                if not sample_id:
                    st.error("❌ Sample ID is required")
                else:
                    with st.spinner("Recalling samples..."):
                        exec_result = execute_recall_sample(sample_id)
                    
                    if exec_result['success']:
                        st.success("✅ Recall completed successfully!")
                        col1, col2 = st.columns(2)
                        col1.metric("Samples Deleted", exec_result['samples_deleted'])
                        col2.metric("Manifests Deleted", exec_result['manifests_deleted'])
                        if exec_result['samples_deleted'] > 0 or exec_result['manifests_deleted'] > 0:
                            st.balloons()
                    else:
                        st.error(f"❌ Failed: {exec_result['error']}")
        else:
            st.button("🗑️ Recall", type="primary", disabled=True, key="recall_btn_disabled")
            st.caption("⚠️ Configure database to enable")

with tab3:
    st.subheader("Fix EAC Records")
    st.markdown("Archive EAC records that have no associated sessions in the `hiv_eac` table.")
    
    st.info("""
    **What this does:**
    - Filters EAC records by `person_uuid` from uploaded Excel file
    - Only updates records with no associated sessions in `hiv_eac_session`
    - Sets `archived = 5` for matching records
    """)
    
    with st.expander("View SQL Query", expanded=False):
        st.code("""
UPDATE hiv_eac eac 
SET archived = 5 
WHERE person_uuid IN (... values from Excel ...)
AND NOT EXISTS (
    SELECT * FROM hiv_eac_session hes 
    WHERE eac_id = eac.uuid
)
        """, language="sql")
    
    eac_file = st.file_uploader(
        "Upload Excel file with person_uuid column",
        type=['xlsx'],
        key="eac_upload",
        help="Required: Excel file must contain a column named 'person_uuid'"
    )
    
    eac_uuids = None
    if eac_file is not None:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
            tmp_file.write(eac_file.getvalue())
            tmp_file_path = tmp_file.name
        
        result = read_uuids_from_excel(tmp_file_path, column_name='person_uuid')
        os.unlink(tmp_file_path)
        
        if result['success']:
            eac_uuids = result['uuids']
            st.success(f"✓ File uploaded: {eac_file.name}")
            st.metric("Person UUIDs Found", result['count'])
            
            with st.expander("View UUIDs", expanded=False):
                for idx, uuid in enumerate(eac_uuids[:50], 1):
                    st.code(f"{idx}. {uuid}", language=None)
                if result['count'] > 50:
                    st.info(f"... and {result['count'] - 50} more")
            
            if db_configured:
                if st.button("🔧 Run EAC Fix", type="primary", key="eac_fix_btn"):
                    with st.spinner("Fixing EAC records..."):
                        exec_result = execute_eac_fix(eac_uuids)
                    
                    if exec_result['success']:
                        st.success("✅ EAC fix completed successfully!")
                        st.metric("Records Updated", exec_result['update_count'])
                        if exec_result['update_count'] > 0:
                            st.balloons()
                    else:
                        st.error(f"❌ Failed: {exec_result['error']}")
            else:
                st.button("🔧 Run EAC Fix", type="primary", disabled=True, key="eac_fix_btn_disabled")
                st.caption("⚠️ Configure database to enable")
        else:
            st.error(f"❌ {result['error']}")
            if result.get('available_columns'):
                st.warning(f"Available columns: {', '.join(result['available_columns'])}")
    else:
        st.info("👆 Upload an Excel file with person_uuid column to begin")

with tab4:
    pmtct_page = st.radio(
        "Select Function",
        ["📝 Infant PCR Data Entry", "🔄 Update Testing Setting", "🙈 Hide HTS Entries", "🔬 Update Test Result"],
        horizontal=True,
        key="pmtct_page_selector"
    )
    
    if pmtct_page == "📝 Infant PCR Data Entry":
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
                    results_label = st.selectbox(
                        "Results *",
                        options=[""] + list(RESULTS_OPTIONS.keys()),
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
                    elif not results_label:
                        st.error("❌ Results is required")
                    else:
                        test_type_value = TEST_TYPE_OPTIONS.get(test_type_label)
                        age_at_test_value = AGE_AT_TEST_OPTIONS.get(age_at_test_label)
                        results_value = RESULTS_OPTIONS.get(results_label)
                        
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
                            'results': results_value,
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
    
    elif pmtct_page == "🔄 Update Testing Setting":
        st.subheader("Update Testing Setting")
        st.markdown("Update the testing setting for a patient in the `hts_risk_stratification` table.")
        
        st.info("""
        **What this does:**
        - Finds the risk stratification record for the given patient
        - Updates the `testing_setting` field with the new value
        """)
        
        with st.expander("View SQL Query", expanded=False):
            st.code("""
WITH x AS (
    SELECT hrs.testing_setting, hrs.uuid 
    FROM hts_risk_stratification hrs 
    INNER JOIN hts_client hc ON hc.risk_stratification_code = hrs.code
    WHERE hc.person_uuid = [Patient ID]
)
UPDATE hts_risk_stratification h 
SET testing_setting = [New Value]
FROM x 
WHERE h.uuid = x.uuid
            """, language="sql")
        
        patient_id = st.text_input(
            "Patient ID *",
            placeholder="Enter person_uuid",
            key="update_patient_id"
        )
        
        testing_setting_options = {
            "ANC": "FACILITY_HTS_TEST_SETTING_ANC",
            "Retesting": "FACILITY_HTS_TEST_SETTING_RETESTING",
            "L&D": "FACILITY_HTS_TEST_SETTING_L&D",
            "Post Natal Ward/Breastfeeding": "FACILITY_HTS_TEST_SETTING_POST_NATAL_WARD_BREASTFEEDING",
            "Ward/Inpatient": "FACILITY_HTS_TEST_SETTING_WARD_INPATIENT",
            "CT": "FACILITY_HTS_TEST_SETTING_CT",
            "TB": "FACILITY_HTS_TEST_SETTING_TB",
            "STI": "FACILITY_HTS_TEST_SETTING_STI",
            "SNS": "FACILITY_HTS_TEST_SETTING_SNS",
            "Index": "FACILITY_HTS_TEST_SETTING_INDEX",
            "Emergency": "FACILITY_HTS_TEST_SETTING_EMERGENCY",
            "Blood Bank": "FACILITY_HTS_TEST_SETTING_BLOOD_BANK",
            "Pediatric": "FACILITY_HTS_TEST_SETTING_PEDIATRIC",
            "Malnutrition": "FACILITY_HTS_TEST_SETTING_MALNUTRITION",
            "PrEP Testing": "FACILITY_HTS_TEST_SETTING_PREP_TESTING",
            "Spoke health facility": "FACILITY_HTS_TEST_SETTING_SPOKE_HEALTH_FACILITY",
            "Standalone HTS": "FACILITY_HTS_TEST_SETTING_STANDALONE_HTS",
            "Others (Specify)": "FACILITY_HTS_TEST_SETTING_OTHERS_(SPECIFY)",
            "Others": "FACILITY_HTS_TEST_SETTING_OTHERS",
            "FP": "FACILITY_HTS_TEST_SETTING_FP",
        }
        
        selected_label = st.selectbox(
            "New Value *",
            options=list(testing_setting_options.keys()),
            key="update_new_value"
        )
        new_value = testing_setting_options[selected_label]
        
        if db_configured:
            if st.button("🔄 Update Testing Setting", type="primary", key="pmtct_update_btn"):
                if not patient_id:
                    st.error("❌ Patient ID is required")
                else:
                    with st.spinner("Updating testing setting..."):
                        exec_result = execute_testing_setting_update(patient_id, new_value)
                    
                    if exec_result['success']:
                        if exec_result['update_count'] > 0:
                            st.success(f"✅ Successfully updated {exec_result['update_count']} record(s)!")
                            st.balloons()
                        else:
                            st.warning("⚠️ No records found for this Patient ID")
                    else:
                        st.error(f"❌ Failed: {exec_result['error']}")
        else:
            st.button("🔄 Update Testing Setting", type="primary", disabled=True, key="pmtct_update_btn_disabled")
            st.caption("⚠️ Configure database to enable")
    
    elif pmtct_page == "🙈 Hide HTS Entries":
        st.subheader("Hide HTS Entries")
        st.markdown("Archive HTS client records by setting `archived = 1`.")
        
        st.info("""
        **What this does:**
        - Reads person_uuid values from uploaded Excel file
        - Sets `archived = 1` for matching HTS client records
        """)
        
        with st.expander("View SQL Query", expanded=False):
            st.code("""
UPDATE hts_client 
SET archived = 1 
WHERE person_uuid IN (... values from Excel ...)
            """, language="sql")
        
        hide_hts_file = st.file_uploader(
            "Upload Excel file with person_uuid column",
            type=['xlsx'],
            key="hide_hts_upload",
            help="Excel file must contain a column named 'person_uuid'"
        )
        
        if hide_hts_file is not None:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
                tmp_file.write(hide_hts_file.getvalue())
                tmp_file_path = tmp_file.name
            
            result = read_uuids_from_excel(tmp_file_path, column_name='person_uuid')
            os.unlink(tmp_file_path)
            
            if result['success']:
                hts_uuids = result['uuids']
                st.success(f"✓ File uploaded: {hide_hts_file.name}")
                st.metric("Person UUIDs Found", result['count'])
                
                with st.expander("View UUIDs", expanded=False):
                    for idx, uuid in enumerate(hts_uuids[:50], 1):
                        st.code(f"{idx}. {uuid}", language=None)
                    if result['count'] > 50:
                        st.info(f"... and {result['count'] - 50} more")
                
                if db_configured:
                    if st.button("🙈 Hide HTS Entries", type="primary", key="hide_hts_btn"):
                        with st.spinner("Hiding HTS entries..."):
                            exec_result = execute_hide_hts_entries(hts_uuids)
                        
                        if exec_result['success']:
                            st.success(f"✅ Successfully archived {exec_result['update_count']} record(s)!")
                            if exec_result['update_count'] > 0:
                                st.balloons()
                        else:
                            st.error(f"❌ Failed: {exec_result['error']}")
                else:
                    st.button("🙈 Hide HTS Entries", type="primary", disabled=True, key="hide_hts_btn_disabled")
                    st.caption("⚠️ Configure database to enable")
            else:
                st.error(f"❌ {result['error']}")
                if result.get('available_columns'):
                    st.warning(f"Available columns: {', '.join(result['available_columns'])}")
        else:
            st.info("👆 Upload an Excel file with person_uuid column to begin")
    
    elif pmtct_page == "🔬 Update Test Result":
        st.subheader("Update Test Result")
        st.markdown("Update HIV test result to 'Negative' for HTS clients.")
        
        st.info("""
        **What this does:**
        - Reads person_uuid values from uploaded Excel file
        - Sets `hiv_test_result = 'Negative'` for matching HTS client records
        """)
        
        with st.expander("View SQL Query", expanded=False):
            st.code("""
UPDATE hts_client 
SET hiv_test_result = 'Negative' 
WHERE person_uuid IN (... values from Excel ...)
            """, language="sql")
        
        update_result_file = st.file_uploader(
            "Upload Excel file with person_uuid column",
            type=['xlsx'],
            key="update_result_upload",
            help="Excel file must contain a column named 'person_uuid'"
        )
        
        if update_result_file is not None:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
                tmp_file.write(update_result_file.getvalue())
                tmp_file_path = tmp_file.name
            
            result = read_uuids_from_excel(tmp_file_path, column_name='person_uuid')
            os.unlink(tmp_file_path)
            
            if result['success']:
                result_uuids = result['uuids']
                st.success(f"✓ File uploaded: {update_result_file.name}")
                st.metric("Person UUIDs Found", result['count'])
                
                with st.expander("View UUIDs", expanded=False):
                    for idx, uuid in enumerate(result_uuids[:50], 1):
                        st.code(f"{idx}. {uuid}", language=None)
                    if result['count'] > 50:
                        st.info(f"... and {result['count'] - 50} more")
                
                if db_configured:
                    if st.button("🔬 Update Test Result", type="primary", key="update_result_btn"):
                        with st.spinner("Updating test results..."):
                            exec_result = execute_update_test_result(result_uuids)
                        
                        if exec_result['success']:
                            st.success(f"✅ Successfully updated {exec_result['update_count']} record(s)!")
                            if exec_result['update_count'] > 0:
                                st.balloons()
                        else:
                            st.error(f"❌ Failed: {exec_result['error']}")
                else:
                    st.button("🔬 Update Test Result", type="primary", disabled=True, key="update_result_btn_disabled")
                    st.caption("⚠️ Configure database to enable")
            else:
                st.error(f"❌ {result['error']}")
                if result.get('available_columns'):
                    st.warning(f"Available columns: {', '.join(result['available_columns'])}")
        else:
            st.info("👆 Upload an Excel file with person_uuid column to begin")

with tab5:
    custom_query_page = st.radio(
        "Select Function",
        ["▶️ Execute Query", "📊 Generate Custom Report"],
        horizontal=True,
        key="custom_query_page_selector"
    )
    
    custom_query = st.text_area(
        "SQL Query",
        height=200,
        placeholder="Enter your SQL query here...\n\nFor Execute Query (DML), use %(uuids)s as placeholder for person_uuid values.\nExample: UPDATE patient_person SET status = 'active' WHERE uuid = ANY(%(uuids)s)",
        key="custom_query_input"
    )
    
    if custom_query_page == "▶️ Execute Query":
        st.subheader("Execute Query")
        st.markdown("Execute DML statements (INSERT, UPDATE, DELETE) filtered by person_uuid values.")
        
        st.info("""
        **How to use:**
        - Use `%(uuids)s` in your query as placeholder for person_uuid values
        - Example: `UPDATE patient_person SET status = 'active' WHERE uuid = ANY(%(uuids)s)`
        """)
        
        report_uuid_input = st.text_input(
            "Enter person_uuid (or upload Excel file below)",
            placeholder="Enter a single person_uuid",
            key="report_uuid_input"
        )
        
        report_file = st.file_uploader(
            "Or upload Excel file with person_uuid column",
            type=['xlsx'],
            key="report_upload",
            help="Excel file must contain a column named 'person_uuid'"
        )
        
        report_uuids = None
        if report_file is not None:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
                tmp_file.write(report_file.getvalue())
                tmp_file_path = tmp_file.name
            
            result = read_uuids_from_excel(tmp_file_path, column_name='person_uuid')
            os.unlink(tmp_file_path)
            
            if result['success']:
                report_uuids = result['uuids']
                st.success(f"✓ File uploaded: {report_file.name}")
                st.metric("Person UUIDs Found", result['count'])
            else:
                st.error(f"❌ {result['error']}")
                if result.get('available_columns'):
                    st.warning(f"Available columns: {', '.join(result['available_columns'])}")
        elif report_uuid_input.strip():
            report_uuids = [report_uuid_input.strip()]
            st.info(f"Using single UUID: {report_uuid_input.strip()}")
        
        if db_configured:
            if st.button("▶️ Run", type="primary", key="execute_query_btn"):
                query_upper = custom_query.strip().upper()
                is_dml = query_upper.startswith("INSERT") or query_upper.startswith("UPDATE") or query_upper.startswith("DELETE")
                
                if not custom_query.strip():
                    st.error("❌ Please enter a SQL query")
                elif not is_dml:
                    st.error("❌ Only DML statements (INSERT, UPDATE, DELETE) are allowed")
                elif not report_uuids:
                    st.error("❌ Please enter a person_uuid or upload an Excel file")
                elif "%(uuids)s" not in custom_query:
                    st.error("❌ Query must contain %(uuids)s placeholder for person_uuid values")
                else:
                    with st.spinner("Executing query..."):
                        exec_result = execute_dml_with_uuids(custom_query, report_uuids)
                    
                    if exec_result['success']:
                        st.success(f"✅ Query executed successfully! Rows affected: {exec_result['row_count']}")
                        if exec_result['row_count'] > 0:
                            st.balloons()
                    else:
                        st.error(f"❌ Failed: {exec_result['error']}")
        else:
            st.button("▶️ Run", type="primary", disabled=True, key="execute_query_btn_disabled")
            st.caption("⚠️ Configure database to enable")
    
    else:
        st.subheader("Generate Custom Report")
        st.markdown("Run a custom SQL query and download the results as an Excel file.")
        
        st.warning("**Note:** Only SELECT queries are supported. Modifying queries (INSERT, UPDATE, DELETE) are not allowed.")
        
        if db_configured:
            if st.button("📊 Generate Report", type="primary", key="generate_report_btn"):
                if not custom_query.strip():
                    st.error("❌ Please enter a SQL query")
                elif not custom_query.strip().upper().startswith("SELECT"):
                    st.error("❌ Only SELECT queries are allowed")
                else:
                    with st.spinner("Generating report..."):
                        exec_result = execute_custom_query(custom_query)
                    
                    if exec_result['success']:
                        st.success(f"✅ Report generated! Rows returned: {exec_result['row_count']}")
                        
                        if exec_result['row_count'] > 0:
                            st.dataframe(exec_result['data'], use_container_width=True)
                            
                            output = BytesIO()
                            exec_result['data'].to_excel(output, index=False, engine='openpyxl')
                            output.seek(0)
                            
                            st.download_button(
                                label="📥 Download as Excel",
                                data=output,
                                file_name="custom_report.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                key="download_report_results"
                            )
                        else:
                            st.info("Query returned no results")
                    else:
                        st.error(f"❌ Failed: {exec_result['error']}")
        else:
            st.button("📊 Generate Report", type="primary", disabled=True, key="generate_report_btn_disabled")
            st.caption("⚠️ Configure database to enable")

with tab6:
    hiv_enrollment_tab = st.tabs(["Upload OVC details"])
    
    with hiv_enrollment_tab[0]:
        st.subheader("Upload OVC Details")
        st.markdown("Bulk update OVC numbers from an Excel file.")
        
        st.info("""
        **Expected columns (in order):**
        - hospital_number
        - house_hold unique id
        - ovc unique_id
        
        **What this does:**
        - Updates hiv_enrollment table with house_hold_number and ovc_number for each unique_id
        """)
        
        ovc_file = st.file_uploader(
            "Upload Excel file with OVC details",
            type=['xlsx'],
            key="ovc_upload",
            help="Excel file must have columns: hospital_number, house_hold unique id, ovc unique_id"
        )
        
        if ovc_file is not None:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
                tmp_file.write(ovc_file.getvalue())
                tmp_file_path = tmp_file.name
            
            try:
                df = pd.read_excel(tmp_file_path)
                os.unlink(tmp_file_path)
                
                required_columns = ['hospital_number', 'house_hold unique id', 'ovc unique_id']
                if list(df.columns) == required_columns:
                    st.success(f"✓ File uploaded: {ovc_file.name}")
                    st.metric("Rows Found", len(df))
                    
                    with st.expander("Preview Data", expanded=False):
                        st.dataframe(df.head(10), use_container_width=True)
                        if len(df) > 10:
                            st.info(f"... and {len(df) - 10} more rows")
                    
                    updates = []
                    for _, row in df.iterrows():
                        unique_id = str(row['hospital_number']).strip()
                        house_hold_number = str(row['house_hold unique id']).strip()
                        ovc_number = str(row['ovc unique_id']).strip()
                        updates.append((house_hold_number, ovc_number, unique_id))
                    
                    st.info(f"Ready to update {len(updates)} records")
                    
                    if db_configured:
                        if st.button("🔄 Update HIV Enrollment", type="primary", key="hiv_enrollment_update_btn"):
                            with st.spinner("Updating hiv_enrollment records..."):
                                exec_result = execute_hiv_enrollment_update(updates)
                            
                            if exec_result['success']:
                                st.success("✅ HIV enrollment update completed successfully!")
                                st.metric("Records Updated", exec_result['row_count'])
                                if exec_result['row_count'] > 0:
                                    st.balloons()
                            else:
                                st.error(f"❌ Failed: {exec_result['error']}")
                    else:
                        st.button("🔄 Update HIV Enrollment", type="primary", disabled=True, key="hiv_enrollment_update_btn_disabled")
                        st.caption("⚠️ Configure database to enable")
                else:
                    st.error(f"❌ Invalid column structure. Expected: {', '.join(required_columns)}")
                    st.warning(f"Found columns: {', '.join(df.columns)}")
            except Exception as e:
                os.unlink(tmp_file_path)
                st.error(f"❌ Error reading file: {str(e)}")
        else:
            st.info("👆 Upload an Excel file to begin")

with tab7:
    tb_tab = st.tabs(["Upload TPT Completion Data"])

    with tb_tab[0]:
        st.subheader("Upload TPT Completion Data")
        st.markdown("Bulk set TPT completion dates for given clients")

        st.info("""
        **Expected columns (in order):**
        - hospital_number
        - completion_date

        **What this does:**
        - Sets TPT completion dates for given clients
        """)

        tb_file = st.file_uploader(
            "Upload Excel file with TB completion data",
            type=['xlsx'],
            key="tb_completion_upload",
            help="Excel file must have columns: hospital_number, completion_date"
        )

        if tb_file is not None:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
                tmp_file.write(tb_file.getvalue())
                tmp_file_path = tmp_file.name

            try:
                df = pd.read_excel(tmp_file_path)
                os.unlink(tmp_file_path)

                required_columns = ['hospital_number', 'completion_date']
                if list(df.columns) == required_columns:
                    st.success(f"✓ File uploaded: {tb_file.name}")
                    st.metric("Rows Found", len(df))

                    with st.expander("Preview Data", expanded=False):
                        st.dataframe(df.head(10), use_container_width=True)
                        if len(df) > 10:
                            st.info(f"... and {len(df) - 10} more rows")

                    updates = []
                    for _, row in df.iterrows():
                        hosp_num = str(row['hospital_number']).strip()
                        completion_date = str(row['completion_date']).strip()
                        updates.append((hosp_num, completion_date))

                    st.info(f"Ready to update {len(updates)} records")

                    if db_configured:
                        if st.button("🔄 Update TB completion", type="primary", key="tb_completion_update_btn"):
                            with st.spinner("Updating TB completion records..."):
                                exec_result = execute_tb_completion_update(updates)

                            if exec_result['success']:
                                st.success("✅ TB completion update completed successfully!")
                                st.metric("Records Updated", exec_result['row_count'])
                                if exec_result['row_count'] > 0:
                                    st.balloons()
                            else:
                                st.error(f"❌ Failed: {exec_result['error']}")
                    else:
                        st.button("🔄 Update TB completion", type="primary", disabled=True, key="tb_completion_update_btn_disabled")
                        st.caption("⚠️ Configure database to enable")
                else:
                    st.error(f"❌ Invalid column structure. Expected: {', '.join(required_columns)}")
                    st.warning(f"Found columns: {', '.join(df.columns)}")
            except Exception as e:
                os.unlink(tmp_file_path)
                st.error(f"❌ Error reading file: {str(e)}")
        else:
            st.info("👆 Upload an Excel file to begin")

with tab8:
    st.subheader("NDR Issues")
    ndr_sub_tab = st.tabs(["Target extraction for specific clients"])[0]

    with ndr_sub_tab:
        st.markdown("Upload Excel with person_uuid column to extract NDR data for specified patients.")

        uploaded_file = st.file_uploader(
            "Upload Excel file",
            type=['xlsx'],
            key="ndr_upload"
        )

        if uploaded_file is not None:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                tmp_file_path = tmp_file.name

            result = read_uuids_from_excel(tmp_file_path)
            os.unlink(tmp_file_path)

            if result['success']:
                patient_ids = ','.join(result['uuids'])
                
                # Get facility
                try:
                    with get_db_connection() as conn:
                        cursor = conn.cursor(cursor_factory=RealDictCursor)
                        cursor.execute("SELECT current_organisation_unit_id FROM base_application_user LIMIT 1")
                        row = cursor.fetchone()
                        facility = row['current_organisation_unit_id']
                except Exception as e:
                    st.error(f"Database error: {e}")
                    st.stop()

                # Build api_url
                initial_value = st.selectbox(
                    "Initial extraction?",
                    options=["false", "true"],
                    index=0,
                    key="ndr_initial_param",
                    help="Set to 'true' for an initial extraction, 'false' for incremental."
                )
                api_url = f"http://localhost:9120/api/v1/ndr/generate/patients?facilityIds={facility}&initial={initial_value}&patientIds={patient_ids}"

                st.info(f"**API URL:** {api_url}")
                st.warning("Please confirm the API URL before proceeding.")

                if st.button("Confirm and Execute Extraction", type="primary"):
                    progress = st.progress(0)
                    status = st.empty()

                    with st.spinner("Executing extraction..."):
                        try:
                            progress.progress(5)
                            status.info("Authenticating...")

                            # Auth
                            auth_url = os.getenv("AUTH_URL")
                            payload = {
                                "username": os.getenv("USER"),
                                "password": os.getenv("PASSWORD")
                            }
                            if not payload["username"] or not payload["password"]:
                                st.error("USERNAME or PASSWORD not found in environment variables")
                                st.stop()
                            response = requests.post(auth_url, json=payload)
                            if response.status_code != 200:
                                st.error(f"Authentication failed: {response.status_code} - {response.text}")
                                st.stop()
                            token = response.json().get('id_token')
                            progress.progress(25)

                            # API call
                            status.info("Calling NDR extraction API...")
                            headers = {"Authorization": f"Bearer {token}"}
                            response = requests.get(api_url, headers=headers)
                            if response.status_code != 200:
                                st.error(f"API request failed: {response.status_code} - {response.text}")
                                st.stop()
                            progress.progress(60)

                            # File compression
                            status.info("Packaging XML files into ZIP...")
                            source_dir = os.path.join(os.getenv('NDR_TEMP_DIR', 'runtime/ndr/transfer/temp'), f"runtime/ndr/transfer/temp/{facility}/")
                            xml_files = glob.glob(os.path.join(source_dir, "*.xml"))
                            progress.progress(80)

                            if xml_files:
                                destination_zip = os.path.join(os.path.expanduser("~"), "Downloads", "treatmentxml.zip")
                                with zipfile.ZipFile(destination_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
                                    for file in xml_files:
                                        zipf.write(file, os.path.basename(file))
                                progress.progress(100)
                                st.success("NDR files are ready for upload.")
                                # Provide download button
                                with open(destination_zip, "rb") as f:
                                    st.download_button(
                                        label="Download ZIP",
                                        data=f,
                                        file_name="treatmentxml.zip",
                                        mime="application/zip"
                                    )
                            else:
                                progress.progress(100)
                                st.warning("No valid refills between period")
                        except Exception as e:
                            progress.progress(100)
                            st.error(f"Error during extraction: {e}")
            else:
                st.error(result['error'])
        else:
            st.info("👆 Upload an Excel file to begin")

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
