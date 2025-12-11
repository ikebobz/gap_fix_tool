import streamlit as st
import tempfile
import os
from datetime import date
from services import (
    validate_db_credentials,
    read_uuids_from_excel,
    execute_verification_query,
    execute_lab_sync,
    insert_pmtct_record
)

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

tab1, tab2, tab3 = st.tabs([
    "📋 Client Verification Import",
    "🔬 Lab Result Sync", 
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

with tab2:
    st.subheader("Lab Result Sync")
    st.markdown("Sync test results from `lims_result` to `laboratory_result` table.")
    
    st.info("""
    **What this does:**
    - Finds records where `test_result` differs from `result_reported`
    - Updates `laboratory_result.result_reported` with the correct `test_result` value
    - Only processes numeric results (matching pattern `\\d+\\.\\d+`)
    """)
    
    st.code("""
    UPDATE laboratory_result r 
    SET result_reported = test_result 
    FROM (
        SELECT test_result, result_reported, lr.uuid 
        FROM lims_result lmr 
        INNER JOIN laboratory_result lr ON lr.test_id = lmr.test_id 
        WHERE test_result ~ '\\d+\\.\\d+' AND test_result <> result_reported
    ) s
    WHERE r.uuid = s.uuid
    """, language="sql")
    
    if db_configured:
        if st.button("🔄 Run Lab Result Sync", type="primary", key="lab_sync_btn"):
            with st.spinner("Syncing lab results..."):
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
            age_at_test = st.text_input(
                "Age at Test",
                placeholder="e.g., 6 weeks, 3 months"
            )
        
        with col2:
            visit_date = st.date_input(
                "Visit Date *",
                value=date.today()
            )
            test_type = st.selectbox(
                "Test Type *",
                options=["", "PCR", "Rapid Test", "Other"],
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
            date_sample_collected = st.date_input(
                "Date Sample Collected",
                value=None
            )
            date_sample_sent = st.date_input(
                "Date Sample Sent",
                value=None
            )
        
        with col2:
            date_result_received_at_facility = st.date_input(
                "Date Result Received at Facility",
                value=None
            )
            date_result_received_by_caregiver = st.date_input(
                "Date Result Received by Caregiver",
                value=None
            )
        
        st.markdown("### Identifiers")
        unique_uuid = st.text_input(
            "Unique UUID (optional)",
            placeholder="Leave blank to auto-generate"
        )
        
        submitted = st.form_submit_button("💾 Save PMTCT Record", type="primary")
        
        if submitted:
            if not infant_hospital_number:
                st.error("❌ Infant Hospital Number is required")
            elif not test_type:
                st.error("❌ Test Type is required")
            elif not results:
                st.error("❌ Results is required")
            elif not db_configured:
                st.error("❌ Database not configured")
            else:
                record_data = {
                    'visit_date': visit_date,
                    'infant_hospital_number': infant_hospital_number,
                    'anc_number': anc_number or None,
                    'age_at_test': age_at_test or None,
                    'test_type': test_type,
                    'date_sample_collected': date_sample_collected,
                    'date_sample_sent': date_sample_sent,
                    'date_result_received_at_facility': date_result_received_at_facility,
                    'date_result_received_by_caregiver': date_result_received_by_caregiver,
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
    
    st.markdown("---")
    st.markdown("### Bulk Import from Excel")
    
    pmtct_file = st.file_uploader(
        "Upload Excel file with PMTCT data",
        type=['xlsx'],
        key="pmtct_upload",
        help="Excel file should have columns matching the form fields above"
    )
    
    if pmtct_file is not None:
        st.info("📋 Bulk import feature: Upload an Excel file with columns matching the form fields to import multiple records at once.")
        st.warning("⚠️ Bulk import requires columns: infant_hospital_number, visit_date, test_type, results (at minimum)")

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
