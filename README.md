# HIV Observation Data Import Script

This Python script reads person UUIDs from an Excel file and executes SQL queries to insert verification data into the LAMISPLUS PostgreSQL database.

## Features

- Reads person UUIDs from Excel file with a `person_uuid` column
- Inserts client verification records into `hiv_observation` table
- Updates incorrect status dates in `hiv_status_tracker` table
- Includes transaction management and error handling
- Confirmation prompt before executing database operations

## Setup

1. **Configure Database Connection**
   
   Copy `.env.example` to `.env` and fill in your database credentials:
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

2. **Prepare Excel File**
   
   Create an Excel file (e.g., `person_uuids.xlsx`) with a column named `person_uuid` containing the UUIDs you want to process.
   
   Example structure:
   ```
   | person_uuid                          |
   |--------------------------------------|
   | 080e68d8-7be2-6141-8959-9f6951704ad0 |
   | 0f4a1c07-dd74-4d08-bba6-32595f11d354 |
   | 1063fa10-82fe-4e1b-8890-244da2fee1b9 |
   ```

## Usage

Run the script with the default Excel file (`person_uuids.xlsx`):
```bash
python execute_hiv_query.py
```

Or specify a custom Excel file:
```bash
python execute_hiv_query.py /path/to/your/file.xlsx
```

The script will:
1. Read all unique UUIDs from the Excel file
2. Display the UUIDs to be processed
3. Ask for confirmation before executing
4. Execute the INSERT and UPDATE queries
5. Report the number of records affected

## What the Script Does

1. **INSERT Operation**: Creates client verification records in `hiv_observation` table for each UUID found in the `patient_person` table
2. **UPDATE Operation**: Corrects status dates in `hiv_status_tracker` from '0209-01-31' to '2009-01-31'

## Safety Features

- User confirmation required before database execution
- Transaction rollback on errors
- Validates Excel file and column existence
- Filters out NULL/empty UUIDs
- Clear error messages and status reporting

## Requirements

- Python 3.11+
- pandas
- openpyxl
- psycopg2-binary
- python-dotenv
