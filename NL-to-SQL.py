import sqlite3
import os
import argparse
from typing import List, Tuple, Optional, Any
from groq import Groq, GroqError

# --- Configuration ---
# It's recommended to use environment variables for sensitive data like API keys.
# Example: export GROQ_API_KEY='your_api_key_here'
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "Enter Your API Key Here")
# Consider making the model configurable as well
GROQ_MODEL = "llama-3.3-70b-versatile" # User specified model

# --- Groq Client Initialization ---
try:
    # Initialize the Groq client with the API key.
    client = Groq(api_key=GROQ_API_KEY)
    print("Groq client initialized successfully.")
except GroqError as e:
    # Handle errors during client initialization (e.g., invalid key).
    print(f"Error initializing Groq client: {e}")
    exit(1) # Exit if the client cannot be initialized.
except Exception as e:
    # Handle any other unexpected errors during initialization.
    print(f"An unexpected error occurred during Groq client initialization: {e}")
    exit(1)

def get_db_schema(cursor: sqlite3.Cursor) -> Tuple[Optional[str], Optional[List[str]]]:
    """
    Retrieves the first table name and its column names from the database.

    Args:
        cursor: The SQLite database cursor.

    Returns:
        A tuple containing the table name (str) and a list of column names (List[str]),
        or (None, None) if no tables are found or an error occurs.

    Note:
        This function currently only handles the *first* table found.
        For databases with multiple tables, this logic would need enhancement.
    """
    try:
        # Get the list of tables from the SQLite master table.
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        if not tables:
            # If no tables are found, print an error and return None.
            print("Error: No tables found in the database.")
            return None, None

        # --- Simplification: Using the first table ---
        # For simplicity, use the first table found in the database.
        table_name = tables[0][0]
        print(f"Using the first table found: '{table_name}'")
        # --- End Simplification ---

        # Get column information for the selected table using PRAGMA.
        # Use backticks ` around table name for safety (handles special chars/keywords).
        cursor.execute(f"PRAGMA table_info(`{table_name}`);")
        columns_info = cursor.fetchall()
        # Extract column names (the second element, index 1, in each tuple).
        columns = [column[1] for column in columns_info]
        return table_name, columns
    except sqlite3.Error as e:
        # Handle SQLite errors during schema retrieval.
        print(f"SQLite error while fetching schema for table '{tables[0][0] if tables else 'N/A'}': {e}")
        return None, None
    except Exception as e:
        # Handle any other unexpected errors.
        print(f"An unexpected error occurred fetching schema: {e}")
        return None, None

def generate_sql_query(
    user_input: str,
    database_name: str,
    table_name: str,
    columns: List[str]
) -> Optional[str]:
    """
    Uses the Groq API to convert a natural language query into an SQL query.

    Args:
        user_input: The natural language query from the user.
        database_name: The name of the database file (without extension).
        table_name: The name of the relevant table.
        columns: A list of column names in the table.

    Returns:
        The generated SQL query string, or None if an error occurs.
    """
    # Format column names with backticks for the prompt.
    columns_str = ", ".join(f"`{col}`" for col in columns)
    # Construct the system prompt for the LLM.
    system_prompt = (
        f"You are a helpful assistant that converts plain English questions into SQL queries "
        f"for a SQLite database. "
        # f"The database name is '{database_name}'. " # Database name might not be needed if table/cols are clear
        f"The relevant table name is `{table_name}` and its columns are: {columns_str}. "
        f"IMPORTANT: Your output must be ONLY the SQL query itself, with no explanations, "
        f"markdown formatting (like ```sql), comments (--), or any surrounding text. "
        f"Ensure the query is valid SQLite syntax and only uses the provided table and columns."
        f"Prioritize SELECT statements. Only generate other types (INSERT, UPDATE, DELETE) if explicitly asked."
    )

    # Prepare the messages for the Groq API chat completion request.
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_input},
    ]

    print("\n--- Sending request to Groq API ---")
    # print(f"System Prompt Hint: Using table '{table_name}' with columns: {columns_str}") # Optional: Uncomment for debugging
    print(f"User Query: {user_input}")
    print("------------------------------------")

    try:
        # Call the Groq API to generate the chat completion.
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            max_tokens=150,  # Limit the length of the generated SQL query.
            temperature=0.2, # Lower temperature for more deterministic and focused SQL output.
            stop=None        # Ensure the model doesn't stop prematurely.
        )
        # Extract the generated SQL query from the response.
        sql_query = response.choices[0].message.content.strip()

        # --- Basic Cleanup and Validation ---
        # Remove potential markdown code fences (```sql ... ```) if the LLM adds them.
        if sql_query.startswith("```sql"):
            sql_query = sql_query[6:]
        if sql_query.endswith("```"):
            sql_query = sql_query[:-3]
        # Remove surrounding whitespace and any trailing semicolon added by the LLM.
        sql_query = sql_query.strip().rstrip(';')

        # Basic safety check: Warn if the generated query might modify data.
        if not sql_query.upper().startswith("SELECT"):
             print(f"Warning: Generated query might modify data: {sql_query}")
             # Enhancement idea: Add a user confirmation step here for non-SELECT queries.

        # Check if the LLM returned an empty string.
        if not sql_query:
            print("Error: LLM returned an empty query.")
            return None

        print(f"Generated SQL Query (raw): {sql_query}")
        return sql_query

    except GroqError as e:
        # Handle API errors from Groq.
        print(f"Groq API error during SQL generation: {e}")
        return None
    except Exception as e:
        # Handle any other unexpected errors during generation.
        print(f"An unexpected error occurred during SQL generation: {e}")
        return None

