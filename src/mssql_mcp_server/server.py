import asyncio
import logging
import os
from contextlib import contextmanager
from typing import List, Optional, Tuple, Any
import pyodbc
from mcp.server import Server
from mcp.types import Resource, Tool, TextContent
from pydantic import AnyUrl
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("mssql_mcp_server.log")
    ]
)
logger = logging.getLogger("mssql_mcp_server")


# ---------- Configuration ----------

class DatabaseConfig:
    """Database configuration management"""
    
    def __init__(self, server_name: Optional[str] = None, database_name: Optional[str] = None):
        self.server = server_name or os.getenv("MSSQL_SERVER", "localhost")
        self.database = database_name or os.getenv("MSSQL_DATABASE", "master")
        self.trust_server_certificate = os.getenv("TrustServerCertificate", "yes")
        self.trusted_connection = os.getenv("Trusted_Connection", "yes")
    
    @property
    def connection_string(self) -> str:
        """Generate ODBC connection string"""
        return (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={self.server};"
            f"DATABASE={self.database};"
            f"TrustServerCertificate={self.trust_server_certificate};"
            f"Trusted_Connection={self.trusted_connection};"
        )
    
    def master_connection_string(self) -> str:
        """Generate connection string for master database"""
        return (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={self.server};"
            f"DATABASE=master;"
            f"TrustServerCertificate={self.trust_server_certificate};"
            f"Trusted_Connection={self.trusted_connection};"
        )


# ---------- Database Operations ----------

