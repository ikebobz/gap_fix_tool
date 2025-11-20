# HIV Observation Data Import

Import client verification records into the LAMISPLUS PostgreSQL database using either a web interface or command-line script.

## Features

- 🌐 **Web Interface** - User-friendly browser-based UI with file upload
- 💻 **Command Line** - Scriptable CLI for automation and batch processing
- 📊 **Excel Integration** - Read person UUIDs from Excel files with `person_uuid` column
- 🔒 **Secure** - Parameterized SQL queries prevent injection attacks
- 🔄 **Transaction Safe** - Automatic rollback on errors
- ✅ **Validation** - File and data validation with clear error messages

## Quick Start

### 1. Configure Database Connection

Create a `.env` file with your database credentials:

```bash
cp .env.example .env
```

Edit `.env` with your actual database details:
```
DB_HOST=your_database_host
DB_PORT=5432
DB_NAME=LAMISPLUS
DB_USER=your_username
DB_PASSWORD=your_password
```

### 2. Choose Your Interface

#### Option A: Web Interface (Recommended)

The Streamlit web interface is automatically started and accessible through the webview panel.

**Features:**
- Drag-and-drop file upload
- Preview UUIDs before execution
- Visual feedback and status messages
- No command-line knowledge required

Simply:
1. Open the webview (the app is already running)
2. Upload your Excel file
3. Review the UUIDs
4. Click "Execute Query"

#### Option B: Command Line Interface

For automation or scripting:

```bash
python execute_hiv_query.py person_uuids.xlsx
```

Or specify a custom file path:
```bash
python execute_hiv_query.py /path/to/your/file.xlsx
```

The CLI will:
1. Read all unique UUIDs from the Excel file
2. Display the UUIDs to be processed
3. Ask for confirmation before executing
4. Execute the INSERT and UPDATE queries
5. Report the number of records affected

## Excel File Format

Your Excel file must contain a column named `person_uuid`:

| person_uuid |
|-------------|
| 080e68d8-7be2-6141-8959-9f6951704ad0 |
| 0f4a1c07-dd74-4d08-bba6-32595f11d354 |
| 1063fa10-82fe-4e1b-8890-244da2fee1b9 |

- Column name must be exactly **`person_uuid`**
- UUIDs should be in standard UUID format
- Empty rows will be automatically skipped
- Duplicate UUIDs will be processed only once

## What the Application Does

### 1. INSERT Operation
Creates client verification records in `hiv_observation` table for each UUID found in the `patient_person` table:
- Sets facility_id to 1759
- Creates verification data with "Records Verified" status
- Generates new UUIDs for records and visits

### 2. UPDATE Operation
Corrects status dates in `hiv_status_tracker`:
- Changes '0209-01-31' to '2009-01-31' (fixes year typo)

## Safety Features

- ✓ Parameterized queries using `ANY(%s)` prevent SQL injection
- ✓ User confirmation required before database execution
- ✓ Transaction rollback on errors
- ✓ Validates Excel file and column existence
- ✓ Filters out NULL/empty UUIDs
- ✓ Guaranteed resource cleanup with finally blocks
- ✓ Clear error messages and status reporting

## Project Structure

```
.
├── app.py                      # Streamlit web interface
├── execute_hiv_query.py        # Command-line interface
├── hiv_service.py              # Shared business logic
├── person_uuids_sample.xlsx    # Sample data file
├── .env.example                # Database configuration template
├── .env                        # Your database credentials (not in version control)
└── README.md                   # This file
```

## Requirements

### Python Dependencies
- Python 3.11+
- pandas
- openpyxl
- psycopg2-binary
- python-dotenv
- streamlit

All dependencies are pre-installed in this Replit environment.

### Database Requirements
- PostgreSQL database with LAMISPLUS schema
- Required PostgreSQL extension: `uuid-ossp` (for uuid_generate_v4() function)
  
  To enable the extension if not already available:
  ```sql
  CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
  ```

- Required tables:
  - `patient_person`
  - `hiv_observation`
  - `hiv_status_tracker`

## Troubleshooting

### "Database credentials not found"
- Ensure you've created a `.env` file
- Check that `DB_USER` and `DB_PASSWORD` are set
- Restart the application after editing `.env`

### "Column 'person_uuid' not found"
- Verify your Excel file has a column named exactly `person_uuid`
- Check for typos or extra spaces in the column name

### Database connection errors
- Verify your database host, port, and credentials
- Ensure the database is accessible from this environment
- Check that the LAMISPLUS database exists

## Security Notes

- Never commit `.env` file to version control
- Database credentials are stored in environment variables
- All SQL queries use parameterized statements
- Transactions ensure data consistency
