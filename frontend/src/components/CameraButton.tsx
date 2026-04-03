"use client";
/**
 * CameraButton — Opens the device camera (or file picker) to capture a receipt photo.
 * Shows a confirmation modal with photo preview before sending to the AI.
 */

import { useCallback, useRef, useState } from "react";
import type { ImageChatResponse } from "@/lib/types";
import { sendImageChat } from "@/lib/api";

interface CameraButtonProps {
  language: string;
  onResponse: (res: ImageChatResponse) => void;
  onError: (msg: string) => void;
  disabled?: boolean;
}

type CameraState = "idle" | "preview" | "sending";

export default function CameraButton({
  language,
  onResponse,
  onError,
  disabled = false,
}: CameraButtonProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [cameraState, setCameraState] = useState<CameraState>("idle");
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const handleFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (!file) return;

      setSelectedFile(file);
      const url = URL.createObjectURL(file);
      setPreviewUrl(url);
      setCameraState("preview");

      // Reset input so the same file can be re-selected
      e.target.value = "";
    },
    []
  );

  const handleConfirm = useCallback(async () => {
    if (!selectedFile) return;
    setCameraState("sending");

    try {
      const res = await sendImageChat(selectedFile, undefined, language);
      onResponse(res);
    } catch (e) {
      onError(e instanceof Error ? e.message : "Image processing failed.");
    } finally {
      // Clean up
      if (previewUrl) URL.revokeObjectURL(previewUrl);
      setPreviewUrl(null);
      setSelectedFile(null);
      setCameraState("idle");
    }
  }, [selectedFile, language, onResponse, onError, previewUrl]);

  const handleCancel = useCallback(() => {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setPreviewUrl(null);
    setSelectedFile(null);
    setCameraState("idle");
  }, [previewUrl]);

  return (
    <>
      {/* Camera trigger button */}
      <button
        type="button"
        onClick={() => fileInputRef.current?.click()}
        disabled={disabled || cameraState !== "idle"}
        aria-label="Take a photo of a receipt or note"
        className={`
          h-14 w-14 rounded-full flex items-center justify-center
          border-2 transition-all duration-200
          ${
            disabled || cameraState !== "idle"
              ? "border-border text-text-disabled bg-gray-50 cursor-not-allowed"
              : "border-accent-800 text-accent-800 bg-accent-light hover:bg-accent-800 hover:text-white active:scale-95 shadow-sm"
          }
        `}
      >
        <CameraIcon />
      </button>

      {/* Hidden file input — opens camera on mobile */}
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        capture="environment"
        className="sr-only"
        onChange={handleFileChange}
        aria-hidden="true"
      />

      {/* Preview Modal */}
      {cameraState === "preview" || cameraState === "sending" ? (
        <PhotoModal
          previewUrl={previewUrl}
          isSending={cameraState === "sending"}
          onConfirm={handleConfirm}
          onCancel={handleCancel}
        />
      ) : null}
    </>
  );
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function PhotoModal({
  previewUrl,
  isSending,
  onConfirm,
  onCancel,
}: {
  previewUrl: string | null;
  isSending: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/60 backdrop-blur-sm animate-fade-in"
      role="dialog"
      aria-modal="true"
      aria-label="Photo confirmation"
    >
      <div className="bg-white rounded-t-3xl sm:rounded-2xl w-full max-w-sm mx-0 sm:mx-4 shadow-2xl overflow-hidden">
        {/* Preview image */}
        {previewUrl && (
          <div className="relative bg-black max-h-64 overflow-hidden">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={previewUrl}
              alt="Receipt preview"
              className="w-full max-h-64 object-contain"
            />
          </div>
        )}

        <div className="px-5 py-4">
          <p className="text-base font-semibold text-text-primary mb-1">
            Use this photo?
          </p>
          <p className="text-sm text-text-secondary mb-4">
            Susu Books will read the receipt and record the transactions.
          </p>

          <div className="flex gap-3">
            <button
              type="button"
              onClick={onCancel}
              disabled={isSending}
              className="
                flex-1 py-3 rounded-xl border-2 border-border text-sm font-semibold
                text-text-secondary hover:border-text-secondary transition-colors
                disabled:opacity-50 disabled:cursor-not-allowed
              "
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={onConfirm}
              disabled={isSending}
              className="
                flex-1 py-3 rounded-xl bg-primary-900 text-white text-sm font-semibold
                hover:bg-primary-700 active:scale-95 transition-all
                disabled:opacity-50 disabled:cursor-not-allowed
                flex items-center justify-center gap-2
              "
            >
              {isSending ? (
                <>
                  <span className="h-4 w-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                  Scanning…
                </>
              ) : (
                "Read Receipt"
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function CameraIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      className="h-6 w-6"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z" />
      <circle cx="12" cy="13" r="4" />
    </svg>
  );
}
