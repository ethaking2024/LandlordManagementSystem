# LMS Installation Guide — End Users

This guide explains how a normal Windows user installs and runs the **Landlord Management System (LMS)** as a packaged desktop application. It assumes you are not a developer and have no Python or PyCharm installed.

LMS uses **PostgreSQL** for its database. PostgreSQL must be installed and a database created before the application can store data. This is a one-time setup.

---

## 1. System requirements

- Windows 10 or Windows 11 (64-bit)
- PostgreSQL 14 or newer (the free **PostgreSQL installer** from [postgresql.org](https://www.postgresql.org/download/windows/))
- The packaged `LMS` application folder (see section 3)

No Python, PyCharm, or other development tools are required.

---

## 2. One-time PostgreSQL setup

### 2.1 Install PostgreSQL

1. Download the PostgreSQL installer from <https://www.postgresql.org/download/windows/> (choose the latest 17.x or 16.x version).
2. Run the installer. When prompted for a **password** for the `postgres` superuser, choose a password you will remember and write it down.
3. Accept the default port **5432**.
4. The installer also installs the **PostgreSQL command line tools** (`pg_dump`, `pg_restore`, `psql`). LMS uses these tools for **Backup & Restore**, so leave them installed (they are installed by default).

### 2.2 Create the database

1. Open the **Start menu** and launch **SQL Shell (psql)**.
2. Press Enter for the defaults (server `localhost`, port `5432`, database `postgres`), and enter the `postgres` password you chose.
3. Create a database user and database by typing:

```sql
CREATE USER lms_user WITH PASSWORD 'choose_a_strong_password';
CREATE DATABASE lms_dev OWNER lms_user;
```

4. Type `\q` to exit.

---

## 3. Install the application

1. Copy the **entire** `LMS` folder (the release folder containing `LMS.exe`) to your computer, for example to `C:\Programs\LMS`.
2. Inside the folder you will find `LMS.exe`. You can create a shortcut to it on your desktop.

> Important: keep the whole `LMS` folder together. `LMS.exe` needs the other files next to it.

---

## 4. Configure the application (first run)

LMS reads its configuration from a file named `.env` located **next to `LMS.exe`**.

1. In the `LMS` folder you will find `env.example` (a template).
2. Copy it and rename the copy to **`.env`**.
3. Open `.env` with Notepad and set `DATABASE_URL` to your database. Replace `lms_user`, the password, and any other values you chose in section 2.2:

```
DATABASE_URL=postgresql+psycopg://lms_user:your_password@localhost:5432/lms_dev
```

4. Save the file.

> Never share this `.env` file — it contains your database password.

### 4.1 Apply the database schema (first run only)

The application ships with its database migrations. On first run, apply them once from a PowerShell window:

```powershell
cd C:\Programs\LMS
.\LMS.exe --migrate
```

An exit code of `0` means the schema was applied successfully. (You can check with `$LASTEXITCODE`.)

---

## 5. Run the application

Double-click `LMS.exe`, or run it from PowerShell:

```powershell
cd C:\Programs\LMS
.\LMS.exe
```

The main window opens with navigation on the left. All your data is stored in the PostgreSQL database you created.

---

## 6. Configuration reference

All settings live in the `.env` file next to `LMS.exe`.

| Setting | Required | Description |
| --- | --- | --- |
| `DATABASE_URL` | Yes | PostgreSQL connection string, e.g. `postgresql+psycopg://lms_user:password@localhost:5432/lms_dev` |
| `PG_BIN_DIR` | No | Folder containing `pg_dump`/`pg_restore`/`psql`. Usually not needed; LMS finds the tools automatically. Only set it if the tools are installed somewhere unusual. |
| `BACKUP_DIR` | No | Folder where backups are stored. Defaults to `%LOCALAPPDATA%\LMS\Backups` (your user data folder) — this keeps backups safe when you update the application. |
| `LOG_LEVEL` | No | `DEBUG`, `INFO`, `WARNING`, `ERROR`. Defaults to `DEBUG`. |

---

## 7. Backup & Restore

### 7.1 Create a backup

1. Open **Settings** from the sidebar.
2. Click **Create Backup**. A full database backup is written to the backup location shown on the page.

Backups are stored in `%LOCALAPPDATA%\LMS\Backups` (or your chosen `BACKUP_DIR`) — **outside** the application folder, so updating or re-installing LMS never deletes them.

### 7.2 Verify a backup

Click **Verify Backup...**, choose a `.dump` file, and LMS confirms it is a valid, restorable backup.

### 7.3 Restore a backup

1. Click **Restore from Backup...**.
2. Choose the `.dump` file to restore.
3. Confirm the warning. **Restoring replaces your current data with the contents of the backup** and cannot be undone.

Backups also work from the command line with the PostgreSQL tools if you prefer.

---

## 8. Updating the application

1. Close LMS.
2. Replace the contents of the `LMS` folder with the new release folder.
3. Keep your existing `.env` file (copy it back if you replaced the whole folder) — your configuration and backups are preserved.
4. Run `.\LMS.exe --migrate` once to apply any schema changes from the new version.
5. Start `LMS.exe`.

---

## 9. Troubleshooting

| Problem | Solution |
| --- | --- |
| The application does not start | Check that `.env` exists next to `LMS.exe` and that `DATABASE_URL` is correct (section 4). |
| "Database Error" when opening pages | PostgreSQL may not be running (start it from Services, e.g. `postgresql-x64-17`), or the password in `DATABASE_URL` is wrong. |
| Backup/Restore buttons fail | The PostgreSQL tools (`pg_dump`, `pg_restore`, `psql`) are not found. Re-install PostgreSQL, or set `PG_BIN_DIR` to the tools folder, e.g. `C:\Program Files\PostgreSQL\17\bin`. |
| `--migrate` fails | Make sure the database and user from section 2.2 exist and `DATABASE_URL` is correct. |

For a self-diagnosis, run from PowerShell:

```powershell
.\LMS.exe --self-check
```

A `0` exit code means configuration, database connection, and backup tooling are all available.
