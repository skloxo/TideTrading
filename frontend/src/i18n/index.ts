import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import LanguageDetector from "i18next-browser-languagedetector";
import en from "./locales/en.json";
import zhCN from "./locales/zh-CN.json";

// Language registry — only Chinese and English are supported.
export const SUPPORTED_LANGUAGES = [
  { code: "en", label: "English", dir: "ltr" as const },
  { code: "zh-CN", label: "中文", dir: "ltr" as const },
] as const;

export type SupportedLanguageCode = (typeof SUPPORTED_LANGUAGES)[number]["code"];

export function isRtl(_code: string): boolean {
  return false;
}

export function applyDocumentDirection(code: string): void {
  if (typeof document === "undefined") return;
  document.documentElement.setAttribute("dir", "ltr");
  document.documentElement.setAttribute("lang", code);
}

if (typeof window !== "undefined" && !localStorage.getItem("i18nextLng")) {
  localStorage.setItem("i18nextLng", "zh-CN");
}

const isTest = typeof (globalThis as any).process !== "undefined" && (globalThis as any).process.env?.VITEST;

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    lng: isTest ? "en" : undefined,
    resources: {
      en: { translation: en },
      "zh-CN": { translation: zhCN },
    },
    // Default to Chinese (zh-CN) for all new visitors.
    fallbackLng: isTest ? "en" : "zh-CN",
    supportedLngs: SUPPORTED_LANGUAGES.map((l) => l.code),
    interpolation: { escapeValue: false },
    detection: {
      order: typeof window !== "undefined"
        ? ["localStorage", "navigator"]
        : ["localStorage"],
      caches: ["localStorage"],
      lookupLocalStorage: "i18nextLng",
    },
  });

applyDocumentDirection(i18n.language || "en");
i18n.on("languageChanged", (lng) => applyDocumentDirection(lng));
i18n.on("initialized", () => {
  if (i18n.language) applyDocumentDirection(i18n.language);
});

export default i18n;
