// web/lib/api.ts
export type Inputs = {
  catalog_path: string;
  goal: "cs" | "pre_med" | "biotech";
  starting_math: string;
  science_pathway: string;
  prefer_spanish: boolean;
  completed_courses: string[];
  gpa: { default_letter: "A" | "B" | "C"; overrides: Record<string, string> };
  uc_cfg: { max_bonus_semesters: number; honors_keywords: string[] };
  completed_math?: string | null;
  course_level_prefs?: {
    english?: "regular" | "honors" | "ap";
    history?: "regular" | "honors" | "ap";
    science?: "regular" | "honors" | "ap";
  };
};

export async function generatePlan(inputs: Inputs) {
  // Call SAME ORIGIN route handler (Next.js) which proxies to FastAPI
  const res = await fetch("/api/generate", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(inputs),
  });

  const text = await res.text();

  if (!res.ok) {
    // Make the UI show something helpful
    throw new Error(`HTTP ${res.status}: ${text}`);
  }

  try {
    return JSON.parse(text);
  } catch {
    throw new Error(`Invalid JSON from server: ${text}`);
  }
}