def execute_sql_query(db_path: str, query: str) -> Optional[List[Tuple[Any, ...]]]:
    """
    Executes a given SQL query against the specified SQLite database.

    Args:
        db_path: The file path to the SQLite database.
        query: The SQL query string to execute.

    Returns:
        A list of tuples representing the query results (for SELECT),
        an empty list (for successful non-SELECT), or None if an error occurs.
    """
    if not query:
        # Don't proceed if the query string is empty.
        print("Error: No SQL query provided to execute.")
        return None

    conn = None # Initialize connection variable.
    try:
        # Connect to the SQLite database.
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        print(f"\nExecuting SQL Query: {query}")
        # Execute the generated SQL query.
        cursor.execute(query)

        # Determine if the query is a SELECT statement (simple check).
        is_select_query = query.strip().upper().startswith("SELECT")

        if is_select_query:
            # If it's a SELECT query, fetch all results.
            result = cursor.fetchall()
            print(f"Query executed successfully. Fetched {len(result)} rows.")
        else:
            # For non-SELECT queries (INSERT, UPDATE, DELETE, etc.), commit the changes.
            conn.commit()
            result = []   # Indicate success but no rows fetched.
            print("Non-SELECT query executed and changes committed.")

        # Close the database connection.
        conn.close()
        return result
    except sqlite3.Error as e:
        # Handle SQLite errors during query execution.
        print(f"SQLite error during execution: {e}")
        print(f"Failed Query: {query}")
        if conn:
            conn.close() # Ensure connection is closed even on error.
        return None
    except Exception as e:
        # Handle any other unexpected errors during execution.
        print(f"An unexpected error occurred during query execution: {e}")
        if conn:
            conn.close()
        return None

def main():
    """
    Main function to parse arguments, get user input, generate and execute SQL.
    """
    # Set up command-line argument parsing.
    parser = argparse.ArgumentParser(
        description="Convert natural language to SQL queries using Groq and execute them on a SQLite DB.",
        epilog="Example: python nl_to_sql_groq.py my_database.db -q 'Show me all users from California'"
    )
    parser.add_argument("db_path", help="Path to the SQLite database file.")
    parser.add_argument("-q", "--query", help="Natural language query (prompts if not provided)", default=None)

    args = parser.parse_args()
    database_path = args.db_path

    # --- Input Validation ---
    # Check if the database file exists.
    if not os.path.exists(database_path):
        print(f"Error: Database file not found at '{database_path}'")
        return

    # Check if the API key placeholder is still present.
    if GROQ_API_KEY == "Enter Your API Key Here":
         print("\nWarning: Groq API key is not set.")
         print("Please set the GROQ_API_KEY environment variable or replace the placeholder in the script.")
         # Consider exiting if the API key is mandatory for operation.
         # return

    # --- Database Connection and Schema Retrieval ---
    conn = None
    try:
        # Connect to the DB to retrieve schema information.
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        # Extract the base name of the database file (e.g., "my_database").
        database_name = os.path.basename(database_path).split(".")[0]
        # Get the first table name and its columns.
        table_name, columns = get_db_schema(cursor)
        # Close the connection promptly after getting schema.
        conn.close()

        # Exit if schema retrieval failed (error message already printed).
        if not table_name or not columns:
            return

    except sqlite3.Error as e:
        # Handle errors connecting to the DB or getting schema.
        print(f"SQLite error connecting to DB or getting schema: {e}")
        if conn: conn.close()
        return
    except Exception as e:
        # Handle other unexpected errors during setup.
        print(f"An unexpected error occurred during DB setup: {e}")
        if conn: conn.close()
        return

    # --- Get User Input ---
    if args.query:
        # Use the query provided via command-line argument.
        user_input = args.query
        print(f"Using provided query: {user_input}")
    else:
        # Prompt the user for input interactively.
        try:
            user_input = input(f"\nPlease enter your query (using table '{table_name}'):\n> ")
            if not user_input:
                 # Exit if the user provides no input.
                 print("No input provided. Exiting.")
                 return
        except EOFError: # Handle Ctrl+D or end-of-file.
            print("\nInput stream closed. Exiting.")
            return
        except KeyboardInterrupt: # Handle Ctrl+C.
            print("\nOperation cancelled by user. Exiting.")
            return

    # --- Generate SQL Query ---
    # Call the function to convert natural language to SQL.
    sql_query = generate_sql_query(user_input, database_name, table_name, columns)

    # Exit if SQL generation failed.
    if not sql_query:
        print("Failed to generate SQL query. Exiting.")
        return

    # --- Execute SQL Query ---
    # Call the function to execute the generated SQL against the database.
    results = execute_sql_query(database_path, sql_query)

    # --- Display Results ---
    if results is not None:
        print("\n--- Query Results ---")
        if results:
            # Print results row by row.
            # Enhancement idea: Use a library like 'tabulate' for formatted table output.
            # from tabulate import tabulate
            # headers = [...] # Need column headers for tabulate
            # print(tabulate(results, headers=headers, tablefmt="pretty"))
            for i, row in enumerate(results):
                print(f"Row {i+1}: {row}")
        else:
            # Handle cases where the query ran successfully but returned no rows,
            # or if it was a non-SELECT query.
             if sql_query.strip().upper().startswith("SELECT"):
                 print("(Query executed successfully, but returned no matching rows)")
             # Else: message for successful non-SELECT already printed in execute_sql_query

    else:
        # Message if the query execution itself failed.
        print("\nQuery execution failed.")

# Standard Python entry point check.
if __name__ == "__main__":
    main()
