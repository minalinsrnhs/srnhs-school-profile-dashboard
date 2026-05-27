# Update the Already-Published Online Dashboard

Because the dashboard is already running online, you do not need to create a new database or delete existing online data for this visual and automatic-baseline update.

## Replace these files in the existing GitHub repository

1. `static/style.css`
2. `static/app.js`
3. `templates/dashboard.html`
4. `app.py`
5. `docs/LATEST_UI_AND_COHORT_BASELINE_UPDATE.md` (optional documentation file)

## Why no database SQL change is required

The automatic baseline feature writes into the existing `cohort_records` fields. No new database columns are needed.

## After committing the files

- If Render Auto-Deploy is enabled, wait for the new deployment to finish.
- If Auto-Deploy is off, open Render and choose **Manual Deploy > Deploy latest commit**.
- Hard refresh the online browser page after deployment.
- Test: Dashboard mobile layout, Add School Year automatic baseline, and Excel upload of a test new year.

## Do not overwrite the live data unnecessarily

Do not run Full Sync with an incomplete Excel workbook. Use Add/Update for adding one new year.
