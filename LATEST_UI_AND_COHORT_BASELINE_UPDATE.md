# Latest Interface and Automatic Cohort Baseline Update

## Interface refinements

- Dashboard typography is compact and readable, with most working text kept within 12 to 15 pixels.
- Large unused gaps in chart and analytics cards were reduced by allowing panels to use their content height rather than forced tall blocks.
- Charts remain arranged as two panels per row on desktop and stack cleanly on phones.
- The dashboard's mobile layout uses smaller, aligned KPI cards, filters, data-entry fields, panels, and modals.
- The mobile login layout uses a smaller logo, compact username/password pills, and a login card that fits narrow screens.

## Automatic cohort baseline in Add School Year

When adding a school year, the dashboard automatically looks for the Grade 7 enrollment from five school years earlier to use as the cohort baseline for the new Grade 12 year.

Example:

- New year entered: `2026-2027`
- Automatic baseline year: `2021-2022`
- Baseline source: stored Grade 7 enrollment for SY 2021-2022
- Existing starting data value: `262`

The Grade 12 current enrollment is taken directly from the new Grade 12 entry in the Add School Year form.

If the required historical Grade 7 year does not exist in the stored records, the dashboard displays a manual baseline input area. A baseline should only be entered there when an official historical value is available.

## Excel upload behavior

After an Excel upload, the dashboard also automatically creates or refreshes cohort baseline values whenever the required Grade 7 historical enrollment exists in saved data. It does not invent a baseline when historical data are missing.

## Files changed in this update

- `static/style.css`
- `static/app.js`
- `templates/dashboard.html`
- `app.py`

The database schema does not require a change for this feature because the existing cohort fields store the resulting baseline year and baseline count.
