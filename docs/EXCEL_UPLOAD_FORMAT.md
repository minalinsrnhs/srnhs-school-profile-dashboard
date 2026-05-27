# Adding New Data Through Excel Upload

Use either of these bundled workbooks:

- `excel/SRNHS_New_School_Year_Upload_Template.xlsx` for entering one additional school year.
- `excel/SRNHS_Dashboard_Data_Simple_Editable.xlsx` for full saved-data backup and multi-year updating.

## Accepted input sheet

The upload feature reads `DATA_ENTRY`, beginning at row 6, with these columns:

| Column | Required Content |
|---|---|
| School Year | Example: `2026-2027` |
| Level | `JHS` or `SHS` |
| Grade Level | `Grade 7` to `Grade 12` |
| Enrollment | Student count |
| Dropouts | Student count |
| Repeaters | Student count |
| Teachers | Teacher count |
| Dropout Rate | Formula cell, may remain formula-driven |
| Repeater Rate | Formula cell, may remain formula-driven |

When all grade rows for a new year are filled in and uploaded, that year appears in the dashboard year pills and analytics after the upload completes.

## Optional imported sheets

If included, the dashboard also reads:

- `RESOURCES` for classroom totals.
- `COHORT_TRANSITION` for cohort survival inputs.
- `ACTION_PLANS` for long-term suggested actions, indicators, target values, monitoring periods, status, and progress notes.

## Exported workbook

The Reports page generates a new formula-driven Excel workbook from all currently saved dashboard data. This provides a clean backup and editable reference copy after online changes are made.


## Two-way dashboard and Excel workflow

- Editing records in the dashboard updates the live saved records and the next downloaded Excel workbook.
- Uploading with **Add/Update** adds new years or refreshes matching school-year records without removing saved years absent from the upload.
- Uploading with **Full Sync** makes saved school records match the uploaded workbook, including removals. Use this only with a full intended master workbook and after confirming the warning.
- For published multi-user operation, the central online database is the live source, while Excel remains the editable upload/download and backup format.

## Deletion and correction workflow

- To remove a complete school year directly, use **School Records > Delete Selected School Year** after selecting that year.
- To reflect deletions made inside an Excel master workbook, upload the workbook using **Full Sync** mode.
- The app shows a confirmation warning before deletion.
- After deletion, the removed year no longer appears in subsequent Updated Excel downloads.
- Use **Undo Last Data Change** immediately after an accidental edit, upload, add-year save, deletion, cohort/classroom change, or action-plan change.
- Because a browser cannot silently rewrite a file stored on your laptop, download a new Updated Excel Workbook after final dashboard changes.
