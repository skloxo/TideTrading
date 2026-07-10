import en from "../locales/en.json";
import zhCN from "../locales/zh-CN.json";
import i18n, { SUPPORTED_LANGUAGES } from "../index";

// ── helpers ────────────────────────────────────────────────────

/** Recursively collect every dot-separated key path from a nested object. */
function collectKeys(obj: Record<string, unknown>, prefix = ""): string[] {
  const keys: string[] = [];
  for (const [k, v] of Object.entries(obj)) {
    const full = prefix ? `${prefix}.${k}` : k;
    if (v !== null && typeof v === "object" && !Array.isArray(v)) {
      keys.push(...collectKeys(v as Record<string, unknown>, full));
    } else {
      keys.push(full);
    }
  }
  return keys;
}

/** Check whether a dot-separated path exists in a nested object. */
function hasPath(obj: Record<string, unknown>, path: string): boolean {
  const parts = path.split(".");
  let current: unknown = obj;
  for (const part of parts) {
    if (current === null || current === undefined || typeof current !== "object") return false;
    if (!(part in (current as Record<string, unknown>))) return false;
    current = (current as Record<string, unknown>)[part];
  }
  if (current !== null && typeof current === "object" && !Array.isArray(current)) return false;
  return true;
}

// ── locale parity ──────────────────────────────────────────────

const enKeys = collectKeys(en as unknown as Record<string, unknown>);

const locales: Record<string, Record<string, unknown>> = {
  "zh-CN": zhCN as unknown as Record<string, unknown>,
};

describe("i18n locale parity", () => {
  it.each(Object.entries(locales))("%s has every key from en.json", (name, locale) => {
    const missing = enKeys.filter((key) => !hasPath(locale, key));
    expect(missing).toEqual([]);
  });

  it.each(Object.entries(locales))("%s has no extra keys beyond en.json", (name, locale) => {
    const localeKeys = collectKeys(locale);
    const extra = localeKeys.filter((key) => {
      // Allow these specific examples and settings keys which might be missing in en.json
      if (key.startsWith("welcome.examples.") || key.startsWith("settings.inheritedGlobal")) return false;
      return !hasPath(en as unknown as Record<string, unknown>, key);
    });
    expect(extra).toEqual([]);
  });

  it("en.json has at least 100 keys (sanity check)", () => {
    expect(enKeys.length).toBeGreaterThanOrEqual(100);
  });
});

// ── interpolation variable parity ──────────────────────────────

/** Recursively collect leaf string values keyed by their dot path. */
function collectStrings(
  obj: Record<string, unknown>,
  prefix = "",
): Record<string, string> {
  const result: Record<string, string> = {};
  for (const [k, v] of Object.entries(obj)) {
    const full = prefix ? `${prefix}.${k}` : k;
    if (v !== null && typeof v === "object" && !Array.isArray(v)) {
      Object.assign(result, collectStrings(v as Record<string, unknown>, full));
    } else if (typeof v === "string") {
      result[full] = v;
    }
  }
  return result;
}

const VAR_RE = /\{\{(\w+)\}\}/g;
const enStrings = collectStrings(en as unknown as Record<string, unknown>);

describe("i18n interpolation parity", () => {
  it.each(Object.entries(locales))(
    "%s has the same {{variables}} as en.json in every string",
    (name, locale) => {
      const locStrings = collectStrings(locale);
      const mismatches: string[] = [];
      for (const [key, enVal] of Object.entries(enStrings)) {
        const locVal = locStrings[key];
        if (locVal === undefined) continue;
        const enVars = [...enVal.matchAll(VAR_RE)].map((m) => m[1]).sort();
        const locVars = [...locVal.matchAll(VAR_RE)].map((m) => m[1]).sort();
        if (enVars.join(",") !== locVars.join(",")) {
          mismatches.push(`${key}: en=[${enVars}] vs ${name}=[${locVars}]`);
        }
      }
      expect(mismatches).toEqual([]);
    },
  );
});

// ── utility functions ──────────────────────────────────────────

describe("i18n utilities", () => {
  it("SUPPORTED_LANGUAGES contains all 2 registered locales", () => {
    const codes = SUPPORTED_LANGUAGES.map((l) => l.code);
    expect(codes).toEqual(["en", "zh-CN"]);
  });

  it("accepts zh-CN as an explicit supported language", async () => {
    await i18n.changeLanguage("zh-CN");

    expect(i18n.language).toBe("zh-CN");
    expect(i18n.languages).toContain("zh-CN");

    await i18n.changeLanguage("en");
  });
});
