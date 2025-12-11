import pandas as pd

def read_uuids_from_excel(file_path, column_name='person_uuid'):
    try:
        df = pd.read_excel(file_path)
        
        if column_name not in df.columns:
            return {
                'success': False,
                'error': f"Column '{column_name}' not found in Excel file.",
                'available_columns': list(df.columns),
                'uuids': None
            }
        
        uuids = df[column_name].dropna().astype(str).str.strip().unique().tolist()
        return {
            'success': True,
            'uuids': uuids,
            'count': len(uuids),
            'error': None
        }
    
    except FileNotFoundError:
        return {
            'success': False,
            'error': f"File '{file_path}' not found.",
            'uuids': None
        }
    except Exception as e:
        return {
            'success': False,
            'error': f"Error reading Excel file: {str(e)}",
            'uuids': None
        }

def read_excel_file(file_path):
    try:
        df = pd.read_excel(file_path)
        return {
            'success': True,
            'dataframe': df,
            'columns': list(df.columns),
            'row_count': len(df),
            'error': None
        }
    except Exception as e:
        return {
            'success': False,
            'error': f"Error reading Excel file: {str(e)}",
            'dataframe': None
        }
