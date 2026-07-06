import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import LanguageDetector from "i18next-browser-languagedetector";
import en from "./locales/en.json";
import zhCN from "./locales/zh-CN.json";

if (typeof window !== "undefined" && !localStorage.getItem("i18nextLng")) {
  localStorage.setItem("i18nextLng", "zh-CN");
}

const isTest = typeof process !== "undefined" && process.env.VITEST;

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
    // If the user explicitly switches to English via the language toggle,
    // that choice is persisted to localStorage and respected on return visits.
    fallbackLng: isTest ? "en" : "zh-CN",
    interpolation: { escapeValue: false },
    detection: {
      order: ["localStorage"],
      lookupLocalStorage: "i18nextLng",
      caches: ["localStorage"],
    },
  });

export default i18n;
