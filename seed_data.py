"""Initial SRNHS school-level dataset bundled with the dashboard.

The dashboard is designed to accept future school years through manual entry or
Excel upload.  Values here initialize a new installation only.
"""

SETTINGS = {
    "dashboard_title": "SRNHS School Profile Analysis Dashboard",
    "school_name": "Sto. Rosario National High School",
    "location": "Minalin, Pampanga",
    "subtitle": "Data-Driven Monitoring of Enrollment, Retention, Resources, and Teacher Deployment",
    "logo_url": "/static/assets/srnhs_logo.png",
    "login_background_url": "/static/assets/srnhs_school_background.jpg",
    "main_green": "#168447",
    "sidebar_color": "#071B12",
    "page_background": "#F8FBF8",
}

RECORDS = {
    "2021-2022": {
        "grades": [262, 266, 241, 224, 198, 189],
        "dropouts": [1, 2, 4, 2, 3, 0],
        "repeaters": [7, 4, 3, 1, 2, 3],
        "teachers": [11, 11, 6, 10, 8, 6],
    },
    "2022-2023": {
        "grades": [205, 267, 258, 224, 182, 169],
        "dropouts": [0, 1, 1, 0, 0, 0],
        "repeaters": [3, 6, 9, 3, 3, 1],
        "teachers": [10, 10, 8, 10, 8, 7],
    },
    "2023-2024": {
        "grades": [160, 196, 258, 239, 153, 168],
        "dropouts": [0, 0, 1, 1, 1, 0],
        "repeaters": [5, 12, 12, 7, 5, 0],
        "teachers": [9, 9, 8, 8, 8, 8],
    },
    "2024-2025": {
        "grades": [198, 160, 190, 235, 158, 148],
        "dropouts": [0, 4, 1, 0, 0, 5],
        "repeaters": [4, 0, 5, 8, 1, 1],
        "teachers": [9, 9, 8, 8, 8, 8],
    },
    "2025-2026": {
        "grades": [194, 187, 157, 176, 132, 156],
        "dropouts": [0, 2, 4, 0, 0, 0],
        "repeaters": [4, 6, 6, 5, 0, 0],
        "teachers": [9, 9, 8, 8, 8, 8],
    },
}

RESOURCES = {
    "2021-2022": {"jhs_classrooms": 28, "shs_classrooms": 10},
    "2022-2023": {"jhs_classrooms": 24, "shs_classrooms": 10},
    "2023-2024": {"jhs_classrooms": 24, "shs_classrooms": 10},
    "2024-2025": {"jhs_classrooms": 24, "shs_classrooms": 10},
    "2025-2026": {"jhs_classrooms": 24, "shs_classrooms": 10},
}

ROOM_SIZES = {
    "Grade 7": (7, 9),
    "Grade 8": (7, 9),
    "Grade 9": (9, 9),
    "Grade 10": (9, 9),
    "Grade 11": (9, 9),
    "Grade 12": (9, 9),
}

COHORT = {
    "2021-2022": {"baseline_year": "2016-2017", "grade7_baseline": 264, "grade12_current": 189},
    "2022-2023": {"baseline_year": "2017-2018", "grade7_baseline": 240, "grade12_current": 169},
    "2023-2024": {"baseline_year": "2018-2019", "grade7_baseline": 228, "grade12_current": 168},
    "2024-2025": {"baseline_year": "2019-2020", "grade7_baseline": 244, "grade12_current": 148},
    "2025-2026": {"baseline_year": "2020-2021", "grade7_baseline": 274, "grade12_current": 156},
}

