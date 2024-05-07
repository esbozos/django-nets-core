-- Nets Core Postgre Model to JSON
-- Description: This function converts a model to a JSON object for use in the Nets Core API
-- Parameters: 
--  table_name: table name of the model, e.g. "auth.user"
--  fields: Fields to include in the JSON object, e.g. "id,username,email"
--  object_id: ID of the object to convert to JSON object, e.g. 1
-- Returns: JSON object, e.g. {"id": 1, "username": "admin", "email": "any@mail.com"}
-- 
-- Created: 2024-05-07
-- Author: Norman Torres
-- Last Modified: 2024-05-07
-- License: MIT
-- Version: 1.0
-- 
-- Usage:
-- RAW SQL: SELECT nets_core_postgre_model_to_json('auth_user', 'id,username,email', 1);
-- NetsCoreModelToJson(instance=user, fields='id,username,email').json()
--
-- Dependencies:
-- 1. Django

CREATE OR REPLACE FUNCTION nets_core_postgre_model_to_json(table_name text, fields text, object_id int)
RETURNS json AS $$
DECLARE
    _model text;
    _fields text;
    _object_id int;
    _json json;
BEGIN
    _model := table_name;
    _fields := fields;
    _object_id := object_id;
    -- enclose fields in double quotes to avoid SQL injection
    _fields := REPLACE(_fields, ',', '","');
    _fields := format('t1."%s"', _fields);
    -- invoke dynamic SQL to convert model to JSON object, each fiel should be t1."field_name" using t1 as alias for the model
    EXECUTE format('SELECT row_to_json(t) FROM (SELECT %s FROM %s t1 WHERE id = %s) t', _fields, _model, _object_id) INTO _json;
    
    RETURN _json;
END;
$$ LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION nets_core_postgre_array_model_to_json(table_name text, fields text, object_ids int[])
RETURNS json AS $$
DECLARE
    _model text;
    _fields text;
    _object_ids int[];
    _json json;
BEGIN
    _model := table_name;
    _fields := fields;
    _object_ids := object_ids;
    -- enclose fields in double quotes to avoid SQL injection
    _fields := REPLACE(_fields, ',', '","');
    _fields := format('t1."%s"', _fields);
    -- invoke dynamic SQL to convert model to JSON object, each fiel should be t1."field_name" using t1 as alias for the model
    EXECUTE format('SELECT json_agg(row_to_json(t)) FROM (SELECT %s FROM %s t1 WHERE id = ANY(%s)) t', _fields, _model, _object_ids) INTO _json;
    
    RETURN _json;
END;
$$ LANGUAGE plpgsql;
