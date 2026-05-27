# Local Setup and Testing Guide

## What the ZIP includes

This final package contains the SRNHS dashboard interface, local database mode for testing, interactive analytics, Excel upload/export, PDF report exports, account-holder management with photos, deletion confirmations, and an **Undo Last Data Change** safety feature.

## 1. Extract the ZIP

1. Download the ZIP file.
2. Right-click it and choose **Extract All**.
3. Open the extracted `srnhs-minalin-dashboard-final-submission` folder.
4. Keep its folders unchanged, especially `templates`, `static`, `excel`, `sql`, and `docs`.

## 2. Install Python

Open Command Prompt and run:

```bat
py --version
```

Python 3.12 or later is recommended. When Python is not installed, install Python from its official installer and select **Add Python to PATH**.

## 3. Open Command Prompt in the project folder

In File Explorer, open the extracted project folder. Click the address bar, type `cmd`, and press Enter.

## 4. Create and activate a private environment

```bat
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## 5. Start the app locally

```bat
set FLASK_SECRET_KEY=replace-this-with-a-private-local-string
py app.py
```

Open this address in your browser:

```text
http://127.0.0.1:5000
```

## 6. First local login

```text
Username: admin
Password: srnhsadmin
```

For actual use, change the password immediately through the profile menu.

## 7. Test the final functions

### Dashboard
- All Years is selected by default.
- Select multiple year pills or a single year.
- Select All Grades, JHS, or SHS.
- Switch Forecast On or Off.
- Point to or click a KPI card to open its summarized explanation above the card.
- Hover on graph bars, slices, and points to view interactive values and legends.

### Analytics and Insights & Actions
- Review descriptive, diagnostic, predictive, and prescriptive analytics in every Analytics tab.
- Review dynamic highlights, school concerns, what-if scenarios, and action-plan monitoring.

### School Records
- Edit values from any record table. The app asks for confirmation before saving.
- Add a school year using one card per grade level.
- Upload an `.xlsx` workbook to add or update data. The app asks for confirmation first.
- Choose a specific year in the School Records filter, then use **Delete Selected School Year** to remove it after confirmation.
- Use **Undo Last Data Change** immediately after an accidental saved edit, upload, add-year action, delete-year action, classroom/cohort edit, or action-plan change.

### Reports
- Download the Updated Excel Workbook generated from currently saved dashboard values.
- Download the Dashboard Summary Paper PDF with graphs and analytics.
- Download the School Progress & Action Report PDF for annual monitoring.
- Download Excel workbooks for school records, action plans, and recent activity.

### Accounts
- Add account holders with an optional profile photo.
- Passwords display only as masked dots after saving.
- Log out and test a newly created account.
- Review Recent Activity for saved actions.

## Excel and dashboard reflection rule

In local or online mode, dashboard edits are stored in the application database. The **Full Updated Excel Workbook** download is generated from the current saved dashboard records, so additions and deletions appear in that new Excel export. A web app cannot silently overwrite an Excel file already saved on your personal device. To continue working in Excel, download the updated workbook from Reports after changes.
