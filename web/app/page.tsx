"use client";

import { useMemo, useState } from "react";
import { generatePlan, Inputs } from "@/lib/api";

const defaultInputs: Inputs = {
  catalog_path: "data/foothill_catalog.csv",
  goal: "cs",

  // REMOVE / stop using:
  // starting_math: "honors_algebra2",

  // ADD:
  completed_math: "Honors Algebra II (P)",

  science_pathway: "standard_stem",
  prefer_spanish: true,
  completed_courses: ["Honors Geometry (P)", "Spanish II (P)"],

  // ADD (C):
  course_level_prefs: { english: "honors", history: "ap", science: "regular" },

  gpa: { default_letter: "A", overrides: {} },
  uc_cfg: { max_bonus_semesters: 8, honors_keywords: ["(HP)", "AP ", "Honors "] },
};


function Badge({ ok, text }: { ok: boolean; text: string }) {
  return (
    <span
      className={[
        "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium border",
        ok ? "bg-green-50 border-green-200 text-green-800" : "bg-red-50 border-red-200 text-red-800",
      ].join(" ")}
    >
      {text}
    </span>
  );
}

export default function Home() {
  const [inputs, setInputs] = useState<Inputs>(defaultInputs);
  const [loading, setLoading] = useState(false);
  const [report, setReport] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const completedText = useMemo(
    () => inputs.completed_courses.join("\n"),
    [inputs.completed_courses]
  );

  async function onGenerate() {
    setLoading(true);
    setError(null);
    try {
      const r = await generatePlan(inputs);
      setReport(r);
    } catch (e: any) {
      setError(e?.message ?? "Failed to generate plan");
      setReport(null);
    } finally {
      setLoading(false);
    }
  }

  const validationOk =
    report &&
    (report.validation?.backtracking_errors?.length ?? 0) === 0 &&
    (report.validation?.offered_by_grade_errors?.length ?? 0) === 0;

  return (
    <main className="min-h-screen p-6">
      <div className="mx-auto max-w-6xl grid gap-6">
        <header className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold">High School Planning Optimizer</h1>
            <p className="text-sm text-gray-600">
              Generate a 4-year plan + UC A–G / PUSD graduation audits + GPA summaries.
            </p>
          </div>

          <div className="flex gap-2">
            {report ? (
              <Badge ok={!!validationOk} text={validationOk ? "Valid Plan" : "Check Validation"} />
            ) : (
              <Badge ok={true} text="Ready" />
            )}
          </div>
        </header>

        <div className="grid md:grid-cols-3 gap-6">
          {/* Inputs */}
          <section className="rounded-2xl border p-4 md:col-span-1">
            <h2 className="font-semibold mb-3">Inputs</h2>

            <label className="text-sm">Goal</label>
            <select
              className="w-full border rounded-lg p-2 mb-3"
              value={inputs.goal}
              onChange={(e) => setInputs({ ...inputs, goal: e.target.value as any })}
            >
              <option value="cs">CS</option>
              <option value="pre_med">Pre-Med</option>
              <option value="biotech">Biotech</option>
            </select>

            <label className="text-sm">Highest Completed Math</label>
            <select
              className="w-full border rounded-lg p-2 mb-3"
              value={inputs.completed_math ?? ""}
              onChange={(e) =>
                setInputs({ ...inputs, completed_math: e.target.value || null })
              }
            >
              <option value="">(not set)</option>
              <option value="Geometry (P)">Geometry (P)</option>
              <option value="Honors Geometry (P)">Honors Geometry (P)</option>
              <option value="Algebra II (P)">Algebra II (P)</option>
              <option value="Honors Algebra II (P)">Honors Algebra II (P)</option>
              <option value="Pre-Calculus (P)">Pre-Calculus (P)</option>
              <option value="Honors Pre-Calculus (HP)">Honors Pre-Calculus (HP)</option>
            </select>


            <label className="text-sm">English Level Preference</label>
            <select
              className="w-full border rounded-lg p-2 mb-3"
              value={inputs.course_level_prefs?.english ?? "regular"}
              onChange={(e) =>
                setInputs({
                  ...inputs,
                  course_level_prefs: {
                    ...(inputs.course_level_prefs ?? {}),
                    english: e.target.value,
                  },
                })
              }
            >
              <option value="regular">Regular</option>
              <option value="honors">Honors</option>
              <option value="ap">AP</option>
            </select>

            <label className="text-sm">History Level Preference</label>
            <select
              className="w-full border rounded-lg p-2 mb-3"
              value={inputs.course_level_prefs?.history ?? "regular"}
              onChange={(e) =>
                setInputs({
                  ...inputs,
                  course_level_prefs: {
                    ...(inputs.course_level_prefs ?? {}),
                    history: e.target.value,
                  },
                })
              }
            >
              <option value="regular">Regular</option>
              <option value="honors">Honors</option>
              <option value="ap">AP</option>
            </select>

            <label className="text-sm">Science Pathway</label>
            <select
              className="w-full border rounded-lg p-2 mb-3"
              value={inputs.science_pathway}
              onChange={(e) => setInputs({ ...inputs, science_pathway: e.target.value as any })}
            >
              <option value="standard_stem">Standard STEM</option>
              <option value="pltw_biomed">PLTW Biomed</option>
              <option value="physics_first">Physics First</option>
            </select>

            <label className="flex items-center gap-2 mb-3 text-sm">
              <input
                type="checkbox"
                checked={inputs.prefer_spanish}
                onChange={(e) => setInputs({ ...inputs, prefer_spanish: e.target.checked })}
              />
              Prefer Spanish pathway
            </label>

            <label className="text-sm">Completed Courses (one per line)</label>
            <textarea
              className="w-full border rounded-lg p-2 mb-3 h-28 font-mono text-xs"
              value={completedText}
              onChange={(e) =>
                setInputs({
                  ...inputs,
                  completed_courses: e.target.value
                    .split("\n")
                    .map((s) => s.trim())
                    .filter(Boolean),
                })
              }
            />

            <label className="text-sm">Default Letter Grade</label>
            <select
              className="w-full border rounded-lg p-2 mb-4"
              value={inputs.gpa.default_letter}
              onChange={(e) =>
                setInputs({
                  ...inputs,
                  gpa: { ...inputs.gpa, default_letter: e.target.value as any },
                })
              }
            >
              <option value="A">A</option>
              <option value="B">B</option>
              <option value="C">C</option>
            </select>

            <button
              onClick={onGenerate}
              className="w-full rounded-xl bg-black text-white py-2 disabled:opacity-50"
              disabled={loading}
            >
              {loading ? "Generating..." : "Generate Plan"}
            </button>

            {error && (
              <div className="mt-3 rounded-xl border border-red-200 bg-red-50 p-3">
                <div className="text-sm font-semibold text-red-800">Error</div>
                <pre className="text-xs text-red-800 whitespace-pre-wrap mt-2">{error}</pre>
              </div>
            )}
          </section>

          {/* Outputs */}
          <section className="rounded-2xl border p-4 md:col-span-2">
            <h2 className="font-semibold mb-3">Results</h2>

            {!report ? (
              <p className="text-sm text-gray-600">Enter inputs and click Generate.</p>
            ) : (
              <div className="grid gap-6">
                {/* Summary cards */}
                <div className="grid md:grid-cols-3 gap-4">
                  <div className="rounded-xl border p-3">
                    <h3 className="font-semibold mb-2">UC GPA</h3>
                    <div className="text-sm grid gap-1">
                      <div>Unweighted (9–11): {report.uc_gpa.unweighted_9_11.gpa}</div>
                      <div>Unweighted (10–11): {report.uc_gpa.unweighted_10_11.gpa}</div>
                      <div>Weighted & Capped (10–11): {report.uc_gpa.weighted_capped_10_11.weighted_capped_gpa}</div>
                    </div>
                  </div>

                  <div className="rounded-xl border p-3">
                    <h3 className="font-semibold mb-2">HS GPA</h3>
                    <div className="text-sm grid gap-1">
                      <div>Unweighted: {report.hs_gpa.hs_unweighted_gpa}</div>
                      <div>Weighted: {report.hs_gpa.hs_weighted_gpa}</div>
                    </div>
                  </div>

                  <div className="rounded-xl border p-3">
                    <h3 className="font-semibold mb-2">Validation</h3>
                    <div className="flex flex-wrap gap-2">
                      <Badge ok={(report.validation.backtracking_errors?.length ?? 0) === 0} text="No Backtracking" />
                      <Badge ok={(report.validation.offered_by_grade_errors?.length ?? 0) === 0} text="Offered By Grade" />
                      <Badge ok={(report.uc_ag.gaps?.length ?? 0) === 0} text="UC A–G" />
                    </div>
                  </div>
                </div>

                {/* Plan grid */}
                <div className="rounded-xl border p-3">
                  <h3 className="font-semibold mb-2">4-Year Plan</h3>

                  <div className="grid gap-4">
                    {report.plan.plan.map((yr: any) => (
                      <div key={yr.grade} className="rounded-xl border p-3">
                        <div className="font-semibold mb-2">Grade {yr.grade}</div>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                          {yr.courses.map((slot: any, idx: number) => (
                            <div key={idx} className="rounded-lg border px-3 py-2 text-sm">
                              <div className="text-xs text-gray-500 mb-1">Period {idx + 1}</div>
                              <div className="font-medium">
                                {Array.isArray(slot) ? `${slot[0]} / ${slot[1]}` : slot}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Audits (collapsible) */}
                <div className="grid gap-3">
                  <details className="rounded-xl border p-3">
                    <summary className="cursor-pointer font-semibold">UC A–G Audit</summary>
                    <div className="mt-3 text-sm">
                      <pre className="text-xs whitespace-pre-wrap">
                        {JSON.stringify(report.uc_ag, null, 2)}
                      </pre>
                    </div>
                  </details>

                  <details className="rounded-xl border p-3">
                    <summary className="cursor-pointer font-semibold">PUSD Graduation Audit</summary>
                    <div className="mt-3 text-sm">
                      <pre className="text-xs whitespace-pre-wrap">
                        {JSON.stringify(report.pusd_grad, null, 2)}
                      </pre>
                    </div>
                  </details>

                  <details className="rounded-xl border p-3">
                    <summary className="cursor-pointer font-semibold">Validation Details</summary>
                    <div className="mt-3 text-sm">
                      <pre className="text-xs whitespace-pre-wrap">
                        {JSON.stringify(report.validation, null, 2)}
                      </pre>
                    </div>
                  </details>
                </div>

                {/* Download */}
                <div className="rounded-xl border p-3">
                  <h3 className="font-semibold mb-2">Download</h3>
                  <a
                    className="text-sm underline"
                    href={`data:application/json;charset=utf-8,${encodeURIComponent(
                      JSON.stringify(report, null, 2)
                    )}`}
                    download="report.json"
                  >
                    Download report.json
                  </a>
                </div>
              </div>
            )}
          </section>
        </div>
      </div>
    </main>
  );
}
