import type { ComponentProps } from "react";

export type PriorityLevel = "1" | "2" | "3" | "4" | "5";

type PriorityLevelsProps = ComponentProps<"div"> & {
  property1?: PriorityLevel;
};

const priorityStyles: Record<PriorityLevel, { background: string; foreground: string; label: string }> = {
  "1": { background: "bg-[#d5f4ff]", foreground: "text-[#179fd0]", label: "1 Low" },
  "2": { background: "bg-[#f5edbf]", foreground: "text-[#cdb946]", label: "2 Moderate" },
  "3": { background: "bg-[#ffcda2]", foreground: "text-[#d47725]", label: "3 In Need" },
  "4": { background: "bg-[#fda98f]", foreground: "text-[#d02828]", label: "4 Urgent" },
  "5": { background: "bg-[#d75757]", foreground: "text-[#790f0f]", label: "5 Immediate" },
};

export function PriorityLevels({ className, property1 = "1", ...props }: PriorityLevelsProps) {
  const style = priorityStyles[property1];

  return (
    <div className={`flex h-[26px] w-[96px] items-center justify-center overflow-clip rounded-[14px] px-2 py-1 ${style.background} ${className ?? ""}`} {...props}>
      <p className={`whitespace-nowrap text-[12px] font-medium leading-normal ${style.foreground}`}>{style.label}</p>
    </div>
  );
}
