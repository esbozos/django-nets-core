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
    logger.info(f"Creating nets_core functions for {using} database")
    
    connection = connections[using]
    engine = connection.vendor
    function_files = Path(__file__).parent / "functions"
    for file in function_files.iterdir():
        if file.is_file():
            if f"nets_core_{engine}" in file.name:
                logger.info(f"Creating function from {file}")
                with open(file, "r") as f:
                    connection.cursor().execute(f.read())
    connection.close()
    return True

        