ACTIONS = [
    {
        "school_year": "2025-2026",
        "analysis_type": "Prescriptive",
        "focus_area": "Enrollment Continuity",
        "observed_pattern": "Total enrollment declined across each recorded year from 1,380 to 1,002 students.",
        "data_basis": "Five-year enrollment trend: 1,380, 1,305, 1,174, 1,089, 1,002.",
        "suggested_action": "Strengthen feeder-school coordination and conduct an annual enrollment promotion schedule before enrollment season.",
        "responsible_group": "School Coordination Team",
        "target_indicator": "Total Enrollment and Grade 7 Intake",
        "baseline_value": "1,002 students in SY 2025-2026",
        "target_value": "Reduce further decline in next enrollment cycle",
        "monitoring_period": "Every enrollment period",
        "current_result": "For monitoring",
        "status": "Suggested",
        "progress_notes": "",
        "notes": "Review results after each enrollment period.",
    },
    {
        "school_year": "2025-2026",
        "analysis_type": "Prescriptive",
        "focus_area": "SHS Transition",
        "observed_pattern": "Current Grade 11 enrollment is lower than the previous year Grade 10 count.",
        "data_basis": "Grade 10 in SY 2024-2025: 235; Grade 11 in SY 2025-2026: 132.",
        "suggested_action": "Conduct a Grade 10 SHS plans survey and a one-day school-based orientation on available pathways.",
        "responsible_group": "Guidance and SHS Team",
        "target_indicator": "Transition Rate",
        "baseline_value": "56.17% in SY 2025-2026",
        "target_value": "Increase next Grade 11 continuation rate",
        "monitoring_period": "Before and after next enrollment",
        "current_result": "For monitoring",
        "status": "Suggested",
        "progress_notes": "",
        "notes": "Use survey summaries to improve the next orientation cycle.",
    },
    {
        "school_year": "2023-2024",
        "analysis_type": "Prescriptive",
        "focus_area": "Repeater Support",
        "observed_pattern": "Repeaters reached the highest recorded total of 41, concentrated particularly in Grades 8 and 9.",
        "data_basis": "SY 2023-2024 repeaters: 41; Grades 8 and 9 contribution: 24.",
        "suggested_action": "Organize targeted tutoring and early progress monitoring for grade levels showing elevated repeater counts.",
        "responsible_group": "Academic Support Team",
        "target_indicator": "Repeater Rate",
        "baseline_value": "3.49% in SY 2023-2024",
        "target_value": "Keep yearly repeater rate below peak baseline",
        "monitoring_period": "Quarterly and annual review",
        "current_result": "2.10% in SY 2025-2026",
        "status": "Ongoing",
        "progress_notes": "Continue monitoring grades with the highest latest counts.",
        "notes": "Compare each succeeding school-year repeater trend.",
    },
    {
        "school_year": "2025-2026",
        "analysis_type": "Prescriptive",
        "focus_area": "Classroom Planning",
        "observed_pattern": "Enrollment declined while total classroom count remained at 34 from SY 2022-2023 onward.",
        "data_basis": "Students per classroom fell from 36.3 in SY 2021-2022 to 29.5 in SY 2025-2026.",
        "suggested_action": "Review room utilization for possible learning-support or career-guidance activities using existing rooms.",
        "responsible_group": "Facilities and Guidance Team",
        "target_indicator": "Students per Classroom and Room Use",
        "baseline_value": "29.5 students/classroom in SY 2025-2026",
        "target_value": "Document productive support-room utilization",
        "monitoring_period": "Annual planning",
        "current_result": "For monitoring",
        "status": "Suggested",
        "progress_notes": "",
        "notes": "Confirm implementation through annual school planning.",
    },
    {
        "school_year": "2025-2026",
        "analysis_type": "Prescriptive",
        "focus_area": "Cohort Continuity",
        "observed_pattern": "Cohort survival is lower in the latest recorded cohort than in earlier years.",
        "data_basis": "Cohort survival in SY 2025-2026: 56.93%, compared with 71.59% in SY 2021-2022.",
        "suggested_action": "Maintain a cohort tracking summary and review possible learner movement or continuation patterns annually.",
        "responsible_group": "Guidance and Records Team",
        "target_indicator": "Cohort Survival Rate",
        "baseline_value": "56.93% in SY 2025-2026",
        "target_value": "Improve continuity in succeeding cohorts",
        "monitoring_period": "Annual cohort review",
        "current_result": "For monitoring",
        "status": "Suggested",
        "progress_notes": "",
        "notes": "Use aggregated records only.",
    },
]

GRADE_LABELS = ["Grade 7", "Grade 8", "Grade 9", "Grade 10", "Grade 11", "Grade 12"]
LEVELS = ["JHS", "JHS", "JHS", "JHS", "SHS", "SHS"]
