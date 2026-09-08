"use client";

import { useCallback, useRef, useState } from "react";

interface UploadZoneProps {
  acceptedExtensions: string[];
  files: File[];
  onFilesChange: (files: File[]) => void;
  disabled: boolean;
}

// File selection only -- drag/drop, picker, remove, clear. Processing
// itself is triggered by the caller's own Run button, not here.
export default function UploadZone({ acceptedExtensions, files, onFilesChange, disabled }: UploadZoneProps) {
  const [isDragOver, setIsDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const addFiles = useCallback(
    (incoming: FileList | File[]) => {
      const merged = [...files, ...Array.from(incoming)];
      // De-duplicate by name+size so dropping the same file twice is a no-op.
      const seen = new Set<string>();
      const unique = merged.filter((file) => {
        const key = `${file.name}:${file.size}`;
        if (seen.has(key)) return false;
        seen.add(key);
        return true;
      });
      onFilesChange(unique);
    },
    [files, onFilesChange],
  );

  const acceptAttr = acceptedExtensions.length > 0 ? acceptedExtensions.join(",") : undefined;

  return (
    <div>
      <div
        onDragOver={(event) => {
          event.preventDefault();
          if (!disabled) setIsDragOver(true);
        }}
        onDragLeave={() => setIsDragOver(false)}
        onDrop={(event) => {
          event.preventDefault();
          setIsDragOver(false);
          if (!disabled && event.dataTransfer.files.length > 0) {
            addFiles(event.dataTransfer.files);
          }
        }}
        onClick={() => !disabled && inputRef.current?.click()}
        role="button"
        tabIndex={0}
        aria-disabled={disabled}
        className={`flex flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed px-6 py-10 text-center transition-colors ${
          disabled
            ? "cursor-not-allowed border-slate-200 bg-slate-50 text-slate-400"
            : isDragOver
              ? "cursor-pointer border-slate-500 bg-slate-50 text-slate-700"
              : "cursor-pointer border-slate-300 text-slate-600 hover:border-slate-400 hover:bg-slate-50"
        }`}
      >
        <p className="text-sm font-medium">Drop W-2 files here</p>
        <p className="text-xs text-slate-500">or</p>
        <span className="rounded-md bg-slate-900 px-3 py-1.5 text-xs font-medium text-white">
          Choose Files
        </span>
        <p className="mt-1 text-xs text-slate-400">
          Supported: {acceptedExtensions.join(", ") || "loading…"}
        </p>
        <input
          ref={inputRef}
          type="file"
          multiple
          accept={acceptAttr}
          disabled={disabled}
          className="hidden"
          onChange={(event) => {
            if (event.target.files) addFiles(event.target.files);
            event.target.value = "";
          }}
        />
      </div>

      {files.length > 0 && (
        <div className="mt-3 space-y-2">
          <div className="flex items-center justify-between">
            <p className="text-sm text-slate-600">
              {files.length} file{files.length === 1 ? "" : "s"} selected
            </p>
            <button
              type="button"
              disabled={disabled}
              onClick={() => onFilesChange([])}
              className="text-xs font-medium text-slate-500 hover:text-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Clear all
            </button>
          </div>
          <ul className="max-h-40 space-y-1 overflow-y-auto rounded-md border border-slate-200 p-2">
            {files.map((file, index) => (
              <li
                key={`${file.name}:${file.size}:${index}`}
                className="flex items-center justify-between rounded px-2 py-1 text-sm text-slate-700 hover:bg-slate-50"
              >
                <span className="truncate">{file.name}</span>
                <button
                  type="button"
                  disabled={disabled}
                  onClick={() => onFilesChange(files.filter((_, i) => i !== index))}
                  className="ml-2 shrink-0 text-slate-400 hover:text-red-600 disabled:cursor-not-allowed disabled:opacity-50"
                  aria-label={`Remove ${file.name}`}
                >
                  ✕
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
