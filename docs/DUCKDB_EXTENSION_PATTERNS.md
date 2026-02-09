# DuckDB Extension Patterns and Best Practices

## Overview

This document captures patterns and best practices learned from analyzing DuckDB community extensions, particularly for implementing table functions in C.

## C API vs C++ API

We're using the **C API template** (`extension-template-c`) which has several advantages:
- More stable ABI - won't break between DuckDB versions
- No C++ symbol mangling issues
- Simpler deployment

## Table Function Pattern (C API)

### 1. Create Table Function

```c
duckdb_table_function function = duckdb_create_table_function();
duckdb_table_function_set_name(function, "my_function");
```

### 2. Add Parameters

```c
duckdb_logical_type varchar_type = duckdb_create_logical_type(DUCKDB_TYPE_VARCHAR);
duckdb_table_function_add_parameter(function, varchar_type);
duckdb_destroy_logical_type(&varchar_type);
```

### 3. Bind Function

The bind function is called at query plan time. It:
- Reads input parameters
- Defines output columns
- Optionally sets bind data for later use

```c
void my_bind(duckdb_bind_info info) {
    // Get parameter
    duckdb_value path_val = duckdb_bind_get_parameter(info, 0);
    char *path = duckdb_get_varchar(path_val);
    
    // Add result columns
    duckdb_logical_type varchar_type = duckdb_create_logical_type(DUCKDB_TYPE_VARCHAR);
    duckdb_bind_add_result_column(info, "column_name", varchar_type);
    duckdb_destroy_logical_type(&varchar_type);
    
    // Set bind data (optional)
    MyBindData *bind_data = malloc(sizeof(MyBindData));
    bind_data->path = strdup(path);
    duckdb_bind_set_bind_data(info, bind_data, my_destroy_bind);
    
    duckdb_destroy_value(&path_val);
    duckdb_free(path);
}
```

### 4. Init Function

Called when query execution starts. Sets up state for the scan.

```c
void my_init(duckdb_init_info info) {
    MyBindData *bind_data = (MyBindData *)duckdb_init_get_bind_data(info);
    
    MyInitData *init_data = malloc(sizeof(MyInitData));
    init_data->current_row = 0;
    init_data->file_handle = fopen(bind_data->path, "r");
    
    duckdb_init_set_init_data(info, init_data, my_destroy_init);
}
```

### 5. Main Function

Called repeatedly to produce output chunks.

```c
void my_function(duckdb_function_info info, duckdb_data_chunk output) {
    MyBindData *bind_data = (MyBindData *)duckdb_function_get_bind_data(info);
    MyInitData *init_data = (MyInitData *)duckdb_function_get_init_data(info);
    
    idx_t count = 0;
    // Read rows and populate output vectors
    while (count < STANDARD_VECTOR_SIZE && has_more_data) {
        duckdb_vector vec = duckdb_data_chunk_get_vector(output, 0);
        duckdb_vector_assign_string_element(vec, count, my_string);
        count++;
    }
    
    duckdb_data_chunk_set_size(output, count);
}
```

### 6. Register Function

```c
duckdb_table_function_set_bind(function, my_bind);
duckdb_table_function_set_init(function, my_init);
duckdb_table_function_set_function(function, my_function);
duckdb_register_table_function(connection, function);
duckdb_destroy_table_function(&function);
```

## JSON Handling Strategies

For parsing JSONL files, we have several options:

### Option 1: Built-in JSON Support
DuckDB has built-in JSON functions. We could read files as text and use SQL to parse.

### Option 2: cJSON Library
Lightweight C JSON parser. Include as single file:
- cJSON.c / cJSON.h
- Easy to embed, well-tested

### Option 3: yyjson
Very fast JSON parser, also C-compatible.

**Recommendation**: Use cJSON for simplicity and portability.

## File Structure for Our Extension

```
claude_code_ext/
├── CMakeLists.txt
├── src/
│   ├── claude_code_ext.c           # Entry point
│   ├── include/
│   │   ├── claude_code_ext.h
│   │   ├── json_utils.h
│   │   ├── file_utils.h
│   │   └── table_functions/
│   │       ├── conversations.h
│   │       ├── plans.h
│   │       ├── todos.h
│   │       ├── history.h
│   │       └── stats.h
│   ├── json_utils.c
│   ├── file_utils.c
│   ├── table_functions/
│   │   ├── conversations.c
│   │   ├── plans.c
│   │   ├── todos.c
│   │   ├── history.c
│   │   └── stats.c
│   └── third_party/
│       ├── cJSON.c
│       └── cJSON.h
└── test/
    └── sql/
        └── *.sql
```

## Cloned Reference Extensions

Located in `tmp/` for reference:
- `extension-template-c/` - Base template for C API extensions
- `json_schema/` - Example of JSON handling in extensions
- `hostFS/` - Example of file system operations and table functions

## Key API Functions for Our Use Case

### Type Creation
- `duckdb_create_logical_type(DUCKDB_TYPE_VARCHAR)` - Create varchar
- `duckdb_create_logical_type(DUCKDB_TYPE_BIGINT)` - Create bigint
- `duckdb_create_logical_type(DUCKDB_TYPE_TIMESTAMP)` - Create timestamp
- `duckdb_create_logical_type(DUCKDB_TYPE_BOOLEAN)` - Create boolean

### Vector Operations
- `duckdb_vector_assign_string_element(vec, idx, str)` - Set string
- `duckdb_vector_assign_string_element_len(vec, idx, str, len)` - Set string with length
- `duckdb_validity_set_row_invalid(validity, row)` - Set NULL

### Value Extraction
- `duckdb_get_varchar(value)` - Get string from value
- `duckdb_get_int64(value)` - Get int64 from value

## Build Commands

```bash
# From extension root directory
make

# Test
make test

# Clean
make clean
```

## Extension Functions to Implement

| Function | Description |
|----------|-------------|
| `read_claude_conversations(path)` | Read JSONL conversation files |
| `read_claude_plans(path)` | Read markdown plan files |
| `read_claude_todos(path)` | Read JSON todo files |
| `read_claude_history(path)` | Read history.jsonl |
| `read_claude_stats(path)` | Read stats-cache.json |
