import os
from dotenv import load_dotenv
import psycopg2

# Load environment variables from .env file
load_dotenv()

def list_tables():
    try:
        # Load database credentials from environment variables
        db_host = os.getenv("DB_HOST", "localhost")
        db_port = os.getenv("DB_PORT", "5432")
        db_name = os.getenv("DB_NAME", "labor_observatory")
        db_user = os.getenv("DB_USER", "labor_user")
        db_password = os.getenv("DB_PASSWORD", "your_password")

        # Connect to the PostgreSQL database
        connection = psycopg2.connect(
            host=db_host,
            port=db_port,
            database=db_name,
            user=db_user,
            password=db_password
        )

        cursor = connection.cursor()
        
        # List all tables in the database
        cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';")
        tables = cursor.fetchall()

        print("Tables in the database:")
        for table in tables:
            print(f"- {table[0]}")

        cursor.close()
        connection.close()

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    list_tables()