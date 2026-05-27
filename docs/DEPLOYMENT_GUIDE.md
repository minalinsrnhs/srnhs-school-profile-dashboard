# Final Online Publication Guide: GitHub + Supabase + Render

## Important architecture note

For online multi-device use, this dashboard uses:

- **Flask** for the website and secure server actions.
- **Supabase PostgreSQL** as the central online database.
- **Server-side username/password authentication** with securely hashed passwords stored in the central database. Readable passwords are never exported or shown after saving.
- **Render Web Service** for hosting the Flask website.
- **Excel upload/export** as a controlled data exchange and downloadable backup/report format.

The app does **not** use a local Excel file as the live online database. This prevents one device from overwriting another device's records. Every updated Excel download is generated from the current central database.

## Current official platform references checked for this guide

- Render Flask deployment: `https://render.com/docs/deploy-flask`
- Render Web Services and Git-connected deployment: `https://render.com/docs/web-services`
- Render free services: `https://render.com/docs/free`
- Supabase Data API: `https://supabase.com/docs/guides/api`
- Supabase API key security: `https://supabase.com/docs/guides/getting-started/api-keys`
- Supabase data security and server-only keys: `https://supabase.com/docs/guides/database/secure-data`
- Supabase API access security: `https://supabase.com/docs/guides/api/securing-your-api`

Hosting limits and free-plan availability can change. Review current limits before treating a free deployment as permanent official infrastructure.

---

# Part A. Prepare the files before upload

1. Extract the final ZIP.
2. Do not rename or move these folders:
   - `static`
   - `templates`
   - `excel`
   - `sql`
   - `docs`
3. Do not upload a `.env` file with passwords or keys.
4. The included `.gitignore` prevents common local secret/database files from being committed.

---

# Part B. Create the GitHub repository

1. Log in to GitHub.
2. Click **New repository**.
3. Repository name recommendation:

```text
srnhs-minalin-dashboard
```

4. Set the repository to **Private** unless your school allows the code/assets to be public.
5. Click **Create repository**.
6. Click **uploading an existing file** or **Add file > Upload files**.
7. Upload the contents inside the extracted project folder, including:

```text
app.py
analytics.py
config.py
database.py
excel_export.py
seed_data.py
requirements.txt
Procfile
render.yaml
.gitignore
static/
templates/
excel/
sql/
docs/
```

8. Click **Commit changes**.
9. Check the repository file list. Confirm the school logo and school background appear within `static/assets/`.

---

# Part C. Create Supabase central storage

1. Log in to Supabase.
2. Click **New project**.
3. Suggested project name:

```text
SRNHS Dashboard
```

4. Set a strong private database password and keep it safely recorded outside the dashboard.
5. Wait for the project to finish provisioning.
6. Open **SQL Editor** in your Supabase project.
7. In your extracted ZIP folder, open:

```text
sql/supabase_schema.sql
```

8. Copy all SQL text and paste it into the Supabase SQL Editor.
9. Click **Run**.
10. Confirm that tables are created, including:

```text
dashboard_settings
account_holders
school_records
resources
room_sizes
cohort_records
action_plans
change_history
activity_logs
report_exports
workbook_exports
```

`change_history` supports the dashboard's **Undo Last Data Change** safety feature.

---

# Part D. Get the private Supabase server connection values

1. In the Supabase project, open the Connect dialog or Project Settings / API Keys area.
2. Copy the **Project URL**.
3. Copy the **server-only Secret key** intended for backend use. If your existing project shows only a legacy `service_role` key, this package supports that fallback too.
4. Never place that key into:
   - `static/app.js`
   - HTML templates
   - GitHub code
   - screenshots
   - messages shared publicly

It must be entered only in Render environment-variable settings.

---

# Part E. Deploy the Flask web app on Render

1. Log in to Render.
2. Click **New > Web Service**.
3. Connect GitHub when prompted.
4. Select your `srnhs-minalin-dashboard` repository.
5. Enter these settings:

```text
Name: srnhs-minalin-dashboard
Language / Runtime: Python
Build Command: pip install -r requirements.txt
Start Command: gunicorn app:app
```

6. Add these environment variables in Render:

