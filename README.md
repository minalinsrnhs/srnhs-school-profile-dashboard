# SRNHS School Profile Analysis Dashboard

Final submission package for **Sto. Rosario National High School, Minalin, Pampanga**.

## Final interface and functionality

- Approved full-screen login design with school photo and official logo.
- Modern green, white, and black dashboard layout with compact aligned pill filters.
- Six navigation sections: Dashboard, Analytics, Insights & Actions, School Records, Reports, Accounts.
- **All Years** shown by default; KPI cards combine every selected annual record rather than showing only the latest year, with multi-year and JHS/SHS filtering.
- One aligned KPI row on desktop; explanations open above KPI cards on hover or click.
- Interactive Chart.js graphs with readable legends and hover details.
- Descriptive, diagnostic, predictive, and prescriptive business-intelligence content in each Analytics tab.
- Editable school records, classroom/cohort values, action plans, and account-holder photos.
- Excel upload with Add/Update mode for new years and Full Sync mode for matching additions, edits, and removals.
- Safe deletion of a selected school year and action plans with warning prompts.
- **Undo Last Data Change** for accidental record edits, uploads, new-year saves, deletion, classroom/cohort edits, and action-plan edits.
- Updated Excel export that reflects the currently saved dashboard database.
- Downloadable blank New School Year Excel Upload Template under Reports; uploading it in Add/Update mode adds that new year without removing older records.
- KPI cards calculate combined totals and weighted rates from every selected school year when All Years or multiple years are selected.
- Two PDF reports: Dashboard Summary Paper and School Progress & Action Monitoring Report. PDF generation is already included through the `reportlab` package in `requirements.txt`.
- Mobile-responsive interface.
- SQLite local testing mode and Supabase-backed online multi-user mode.

## First local account

```text
Name: SRNHS Admin
Username: admin
Password: srnhsadmin
```

Use this only for first local testing. Change it before actual use, and set a new private initial password for online publication.

## Start locally

See `docs/LOCAL_SETUP.md`.

## Publish online

See `docs/DEPLOYMENT_GUIDE.md` for step-by-step GitHub, Supabase, Render, mobile, and multi-user setup.

## Excel synchronization note

Dashboard edits and uploads are saved to the active local or online database. Reports > **Full Updated Excel Workbook** generates a new workbook from those saved values, so additions and deletions are reflected in the downloadable Excel export. Browsers cannot silently overwrite an Excel file already saved on a user's computer.


## Final UI refinements

- The approved login page uses the transparent PNG school logo so the background blends with the campus photo.
- The Add School Year area stacks within its tab and does not require sideways scrolling.
- Recent Activity and saved record lists appear newest first.
- Forecast charts can expand to a full-width display by clicking the **Projected Enrollment** legend.
