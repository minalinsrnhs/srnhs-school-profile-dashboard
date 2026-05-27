# Final Submission Changelog

## Final revisions applied

- All Years is the default selection and KPI cards aggregate all selected school years.
- KPI card explanations summarise what happened, why the trend should be reviewed, what may happen next, and what action may be considered.
- Grade-level dashboard visuals also represent the combined selected period when multiple years or All Years are active.
- Forecast legend interaction expands forecast charts to use the full content width.
- Compact green pill filters remain aligned for All Grades, JHS, and SHS.
- Add School Year entry remains inside its panel without horizontal scrolling and stacks responsively on smaller screens.
- Excel upload supports adding/updating a future year through the downloadable New School Year Upload Template.
- Delete School Year, action-plan deletion, and undo-last-data-change safeguards are included.
- Reports include Dashboard Summary PDF, School Progress and Action Monitoring PDF, updated Excel workbook exports, and the new-year Excel template.
- Profile photos are available in account holder management.
- The transparent PNG school logo is used for the approved login and dashboard branding.
- Recent activity and data record lists show latest entries first.

## Deployment note

The ZIP is deployment-ready but not deployed automatically. Publication requires the school to provide its own GitHub repository, Supabase project, backend-only Supabase Secret key, Render account, and a new private online password.

## KPI Analysis Panel Layout Update
- KPI analysis details now display in a dedicated panel below the KPI cards and above the graphs.
- Hover, focus, or tap/click a KPI card to update the visible panel without overlapping the header or filters.
- Mobile view stacks the explanation blocks for readability.
