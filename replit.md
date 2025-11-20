# HIV Observation Data Import Project

## Overview
This project provides a Python script to batch import HIV client verification records into the LAMISPLUS PostgreSQL database. It reads person UUIDs from Excel files and executes parameterized SQL queries to insert verification data and correct historical date errors.

## Current State
The project is complete and ready for use. All components are functional and tested:
- ✓ Python script with secure parameterized queries
- ✓ Excel file reading with validation
- ✓ Database connection management with proper resource cleanup
- ✓ Transaction safety with commit/rollback
- ✓ User confirmation prompts
- ✓ Clear error messages and status reporting

## Recent Changes
**2025-11-20**: Initial project setup
- Created `execute_hiv_query.py` with secure parameterized queries using ANY(%s)
- Implemented proper resource management with finally blocks
- Added Excel file reading functionality
- Created sample data file `person_uuids_sample.xlsx`
- Set up environment variable configuration
- Added comprehensive documentation

## Project Architecture

### Files
- `execute_hiv_query.py` - Main script that reads Excel and executes database queries
- `person_uuids_sample.xlsx` - Sample Excel file with 3 test UUIDs
- `.env` - Database credentials (not in version control)
- `.env.example` - Template for database configuration
- `README.md` - User-facing documentation
- `.gitignore` - Excludes sensitive files and Python artifacts

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

### Dependencies
- pandas & openpyxl: Excel file processing
- psycopg2-binary: PostgreSQL database connectivity
- python-dotenv: Environment variable management

## Usage Instructions

1. Configure database credentials in `.env` file
2. Prepare Excel file with `person_uuid` column
3. Run: `python execute_hiv_query.py [excel_file_path]`
4. Confirm operation when prompted
5. Review console output for results

## User Preferences
None specified yet.

## Database Requirements
- PostgreSQL with LAMISPLUS database
- Tables: `patient_person`, `hiv_observation`, `hiv_status_tracker`
- Extension: `uuid-ossp` (for uuid_generate_v4 function)
