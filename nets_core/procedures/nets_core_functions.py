import os
from pathlib import Path
from django.db import connections

def create_nets_core_functions(using: str = "default"):
    # functions are store in nets_core/procedures/functions/*.sql
    # each file state with nets_core_[db_engine]_[function_name].sql
    # db_engine can be postgresql, mysql, sqlite, etc
    # Example: nets_core_postgresql_model_to_json.sql will create a function to convert a model to json in postgresql
    # we need to check db engine and create the function accordingly
    
    # use stdout to print the sql query
    
    import logging
    logger = logging.getLogger(__name__)
    
    
    connection = connections[using]
    engine = connection.vendor
    logger.warning(f"Creating nets_core functions for {using} database engine {engine}")
    function_files = os.path.join(Path(__file__).parent, "functions")
    for file in os.scandir(function_files):
        if file.is_file():
            if file.name.startswith(f"nets_core_{engine}"):
                with open(file.path, "r") as f:
                    query = f.read()
                    logger.warning(f"Executing {file.name} function")
                    with connection.cursor() as cursor:
                        cursor.execute(query)
    connection.close()
    return True

        