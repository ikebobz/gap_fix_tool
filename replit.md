# HIV Observation Data Import Project

## Overview
This project provides both a web interface and command-line script to batch import HIV client verification records into the LAMISPLUS PostgreSQL database. It reads person UUIDs from Excel files and executes parameterized SQL queries to insert verification data and correct historical date errors.

## Current State
The project is complete with both web and CLI interfaces:
- ✓ Streamlit web UI with drag-and-drop file upload
- ✓ Command-line interface for automation
- ✓ Shared service module with secure parameterized queries
- ✓ Excel file reading with validation
- ✓ Database connection management with proper resource cleanup
- ✓ Transaction safety with commit/rollback
- ✓ User confirmation prompts in both interfaces
- ✓ Clear error messages and status reporting

## Recent Changes
**2025-11-20**: Added Streamlit web interface
- Refactored core logic into `hiv_service.py` for code reuse
- Created `app.py` with Streamlit web UI featuring:
  - File upload with drag-and-drop
  - UUID preview before execution
  - Visual confirmation and result display
  - Database credential validation
- Updated `execute_hiv_query.py` to use shared service module
- Configured Streamlit workflow on port 5000
- Updated documentation with both UI and CLI usage instructions

**2025-11-20**: Initial project setup
- Created secure parameterized queries using ANY(%s)
- Implemented proper resource management with finally blocks
- Added Excel file reading functionality
- Created sample data file `person_uuids_sample.xlsx`
- Set up environment variable configuration
- Added comprehensive documentation

## Project Architecture

### Files
- `app.py` - Streamlit web interface with file upload UI
- `execute_hiv_query.py` - Command-line interface for automation
- `hiv_service.py` - Shared business logic (Excel reading, database operations)
- `person_uuids_sample.xlsx` - Sample Excel file with 3 test UUIDs
- `.env` - Database credentials (not in version control)
- `.env.example` - Template for database configuration
- `README.md` - User-facing documentation
- `.gitignore` - Excludes sensitive files and Python artifacts

### Code Architecture
**Separation of Concerns:**
- `hiv_service.py`: Core business logic
  - `read_uuids_from_excel()`: Excel parsing with structured error handling
  - `execute_hiv_query()`: Parameterized database operations
  - `validate_db_credentials()`: Configuration validation
  - `get_db_config()`: Environment variable management

- `app.py`: Streamlit web interface
  - File upload with temporary file handling
  - UUID preview and confirmation flow
  - Visual result display with metrics
  - User-friendly error messages

- `execute_hiv_query.py`: CLI interface
  - Command-line argument handling
  - Console-based confirmation prompts
  - Structured output for automation

### Database Operations
1. **INSERT**: Creates client verification records in `hiv_observation` table
   - Uses CTE to filter valid person UUIDs from `patient_person` table
   - Inserts verification data with fixed facility_id (1759)
   - Generates new UUIDs for records and visits
   
2. **UPDATE**: Corrects status dates in `hiv_status_tracker`
   - Changes '0209-01-31' to '2009-01-31' (year typo correction)

### Security Features
- Parameterized queries using `uuid = ANY(%s)` to prevent SQL injection
- Environment-based credential management
- Transaction rollback on errors
- Guaranteed resource cleanup with finally blocks
- No credential exposure in UI or logs

### Dependencies
- streamlit: Web interface framework
- pandas & openpyxl: Excel file processing
- psycopg2-binary: PostgreSQL database connectivity
- python-dotenv: Environment variable management

## Usage Instructions

### Web Interface (Recommended)
1. Open the Streamlit app (automatically running in webview)
2. Upload Excel file with `person_uuid` column
3. Review UUIDs in the preview
4. Click "Execute Query" to run
5. View results with insert/update counts

### Command-Line Interface
1. Configure database credentials in `.env` file
2. Prepare Excel file with `person_uuid` column
3. Run: `python execute_hiv_query.py [excel_file_path]`
4. Confirm operation when prompted
5. Review console output for results

## User Preferences
- Prefers browser-based UI for ease of use
- Needs both web and CLI options (CLI for automation)

## Database Requirements
- PostgreSQL with LAMISPLUS database
- Tables: `patient_person`, `hiv_observation`, `hiv_status_tracker`
- Extension: `uuid-ossp` (for uuid_generate_v4 function)

## Future Enhancements
- Add automated tests for Excel parsing and database operations
- Implement UUID normalization to handle whitespace
- Add pagination for large UUID lists in the web interface
