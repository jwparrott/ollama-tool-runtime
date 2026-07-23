# Built-in Tool Functions

Defined in [agent_runtime/builtin_tools.py](../agent_runtime/builtin_tools.py).

These are exposed to the LLM automatically in every tool-enabled chat.

## `register_python_tool`

Purpose:
- create a new custom Python tool file
- add it to the registry

Inputs:
- `name`
- `description`
- `parameters_schema_json`
- `source_code`

Use when:
- adding capabilities without editing runtime internals

## `self_update_files`

Purpose:
- update one or more files in the repo safely

Inputs:
- `files_json` (path -> full file content)
- `note` (snapshot note)
- `test_command` (optional)

Behavior:
1. creates snapshot
2. writes files
3. runs tests
4. rolls back automatically if tests fail

Use when:
- LLM needs to modify project code with protection against lockout/breakage

## `run_tests`

Purpose:
- run test command and return stdout/stderr

Input:
- `test_command` (optional)

Use when:
- validating changes before/after updates

## `list_model_skills`

Purpose:
- list reusable workflow skills/playbooks the model can follow

Use when:
- deciding how to approach a task (review, research, testing, safe updates, new-tool development)

## `get_model_skill`

Purpose:
- fetch one workflow skill/playbook by name

Input:
- `name`

Use when:
- the model needs explicit step-by-step guidance for a specific workflow

## `list_snapshots`

Purpose:
- return snapshot index records

Use when:
- selecting rollback target

## `rollback_snapshot`

Purpose:
- restore project state from snapshot id

Input:
- `snapshot_id`

Use when:
- bad update needs recovery

## `list_tools`

Purpose:
- enumerate built-in + custom tool availability

Use when:
- checking whether expected tools are registered and enabled
