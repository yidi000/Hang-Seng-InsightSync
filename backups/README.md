# Database Backup

The Postgres snapshot is committed as split parts because GitHub rejects single files larger than 100 MB.

To reconstruct the dump:

```bash
cat backups/insightsync_postgres_2026-05-06_curated_snapshot.dump.part-* > backups/insightsync_postgres_2026-05-06_curated_snapshot.dump
```
