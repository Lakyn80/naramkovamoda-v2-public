"use client";

type ToastTone = "success" | "error" | "info";

const toneStyles: Record<ToastTone, string> = {
  success: "bg-emerald-600",
  error: "bg-red-600",
  info: "bg-blue-600",
};

export function Toast({ message, tone = "info", onClose }: { message: string; tone?: ToastTone; onClose?: () => void }) {
  return (
    <div className={`flex items-start gap-3 rounded-lg px-4 py-3 text-sm text-white shadow-lg ${toneStyles[tone]}`}>
      <span className="flex-1">{message}</span>
      {onClose && (
        <button type="button" onClick={onClose} className="text-white/80 hover:text-white">
          ✕
        </button>
      )}
    </div>
  );
}