class DatabaseManager:
    """Handles all database operations and validations"""
    
    SYSTEM_DATABASES = {"master", "tempdb", "msdb", "model"}
    
    def __init__(self, config: DatabaseConfig):
        self.config = config
    
    @contextmanager
    def get_connection(self, use_master: bool = False):
        """Context manager for database connections"""
        conn = None
        try:
            conn_str = self.config.master_connection_string() if use_master else self.config.connection_string
            conn = pyodbc.connect(conn_str, timeout=5)
            yield conn
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            raise
        finally:
            if conn:
                try:
                    conn.close()
                except Exception as e:
                    logger.warning(f"Error closing connection: {e}")
    
    def database_exists(self, database_name: str) -> bool:
        """Check if database exists on the server"""
        try:
            with self.get_connection(use_master=True) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1 FROM sys.databases WHERE name = ?", database_name)
                return cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"Error checking database existence: {e}")
            return False
    
    def table_exists(self, table_name: str) -> bool:
        """Check if table exists in the current database"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT 1 FROM INFORMATION_SCHEMA.TABLES 
                    WHERE TABLE_NAME = ? AND TABLE_TYPE='BASE TABLE'
                """, table_name)
                return cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"Error checking table existence: {e}")
            return False
    
    def stored_procedure_exists(self, proc_name: str) -> bool:
        """Check if stored procedure exists"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT 1 FROM INFORMATION_SCHEMA.ROUTINES 
                    WHERE ROUTINE_NAME = ? AND ROUTINE_TYPE = 'PROCEDURE'
                """, proc_name)
                return cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"Error checking stored procedure existence: {e}")
            return False
    
    def function_exists(self, func_name: str) -> bool:
        """Check if function exists"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT 1 FROM INFORMATION_SCHEMA.ROUTINES 
                    WHERE ROUTINE_NAME = ? AND ROUTINE_TYPE = 'FUNCTION'
                """, func_name)
                return cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"Error checking function existence: {e}")
            return False
    
    def validate_database_access(self) -> Optional[str]:
        """Validate database access and return error message if any"""
        if (self.config.database.lower() not in self.SYSTEM_DATABASES and 
            not self.database_exists(self.config.database)):
            return f"Database '{self.config.database}' does not exist on server '{self.config.server}'"
        return None
    
    def get_tables(self) -> List[Tuple[str]]:
        """Get list of tables in the current database"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE'")
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting tables: {e}")
            return []
    
    def execute_query(self, query: str) -> Tuple[bool, Any]:
        """Execute a SQL query and return (success, result)"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query)
                
                if cursor.description:
                    columns = [desc[0] for desc in cursor.description]
                    rows = cursor.fetchall()
                    result = ["|".join(map(str, row)) for row in rows]
                    return True, "\n".join(["|".join(columns)] + result)
                else:
                    conn.commit()
                    return True, f"Query executed successfully. Rows affected: {cursor.rowcount}"
        except Exception as e:
            logger.error(f"Query execution error: {e}")
            return False, str(e)
    
    def execute_stored_procedure(self, proc_name: str, args: List[str]) -> Tuple[bool, Any]:
        """Execute a stored procedure and return (success, result)"""
        if not self.stored_procedure_exists(proc_name):
            return False, f"Stored procedure '{proc_name}' does not exist."
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                placeholders = ", ".join("?" for _ in args)
                call_str = f"{{CALL {proc_name}({placeholders})}}" if args else f"{{CALL {proc_name}()}}"
                cursor.execute(call_str, *args)
                
                if cursor.description:
                    columns = [desc[0] for desc in cursor.description]
                    rows = cursor.fetchall()
                    result = ["|".join(map(str, row)) for row in rows]
                    return True, "\n".join(["|".join(columns)] + result)
                else:
                    conn.commit()
                    return True, f"Stored procedure executed successfully. Rows affected: {cursor.rowcount}"
        except Exception as e:
            logger.error(f"Stored procedure execution error: {e}")
            return False, str(e)
    
    def execute_function(self, func_name: str, args: List[str]) -> Tuple[bool, Any]:
        """Execute a function and return (success, result)"""
        if not self.function_exists(func_name):
            return False, f"Function '{func_name}' does not exist."
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                placeholders = ", ".join("?" for _ in args)
                
                # Try table-valued function first
                try:
                    query = f"SELECT * FROM dbo.{func_name}({placeholders})"
                    cursor.execute(query, *args)
                except Exception:
                    # Fallback to scalar function
                    logger.info(f"Retrying {func_name} as scalar function")
                    query = f"SELECT dbo.{func_name}({placeholders})"
                    cursor.execute(query, *args)
                
                columns = [desc[0] for desc in cursor.description]
                rows = cursor.fetchall()
                result = ["|".join(map(str, row)) for row in rows]
                return True, "\n".join(["|".join(columns)] + result)
        except Exception as e:
            logger.error(f"Function execution error: {e}")
            return False, str(e)
    
    def read_table_data(self, table_name: str, limit: int = 100) -> str:
        """Read data from a table with optional limit"""
        if not self.table_exists(table_name):
            return f"[ERROR] Table '{table_name}' does not exist in database '{self.config.database}'"
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(f"SELECT TOP {limit} * FROM [{table_name}] WITH (NOLOCK)")
                columns = [desc[0] for desc in cursor.description]
                rows = cursor.fetchall()
                result = ["|".join(map(str, row)) for row in rows]
                return "\n".join(["|".join(columns)] + result)
        except Exception as e:
            logger.error(f"Error reading table data: {e}")
            return f"[ERROR] {str(e)}"


# ---------- Utility ----------

def get_db_config(server_name=None, database_name=None):
    """Legacy function for backward compatibility"""
    config = DatabaseConfig(server_name, database_name)
    return {
        "server": config.server,
        "database": config.database,
        "trust_server_certificate": config.trust_server_certificate,
        "trusted_connection": config.trusted_connection
    }, config.connection_string

def check_database_exists(server: str, database: str) -> bool:
    """Legacy function for backward compatibility"""
    config = DatabaseConfig(server, "master")
    db_manager = DatabaseManager(config)
    return db_manager.database_exists(database)

def check_table_exists(conn, table_name: str) -> bool:
    """Legacy function for backward compatibility"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 1 FROM INFORMATION_SCHEMA.TABLES 
        WHERE TABLE_NAME = ? AND TABLE_TYPE='BASE TABLE'
    """, table_name)
    return cursor.fetchone() is not None

def check_stored_procedure_exists(conn, proc_name: str) -> bool:
    """Legacy function for backward compatibility"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 1 FROM INFORMATION_SCHEMA.ROUTINES 
        WHERE ROUTINE_NAME = ? AND ROUTINE_TYPE = 'PROCEDURE'
    """, proc_name)
    return cursor.fetchone() is not None

def check_function_exists(conn, func_name: str) -> bool:
    """Legacy function for backward compatibility"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 1 FROM INFORMATION_SCHEMA.ROUTINES 
        WHERE ROUTINE_NAME = ? AND ROUTINE_TYPE = 'FUNCTION'
    """, func_name)
    return cursor.fetchone() is not None


