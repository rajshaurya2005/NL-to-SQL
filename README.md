# Natural Language to SQL Query Tool (using Groq API)

This Python script allows you to query a SQLite database using natural language questions. It utilizes the Groq API (with the Llama 3.3 70b model by default) to translate your questions into SQL queries, executes them against the specified database, and displays the results.

## Features

* Converts plain English questions to SQLite queries.
* Uses the fast Groq API for language model inference.
* Automatically detects the first table and its schema in the database.
* Executes the generated SQL query.
* Handles basic error conditions (API errors, DB errors, file not found).
* Supports both interactive input and command-line query passing.
* Includes basic safety warning for non-SELECT queries.

## Prerequisites

* Python 3.7+
* A Groq API key ([Get one here](https://console.groq.com/keys))
* A SQLite database file (`.db`, `.sqlite`, `.sqlite3`)

## Setup

1.  **Clone the repository:**
    ```bash
    git clone <your-repo-url>
    cd <your-repo-name>
    ```

2.  **Set up a virtual environment (Recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set your Groq API Key:**
    It's strongly recommended to set your API key as an environment variable:
    ```bash
    export GROQ_API_KEY='your_actual_groq_api_key'
    ```
    Alternatively, you can replace the placeholder `"Enter Your API Key Here"` directly in the `nl_to_sql_groq.py` script, but this is less secure.

## Usage

Run the script from your terminal, providing the path to your SQLite database file.

**Interactive Mode:**

```bash
python nl_to_sql_groq.py path/to/your/database.db
The script will:Connect to the database.Identify the first table and its columns.Prompt you to enter your query in natural language.Send the query and schema information to the Groq API.Display the generated SQL query.Execute the SQL query.Print the results.Command-Line Query Mode:You can pass your natural language query directly using the -q or --query flag:python nl_to_sql_groq.py path/to/your/database.db -q "Show me all customers with more than 5 orders"
python nl_to_sql_groq.py employees.sqlite --query "What are the names and salaries of employees in the Engineering department?"
LimitationsSingle Table: The script currently only automatically detects and uses the first table found in the database schema. It does not support queries involving multiple tables (JOINs) unless the LLM infers it correctly without explicit multi-table schema info.SQL Generation Accuracy: The accuracy of the generated SQL depends on the LLM's understanding of the natural language query and the provided schema. Complex queries might not be translated correctly. Always review the generated SQL before relying on its results, especially for non-SELECT operations.Security: Executing LLM-generated SQL queries can be risky, especially if the database contains sensitive information or the LLM generates unintended DML/DDL statements (like UPDATE, DELETE, DROP). The script includes a basic warning for non-SELECT queries, but use with caution.Future EnhancementsSupport for multiple tables (passing multiple schemas or using table names in the query).User selection for target table if multiple tables exist.More robust SQL validation before execution.Option for user confirmation before executing non-SELECT queries.Integration with libraries like tabulate for better result formatting.
