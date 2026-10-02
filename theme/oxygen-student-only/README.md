# Hide student-only content in the instructor edition (issue #198)

Every gram page carries a **7 Questions** section and a matching "7 Questions"
jump link, both tagged `audience="student-only"` by `generate_dita.py`.
`instructor.ditaval` strips them — but the Oxygen instructor scenario is
normally published with **no DITAVAL at all**, and an unfiltered build keeps
them, so instructors saw the 7 Questions image on every gram.

`resources/student-only.css` hides both at render time on any page whose
edition marker says *instructor*. The marker is the one
`theme/oxygen-hide-search/xslt/inc/customSearchFlag.xsl` already injects on
every page: alongside `wh-search-hidden` / `wh-search-shown` it now also
carries `wh-edition-student` / `wh-edition-instructor`, derived from the same
test (does the scenario's DITAVAL exclude `audience="-trainee"`?). Nothing to
configure — no parameter, no re-tagging of the source.

| Scenario | `args.filter` | 7 Questions on gram pages |
| --- | --- | --- |
| instructor | blank | present in the HTML, hidden by this CSS |
| instructor | `instructor.ditaval` | filtered out by DITA-OT (CSS unused) |
| student | `trainee.ditaval` | shown |

Instructors keep the root-level **7 Questions** nav topic (`7_questions.html`),
which is unfiltered by design and not matched here.

Wired into `theme/pptx-transform/pptx-transform.opt` as
`resources/student-only.css`, after the stock stylesheets.
