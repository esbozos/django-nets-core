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
-- Last Modified: 2024-07-24
-- License: MIT
-- Version: 1.0
-- 
-- Usage:
-- RAW SQL: SELECT nets_core_postgre_model_to_json('auth_user', 'id,username,email', 1);
-- NetsCoreModelToJson(instance=user, fields='id,username,email').json()
--
-- Dependencies:
-- 1. Django
DROP FUNCTION IF EXISTS nets_core_postgre_model_to_json;
CREATE OR REPLACE FUNCTION nets_core_postgre_model_to_json(table_name text, fields text, object_id bigint)
RETURNS json AS $$
DECLARE
    _model text;
    _fields text;
    _nested_field_name text;
    _nested_field_model text;
    _nested_field text[];
    _nested_field_fields text;
    _nested_field_origin text;
    _nested_query text;
    _nested_queries text[];
    _nested_fields_origin text;
    _array_fields text[];
    _object_id int;
    _json json;
BEGIN
    _model := table_name;
    _fields := fields;
    _object_id := object_id;

    -- fields can contain nested invocation of nets_core_postgre_model_to_json function
    -- e.g. "id,username,email,profile_id:[auth_user_profile;id;user_id;name;last_name]"
    -- profile_id is a nested model, auth_user_profile is the table name, id, name and last_name are the fields to include in the nested model filter by profile_id
    -- field name always should be without _id suffix, e.g. profile_id should be profile
    -- in this case, the profile field will be converted to a JSON object using the nested invocation
    IF POSITION(':' IN _fields) > 0 THEN
        -- extract nested model and fields
        -- split fields by comma
        _array_fields := string_to_array(_fields, ',');        
        FOREACH _nested_field_origin IN ARRAY _array_fields
        LOOP
            IF POSITION(':' IN _nested_field_origin) = 0 THEN
                
                CONTINUE;
            END IF;
            -- split field by colon
            _nested_field := string_to_array(_nested_field_origin, ':');
            _nested_field_name := _nested_field[1];
            _nested_field = string_to_array(substr(_nested_field[2], 2, length(_nested_field[2])-2), ';');
            _nested_field_model := _nested_field[1];
            -- fields are the rest of the array
            _nested_field_fields := ARRAY_TO_STRING(_nested_field[2:], ',');
            
            
            _nested_query := format(
                    	'(SELECT nets_core_postgre_model_to_json(''%s'', ''%s'', t1.%s) AS %s',
                                _nested_field_model,
                                _nested_field_fields,
                                _nested_field_name,
                                REPLACE(_nested_field_name, '_id', '')
                                );
            _nested_queries := array_append(_nested_queries, _nested_query);
            _fields = REPLACE(_fields, _nested_field_origin, '');
            
        END LOOP;
    END IF;

    -- final fields remove empty fields
    -- convert to array and build the fields string if not empty
    _array_fields := ARRAY_REMOVE(string_to_array(_fields, ','), '');
    _fields := ARRAY_TO_STRING(_array_fields, ',');
    

    -- enclose fields in double quotes to avoid SQL injection
    _fields := REPLACE(_fields, ',', '",t1."');
    _fields := format('t1."%s"', _fields);
    -- concatenate nested queries
    IF array_length(_nested_queries, 1) > 0 THEN
        _fields := _fields || ',' || array_to_string(_nested_queries, ',') || ')';
    END IF;
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
    
    -- invoke dynamic SQL to convert model to JSON object, each field should be t1."field_name" using t1 as alias for the model
    fields := REPLACE(fields, ',', '",t1."');
    fields := format('t1."%s"', fields);
    EXECUTE format('SELECT json_agg(row_to_json(t)) FROM (SELECT %s FROM %s t1 WHERE id = ANY(%s)) t', _fields, _model, _object_ids) INTO _json;
    
    RETURN _json;
END;
$$ LANGUAGE plpgsql;
