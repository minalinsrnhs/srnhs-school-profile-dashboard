"""Dynamic business-intelligence calculations for the SRNHS dashboard.

All narrative output is derived from current stored records. Diagnostic language is
carefully worded as a question or investigation point unless supported by an
entered action/evidence record.
"""
from __future__ import annotations

from typing import Any
from seed_data import GRADE_LABELS


def safe_div(num: float, den: float) -> float | None:
    return None if den in (0, None) else num / den


def pct(value: float | None) -> float | None:
    return None if value is None else round(value * 100, 2)


def moneyless_num(value: float | int | None, digits: int = 1) -> str:
    if value is None:
        return "—"
    if float(value).is_integer():
        return f"{int(value):,}"
    return f"{value:,.{digits}f}"


def ordered_years(records: list[dict[str, Any]]) -> list[str]:
    return sorted({str(row["school_year"]) for row in records})


def records_by_year(records: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in records:
        grouped.setdefault(str(row["school_year"]), []).append(row)
    for year in grouped:
        grouped[year].sort(key=lambda r: GRADE_LABELS.index(r["grade_level"]) if r["grade_level"] in GRADE_LABELS else 99)
    return grouped


def linear_forecast(values: list[float], horizon: int = 2) -> list[int]:
    if len(values) < 2:
        return []
    n = len(values)
    xs = list(range(1, n + 1))
    mean_x = sum(xs) / n
    mean_y = sum(values) / n
    denom = sum((x - mean_x) ** 2 for x in xs)
    slope = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, values)) / denom if denom else 0
    intercept = mean_y - slope * mean_x
    return [int(round(intercept + slope * (n + i), 0)) for i in range(1, horizon + 1)]


def next_year(year: str, offset: int = 1) -> str:
    start, end = [int(x) for x in year.split("-")]
    return f"{start + offset}-{end + offset}"


def change_line(first: float | None, latest: float | None, rate: bool = False) -> tuple[float | None, float | None]:
    if first is None or latest is None:
        return None, None
    delta = round(latest - first, 2 if rate else 1)
    rel = pct(safe_div(latest - first, first)) if first else None
    return delta, rel


def direction(delta: float | None) -> str:
    if delta is None or delta == 0:
        return "remained unchanged"
    return "increased" if delta > 0 else "decreased"


def row_for_grade(grouped: dict[str, list[dict[str, Any]]], year: str, grade: str) -> dict[str, Any]:
    return next((row for row in grouped.get(year, []) if row.get("grade_level") == grade), {})


def statement(title: str, text: str, basis: str = "", indicator: str = "") -> dict[str, str]:
    return {"title": title, "text": text, "basis": basis, "indicator": indicator}


