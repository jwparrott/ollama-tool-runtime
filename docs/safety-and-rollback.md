# Safety, Testing, and Rollback

Core files:

- [agent_runtime/self_update.py](../agent_runtime/self_update.py)
- [agent_runtime/snapshots.py](../agent_runtime/snapshots.py)

## Why this exists

Because the model can request project updates, the runtime protects against lockout and broken states.

## Update safety pipeline

`SelfUpdater.update_files(...)` does:

1. validate target paths stay inside project root
2. create snapshot
3. write requested files
4. run tests
5. if tests fail, restore snapshot automatically

## Snapshot storage

- snapshot archives: `.runtime/snapshots/snapshot-<id>.zip`
- index: `.runtime/snapshots/index.json`

`SnapshotManager.restore(...)` restores project files while preserving runtime storage directory (`.runtime`).

## Manual controls

- Create snapshot:
  - `python main.py snapshot --note "before-change"`
- View snapshot records:
  - `python main.py list-tools` and call `list_snapshots` via model, or inspect index file directly
- Roll back:
  - `python main.py rollback --id <snapshot-id>`

## Testing

Default configured test command:

- `python -m unittest discover -s tests`

Run manually:

```powershell
python main.py run-tests
```