```text
DATA_BACKEND=supabase
SESSION_COOKIE_SECURE=1
FLASK_SECRET_KEY=<create a long private random secret>
SUPABASE_URL=<paste your Supabase Project URL>
SUPABASE_SECRET_KEY=<paste your backend-only Supabase Secret key>
# Legacy only when your project uses it: SUPABASE_SERVICE_ROLE_KEY=<legacy backend-only service_role key>
FIRST_ACCOUNT_NAME=SRNHS Admin
FIRST_ACCOUNT_USERNAME=admin
FIRST_ACCOUNT_PASSWORD=<create a new private password for the online dashboard>
MAX_UPLOAD_MB=25
```

7. Never use `srnhsadmin` as the permanent public online password. That password is only the packaged local preview starter password.
8. Choose your service plan after checking the current Render plan limits. A free instance can be suitable for initial school testing, but confirm suitability for ongoing official use.
9. Click **Create Web Service** or **Deploy**.
10. Wait until the deployment log states the web service is live.
11. Open the generated `.onrender.com` site URL.

---

# Part F. First online login and data setup

1. Sign in using:

```text
Username: admin
Password: <the private FIRST_ACCOUNT_PASSWORD you entered in Render>
```

2. Open the account/profile menu and replace the initial password if needed.
3. Open **School Records**.
4. Upload the included Excel workbook if you want to populate/update records from the workbook format:

```text
excel/SRNHS_Dashboard_Data_Simple_Editable.xlsx
```

5. Choose **Add/Update** to add or revise years without removing existing data, or choose **Full Sync** only when the workbook should become the complete dashboard record, including deletions.
6. Confirm the upload warning.
7. Open the Dashboard and verify that cards and charts show school-year records. When **All Years** is selected, KPI cards summarize all selected annual records and rates use combined denominators.
8. Open Reports and download the Updated Excel Workbook to verify export behavior.
9. Download **New School Year Upload Template** when users need a blank format for a future school year.

---

# Part G. Multi-user and mobile testing

1. Open **Accounts > Account Holders**.
2. Add a second account holder with a new username, private password, and optional photo.
3. Use a phone or another laptop to open the Render URL.
4. Log in using the second account.
5. From one device, edit a test record and save it after the warning prompt.
6. Refresh the other device and confirm that its dashboard updates.
7. Verify Recent Activity includes the saved change.
8. Download the Updated Excel Workbook and verify the new values are included.
9. Test a temporary year deletion, then use **Undo Last Data Change** to restore it.

---

# Part H. How future data is added

There are two ways to add future school-year data:

## Option 1. Add inside the dashboard

1. Open **School Records > Add School Year**.
2. Enter the new school year.
3. Fill one input card per grade level.
4. Enter classroom and cohort information when available.
5. Review the computed preview.
6. Click **Save New School Year** and confirm.
7. The new year appears in dashboard pills, analytics, forecasts, reports, and the next updated Excel export.

## Option 2. Upload an updated Excel workbook

1. Download the latest Updated Excel Workbook from Reports.
2. Add or edit values in its formula-driven entry sheets, or download the blank New School Year Upload Template from Reports when encoding one new school year.
3. Save the `.xlsx` file.
4. Return to **School Records > Upload Updated Excel Workbook**.
5. Select **Add/Update** for a new year or value revision. Select **Full Sync** only when additions, updates, and deletions in a complete workbook must all match the dashboard.
6. Upload the file and confirm.
7. New and edited values appear immediately; records removed through Full Sync no longer appear in dashboard views or subsequent Excel exports.

---

# Part I. Deleting and undoing records safely

- To delete a year, open **School Records**, select that specific year in the record filter, and click **Delete Selected School Year**.
- The dashboard asks for confirmation before deleting.
- Deleted records are excluded from new Excel downloads.
- If the deletion was accidental, click **Undo Last Data Change** before making another major data change.
- The undo function also covers recent record edits, uploads, new-year additions, classroom/cohort changes, and action-plan changes.

---

# Part J. Critical security reminders

- Never publish readable passwords.
- Never commit Supabase secret keys or legacy service-role keys to GitHub.
- Never expose secret keys through JavaScript or HTML.
- Only upload aggregated school-level data, not learner names or private individual records.
- Keep at least one active account holder.
- Review activity logs and change account passwords periodically.


# Part K. Included PDF requirement

No separate ReportLab download is needed beyond the normal installation command. `reportlab` is already included in `requirements.txt`, so running `pip install -r requirements.txt` installs the PDF report generator automatically.


# Part L. Included dependencies

You do not need to download ReportLab separately. The included `requirements.txt` installs Flask, Gunicorn, Requests, Werkzeug, OpenPyXL for the dashboard Excel import/export runtime, and ReportLab for PDF reports when Render runs the build command `pip install -r requirements.txt`.
