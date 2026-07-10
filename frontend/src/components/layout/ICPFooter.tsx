import { useTranslation } from "react-i18next";

export function ICPFooter({ className = "" }: { className?: string }) {
  const { i18n } = useTranslation();
  const isZh = i18n.language === "zh-CN";

  return (
    <div className={`text-[10px] text-muted-foreground/50 flex flex-col items-center gap-0.5 ${className}`}>
      <a
        href="https://beian.miit.gov.cn/"
        target="_blank"
        rel="noopener noreferrer"
        className="hover:text-primary transition"
      >
        粤ICP备2026092741号
      </a>
      <span>
        {isZh ? "联系邮箱：" : "Email: "}{" "}
        <a href="mailto:help@tide.red" className="hover:text-primary transition font-mono">
          help@tide.red
        </a>
      </span>
    </div>
  );
}
