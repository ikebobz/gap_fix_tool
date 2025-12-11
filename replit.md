# LAMISPLUS Data Tools

## Overview
A multi-purpose web application for importing and syncing data in the LAMISPLUS PostgreSQL database. Provides both web UI (Streamlit) and command-line interfaces for different data operations.

## Current State
The project is complete with 4 use cases:
- ✓ Client Verification Import - Upload Excel with UUIDs, insert verification records
- ✓ Fix Lab Result Round Off Error - Sync test results from lims_result to laboratory_result
- ✓ Fix EAC - Archive EAC records with no associated sessions
- ✓ PMTCT Infant PCR - Single record form entry or bulk Excel import

## Recent Changes
**2025-12-11**: Multi-use case application
- Rebuilt app with tabbed interface for 3 use cases
- Refactored services into modular structure (db.py, excel.py, verification.py, lab_results.py, pmtct.py)
- Added Lab Result Sync with optional UUID filtering from Excel
- Added PMTCT Infant PCR with form entry and bulk import
- Implemented proper date parsing (multiple formats + Excel serial numbers)
- Added row-level validation with error reporting for bulk imports
- Preview mode gating for all action buttons

**2025-11-20**: Initial project setup
- Created Streamlit web interface
- Secure parameterized SQL queries
- Transaction safety with rollback

## Project Architecture

### Files
```
.
├── app.py                      # Streamlit web interface (4 tabs)
├── execute_hiv_query.py        # CLI for verification import
├── hiv_service.py              # Backward compatibility wrapper
├── services/
│   ├── __init__.py             # Service exports
│   ├── db.py                   # Database connection utilities
│   ├── excel.py                # Excel file reading utilities
│   ├── verification.py         # Client verification operations
│   ├── lab_results.py          # Lab result sync operations
│   ├── eac.py                  # EAC fix operations
│   └── pmtct.py                # PMTCT infant PCR operations
├── person_uuids_sample.xlsx    # Sample data file
├── .env.example                # Database configuration template
└── README.md                   # User documentation
```

### Use Cases

**1. Client Verification Import**
- Upload Excel with `person_uuid` column
- Inserts verification records into `hiv_observation`
- Fixes date errors in `hiv_status_tracker` (0209 → 2009)

**2. Fix Lab Result Round Off Error**
- Syncs `test_result` to `result_reported` in `laboratory_result`
- Only processes numeric results matching `\d+\.\d+`
- Optional UUID filter from Excel upload

**3. Fix EAC**
- Archives EAC records with no associated sessions
- Sets `archived = 5` for orphaned `hiv_eac` records
- Optional UUID filter from Excel upload

**4. PMTCT Infant PCR**
- Single record form entry with validation
- Bulk import from Excel with column mapping
- Proper date parsing (multiple formats)
- Row-level validation with error reporting

### Database Operations
All operations use parameterized queries to prevent SQL injection:
- Verification: `uuid = ANY(%s)`
- Lab Sync: Full table update or filtered by UUID list
- PMTCT: Individual INSERT statements with proper type conversion

### Security Features
- Parameterized SQL queries throughout
- Environment-based credential management
- Transaction rollback on errors
- Preview mode when database not configured
- No credential exposure in UI

### Dependencies
- streamlit: Web interface framework
- pandas & openpyxl: Excel file processing
- psycopg2-binary: PostgreSQL database connectivity
- python-dotenv: Environment variable management

## Usage Instructions

### Web Interface
1. Open the Preview panel in Replit
2. Configure database in `.env` file (or use Preview Mode)
3. Select appropriate tab for your use case
4. Upload Excel file and/or fill form
5. Click action button to execute

### Command-Line Interface
```bash
python execute_hiv_query.py [excel_file_path]
```

## Database Requirements
- PostgreSQL with LAMISPLUS database
- Extension: `uuid-ossp` (for uuid_generate_v4)
- Tables: `patient_person`, `hiv_observation`, `hiv_status_tracker`, `lims_result`, `laboratory_result`, `pmtct_infant_pcr`

## User Preferences
- Prefers browser-based UI for ease of use
- Multi-use case interface with tabs
- Clear validation and error messages