def compute_dashboard(
    records: list[dict[str, Any]],
    resources: list[dict[str, Any]],
    cohorts: list[dict[str, Any]],
    selected_years: list[str] | None = None,
    level: str = "All",
) -> dict[str, Any]:
    """Compute all dashboard values from the selected live records.

    Important behavior:
    - Charts always retain yearly values for trend reading.
    - When more than one year is selected, KPI cards show combined totals/rates
      across every selected year rather than showing only the latest year.
    """
    grouped = records_by_year(records)
    all_years = ordered_years(records)
    if not all_years:
        return {"years": [], "summary": [], "kpis": {}, "insights": [], "concerns": [], "suggested_actions": [], "bi_tabs": {}}

    chosen = [year for year in (selected_years or all_years) if year in all_years] or all_years
    chosen = sorted(chosen)
    resource_map = {str(item["school_year"]): item for item in resources}
    cohort_map = {str(item["school_year"]): item for item in cohorts}
    grade_breakdown: dict[str, dict[str, int]] = {}
    all_summary: dict[str, dict[str, Any]] = {}

    for year in all_years:
        rows = grouped[year]
        filtered = [row for row in rows if level == "All" or row.get("level") == level]
        enrollment = sum(int(row.get("enrollment", 0) or 0) for row in filtered)
        dropouts = sum(int(row.get("dropouts", 0) or 0) for row in filtered)
        repeaters = sum(int(row.get("repeaters", 0) or 0) for row in filtered)
        teachers = sum(int(row.get("teachers", 0) or 0) for row in filtered)
        jhs = sum(int(row.get("enrollment", 0) or 0) for row in rows if row.get("level") == "JHS")
        shs = sum(int(row.get("enrollment", 0) or 0) for row in rows if row.get("level") == "SHS")
        resource = resource_map.get(year, {})
        if level == "JHS":
            classrooms = int(resource.get("jhs_classrooms", 0) or 0)
        elif level == "SHS":
            classrooms = int(resource.get("shs_classrooms", 0) or 0)
        else:
            classrooms = int(resource.get("jhs_classrooms", 0) or 0) + int(resource.get("shs_classrooms", 0) or 0)

        cohort_rate = None
        cohort_base = cohort_current = None
        if level == "All" and year in cohort_map:
            cohort = cohort_map[year]
            cohort_base = int(cohort.get("grade7_baseline", 0) or 0)
            cohort_current = int(cohort.get("grade12_current", 0) or 0)
            cohort_rate = pct(safe_div(cohort_current, cohort_base))

        all_summary[year] = {
            "school_year": year,
            "enrollment": enrollment,
            "jhs": jhs,
            "shs": shs,
            "dropouts": dropouts,
            "dropout_rate": pct(safe_div(dropouts, enrollment)),
            "retained_count": enrollment - dropouts,
            "retention_rate": pct(safe_div(enrollment - dropouts, enrollment)),
            "repeaters": repeaters,
            "repeater_rate": pct(safe_div(repeaters, enrollment)),
            "teachers": teachers,
            "student_teacher_ratio": round(enrollment / teachers, 1) if teachers else None,
            "classrooms": classrooms or None,
            "students_per_classroom": round(enrollment / classrooms, 1) if classrooms else None,
            "cohort_survival": cohort_rate,
            "_cohort_base": cohort_base,
            "_cohort_current": cohort_current,
        }
        grade_breakdown[year] = {row["grade_level"]: int(row.get("enrollment", 0) or 0) for row in filtered}

    # Transition is a whole-school measure and remains hidden for JHS/SHS filtered views.
    for index, year in enumerate(all_years):
        previous_year = all_years[index - 1] if index > 0 else None
        if previous_year and level == "All":
            prev_g10 = int(row_for_grade(grouped, previous_year, "Grade 10").get("enrollment", 0) or 0)
            current_g11 = int(row_for_grade(grouped, year, "Grade 11").get("enrollment", 0) or 0)
            all_summary[year]["transition_rate"] = pct(safe_div(current_g11, prev_g10))
            all_summary[year]["transition_count_gap"] = prev_g10 - current_g11
            all_summary[year]["previous_grade10"] = prev_g10
            all_summary[year]["current_grade11"] = current_g11
        else:
            all_summary[year]["transition_rate"] = None
            all_summary[year]["transition_count_gap"] = None
            all_summary[year]["previous_grade10"] = None
            all_summary[year]["current_grade11"] = None

    for index, year in enumerate(all_years):
        prior = all_summary.get(all_years[index - 1]) if index else None
        current = all_summary[year]
        current["enrollment_change"] = current["enrollment"] - prior["enrollment"] if prior else None
        current["enrollment_change_pct"] = pct(safe_div(current["enrollment"] - prior["enrollment"], prior["enrollment"])) if prior else None
        current["dropout_change_pp"] = round(current["dropout_rate"] - prior["dropout_rate"], 2) if prior else None
        current["repeater_change_pp"] = round(current["repeater_rate"] - prior["repeater_rate"], 2) if prior else None

    summaries = [all_summary[year] for year in chosen]
    first = summaries[0]
    latest = summaries[-1]

    # Combined KPI view: when multiple years are selected, every selected
    # school year is included in the card totals and rate denominators.
    if len(chosen) > 1:
        combined_enrollment = sum(row["enrollment"] for row in summaries)
        combined_dropouts = sum(row["dropouts"] for row in summaries)
        combined_repeaters = sum(row["repeaters"] for row in summaries)
        combined_teachers = sum(row["teachers"] for row in summaries)
        combined_classrooms = sum(row["classrooms"] or 0 for row in summaries)
        cohort_base = sum(row.get("_cohort_base") or 0 for row in summaries)
        cohort_current = sum(row.get("_cohort_current") or 0 for row in summaries)
        transition_base = sum(row.get("previous_grade10") or 0 for row in summaries)
        transition_current = sum(row.get("current_grade11") or 0 for row in summaries)
        selection_summary = {
            "school_year": f"{chosen[0]} to {chosen[-1]}",
            "is_aggregate": True,
            "period_count": len(chosen),
            "enrollment": combined_enrollment,
            "jhs": sum(row["jhs"] for row in summaries),
            "shs": sum(row["shs"] for row in summaries),
            "dropouts": combined_dropouts,
            "dropout_rate": pct(safe_div(combined_dropouts, combined_enrollment)),
            "repeaters": combined_repeaters,
            "repeater_rate": pct(safe_div(combined_repeaters, combined_enrollment)),
            "teachers": combined_teachers,
            "student_teacher_ratio": round(combined_enrollment / combined_teachers, 1) if combined_teachers else None,
            "classrooms": combined_classrooms or None,
            "students_per_classroom": round(combined_enrollment / combined_classrooms, 1) if combined_classrooms else None,
            "cohort_survival": pct(safe_div(cohort_current, cohort_base)) if level == "All" else None,
            "transition_rate": pct(safe_div(transition_current, transition_base)) if level == "All" else None,
            "previous_grade10": transition_base or None,
            "current_grade11": transition_current or None,
            "cohort_base": cohort_base or None,
            "cohort_current": cohort_current or None,
        }
    else:
        selection_summary = {**latest, "is_aggregate": False, "period_count": 1}

    comparison_basis = first if len(summaries) > 1 else all_summary.get(all_years[all_years.index(chosen[0]) - 1]) if all_years.index(chosen[0]) > 0 else None
    comparison_label = f"Trend: {first['school_year']} to {latest['school_year']}" if len(summaries) > 1 else (f"vs {comparison_basis['school_year']}" if comparison_basis else "Current selection")

    forecast_basis_years = chosen if len(chosen) >= 2 else all_years
    forecast_values = linear_forecast([all_summary[y]["enrollment"] for y in forecast_basis_years], 2)
    forecast = [{"school_year": next_year(forecast_basis_years[-1], i + 1), "enrollment": value} for i, value in enumerate(forecast_values)]

    bi_tabs = build_bi_tabs(all_summary, chosen, grouped, level, forecast)
    insights = flatten_highlights(bi_tabs)
    concerns = generate_concerns(all_summary, chosen, grouped, level)
    suggestions = generate_actions(all_summary, chosen, grouped, level, forecast)
    kpis = build_kpis(all_summary, chosen, selection_summary, comparison_basis, comparison_label, level, forecast, grouped)

    return {
        "years": all_years,
        "selected_years": chosen,
        "selection_caption": "All recorded school years - combined KPI view" if chosen == all_years else (", ".join(chosen) + (" - combined KPI view" if len(chosen) > 1 else "")),
        "level": level,
        "summary": summaries,
        "all_summary": [all_summary[y] for y in all_years],
        "latest": latest,
        "first": first,
        "selection_summary": selection_summary,
        "grade_breakdown": grade_breakdown,
        "kpis": kpis,
        "forecast": forecast,
        "insights": insights,
        "concerns": concerns,
        "suggested_actions": suggestions,
        "comparisons": comparison_cards(all_summary, chosen),
        "grade_analysis": grade_analysis(grouped, chosen, level),
        "bi_tabs": bi_tabs,
        "formula_notes": {
            "transition": "Transition rate compares current Grade 11 enrollment with the previous school year's Grade 10 enrollment.",
            "forecast": "Projected values are trend-based planning estimates generated from the selected historical years and are not guaranteed future outcomes.",
            "combined_kpi": "When multiple years are selected, KPI cards calculate combined counts and weighted rates from all selected yearly records.",
        },
    }


