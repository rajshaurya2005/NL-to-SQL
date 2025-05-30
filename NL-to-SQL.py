import sqlite3
import os
import argparse
from typing import List, Tuple, Optional, Any
from groq import Groq, GroqError

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "Enter Your API Key Here")
GROQ_MODEL = "llama-3.3-70b-versatile"

try:
    client = Groq(api_key=GROQ_API_KEY)
    print("Groq client initialized successfully.")
except GroqError as e:
    print(f"Error initializing Groq client: {e}")
    exit(1)
except Exception as e:
    print(f"An unexpected error occurred during Groq client initialization: {e}")
    exit(1)

def get_db_schema(cursor: sqlite3.Cursor) -> Tuple[Optional[str], Optional[List[str]]]:
    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        if not tables:
            print("Error: No tables found in the database.")
            return None, None
            
        table_name = tables[0][0]
        print(f"Using the first table found: '{table_name}'")
        cursor.execute(f"PRAGMA table_info(`{table_name}`);")
        columns_info = cursor.fetchall()
        columns = [column[1] for column in columns_info]
        return table_name, columns
    except sqlite3.Error as e:
        print(f"SQLite error while fetching schema for table '{tables[0][0] if tables else 'N/A'}': {e}")
        return None, None
    except Exception as e:
        print(f"An unexpected error occurred fetching schema: {e}")
        return None, None

def generate_sql_query(
    user_input: str,
    database_name: str,
    table_name: str,
    columns: List[str]
) -> Optional[str]:
    columns_str = ", ".join(f"`{col}`" for col in columns)
    system_prompt = (
        f"You are a helpful assistant that converts plain English questions into SQL queries "
        f"for a SQLite database. "
        f"The relevant table name is `{table_name}` and its columns are: {columns_str}. "
        f"IMPORTANT: Your output must be ONLY the SQL query itself, with no explanations, "
        f"markdown formatting (like ```sql), comments (--), or any surrounding text. "
        f"Ensure the query is valid SQLite syntax and only uses the provided table and columns."
        f"Prioritize SELECT statements. Only generate other types (INSERT, UPDATE, DELETE) if explicitly asked."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_input},
    ]

    print("\n--- Sending request to Groq API ---")
    print(f"User Query: {user_input}")
    print("------------------------------------")

    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            max_tokens=150,
            temperature=0.2,
            stop=None
        )
        sql_query = response.choices[0].message.content.strip()

        if sql_query.startswith("```sql"):
            sql_query = sql_query[6:]
        if sql_query.endswith("```"):
            sql_query = sql_query[:-3]
        sql_query = sql_query.strip().rstrip(';')

        if not sql_query.upper().startswith("SELECT"):
            print(f"Warning: Generated query might modify data: {sql_query}")

        if not sql_query:
            print("Error: LLM returned an empty query.")
            return None

        print(f"Generated SQL Query (raw): {sql_query}")
        return sql_query

    except GroqError as e:
        print(f"Groq API error during SQL generation: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred during SQL generation: {e}")
        return None

def execute_sql_query(db_path: str, query: str) -> Optional[List[Tuple[Any, ...]]]:
    if not query:
        print("Error: No SQL query provided to execute.")
        return None

    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        print(f"\nExecuting SQL Query: {query}")
        cursor.execute(query)

        is_select_query = query.strip().upper().startswith("SELECT")

        if is_select_query:
            result = cursor.fetchall()
            print(f"Query executed successfully. Fetched {len(result)} rows.")
        else:
            conn.commit()
            result = []
            print("Non-SELECT query executed and changes committed.")

        conn.close()
        return result
    except sqlite3.Error as e:
        print(f"SQLite error during execution: {e}")
        print(f"Failed Query: {query}")
        if conn:
            conn.close()
        return None
    except Exception as e:
        print(f"An unexpected error occurred during query execution: {e}")
        if conn:
            conn.close()
        return None

def main():
    parser = argparse.ArgumentParser(
        description="Convert natural language to SQL queries using Groq and execute them on a SQLite DB.",
        epilog="Example: python nl_to_sql_groq.py my_database.db -q 'Show me all users from California'"
    )
    parser.add_argument("db_path", help="Path to the SQLite database file.")
    parser.add_argument("-q", "--query", help="Natural language query (prompts if not provided)", default=None)

    args = parser.parse_args()
    database_path = args.db_path

    if not os.path.exists(database_path):
        print(f"Error: Database file not found at '{database_path}'")
        return

    if GROQ_API_KEY == "Enter Your API Key Here":
        print("\nWarning: Groq API key is not set.")
        print("Please set the GROQ_API_KEY environment variable or replace the placeholder in the script.")

    conn = None
    try:
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        database_name = os.path.basename(database_path).split(".")[0]
        table_name, columns = get_db_schema(cursor)
        conn.close()

        if not table_name or not columns:
            return

    except sqlite3.Error as e:
        print(f"SQLite error connecting to DB or getting schema: {e}")
        if conn: conn.close()
        return
    except Exception as e:
        print(f"An unexpected error occurred during DB setup: {e}")
        if conn: conn.close()
        return

    if args.query:
        user_input = args.query
        print(f"Using provided query: {user_input}")
    else:
        try:
            user_input = input(f"\nPlease enter your query (using table '{table_name}'):\n> ")
            if not user_input:
                print("No input provided. Exiting.")
                return
        except EOFError:
            print("\nInput stream closed. Exiting.")
            return
        except KeyboardInterrupt:
            print("\nOperation cancelled by user. Exiting.")
            return

    sql_query = generate_sql_query(user_input, database_name, table_name, columns)

    if not sql_query:
        print("Failed to generate SQL query. Exiting.")
        return

    results = execute_sql_query(database_path, sql_query)

    if results is not None:
        print("\n--- Query Results ---")
        if results:
            for i, row in enumerate(results):
                print(f"Row {i+1}: {row}")
        else:
            if sql_query.strip().upper().startswith("SELECT"):
                print("(Query executed successfully, but returned no matching rows)")

    else:
        print("\nQuery execution failed.")

if __name__ == "__main__":
    main()
