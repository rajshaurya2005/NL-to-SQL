# Natural Language to SQL Query Tool (using Groq API)

This Python script allows you to query a SQLite database using natural language questions. It utilizes the Groq API to translate your questions into SQL queries, executes them against the specified database, and displays the results.

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
    git clone <your-repo-url> # Replace with your actual repo URL if applicable
    cd <your-repo-name>      # Replace with the cloned directory name
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
    # On Windows Command Prompt:
    # set GROQ_API_KEY=your_actual_groq_api_key
    # On Windows PowerShell:
    # $env:GROQ_API_KEY='your_actual_groq_api_key'
    ```
    Alternatively, you can replace the placeholder `"Enter Your API Key Here"` directly in the `nl_to_sql_groq.py` script, but this is less secure.

## Usage

Run the script from your terminal, providing the path to your SQLite database file.

**Interactive Mode:**

```bash
python nl_to_sql_groq.py path/to/your/database.db
