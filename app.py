import streamlit as st
import tempfile
import os
from hiv_service import read_uuids_from_excel, execute_hiv_query, validate_db_credentials

st.set_page_config(
    page_title="HIV Observation Data Import",
    page_icon="🏥",
    layout="wide"
)

st.title("🏥 HIV Observation Data Import")
st.markdown("Import client verification records into the LAMISPLUS database")

st.markdown("---")

credential_check = validate_db_credentials()
if not credential_check['success']:
    st.error("⚠️ Database Configuration Required")
    st.warning(credential_check['error'])
    st.info("""
    **Setup Instructions:**
    1. Create a `.env` file in your project directory
    2. Add your database credentials:
       ```
       DB_HOST=your_host
       DB_PORT=5432
       DB_NAME=LAMISPLUS
       DB_USER=your_username
       DB_PASSWORD=your_password
       ```
    3. Restart the application
    """)
    st.stop()

st.success("✓ Database credentials configured")

st.markdown("---")

st.subheader("📂 Step 1: Upload Excel File")
st.markdown("Upload an Excel file containing a **`person_uuid`** column with the UUIDs to process.")

uploaded_file = st.file_uploader(
    "Choose an Excel file (.xlsx)",
    type=['xlsx'],
    help="The file must contain a column named 'person_uuid'"
)

if uploaded_file is not None:
    with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        tmp_file_path = tmp_file.name
    
    st.success(f"✓ File uploaded: {uploaded_file.name}")
    
    with st.spinner("Reading Excel file..."):
        result = read_uuids_from_excel(tmp_file_path)
    
    os.unlink(tmp_file_path)
    
    if result['success']:
        st.markdown("---")
        st.subheader("📋 Step 2: Review UUIDs")
        
        col1, col2 = st.columns([1, 3])
        with col1:
            st.metric("Total UUIDs Found", result['count'])
        
        with col2:
            with st.expander("View all UUIDs", expanded=False):
                for idx, uuid in enumerate(result['uuids'], 1):
                    st.code(f"{idx}. {uuid}", language=None)
        
        st.markdown("---")
        st.subheader("🚀 Step 3: Execute Database Operations")
        
        st.info("""
        **This will perform the following operations:**
        - ✓ Insert client verification records into `hiv_observation` table
        - ✓ Update incorrect status dates in `hiv_status_tracker` table
        - ✓ All operations are executed within a transaction (automatic rollback on errors)
        """)
        
        col1, col2, col3 = st.columns([1, 1, 2])
        
        with col1:
            execute_button = st.button(
                "Execute Query",
                type="primary",
                use_container_width=True,
                disabled=result['count'] == 0
            )
        
        if execute_button:
            with st.spinner("Executing database operations..."):
                exec_result = execute_hiv_query(result['uuids'])
            
            st.markdown("---")
            st.subheader("📊 Results")
            
            if exec_result['success']:
                st.success("✅ Transaction completed successfully!")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric(
                        "Records Inserted",
                        exec_result['insert_count'],
                        delta=None,
                        help="Number of verification records inserted into hiv_observation"
                    )
                with col2:
                    st.metric(
                        "Records Updated",
                        exec_result['update_count'],
                        delta=None,
                        help="Number of status dates corrected in hiv_status_tracker"
                    )
                
                st.balloons()
            else:
                st.error("❌ Operation Failed")
                st.error(exec_result['error'])
                if exec_result.get('rolled_back'):
                    st.warning("⚠️ Transaction was rolled back. No changes were made to the database.")
    else:
        st.error("❌ Error Reading Excel File")
        st.error(result['error'])
        if result.get('available_columns'):
            st.warning(f"Available columns in the file: {', '.join(result['available_columns'])}")
            st.info("Please ensure your Excel file has a column named **`person_uuid`**")

else:
    st.info("👆 Please upload an Excel file to begin")

st.markdown("---")
st.markdown("### 💡 Tips")
with st.expander("File Format Requirements"):
    st.markdown("""
    Your Excel file should have the following structure:
    
    | person_uuid |
    |-------------|
    | 080e68d8-7be2-6141-8959-9f6951704ad0 |
    | 0f4a1c07-dd74-4d08-bba6-32595f11d354 |
    | 1063fa10-82fe-4e1b-8890-244da2fee1b9 |
    
    - Column name must be exactly **`person_uuid`**
    - UUIDs should be in standard UUID format
    - Empty rows will be automatically skipped
    - Duplicate UUIDs will be processed only once
    """)

with st.expander("Database Requirements"):
    st.markdown("""
    **Required PostgreSQL Extension:**
    ```sql
    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
    ```
    
    **Required Tables:**
    - `patient_person`
    - `hiv_observation`
    - `hiv_status_tracker`
    """)