def build_kpis(summary: dict[str, dict[str, Any]], years: list[str], display: dict[str, Any], baseline: dict[str, Any] | None, comparison_label: str, level: str, forecast: list[dict[str, Any]], grouped: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    first, latest = summary[years[0]], summary[years[-1]]
    use_base = first if len(years) > 1 else baseline
    projected_next = forecast[0]["enrollment"] if forecast else None
    is_aggregate = bool(display.get("is_aggregate"))
    scope = f"all {len(years)} selected years combined" if is_aggregate else f"SY {latest['school_year']}"

    def card(label: str, key: str, suffix: str, why: str, outlook: str, action: str, rate: bool = False, specific_what: str | None = None) -> dict[str, Any]:
        value = display.get(key)
        base_value = use_base.get(key) if use_base else None
        end_value = latest.get(key)
        if end_value is None or base_value is None:
            delta = relative = None
        elif rate:
            delta = round(end_value - base_value, 2)
            relative = None
        else:
            delta = round(end_value - base_value, 1)
            relative = pct(safe_div(end_value - base_value, base_value)) if base_value else None

        if specific_what:
            what = specific_what
        elif is_aggregate:
            shown = f"{value:.2f}{suffix}" if isinstance(value, float) and suffix == "%" else f"{moneyless_num(value)}{(' ' + suffix) if suffix not in {'%', ':1'} else suffix}"
            what = f"For {scope}, the calculated value is {shown}. The trend comparison below uses the first and latest selected years."
        else:
            shown = f"{value:.2f}{suffix}" if isinstance(value, float) and suffix == "%" else f"{moneyless_num(value)}{(' ' + suffix) if suffix not in {'%', ':1'} else suffix}"
            what = f"For {scope}, the calculated value is {shown}."

        return {
            "label": label,
            "value": value,
            "suffix": suffix,
            "change": delta,
            "change_pct": relative,
            "change_pp": delta if rate else None,
            "comparison_label": comparison_label,
            "series": [{"school_year": y, "value": summary[y].get(key)} for y in years],
            "hover_summary": {"what": what, "why": why, "next": outlook, "action": action},
        }

    enrollment_what = (
        f"Across all {len(years)} selected school years, there are {display['enrollment']:,} total recorded enrollment entries. "
        f"Annual enrollment moved from {first['enrollment']:,} in SY {first['school_year']} to {latest['enrollment']:,} in SY {latest['school_year']}."
        if is_aggregate else None
    )
    dropout_what = (
        f"Across all selected years, {display['dropouts']:,} recorded dropouts out of {display['enrollment']:,} enrollment entries produce a {display['dropout_rate']:.2f}% combined dropout rate."
        if is_aggregate else None
    )
    repeater_what = (
        f"Across all selected years, {display['repeaters']:,} recorded repeaters out of {display['enrollment']:,} enrollment entries produce a {display['repeater_rate']:.2f}% combined repeater rate."
        if is_aggregate else None
    )
    cohort_what = (
        f"Across selected cohorts, {display.get('cohort_current', 0):,} Grade 12 learners are compared with {display.get('cohort_base', 0):,} Grade 7 baseline learners, producing a {display['cohort_survival']:.2f}% combined cohort survival rate."
        if is_aggregate and display.get("cohort_survival") is not None else None
    )
    teacher_what = (
        f"Across all selected school years, {display['enrollment']:,} enrollment entries divided by {display['teachers']:,} recorded teacher assignments produce an aggregate {display['student_teacher_ratio']:.1f}:1 ratio."
        if is_aggregate else None
    )
    transition_what = (
        f"Across selected comparable transitions, {display.get('current_grade11', 0):,} Grade 11 enrollments are compared with {display.get('previous_grade10', 0):,} previous Grade 10 enrollments, producing a {display['transition_rate']:.2f}% combined transition rate."
        if is_aggregate and display.get("transition_rate") is not None else None
    )

    enrollment_outlook = f"The trend-based next-year estimate is {projected_next:,} students." if projected_next is not None else "Add more annual records to strengthen trend planning."
    return {
        "total_enrollment": card(
            "Total Enrollment", "enrollment", "students",
            "The recorded trend should be reviewed with feeder-school intake, continuing learners, and Grade 10-to-11 continuation information before assigning a cause.",
            enrollment_outlook,
            "Monitor new intake and SHS continuation each enrollment cycle, then compare against the selected baseline.",
            specific_what=enrollment_what,
        ),
        "dropout_rate": card(
            "Dropout Rate", "dropout_rate", "%",
            "Changes reflect recorded dropouts relative to enrollment; spikes should be examined by grade level and school-year context.",
            "Continue monitoring yearly and grade-level dropout movement rather than assuming a fixed trend.",
            "Review grade levels contributing the most dropouts and document suitable retention support.",
            rate=True, specific_what=dropout_what,
        ),
        "repeater_rate": card(
            "Repeater Rate", "repeater_rate", "%",
            "A higher rate may reflect learning gaps or academic-support needs; grade-level concentration provides the first review point.",
            "Without monitoring, grade levels with recurring high counts may remain priority areas in future years.",
            "Track targeted remediation and compare the next year's repeater rate against baseline.",
            rate=True, specific_what=repeater_what,
        ),
        "cohort_survival": card(
            "Cohort Survival", "cohort_survival", "%",
            "This follows a starting Grade 7 cohort to Grade 12 and may reflect transfers, non-continuation, or other learner movement that requires additional records.",
            "Lower continuity over time may reduce graduating cohort size unless learner pathways are reviewed.",
            "Use cohort follow-up and SHS orientation monitoring to support continuity planning.",
            rate=True, specific_what=cohort_what,
        ),
        "student_teacher_ratio": card(
            "Students / Teacher", "student_teacher_ratio", ":1",
            "The ratio moves when enrollment or teacher count changes; a lower ratio here follows declining enrollment with relatively stable teacher totals.",
            "If enrollment follows the current trend while teacher count stays stable, the ratio may decline further.",
            "Use the ratio together with deployment needs and program offerings when planning staffing.",
            specific_what=teacher_what,
        ),
        "transition_rate": card(
            "Transition Rate", "transition_rate", "%",
            "This compares Grade 11 enrollment with the corresponding previous Grade 10 count; the difference alone does not confirm transfers or dropouts.",
            "If the gap continues, SHS intake may remain a key monitoring concern.",
            "Conduct a Grade 10 intentions survey and compare actual Grade 11 intake during the next enrollment cycle.",
            rate=True, specific_what=transition_what,
        ),
    }


def build_bi_tabs(summary: dict[str, dict[str, Any]], years: list[str], grouped: dict[str, list[dict[str, Any]]], level: str, forecast: list[dict[str, Any]]) -> dict[str, dict[str, list[dict[str, str]]]]:
    first, latest = summary[years[0]], summary[years[-1]]
    length = len(years)
    enrollment_delta = latest["enrollment"] - first["enrollment"]
    enrollment_pct = pct(safe_div(enrollment_delta, first["enrollment"])) if length > 1 else None
    selected_rows = [summary[y] for y in years]
    largest_drop = min((row for row in selected_rows if row.get("enrollment_change") is not None), key=lambda row: row["enrollment_change"], default=None)
    highest_dropout = max(selected_rows, key=lambda row: row["dropouts"])
    highest_repeaters = max(selected_rows, key=lambda row: row["repeaters"])
    highest_cohort = max((row for row in selected_rows if row.get("cohort_survival") is not None), key=lambda row: row["cohort_survival"], default=None)
    lowest_cohort = min((row for row in selected_rows if row.get("cohort_survival") is not None), key=lambda row: row["cohort_survival"], default=None)
    latest_grade_repeaters = {r["grade_level"]: int(r.get("repeaters", 0) or 0) for r in grouped.get(latest["school_year"], [])}
    top_latest_rep = max(latest_grade_repeaters.items(), key=lambda x: x[1]) if latest_grade_repeaters else ("—", 0)
    g10_prev = latest.get("previous_grade10")
    g11_now = latest.get("current_grade11")
    forecast_one = forecast[0]["enrollment"] if forecast else None
    forecast_two = forecast[1]["enrollment"] if len(forecast) > 1 else None

    enrollment = {
        "descriptive": [
            statement("Enrollment Movement", f"Enrollment {direction(enrollment_delta)} from {first['enrollment']:,} students in SY {first['school_year']} to {latest['enrollment']:,} in SY {latest['school_year']}, a change of {abs(enrollment_delta):,} students{f' or {abs(enrollment_pct):.2f}%' if enrollment_pct is not None else ''}.", "Total enrollment by selected year."),
            statement("Largest Annual Shift", f"The largest annual decline within available comparisons occurred in SY {largest_drop['school_year']} at {abs(largest_drop['enrollment_change']):,} fewer students than the previous recorded year." if largest_drop else "Select multiple years to calculate yearly movement.", "Year-over-year enrollment movement."),
            statement("Latest JHS and SHS Composition", f"In SY {latest['school_year']}, JHS records {latest['jhs']:,} learners and SHS records {latest['shs']:,} learners, showing where current enrollment is concentrated.", "Enrollment grouped by school level."),
        ],
        "diagnostic": [
            statement("Pattern to Examine", "A continuing decline may relate to intake, continuing enrollment, learner movement, SHS choice, or local demographic conditions. The current records identify the pattern but do not confirm one cause.", "Enrollment totals and grade-level distributions."),
            statement("Intake Review Point", "Review Grade 7 intake together with nearby elementary-school feeder data to identify whether new entrants contribute to the downward trend.", "Grade 7 enrollment pattern."),
            statement("Continuation Review Point", "Review the Grade 10-to-Grade 11 transition information, as lower SHS intake can materially affect total school enrollment.", "Transition indicator and SHS enrollment."),
        ],
        "predictive": [
            statement("Next-Year Planning Estimate", f"Based on the historical trend represented in the selected data, estimated enrollment for {forecast[0]['school_year']} is {forecast_one:,} students." if forecast_one is not None else "At least two recorded years are needed for a projection.", "Linear trend planning estimate."),
            statement("Two-Year Outlook", f"The two-year planning estimate is {forecast_two:,} students in {forecast[1]['school_year']}. This estimate must be refreshed after new official enrollment data is added." if forecast_two is not None else "Add further years for an extended view.", "Linear trend planning estimate."),
        ],
        "prescriptive": [
            statement("Annual Enrollment Monitoring", "Create an annual intake and continuation monitoring cycle that compares Grade 7 intake, total enrollment, and Grade 11 continuation after every enrollment period.", "Target indicator: Total Enrollment."),
            statement("Feeder-School Coordination", "Coordinate an enrollment information activity with nearby feeder schools before the next enrollment period and compare Grade 7 intake results afterward.", "Target indicator: Grade 7 Enrollment."),
            statement("SHS Continuation Planning", "Conduct a Grade 10 intention survey and school-based SHS orientation before enrollment, then monitor the following Grade 11 intake.", "Target indicator: Transition Rate."),
        ],
    }
    retention = {
        "descriptive": [
            statement("Dropout Pattern", f"The highest dropout total in the selected years is {highest_dropout['dropouts']} in SY {highest_dropout['school_year']} at {highest_dropout['dropout_rate']:.2f}% of enrollment.", "Dropout count and dropout rate."),
            statement("Repeater Peak", f"Repeaters reached {highest_repeaters['repeaters']} in SY {highest_repeaters['school_year']}, equivalent to a {highest_repeaters['repeater_rate']:.2f}% repeater rate.", "Repeater count and rate."),
            statement("Latest Grade Attention", f"In SY {latest['school_year']}, {top_latest_rep[0]} has the highest recorded repeater count at {top_latest_rep[1]} among the latest grade-level entries.", "Latest grade-level repeater counts."),
        ],
        "diagnostic": [
            statement("Dropout Fluctuation Review", "A spike in dropout values requires review of grade-level circumstances and supporting school records. Numeric changes alone do not identify personal or external reasons.", "Dropout distribution by year and grade."),
            statement("Repeater Concentration Review", "When repeaters concentrate in particular grades, learning-support needs, subject-area performance summaries, and intervention records should be examined.", "Grade-level repeater contribution."),
        ],
        "predictive": [
            statement("Retention Monitoring Outlook", "Because dropout counts fluctuate rather than move consistently in one direction, the next year's rate should be treated as a monitoring result rather than forecast as a fixed outcome.", "Recorded dropout variation."),
            statement("Repeater Planning Outlook", "If grades with elevated repeater counts remain unsupported, they may continue to contribute disproportionately to the yearly total.", "Grade contribution pattern."),
        ],
        "prescriptive": [
            statement("Early Academic Support", "Schedule early progress review and targeted tutoring for grade levels contributing the most repeaters, then measure change in the following year.", "Target indicator: Repeater Rate."),
            statement("Dropout Follow-Up Summary", "Maintain an aggregated, privacy-safe summary of dropout cases by grade level and review changes during each school-year planning cycle.", "Target indicator: Dropout Rate."),
            statement("Intervention Tracker", "Record intervention dates, target grade levels, and yearly outcomes in Action Plans for long-term monitoring.", "Target indicator: Repeaters and Dropouts."),
        ],
    }
    continuity = {
        "descriptive": [
            statement("Cohort Range", f"Cohort survival is highest at {highest_cohort['cohort_survival']:.2f}% in SY {highest_cohort['school_year']} and lowest at {lowest_cohort['cohort_survival']:.2f}% in SY {lowest_cohort['school_year']}." if highest_cohort and lowest_cohort else "Cohort survival is available only for whole-school views.", "Cohort survival values."),
            statement("Latest Transition", f"For SY {latest['school_year']}, Grade 11 enrollment of {g11_now:,} represents {latest['transition_rate']:.2f}% of the previous Grade 10 enrollment of {g10_prev:,}." if latest.get("transition_rate") is not None else "Transition comparison is shown for whole-school views with previous-year data.", "Grade 10-to-Grade 11 continuity measure."),
        ],
        "diagnostic": [
            statement("Movement Records Needed", "A transition gap can relate to transfer, program preference, continuation decisions, or other movement. It must be reviewed through aggregated survey or continuation records before assigning cause.", "Transition gap and cohort trend."),
            statement("SHS Offering Review", "Learner intention surveys can help determine whether available SHS programs match learner preferences and career plans.", "Recommended evidence collection."),
        ],
        "predictive": [
            statement("Continuity Outlook", "If recent cohort and transition reductions continue, future SHS class sizes may remain smaller than earlier cohorts.", "Observed continuity indicators."),
            statement("Planning Trigger", "A continued transition rate decline in the next cycle should trigger a focused review of Grade 10 intentions and Grade 11 intake outcomes.", "Transition trend monitoring."),
        ],
        "prescriptive": [
            statement("Grade 10 Intention Survey", "Conduct an aggregated Grade 10 continuation and preferred-program survey before enrollment and compare intentions with actual Grade 11 enrollment.", "Target indicator: Transition Rate."),
            statement("SHS Orientation Cycle", "Provide annual SHS orientation with clear program pathways and monitor the resulting Grade 11 intake.", "Target indicator: Grade 11 Enrollment."),
            statement("Cohort Monitoring", "Maintain a yearly cohort tracker so survival patterns can be reviewed over a longer period.", "Target indicator: Cohort Survival Rate."),
        ],
    }
    teachers = {
        "descriptive": [
            statement("Teacher Count", f"Recorded teachers total {latest['teachers']} in SY {latest['school_year']}, compared with {first['teachers']} in SY {first['school_year']} for the selected period.", "Teacher totals by school year."),
            statement("Ratio Movement", f"Students per teacher changed from {first['student_teacher_ratio']:.1f}:1 to {latest['student_teacher_ratio']:.1f}:1 across the selected years.", "Enrollment divided by recorded teachers."),
        ],
        "diagnostic": [
            statement("Ratio Interpretation", "A lower student-teacher ratio in this dataset is largely associated with decreasing enrollment while teacher totals remain comparatively stable; it should not automatically be treated as improved instructional quality.", "Enrollment and teacher totals."),
            statement("Deployment Review", "Learning-area and SHS offering records should be examined before reallocating teachers or interpreting staffing needs.", "Teacher distribution context."),
        ],
        "predictive": [
            statement("Assumption-Based Ratio", f"If next-year projected enrollment is {forecast_one:,} and the teacher total remains at {latest['teachers']}, the ratio would be about {forecast_one/latest['teachers']:.1f}:1." if forecast_one and latest['teachers'] else "Set an assumed teacher count in What-If to calculate an outlook.", "Enrollment trend with constant teacher-count assumption."),
        ],
        "prescriptive": [
            statement("Deployment Review Cycle", "Review teacher deployment together with enrollment, class offerings, and learner program preferences before the next staffing plan.", "Target indicator: Student-Teacher Ratio and offering coverage."),
            statement("Scenario Planning", "Use the What-If tool to compare expected ratios under changing enrollment and teacher-count assumptions.", "Target indicator: Students per Teacher."),
        ],
    }
    resources = {
        "descriptive": [
            statement("Classroom Availability", f"Classrooms total {latest['classrooms']} in SY {latest['school_year']}, compared with {first['classrooms']} in SY {first['school_year']} in the selected view.", "Recorded classroom totals."),
            statement("Students per Classroom", f"The student-classroom ratio changed from {first['students_per_classroom']:.1f}:1 to {latest['students_per_classroom']:.1f}:1 across the selected years." if first.get('students_per_classroom') and latest.get('students_per_classroom') else "Enter classroom counts to calculate ratio trends.", "Enrollment divided by classrooms."),
        ],
        "diagnostic": [
            statement("Utilization Review", "A lower students-per-classroom ratio may indicate available space for support activities, subject to actual room schedules and room use records.", "Classroom and enrollment comparison."),
        ],
        "predictive": [
            statement("Capacity Outlook", f"If classrooms remain at {latest['classrooms']} and projected enrollment becomes {forecast_one:,}, the ratio would be about {forecast_one/latest['classrooms']:.1f} students per classroom." if forecast_one and latest.get('classrooms') else "Add classroom and projection data for capacity outlook.", "Constant classroom-count assumption."),
        ],
        "prescriptive": [
            statement("Learning Support Space", "Review whether available rooms can support remedial sessions, guidance activities, or SHS information sessions while maintaining normal class needs.", "Target indicator: Students per Classroom and Action Plan progress."),
            statement("Annual Room Review", "Update classroom counts and intended uses each year before drawing planning conclusions from capacity indicators.", "Target indicator: Classroom Utilization."),
        ],
    }
    return {"enrollment": enrollment, "retention": retention, "continuity": continuity, "teachers": teachers, "resources": resources}


def flatten_highlights(bi_tabs: dict[str, dict[str, list[dict[str, str]]]]) -> list[dict[str, str]]:
    labels = {"enrollment": "Enrollment", "retention": "Retention", "continuity": "Continuity", "teachers": "Teachers", "resources": "Resources"}
    highlights: list[dict[str, str]] = []
    for key in ["enrollment", "retention", "continuity", "teachers", "resources"]:
        for item in bi_tabs[key]["descriptive"][:2]:
            highlights.append({"category": labels[key], "title": item["title"], "text": item["text"]})
    return highlights


def generate_concerns(summary: dict[str, dict[str, Any]], years: list[str], grouped: dict[str, list[dict[str, Any]]], level: str) -> list[dict[str, str]]:
    first, latest = summary[years[0]], summary[years[-1]]
    concerns: list[dict[str, str]] = []
    if len(years) > 1 and latest["enrollment"] < first["enrollment"]:
        concerns.append({"level": "High", "title": "Enrollment Decline", "text": f"Enrollment is {first['enrollment'] - latest['enrollment']:,} students below the first selected year. Review intake and continuation patterns annually."})
    if level == "All" and latest.get("transition_rate") is not None and latest["transition_rate"] < 70:
        concerns.append({"level": "High", "title": "SHS Continuity", "text": f"Latest transition rate is {latest['transition_rate']:.2f}%. Collect Grade 10 intention and actual continuation information."})
    highest_rep = max((summary[y] for y in years), key=lambda row: row["repeaters"])
    if highest_rep["repeaters"] >= 25:
        concerns.append({"level": "Moderate", "title": "Repeater Concentration", "text": f"Repeaters peaked at {highest_rep['repeaters']} in SY {highest_rep['school_year']}. Review grade-level academic support trends."})
    if latest.get("cohort_survival") is not None and latest["cohort_survival"] < 65:
        concerns.append({"level": "High", "title": "Cohort Continuity", "text": f"Latest cohort survival is {latest['cohort_survival']:.2f}%. Continue long-term cohort tracking and follow-up."})
    if latest.get("students_per_classroom") is not None and latest["students_per_classroom"] < 32:
        concerns.append({"level": "Planning", "title": "Space Utilization", "text": f"Latest ratio is {latest['students_per_classroom']:.1f} students per classroom. Review possible support-room uses alongside schedules."})
    return concerns


def generate_actions(summary: dict[str, dict[str, Any]], years: list[str], grouped: dict[str, list[dict[str, Any]]], level: str, forecast: list[dict[str, Any]]) -> list[dict[str, str]]:
    latest = summary[years[-1]]
    return [
        {"title": "Enrollment Monitoring Cycle", "action": "Track Grade 7 intake and total enrollment after every enrollment period; compare actual results with the selected historical baseline.", "basis": f"Latest enrollment: {latest['enrollment']:,} students.", "monitor": "Total Enrollment and Grade 7 Intake", "period": "Every school year"},
        {"title": "SHS Continuation Review", "action": "Administer a Grade 10 intention survey and provide SHS orientation before enrollment; compare results with next Grade 11 intake.", "basis": f"Latest transition rate: {latest.get('transition_rate'):.2f}%" if latest.get('transition_rate') is not None else "Use whole-school view for transition data.", "monitor": "Transition Rate", "period": "Before and after enrollment"},
        {"title": "Targeted Academic Support", "action": "Use grade-level repeater data to prioritize tutoring, early progress review, and intervention tracking for affected classes.", "basis": f"Latest repeaters: {latest['repeaters']} students.", "monitor": "Repeater Count and Rate", "period": "Quarterly and yearly"},
        {"title": "Cohort Continuity Tracking", "action": "Keep an annual cohort tracker and review Grade 12 outcomes against Grade 7 baseline counts.", "basis": f"Latest cohort survival: {latest.get('cohort_survival'):.2f}%" if latest.get('cohort_survival') is not None else "Whole-school cohort measure only.", "monitor": "Cohort Survival", "period": "Annual"},
        {"title": "Classroom Utilization Plan", "action": "Review available rooms for remedial, guidance, or SHS information activities while maintaining class schedules.", "basis": f"Latest students/classroom: {latest.get('students_per_classroom'):.1f}" if latest.get('students_per_classroom') else "Add classroom records.", "monitor": "Students per Classroom", "period": "Annual planning"},
        {"title": "Forecast Review", "action": "Compare next recorded enrollment with the trend estimate and revise actions when actual data differs.", "basis": f"Next-year estimate: {forecast[0]['enrollment']:,}" if forecast else "Projection requires two years.", "monitor": "Projected versus Actual Enrollment", "period": "Next enrollment cycle"},
    ]


def comparison_cards(summary: dict[str, dict[str, Any]], years: list[str]) -> list[dict[str, Any]]:
    first, latest = summary[years[0]], summary[years[-1]]
    pairs = [
        ("Enrollment", "enrollment", "students", False),
        ("Dropout Rate", "dropout_rate", "pp", True),
        ("Repeater Rate", "repeater_rate", "pp", True),
        ("Students / Teacher", "student_teacher_ratio", ":1", False),
        ("Students / Classroom", "students_per_classroom", ":1", False),
        ("Cohort Survival", "cohort_survival", "pp", True),
    ]
    cards = []
    for label, key, suffix, rate in pairs:
        before, after = first.get(key), latest.get(key)
        if before is None or after is None:
            continue
        delta = round(after - before, 2 if rate else 1)
        cards.append({"label": label, "first": before, "latest": after, "delta": delta, "suffix": suffix, "basis": f"{first['school_year']} to {latest['school_year']}"})
    return cards


def grade_analysis(grouped: dict[str, list[dict[str, Any]]], years: list[str], level: str) -> list[dict[str, Any]]:
    first_rows = {r["grade_level"]: r for r in grouped[years[0]] if level == "All" or r["level"] == level}
    latest_rows = {r["grade_level"]: r for r in grouped[years[-1]] if level == "All" or r["level"] == level}
    out = []
    for grade in GRADE_LABELS:
        if grade not in latest_rows or grade not in first_rows:
            continue
        first = int(first_rows[grade].get("enrollment", 0) or 0)
        latest = int(latest_rows[grade].get("enrollment", 0) or 0)
        rep = int(latest_rows[grade].get("repeaters", 0) or 0)
        out.append({"grade_level": grade, "first": first, "latest": latest, "change": latest - first, "repeaters_latest": rep, "dropouts_latest": int(latest_rows[grade].get("dropouts", 0) or 0)})
    return out