# ---------- Server ----------

app = Server("mssql_mcp_server")


@app.list_resources()
async def list_resources(server_name=None, database_name=None) -> list[Resource]:
    """List available database resources (tables)"""
    config = DatabaseConfig(server_name, database_name)
    db_manager = DatabaseManager(config)
    
    # Validate database access
    error_msg = db_manager.validate_database_access()
    if error_msg:
        logger.error(error_msg)
        return []
    
    try:
        tables = db_manager.get_tables()
        resources = [
            Resource(
                uri=f"mssql://{table[0]}/data",
                name=f"Table: {table[0]}",
                mimeType="text/plain",
                description=f"Data in table: {table[0]}"
            )
            for table in tables
        ]
        return resources
    except Exception as e:
        logger.error(f"Failed to list resources: {e}", exc_info=True)
        return []


@app.read_resource()
async def read_resource(uri: AnyUrl, server_name=None, database_name=None) -> str:
    """Read data from a database resource (table)"""
    config = DatabaseConfig(server_name, database_name)
    db_manager = DatabaseManager(config)
    
    # Validate database access
    error_msg = db_manager.validate_database_access()
    if error_msg:
        return f"[ERROR] {error_msg}"
    
    # Extract table name from URI
    table_name = str(uri)[8:].split('/')[0]
    
    try:
        return db_manager.read_table_data(table_name)
    except Exception as e:
        logger.error(f"Error reading resource: {e}", exc_info=True)
        return f"[ERROR] {str(e)}"


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools for SQL operations"""
    return [
        Tool(
            name="execute_sql",
            description="Execute an SQL query or stored procedure",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "SQL query to execute"
                    },
                    "stored_proc": {
                        "type": "string",
                        "description": "Name of stored procedure to execute"
                    },
                    "proc_args": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Arguments for stored procedure"
                    },
                    "function_name": {
                        "type": "string",
                        "description": "Name of function to execute"
                    },
                    "func_args": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Arguments for function"
                    },
                    "server_name": {
                        "type": "string",
                        "description": "SQL Server instance name"
                    },
                    "database_name": {
                        "type": "string",
                        "description": "Database name to connect to"
                    }
                },
                "required": []
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Execute SQL operations based on tool arguments"""
    if name != "execute_sql":
        return [TextContent(type="text", text=f"[ERROR] Unknown tool: {name}")]
    
    # Extract arguments
    server_name = arguments.get("server_name")
    database_name = arguments.get("database_name")
    query = arguments.get("query")
    stored_proc = arguments.get("stored_proc")
    proc_args = arguments.get("proc_args", [])
    function_name = arguments.get("function_name")
    func_args = arguments.get("func_args", [])
    
    # Initialize database manager
    config = DatabaseConfig(server_name, database_name)
    db_manager = DatabaseManager(config)
    
    # Validate database access
    error_msg = db_manager.validate_database_access()
    if error_msg:
        logger.error(error_msg)
        return [TextContent(type="text", text=f"[ERROR] {error_msg}")]
    
    # Execute based on operation type
    try:
        if stored_proc:
            success, result = db_manager.execute_stored_procedure(stored_proc, proc_args)
        elif function_name:
            success, result = db_manager.execute_function(function_name, func_args)
        elif query:
            success, result = db_manager.execute_query(query)
        else:
            return [TextContent(type="text", text="[ERROR] No valid operation provided: query, stored_proc, or function_name.")]
        
        if success:
            return [TextContent(type="text", text=result)]
        else:
            return [TextContent(type="text", text=f"[ERROR] {result}")]
            
    except Exception as e:
        logger.error(f"Tool execution error: {e}", exc_info=True)
        return [TextContent(type="text", text=f"[ERROR] {str(e)}")]


# ---------- Entry Point ----------

async def main():
    """Main entry point for the MSSQL MCP server"""
    from mcp.server.stdio import stdio_server

    logger.info("Starting MSSQL MCP server...")
    
    try:
        config = DatabaseConfig()
        logger.info(f"Database config: {config.server}/{config.database}")

        async with stdio_server() as (read_stream, write_stream):
            await app.run(read_stream, write_stream, app.create_initialization_options())
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())
